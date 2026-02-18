"""
Seed Data: Genera datos sintéticos en la capa Silver para permitir el entrenamiento.
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def seed_silver_prices():
    print("🌱 Sembrando datos sintéticos para entrenamiento local...")

    data = []
    start_date = datetime.now() - timedelta(days=100)

    # Generar tendencia alcista con volatilidad para Bitcoin
    price = 40000.0
    vol = 1500000000.0

    for i in range(100):
        current_date = (start_date + timedelta(days=i)).date()
        price *= (1 + np.random.normal(0.001, 0.015))  # Random walk
        vol *= (1 + np.random.normal(0.005, 0.05))

        data.append({
            "coin_id": "bitcoin",
            "price_date": current_date,
            "price_usd": float(price),
            "volume_24h_usd": float(vol),
            "market_cap_usd": float(price * 19000000),
            "price_change_pct_1d": 0.5
        })

    df = pd.DataFrame(data)
    os.makedirs("data/local_cache", exist_ok=True)
    df.to_csv("data/local_cache/silver_daily_prices.csv", index=False)
    print(
        f"✅ Datos guardados en data/local_cache/silver_daily_prices.csv ({len(df)} filas)")


if __name__ == "__main__":
    seed_silver_prices()
