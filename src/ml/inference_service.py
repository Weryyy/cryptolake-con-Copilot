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
    catalog = get_iceberg_catalog()

    # Cargar Memoria Histórica
    model_hist = TemporalFusionTransformer(input_dim=1).to(device)
    if os.path.exists("models/tft_historical.pth"):
        model_hist.load_state_dict(torch.load(
            "models/tft_historical.pth", map_location=device))
        print("✅ Memoria HISTORICA cargada.")

    # Cargar Memoria Reciente
    model_recent = TemporalFusionTransformer(input_dim=1).to(device)
    if os.path.exists("models/tft_recent.pth"):
        model_recent.load_state_dict(torch.load(
            "models/tft_recent.pth", map_location=device))
        print("✅ Memoria RECIENTE cargada.")

    model_hist.eval()
    model_recent.eval()

    print("🤖 Servicio de Inferencia (Dual Memory) Iniciado...")

    while True:
        try:
            # 1. Obtener últimos datos (Filtramos por Bitcoin para el PoC)
            table = catalog.load_table("silver.realtime_vwap")
            # Escaneamos más para asegurar que tenemos suficientes de la misma moneda
            df_raw = table.scan().to_arrow().to_pylist()

            # Filtramos los últimos 10 de Bitcoin
            btc_data = [r for r in df_raw if r["coin_id"] == "bitcoin"]
            btc_data = sorted(btc_data, key=lambda x: x["window_start"])

            if len(btc_data) < 10:
                print("⌛ Esperando más datos de Bitcoin en Iceberg...")
                time.sleep(10)
                continue

            prices = [r["close"] for r in btc_data[-10:]]
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

            # 3. Preparar inputs reales (Normalizados)
            p_min, p_max = min(prices), max(prices)
            denom = (p_max - p_min) if p_max > p_min else 1.0
            prices_norm = [(p - p_min) / denom for p in prices]

            x = torch.tensor(prices_norm).view(1, 10, 1).to(device)
            # Agentes: [RSI_Bias, Sentiment_Bias]
            a_op = torch.tensor([[rsi_bias, fg_bias]]).to(device)

            # 4. Inferencia Dual
            with torch.no_grad():
                pred_h = model_hist(x, x, a_op).item()
                pred_r = model_recent(x, x, a_op).item()

                # Combinación: 80% Reciente (Sensibilidad) + 20% Histórica
                # Añadimos un pequeño factor de volatilidad para que no sea plana
                pred_norm = (pred_r * 0.8) + (pred_h * 0.2)

                # De-normalizar
                pred_final = (pred_norm * denom) + p_min

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
