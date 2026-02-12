"""
Entrenamiento del Modelo CryptoLake.

Este script lee datos de Iceberg (Capa Silver), entrena el modelo TFT
y guarda los pesos en el directorio /models.
"""
import torch
import torch.nn as nn
import torch.optim as optim
import pandas as pd
import numpy as np
from src.ml.models import TemporalFusionTransformer, get_device
from src.serving.api.utils import get_iceberg_catalog


def load_training_data(coin_id="bitcoin", days=None):
    """Carga datos historicos de Iceberg para entrenamiento."""
    catalog = get_iceberg_catalog()
    try:
        table = catalog.load_table("silver.daily_prices")

        # Filtro opcional por dias (para memoria reciente)
        if days:
            from datetime import date, timedelta
            start_date = date.today() - timedelta(days=days)
            row_filter = f"coin_id == '{coin_id}' AND price_date >= '{start_date}'"
        else:
            row_filter = f"coin_id == '{coin_id}'"

        df = table.scan(row_filter=row_filter).to_arrow().to_pandas()
        df = df.sort_values("price_date")
        return df
    except Exception as e:
        print(f"❌ Error cargando datos de Iceberg: {e}")
        return None


def train(mode="historical"):
    """
    mode: 'historical' (todo) o 'recent' (ultimos 15 dias)
    """
    device = get_device()
    days = 15 if mode == "recent" else None
    df = load_training_data(days=days)

    if df is None or len(df) < 10:
        print(
            f"⚠️ No hay suficientes datos para modo {mode}. Ingiere mas precios.")
        return

    print(f"🧠 Entrenando modelo MEMORIA: {mode.upper()} ({len(df)} dias)")
    # En un caso real usariamos mas features y MinMaxScaler
    data = df["price_usd"].values.astype(np.float32)
    data_norm = (data - data.min()) / (data.max() - data.min())

    # Crear secuencias (X: 10 dias, Y: siguiente dia)
    X, Y = [], []
    for i in range(len(data_norm)-11):
        X.append(data_norm[i:i+10])
        Y.append(data_norm[i+10])

    X = torch.tensor(X).unsqueeze(-1).to(device)  # [Batch, Seq, Features]
    Y = torch.tensor(Y).unsqueeze(-1).to(device)

    # Inicializar modelo
    model = TemporalFusionTransformer(input_dim=1).to(device)
    lr = 0.02 if mode == "recent" else 0.005
    optimizer = optim.Adam(model.parameters(), lr=lr)
    criterion = nn.MSELoss()

    print(f"🚀 Empezando entrenamiento con {len(X)} secuencias...")
    model.train()
    epochs = 100 if mode == "recent" else 50
    for epoch in range(epochs):
        optimizer.zero_grad()
        # El modelo espera (x_long, x_short, agents)
        # Por ahora pasamos la misma secuencia para ambos
        output = model(X, X, torch.zeros(len(X), 2).to(device))
        loss = criterion(output, Y)
        loss.backward()
        optimizer.step()

        if epoch % 10 == 0:
            print(f"Epoch {epoch} | Loss: {loss.item():.6f}")

    # Guardar modelo con el prefijo del modo
    os.makedirs("models", exist_ok=True)
    save_path = f"models/tft_{mode}.pth"
    torch.save(model.state_dict(), save_path)
    print(f"✅ Modelo {mode} guardado en {save_path}")


if __name__ == "__main__":
    import os
    import sys

    # Permitir pasar el modo como argumento
    mode = sys.argv[1] if len(sys.argv) > 1 else "historical"
    train(mode=mode)
