"""
Entrenamiento del Modelo CryptoLake.

Lee datos reales de Iceberg, calcula indicadores técnicos (RSI, SMA),
genera señales de agentes REALES por ventana, y entrena el TFT.

Features por timestep (input_dim=4):
  [precio_norm, volumen_norm, rsi_norm, sma_ratio]
Agent opinions (agent_dim=2):
  [señal_técnica_real, señal_sentimiento_real]

Optimizado para: Xeon E5-1620 v3, 32GB RAM, CPU-only.
"""
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
import pandas as pd
import numpy as np
import time
import os
from datetime import timedelta
from src.ml.models import (
    TemporalFusionTransformer,
    CouncilOfAgents,
    compute_rsi,
    compute_sma,
    get_device,
)
from src.serving.api.utils import get_iceberg_catalog


# ──────────────────────────────────────────────────────────────
# Carga de datos
# ──────────────────────────────────────────────────────────────

def load_daily_data(coin_id="bitcoin", days=None):
    """Carga precios diarios desde Iceberg (silver.daily_prices)."""
    try:
        catalog = get_iceberg_catalog()
        table = catalog.load_table("silver.daily_prices")
        if days:
            from datetime import date
            start_date = date.today() - timedelta(days=days)
            row_filter = f"coin_id == '{coin_id}' AND price_date >= '{start_date}'"
        else:
            row_filter = f"coin_id == '{coin_id}'"
        df = table.scan(
            row_filter=row_filter,
            selected_fields=("coin_id", "price_date",
                             "price_usd", "volume_24h_usd"),
        ).to_arrow().to_pandas()
        df = df.sort_values("price_date").reset_index(drop=True)
        return df
    except Exception as e:
        print(f"⚠️ Iceberg daily_prices no disponible: {e}")
        return None


def load_realtime_data(coin_id="bitcoin", hours=None):
    """Carga datos OHLC de 30s desde Iceberg (silver.realtime_vwap).

    Resamplea a velas de 15 minutos para tener una escala intermedia
    que complemente los datos diarios.
    """
    try:
        catalog = get_iceberg_catalog()
        table = catalog.load_table("silver.realtime_vwap")
        table.refresh()
        row_filter = f"coin_id == '{coin_id}'"
        if hours:
            from datetime import datetime, timezone
            since = datetime.now(timezone.utc) - timedelta(hours=hours)
            row_filter += f" AND window_start >= '{since.isoformat()}'"
        df = table.scan(
            row_filter=row_filter,
            selected_fields=("coin_id", "window_start",
                             "close", "total_volume"),
        ).to_arrow().to_pandas()
        df = df.sort_values("window_start").reset_index(drop=True)
        if len(df) < 2:
            return None
        # Resamplear a velas de 15 min para densidad razonable
        df["window_start"] = pd.to_datetime(df["window_start"], utc=True)
        df = df.set_index("window_start")
        resampled = df.resample("15min").agg(
            {"close": "last", "total_volume": "sum", "coin_id": "first"}
        ).dropna()
        resampled = resampled.reset_index()
        resampled = resampled.rename(columns={
            "close": "price_usd",
            "total_volume": "volume_24h_usd",
            "window_start": "price_date",
        })
        return resampled
    except Exception as e:
        print(f"⚠️ Iceberg realtime_vwap no disponible: {e}")
        return None


def get_fear_greed_value():
    """Obtiene el último Fear & Greed index de Iceberg."""
    try:
        catalog = get_iceberg_catalog()
        table = catalog.load_table("bronze.fear_greed_index")
        rows = table.scan(
            selected_fields=("value", "timestamp"),
        ).to_arrow().to_pylist()
        if rows:
            latest = sorted(
                rows, key=lambda x: x["timestamp"], reverse=True)[0]
            return int(latest["value"])
    except Exception:
        pass
    return 50  # Neutral default


# ──────────────────────────────────────────────────────────────
# Feature engineering
# ──────────────────────────────────────────────────────────────

