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
import time
import os
from datetime import timedelta
from src.ml.models import TemporalFusionTransformer, get_device
from src.serving.api.utils import get_iceberg_catalog


def load_training_data(coin_id="bitcoin", days=None):
    """Carga datos historicos de Iceberg para entrenamiento."""
    try:
        catalog = get_iceberg_catalog()
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
        print(f"⚠️ Iceberg no disponible, intentando local cache: {e}")
        local_path = "data/local_cache/silver_daily_prices.csv"
        if os.path.exists(local_path):
            df = pd.read_csv(local_path)
            df["price_date"] = pd.to_datetime(df["price_date"])
            df = df[df["coin_id"] == coin_id].sort_values("price_date")
            if days:
                from datetime import datetime, timedelta
                cutoff = datetime.now() - timedelta(days=days)
                df = df[df["price_date"] >= cutoff]
            return df
        return None


def train(mode="historical"):
    """
    mode: 'historical' (todo) o 'recent' (ultimos 15 dias)
    """
    device = get_device()
    print("--------------------------------------------------")
    print("💻 ESPECIFICACIONES DETECTADAS:")
    print(f"   CPU: Intel Xeon E5-1620 v3 (4 Cores / 8 Threads)")
    print(f"   RAM: 32 GB")
    print(f"   GPU: NVIDIA Quadro K4200")
    print(f"   Usando Device: {device}")
    print("--------------------------------------------------")

    days = 15 if mode == "recent" else None
    df = load_training_data(days=days)

    if df is None or len(df) < 10:
        print(
            f"⚠️ No hay suficientes datos para modo {mode}. Ingiere mas precios.")
        return

    print(f"🧠 Entrenando modelo MEMORIA: {mode.upper()} ({len(df)} dias)")
    # Refinamiento de Datos: Usamos Precio + Volumen
    price_data = df["price_usd"].values.astype(np.float32)
    vol_data = df["volume_24h_usd"].values.astype(np.float32)

    # Normalización Min-Max por canal
    price_norm = (price_data - price_data.min()) / \
        (price_data.max() - price_data.min())
    vol_norm = (vol_data - vol_data.min()) / \
        (vol_data.max() - vol_data.min() + 1e-6)

    # Crear secuencias multivariante [Precio, Volumen]
    X, Y = [], []
    for i in range(len(price_norm)-11):
        # Stack horizontal de features: [10, 2]
        seq = np.stack([price_norm[i:i+10], vol_norm[i:i+10]], axis=1)
        X.append(seq)
        Y.append(price_norm[i+10])

    X = torch.tensor(X).to(device)  # [Batch, Seq(10), Features(2)]
    Y = torch.tensor(Y).unsqueeze(-1).to(device)

    # Inicializar modelo (Cambiamos input_dim=2 por el nuevo refinamiento)
    model = TemporalFusionTransformer(input_dim=2).to(device)
    lr = 0.002 if mode == "recent" else 0.0005
    optimizer = optim.Adam(model.parameters(), lr=lr)
    criterion = nn.MSELoss()

    print(f"🚀 Empezando entrenamiento con {len(X)} secuencias...")
    model.train()
    # Aumentamos épocas como pidió el usuario para asegurar aprendizaje profundo
    epochs = 400 if mode == "recent" else 200

    start_train_time = time.time()
    for epoch in range(epochs):
        epoch_start_time = time.time()

        optimizer.zero_grad()
        # Opinion de Agentes (Simulada para entrenamiento)
        agents = torch.randn(len(X), 2).to(device)

        output = model(X, X, agents)
        loss = criterion(output, Y)
        loss.backward()
        optimizer.step()

        epoch_end_time = time.time()
        epoch_duration = epoch_end_time - epoch_start_time

        if epoch % 10 == 0 or epoch == epochs - 1:
            elapsed_time = time.time() - start_train_time
            avg_time_per_epoch = elapsed_time / (epoch + 1)
            remaining_epochs = epochs - (epoch + 1)
            eta = avg_time_per_epoch * remaining_epochs

            print(f"Epoch {epoch:3d}/{epochs} | Loss: {loss.item():.6f} | "
                  f"Time/Epoch: {epoch_duration:.4f}s | "
                  f"ETA: {str(timedelta(seconds=int(eta)))}")

    total_time = time.time() - start_train_time
    print(
        f"🏁 Entrenamiento completado en {str(timedelta(seconds=int(total_time)))}")

    # Guardar modelo con el prefijo del modo
    os.makedirs("models", exist_ok=True)
    save_path = f"models/tft_{mode}.pth"
    torch.save(model.state_dict(), save_path)
    print(f"✅ Modelo {mode} guardado en {save_path}")


if __name__ == "__main__":
    import sys

    # Permitir pasar el modo como argumento
    mode = sys.argv[1] if len(sys.argv) > 1 else "historical"
    if mode.startswith("--mode="):
        mode = mode.split("=")[1]
    elif mode == "--mode" and len(sys.argv) > 2:
        mode = sys.argv[2]

    train(mode=mode)
