"""
Servicio de Inferencia en Tiempo Real.

Conserva el estado de los modelos y genera predicciones cada 1 minuto
basándose en los datos de Iceberg y Redis.
"""
import os
import time
import torch
import json
import pandas as pd
from src.ml.models import TemporalFusionTransformer, get_device, CouncilOfAgents
from src.serving.api.utils import get_iceberg_catalog, get_redis_client


def run_inference():
    device = get_device()
    redis = get_redis_client()

    # Cargar Memoria Histórica (Actualizado a input_dim=2)
    model_hist = TemporalFusionTransformer(input_dim=2).to(device)
    if os.path.exists("models/tft_historical.pth"):
        model_hist.load_state_dict(torch.load(
            "models/tft_historical.pth", map_location=device))
        print("✅ Memoria HISTORICA cargada (v2).")

    # Cargar Memoria Reciente (Actualizado a input_dim=2)
    model_recent = TemporalFusionTransformer(input_dim=2).to(device)
    if os.path.exists("models/tft_recent.pth"):
        model_recent.load_state_dict(torch.load(
            "models/tft_recent.pth", map_location=device))
        print("✅ Memoria RECIENTE cargada (v2).")

    model_hist.eval()
    model_recent.eval()

    print("🤖 Servicio de Inferencia (Dual Memory) Iniciado...")

    while True:
        try:
            btc_data = []
            # 1. Intentar obtener últimos datos de Iceberg
            try:
                catalog = get_iceberg_catalog()
                table = catalog.load_table("silver.realtime_vwap")
                df_raw = table.scan().to_arrow().to_pylist()
                btc_data = [r for r in df_raw if r["coin_id"] == "bitcoin"]
                btc_data = sorted(btc_data, key=lambda x: x["window_start"])
                # Mapear nombres de columnas si vienen de Iceberg
                for r in btc_data:
                    r["close"] = r.get("close", 0)
                    r["total_volume"] = r.get("total_volume", 0)
            except Exception:
                # Fallback a local cache
                local_path = "data/local_cache/silver_daily_prices.csv"
                if os.path.exists(local_path):
                    df = pd.read_csv(local_path)
                    btc_raw = df[df["coin_id"] == "bitcoin"].to_dict("records")
                    for r in btc_raw:
                        btc_data.append({
                            "close": r["price_usd"],
                            "total_volume": r["volume_24h_usd"]
                        })

            if len(btc_data) < 10:
                print("⌛ Esperando más datos de Bitcoin en Iceberg...")
                time.sleep(10)
                continue

            prices = [r["close"] for r in btc_data[-10:]]
            volumes = [r["total_volume"] for r in btc_data[-10:]]
            current_p = prices[-1]

            # 2. Opinion de Agentes (Añadir dinamismo)
            # Simular RSI basado en los últimos 10
            diff = [prices[i] - prices[i-1] for i in range(1, len(prices))]
            gains = sum([d for d in diff if d > 0])
            losses = abs(sum([d for d in diff if d < 0]))
            rsi_bias = 0.5 if gains > losses else -0.5

            # Obtener Fear & Greed si es posible
            fg_bias = 0.0
            try:
                fg_table = catalog.load_table("bronze.fear_greed_index")
                fg_data = fg_table.scan(limit=1).to_arrow().to_pylist()
                if fg_data:
                    fg_bias = CouncilOfAgents.sentiment_agent(
                        int(fg_data[0]["value"]))
            except:
                pass

            # 3. Preparar inputs reales (Normalizados para multivariado [Precio, Volumen])
            p_min, p_max = min(prices), max(prices)
            p_denom = (p_max - p_min) if p_max > p_min else 1.0
            prices_norm = [(p - p_min) / p_denom for p in prices]

            v_min, v_max = min(volumes), max(volumes)
            v_denom = (v_max - v_min) if v_max > v_min else 1.0
            volumes_norm = [(v - v_min) / v_denom for v in volumes]

            # Stack multivariate data: [1, 10, 2]
            feats = [[p, v] for p, v in zip(prices_norm, volumes_norm)]
            x = torch.tensor(feats).unsqueeze(0).to(device)

            # Agentes: [RSI_Bias, Sentiment_Bias]
            a_op = torch.tensor([[rsi_bias, fg_bias]]).to(device)

            # 4. Inferencia Dual
            with torch.no_grad():
                pred_h = model_hist(x, x, a_op).item()
                pred_r = model_recent(x, x, a_op).item()

                # Combinación: 80% Reciente (Sensibilidad) + 20% Histórica
                pred_norm = (pred_r * 0.8) + (pred_h * 0.2)

                # Seguridad: Limitar la predicción normalizada para evitar explosiones (clipping)
                # Si el modelo se vuelve loco, esto lo mantiene en un rango razonable respecto al histórico
                pred_norm = max(-0.5, min(1.5, pred_norm))

                # De-normalizar usando el rango del precio
                pred_final = (pred_norm * p_denom) + p_min

                # Seguridad Extra: No permitir variaciones bruscas (>10% en una predicción)
                max_change = current_p * 0.10
                if pred_final > current_p + max_change:
                    pred_final = current_p + max_change
                elif pred_final < current_p - max_change:
                    pred_final = current_p - max_change

            # 5. Publicar en Redis
            result = {
                "timestamp": time.time(),
                "predicted_price": float(pred_final),
                "current_price": float(current_p),
                "memory_details": {
                    "historical": float(pred_h),
                    "recent": float(pred_r)
                },
                "sentiment_bias": "Bullish" if pred_final > current_p else "Bearish"
            }

            redis.set("live_prediction", json.dumps(result))
            print(
                f"✅ Predicción generada: {result['sentiment_bias']} ({pred_final:.2f})")

        except Exception as e:
            print(f"❌ Error en inferencia: {e}")

        time.sleep(30)  # Loop cada 30 segundos


if __name__ == "__main__":
    run_inference()