def build_features(prices, volumes, window_size=10):
    """Construye features de 4 dimensiones y señales de agentes REALES.

    Features por timestep:
      [precio_norm, volumen_norm, rsi_norm, sma_ratio]
    Agent signals por ventana:
      [technical_signal, sentiment_signal]

    Returns:
        X: [N, window_size, 4]
        Y: [N, 1]
        agents: [N, 2]
        normalización: dict con min/max para denormalizar
    """
    prices = np.asarray(prices, dtype=np.float64)
    volumes = np.asarray(volumes, dtype=np.float64)

    # Indicadores técnicos sobre toda la serie
    rsi_period = min(14, max(3, len(prices) // 4))
    rsi = compute_rsi(prices, period=rsi_period)
    sma_short = compute_sma(prices, min(5, len(prices)))
    sma_long = compute_sma(prices, min(10, len(prices)))

    # SMA ratio: short/long - 1 (centrado en 0)
    sma_ratio = np.where(
        sma_long > 0,
        (sma_short / (sma_long + 1e-10)) - 1.0,
        0.0,
    )

    # Normalización min-max
    p_min, p_max = prices.min(), prices.max()
    p_denom = p_max - p_min if p_max > p_min else 1.0
    prices_norm = (prices - p_min) / p_denom

    v_min, v_max = volumes.min(), volumes.max()
    v_denom = v_max - v_min if v_max > v_min else 1.0
    volumes_norm = (volumes - v_min) / v_denom

    # RSI normalizado a [0, 1]
    rsi_norm = np.nan_to_num(rsi, nan=50.0) / 100.0

    # SMA ratio clipped
    sma_ratio_clipped = np.clip(sma_ratio * 10, -1.0, 1.0)

    # Obtener Fear & Greed para sentiment agent
    fg_val = get_fear_greed_value()

    # Construir secuencias
    X, Y, agent_signals = [], [], []
    for i in range(len(prices_norm) - window_size - 1):
        seq = np.stack([
            prices_norm[i:i + window_size],
            volumes_norm[i:i + window_size],
            rsi_norm[i:i + window_size],
            sma_ratio_clipped[i:i + window_size],
        ], axis=1)  # [window_size, 4]
        X.append(seq)
        Y.append(prices_norm[i + window_size])

        # Señales de agentes REALES para esta ventana
        window_prices = prices[i:i + window_size]
        tech_signal, sent_signal = CouncilOfAgents.compute_agents_for_series(
            window_prices, fg_val
        )
        agent_signals.append([tech_signal, sent_signal])

    norm_info = {"p_min": p_min, "p_max": p_max, "p_denom": p_denom}
    return (
        np.array(X, dtype=np.float32),
        np.array(Y, dtype=np.float32),
        np.array(agent_signals, dtype=np.float32),
        norm_info,
    )


# ──────────────────────────────────────────────────────────────
# Entrenamiento
# ──────────────────────────────────────────────────────────────

def train(mode="historical"):
    """
    mode:
      'historical' — todos los datos disponibles (daily + realtime resampleado)
      'recent'     — últimas 48h de datos realtime (velas 15min)
    """
    device = get_device()
    print("=" * 55)
    print("💻 HARDWARE:")
    print("   CPU: Intel Xeon E5-1620 v3 (4C/8T @ 3.50GHz)")
    print("   RAM: 32 GB")
    print(f"   Device: {device}")
    print("   Threads: ", end="")
    n_threads = min(4, os.cpu_count() or 4)
    torch.set_num_threads(n_threads)
    print(f"{n_threads} (optimizado)")
    print("=" * 55)

    # ── Cargar datos según modo ──
    if mode == "recent":
        print("📡 Modo RECENT: cargando datos realtime...")
        df = load_realtime_data("bitcoin")  # all available realtime
        if df is None or len(df) < 15:
            print("⚠️ Pocos datos realtime, intentando daily últimos 30 días...")
            df = load_daily_data("bitcoin", days=30)
    else:
        print("📚 Modo HISTORICAL: cargando todos los datos disponibles...")
        # Combinar daily + realtime resampleado
        df_daily = load_daily_data("bitcoin")
        df_rt = load_realtime_data("bitcoin")
        frames = [f for f in [df_daily, df_rt] if f is not None and len(f) > 0]
        if frames:
            # Normalizar columna price_date a datetime para poder concatenar
            for f in frames:
                f["price_date"] = pd.to_datetime(f["price_date"], utc=True)
            df = pd.concat(frames, ignore_index=True)
            df = df.sort_values("price_date").reset_index(drop=True)
            # Eliminar duplicados cercanos en tiempo
            df = df.drop_duplicates(subset=["price_usd"], keep="last")
        else:
            df = None

    if df is None or len(df) < 15:
        print(
            f"❌ No hay suficientes datos para modo {mode}. Min 15 registros.")
        return

    print(f"🧠 Entrenando MEMORIA {mode.upper()} con {len(df)} registros")

    # ── Feature engineering ──
    prices = df["price_usd"].values
    volumes = df["volume_24h_usd"].fillna(0).values
    window_size = min(10, len(prices) // 3)

    X_np, Y_np, agents_np, norm_info = build_features(
        prices, volumes, window_size)
    if len(X_np) < 3:
        print(f"❌ Muy pocas secuencias ({len(X_np)}). Necesitas más datos.")
        return

    print(f"   Secuencias: {len(X_np)} | Window: {window_size} | Features: 4")
    print(
        f"   Price range: ${norm_info['p_min']:,.2f} - ${norm_info['p_max']:,.2f}")

    # ── Train/Val split (80/20) ──
    split_idx = max(1, int(len(X_np) * 0.8))
    X_train, X_val = X_np[:split_idx], X_np[split_idx:]
    Y_train, Y_val = Y_np[:split_idx], Y_np[split_idx:]
    A_train, A_val = agents_np[:split_idx], agents_np[split_idx:]

    # Tensores
    X_t = torch.tensor(X_train).to(device)
    Y_t = torch.tensor(Y_train).unsqueeze(-1).to(device)
    A_t = torch.tensor(A_train).to(device)

    X_v = torch.tensor(X_val).to(device)
    Y_v = torch.tensor(Y_val).unsqueeze(-1).to(device)
    A_v = torch.tensor(A_val).to(device)

    # Mini-batches para eficiencia en CPU
    batch_size = min(64, len(X_train))
    dataset = TensorDataset(X_t, Y_t, A_t)
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

    print(
        f"   Train: {len(X_train)} | Val: {len(X_val)} | Batch: {batch_size}")

    # ── Modelo ──
    model = TemporalFusionTransformer(input_dim=4, agent_dim=2).to(device)
    lr = 0.003 if mode == "recent" else 0.001
    optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    criterion = nn.MSELoss()
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="min", factor=0.5, patience=30,
    )

    epochs = 300 if mode == "recent" else 150
    best_val_loss = float("inf")
    best_state = None
    patience_counter = 0
    early_stop_patience = 50

    print(
        f"🚀 Entrenamiento: {epochs} epochs, lr={lr}, early_stop={early_stop_patience}")
    start_time = time.time()

    for epoch in range(epochs):
        # ── Train ──
        model.train()
        epoch_loss = 0.0
        n_batches = 0
        for xb, yb, ab in loader:
            optimizer.zero_grad()
            out = model(xb, xb, ab)
            loss = criterion(out, yb)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            epoch_loss += loss.item()
            n_batches += 1

        avg_train_loss = epoch_loss / max(n_batches, 1)

        # ── Validation ──
        model.eval()
        with torch.no_grad():
            val_out = model(X_v, X_v, A_v)
            val_loss = criterion(val_out, Y_v).item()

        scheduler.step(val_loss)

        # ── Early stopping ──
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_state = {k: v.clone() for k, v in model.state_dict().items()}
            patience_counter = 0
        else:
            patience_counter += 1

        if epoch % 20 == 0 or epoch == epochs - 1 or patience_counter >= early_stop_patience:
            elapsed = time.time() - start_time
            eta = (elapsed / (epoch + 1)) * (epochs - epoch - 1)
            lr_now = optimizer.param_groups[0]["lr"]
            print(
                f"  Epoch {epoch:3d}/{epochs} | "
                f"Train: {avg_train_loss:.6f} | Val: {val_loss:.6f} | "
                f"Best: {best_val_loss:.6f} | LR: {lr_now:.5f} | "
                f"ETA: {str(timedelta(seconds=int(eta)))}"
            )

        if patience_counter >= early_stop_patience:
            print(
                f"⏹️  Early stopping en epoch {epoch} (sin mejora en {early_stop_patience} epochs)")
            break

    total_time = time.time() - start_time
    print(
        f"🏁 Entrenamiento completado en {str(timedelta(seconds=int(total_time)))}")

    # ── Guardar mejor modelo ──
    if best_state is not None:
        model.load_state_dict(best_state)

    os.makedirs("models", exist_ok=True)
    save_path = f"models/tft_{mode}.pth"
    torch.save(model.state_dict(), save_path)
    print(
        f"✅ Modelo {mode} guardado: {save_path} (val_loss={best_val_loss:.6f})")

    # Guardar norm_info para inferencia
    norm_path = f"models/norm_{mode}.pth"
    torch.save(norm_info, norm_path)
    print(f"✅ Normalización guardada: {norm_path}")


if __name__ == "__main__":
    import sys

    mode = sys.argv[1] if len(sys.argv) > 1 else "historical"
    if mode.startswith("--mode="):
        mode = mode.split("=")[1]
    elif mode == "--mode" and len(sys.argv) > 2:
        mode = sys.argv[2]

    train(mode=mode)
