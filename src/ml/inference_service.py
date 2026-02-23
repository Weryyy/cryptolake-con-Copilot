"""
Servicio de Inferencia en Tiempo Real.

Genera predicciones cada 30 segundos usando:
- Modelo TFT con 4 features: [precio, volumen, RSI, SMA_ratio]
- Señales de agentes REALES: [técnica (RSI+SMA), sentimiento (F&G)]
- Ensemble dual: 80% reciente + 20% histórico

Optimizado para CPU (Xeon E5-1620 v3).
"""
import os
import time
import torch
import json
import numpy as np
from src.ml.models import (
    TemporalFusionTransformer,
    CouncilOfAgents,
    compute_rsi,
    compute_sma,
    get_device,
)
from src.serving.api.utils import get_iceberg_catalog, get_redis_client


def load_model(path, device):
    """Carga un modelo TFT con la nueva arquitectura (input_dim=4)."""
    model = TemporalFusionTransformer(input_dim=4, agent_dim=2).to(device)
    if os.path.exists(path):
        model.load_state_dict(torch.load(path, map_location=device))
        print(f"✅ Modelo cargado: {path}")
    else:
        print(f"⚠️ Modelo no encontrado: {path} (usando pesos aleatorios)")
    model.eval()
    return model


def get_btc_data(catalog):
    """Obtiene últimos datos BTC de Iceberg con filtro optimizado."""
    table = catalog.load_table("silver.realtime_vwap")
    table.refresh()

    from datetime import datetime, timezone, timedelta
    since = datetime.now(timezone.utc) - timedelta(hours=2)
    row_filter = f"coin_id == 'bitcoin' AND window_start >= '{since.isoformat()}'"

    df = table.scan(
        row_filter=row_filter,
        selected_fields=("window_start", "close", "total_volume"),
    ).to_arrow().to_pylist()

    return sorted(df, key=lambda x: str(x["window_start"]))


def get_fear_greed(catalog):
    """Obtiene último Fear & Greed value."""
    try:
        table = catalog.load_table("bronze.fear_greed_index")
        rows = table.scan(
            selected_fields=("value", "timestamp"),
        ).to_arrow().to_pylist()
        if rows:
            latest = sorted(rows, key=lambda x: x["timestamp"], reverse=True)[0]
            return int(latest["value"])
    except Exception:
        pass
    return 50


def build_inference_features(prices, volumes, window_size=10):
    """Construye el tensor de 4 features para inferencia.

    Mismo pipeline que en training para consistencia.
    """
    prices = np.asarray(prices, dtype=np.float64)
    volumes = np.asarray(volumes, dtype=np.float64)

    # Indicadores
    rsi_period = min(14, max(3, len(prices) // 3))
    rsi = compute_rsi(prices, period=rsi_period)
    sma_short = compute_sma(prices, min(5, len(prices)))
    sma_long = compute_sma(prices, min(10, len(prices)))

    sma_ratio = np.where(
        sma_long > 0,
        (sma_short / (sma_long + 1e-10)) - 1.0,
        0.0,
    )

    # Normalización
    p_min, p_max = prices.min(), prices.max()
    p_denom = p_max - p_min if p_max > p_min else 1.0
    prices_norm = (prices - p_min) / p_denom

    v_min, v_max = volumes.min(), volumes.max()
    v_denom = v_max - v_min if v_max > v_min else 1.0
    volumes_norm = (volumes - v_min) / v_denom

    rsi_norm = np.nan_to_num(rsi, nan=50.0) / 100.0
    sma_ratio_clipped = np.clip(sma_ratio * 10, -1.0, 1.0)

    # Tomar última ventana
    feats = np.stack([
        prices_norm[-window_size:],
        volumes_norm[-window_size:],
        rsi_norm[-window_size:],
        sma_ratio_clipped[-window_size:],
    ], axis=1)  # [window_size, 4]

    return feats, p_min, p_max, p_denom


def run_inference():
    device = get_device()
    torch.set_num_threads(min(4, os.cpu_count() or 4))
    redis = get_redis_client()

    # Cargar modelos con nueva arquitectura
    model_hist = load_model("models/tft_historical.pth", device)
    model_recent = load_model("models/tft_recent.pth", device)

    print("🤖 Servicio de Inferencia v2 (Dual Memory + Real Agents) Iniciado...")

    catalog = get_iceberg_catalog()
    consecutive_errors = 0

    while True:
        try:
            # 1. Obtener datos recientes de BTC
            btc_data = get_btc_data(catalog)

            if len(btc_data) < 15:
                print(f"⌛ Esperando más datos BTC ({len(btc_data)}/15)...")
                time.sleep(10)
                continue

            prices = [r["close"] for r in btc_data[-30:]]  # últimos 30 puntos
            volumes = [r["total_volume"] for r in btc_data[-30:]]
            current_price = prices[-1]

            # 2. Señales de agentes REALES
            fg_val = get_fear_greed(catalog)
            tech_signal = CouncilOfAgents.technical_agent(prices)
            sent_signal = CouncilOfAgents.sentiment_agent(fg_val)

            # 3. Feature engineering (mismo pipeline que training)
            feats, p_min, p_max, p_denom = build_inference_features(
                prices, volumes, window_size=10
            )

            x = torch.tensor(feats, dtype=torch.float32).unsqueeze(0).to(device)
            a_op = torch.tensor([[tech_signal, sent_signal]], dtype=torch.float32).to(device)

            # 4. Inferencia dual
            with torch.no_grad():
                pred_h = model_hist(x, x, a_op).item()
                pred_r = model_recent(x, x, a_op).item()

                # Ensemble: 80% reciente + 20% histórico
                pred_norm = pred_r * 0.8 + pred_h * 0.2

                # Clip normalizado
                pred_norm = max(-0.5, min(1.5, pred_norm))

                # De-normalizar
                pred_final = (pred_norm * p_denom) + p_min

                # Safety: max ±10% change
                max_change = current_price * 0.10
                pred_final = np.clip(
                    pred_final,
                    current_price - max_change,
                    current_price + max_change,
                )

            # 5. Publicar en Redis
            result = {
                "timestamp": time.time(),
                "coin_id": "bitcoin",
                "predicted_price": float(pred_final),
                "current_price": float(current_price),
                "memory_details": {
                    "historical": float(pred_h),
                    "recent": float(pred_r),
                },
                "agents": {
                    "technical": float(tech_signal),
                    "sentiment": float(sent_signal),
                    "fear_greed": fg_val,
                },
                "sentiment_bias": "Bullish" if pred_final > current_price else "Bearish",
            }

            redis.set("live_prediction", json.dumps(result))
            diff_pct = ((pred_final - current_price) / current_price) * 100
            print(
                f"✅ ${pred_final:,.2f} ({diff_pct:+.2f}%) "
                f"| bias={result['sentiment_bias']} "
                f"| tech={tech_signal:+.2f} sent={sent_signal:+.2f} "
                f"| h={pred_h:.4f} r={pred_r:.4f}"
            )
            consecutive_errors = 0

        except Exception as e:
            consecutive_errors += 1
            print(f"❌ Error inferencia ({consecutive_errors}): {e}")
            if consecutive_errors > 5:
                print("⚠️ Demasiados errores consecutivos, esperando 60s...")
                time.sleep(60)
                consecutive_errors = 0

        time.sleep(30)


if __name__ == "__main__":
    run_inference()
