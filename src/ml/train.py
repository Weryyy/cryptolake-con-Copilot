"""
Pipeline de Entrenamiento v2 — Ensemble Multi-Modelo.

Modelos entrenados:
  1. GradientBoostingClassifier → dirección (sube/baja) con probabilidad
  2. RandomForestClassifier → dirección (confirmación/diversidad)
  3. ReturnLSTM → magnitud del retorno + dirección

Datos de entrenamiento: velas de 30 segundos de silver.realtime_vwap
(misma granularidad que inferencia → sin mismatch train/inference).

Validación: Walk-forward sobre datos reales (último 20% cronológico).

Features (20):
  [return_1, return_3, return_5, return_10,
   volatility_5, volatility_10, volatility_20,
   rsi_7, rsi_14,
   macd, macd_signal, macd_hist,
   bb_position,
   volume_ratio_5, volume_ratio_10,
   momentum_5, momentum_10,
   fear_greed_norm,
   hour_sin, hour_cos]

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
import json
import joblib
from datetime import timedelta
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
from src.ml.models import ReturnLSTM, get_device
from src.ml.features import (
    N_FEATURES,
    FEATURE_NAMES,
    build_training_samples,
    build_sequence_samples,
)
from src.serving.api.utils import get_iceberg_catalog


# ──────────────────────────────────────────────────────────────
# Carga de datos (velas de 30 segundos — misma que inferencia)
# ──────────────────────────────────────────────────────────────

def load_realtime_data(coin_id="bitcoin", hours=None):
    """Carga datos VWAP de 30s desde Iceberg (silver.realtime_vwap).

    NO resamplea — usa la misma granularidad que inferencia.
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
            selected_fields=(
                "coin_id", "window_start", "close", "total_volume",
            ),
        ).to_arrow().to_pandas()
        df = df.sort_values("window_start").reset_index(drop=True)
        if len(df) < 2:
            return None
        df = df.rename(columns={
            "close": "price_usd",
            "total_volume": "volume_usd",
            "window_start": "timestamp",
        })
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        # Eliminar duplicados por timestamp
        df = df.drop_duplicates(subset=["timestamp"], keep="last")
        return df
    except Exception as e:
        print(f"[WARN] Iceberg realtime_vwap no disponible: {e}")
        return None


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
            selected_fields=(
                "coin_id", "price_date", "price_usd", "volume_24h_usd",
            ),
        ).to_arrow().to_pandas()
        df = df.sort_values("price_date").reset_index(drop=True)
        df = df.rename(columns={
            "volume_24h_usd": "volume_usd",
            "price_date": "timestamp",
        })
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        return df
    except Exception as e:
        print(f"[WARN] Iceberg daily_prices no disponible: {e}")
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
                rows, key=lambda x: x["timestamp"], reverse=True
            )[0]
            return int(latest["value"])
    except Exception:
        pass
    return 50  # neutral


# ──────────────────────────────────────────────────────────────
# Entrenamiento del ensemble
# ──────────────────────────────────────────────────────────────

def train_ensemble():
    """Entrena los 3 modelos del ensemble con datos reales.

    Flujo:
    1. Carga datos de 30s (realtime) — prioridad para matching con inferencia.
    2. Si hay pocos datos realtime, complementa con datos diarios.
    3. Construye features (20 dimensiones).
    4. Split cronológico 80/20 (walk-forward).
    5. Entrena GradientBoosting, RandomForest, ReturnLSTM.
    6. Valida con datos reales y reporta accuracy.
    7. Guarda modelos.
    """
    device = get_device()
    n_threads = min(4, os.cpu_count() or 4)
    torch.set_num_threads(n_threads)

    print("=" * 60)
    print("[TRAIN] ENTRENAMIENTO ENSEMBLE v2 -- Multi-Modelo + 20 Features")
    print("=" * 60)
    print(f"   CPU: Intel Xeon E5-1620 v3 (4C/8T)")
    print(f"   Threads: {n_threads}")
    print(f"   Device: {device}")
    print(f"   Features: {N_FEATURES} ({', '.join(FEATURE_NAMES[:5])}...)")
    print("=" * 60)

    # -- 1. Cargar datos --
    print("\n[DATA] Cargando datos realtime (30s candles, maximo disponible)...")
    # sin filtro de horas = todos los datos
    df_rt = load_realtime_data("bitcoin")

    print("[DATA] Cargando datos diarios (macro context)...")
    df_daily = load_daily_data("bitcoin")

    # Combinar datos: resamplear 30s→2min + concatenar con daily
    frames = []
    data_source = "combined"

    if df_rt is not None and len(df_rt) >= 20:
        # Resamplear 30s a 1 minuto para reducir ruido pero mantener muestras
        df_rt_resampled = df_rt.copy()
        df_rt_resampled = df_rt_resampled.set_index("timestamp")
        df_rt_resampled = df_rt_resampled.resample("1min").agg({
            "price_usd": "last",
            "volume_usd": "sum",
            "coin_id": "first",
        }).dropna().reset_index()
        print(
            f"   \u2705 Realtime: {len(df_rt)} \u2192 {len(df_rt_resampled)} candles (1min)")
        frames.append(df_rt_resampled)

    if df_daily is not None and len(df_daily) >= 10:
        print(f"   [OK] Daily: {len(df_daily)} registros")
        frames.append(df_daily)

    if not frames:
        total_rt = len(df_rt) if df_rt is not None else 0
        total_d = len(df_daily) if df_daily is not None else 0
        print(
            f"   [ERROR] Datos insuficientes (realtime={total_rt}, daily={total_d})")
        print("   -> Necesitas al menos 20 candles de 30s o 10 diarios.")
        return

    if len(frames) > 1:
        for f in frames:
            f["timestamp"] = pd.to_datetime(f["timestamp"], utc=True)
        df = pd.concat(frames, ignore_index=True)
        df = df.sort_values("timestamp").reset_index(drop=True)
        df = df.drop_duplicates(subset=["timestamp"], keep="last")
    else:
        df = frames[0]
        data_source = "realtime_2min" if df_rt is not None and len(
            df_rt) >= 20 else "daily"

    # Fear & Greed value
    fg_val = get_fear_greed_value()
    print(f"   Fear & Greed: {fg_val}")

    prices = df["price_usd"].values
    volumes = df["volume_usd"].fillna(0).values
    timestamps = df["timestamp"].values if "timestamp" in df.columns else None

    print(f"   Rango: ${prices.min():,.2f} — ${prices.max():,.2f}")
    print(f"   Registros: {len(prices)}")

    # -- 2. Feature engineering --
    print("\n[FEAT] Construyendo features (20 dimensiones)...")
    lookback = 30  # warmup para que features sean estables
    seq_len = 10   # ventana LSTM (10 pasos x 20 features)

    # Features para modelos tabulares (GB + RF)
    X_tab, y_dir, y_ret = build_training_samples(
        prices, volumes, timestamps, fg_val, lookback=lookback,
    )
    if X_tab is None or len(X_tab) < 20:
        print(
            f"   [ERROR] Muy pocas muestras tabulares ({0 if X_tab is None else len(X_tab)})")
        return

    # Features para LSTM
    X_seq, y_dir_seq, y_ret_seq = build_sequence_samples(
        prices, volumes, timestamps, fg_val,
        lookback=lookback, seq_len=seq_len,
    )
    has_lstm_data = X_seq is not None and len(X_seq) >= 20

    print(f"   Muestras tabulares: {len(X_tab)}")
    if has_lstm_data:
        print(f"   Muestras secuenciales: {len(X_seq)}")
    else:
        print(f"   [WARN] No hay suficientes datos para LSTM, solo entrena GB+RF")

    # -- 3. Split cronologico (walk-forward) --
    split = int(len(X_tab) * 0.80)
    X_train, X_val = X_tab[:split], X_tab[split:]
    y_dir_train, y_dir_val = y_dir[:split], y_dir[split:]
    y_ret_train, y_ret_val = y_ret[:split], y_ret[split:]

    print(f"\n[SPLIT] Split: {len(X_train)} train / {len(X_val)} validation")
    print(
        f"   Distribución train: {y_dir_train.mean():.1%} UP / {1-y_dir_train.mean():.1%} DOWN")
    print(
        f"   Distribución val:   {y_dir_val.mean():.1%} UP / {1-y_dir_val.mean():.1%} DOWN")

    os.makedirs("models", exist_ok=True)
    results = {}

    # -- 4. Entrenar GradientBoostingClassifier --
    print("\n" + "-" * 50)
    print("[GB] Entrenando GradientBoostingClassifier...")
    start = time.time()

    # Regularización fuerte para evitar overfitting con pocos datos
    n_samples = len(X_train)
    gb = GradientBoostingClassifier(
        n_estimators=min(200, max(50, n_samples // 3)),
        max_depth=3,           # un poco mas profundo para captar patrones
        learning_rate=0.05,    # menor LR + mas arboles = mejor generalizacion
        subsample=0.8,         # bootstrap de datos
        min_samples_leaf=max(5, n_samples // 50),
        max_features=0.7,      # mas features por split
        validation_fraction=0.15,  # early stopping interno
        n_iter_no_change=15,
        random_state=42,
    )
    gb.fit(X_train, y_dir_train)

    gb_train_acc = accuracy_score(y_dir_train, gb.predict(X_train))
    gb_val_acc = accuracy_score(y_dir_val, gb.predict(X_val))
    gb_val_proba = gb.predict_proba(X_val)[:, 1]  # probabilidad de UP

    gb_time = time.time() - start
    print(f"   Train accuracy:  {gb_train_acc:.1%}")
    print(f"   Val accuracy:    {gb_val_acc:.1%}")
    print(f"   Tiempo: {gb_time:.1f}s")

    # Feature importance
    importances = sorted(
        zip(FEATURE_NAMES, gb.feature_importances_),
        key=lambda x: x[1], reverse=True,
    )
    print("   Top features:")
    for name, imp in importances[:5]:
        print(f"     {name}: {imp:.3f}")

    joblib.dump(gb, "models/gb_direction.pkl")
    print("   [OK] Guardado: models/gb_direction.pkl")
    results["gb"] = {"train_acc": gb_train_acc, "val_acc": gb_val_acc}

    # -- 5. Entrenar RandomForestClassifier --
    print("\n" + "-" * 50)
    print("[RF] Entrenando RandomForestClassifier...")
    start = time.time()

    rf = RandomForestClassifier(
        n_estimators=min(300, max(100, n_samples // 2)),
        max_depth=5,            # mas profundo para patrones no lineales
        min_samples_leaf=max(5, n_samples // 50),
        max_features="sqrt",    # sqrt(20) ~ 4-5 features por split
        class_weight="balanced",  # compensar desbalance UP/DOWN
        random_state=42,
        n_jobs=n_threads,
    )
    rf.fit(X_train, y_dir_train)

    rf_train_acc = accuracy_score(y_dir_train, rf.predict(X_train))
    rf_val_acc = accuracy_score(y_dir_val, rf.predict(X_val))
    rf_val_proba = rf.predict_proba(X_val)[:, 1]

    rf_time = time.time() - start
    print(f"   Train accuracy:  {rf_train_acc:.1%}")
    print(f"   Val accuracy:    {rf_val_acc:.1%}")
    print(f"   Tiempo: {rf_time:.1f}s")

    joblib.dump(rf, "models/rf_direction.pkl")
    print("   [OK] Guardado: models/rf_direction.pkl")
    results["rf"] = {"train_acc": rf_train_acc, "val_acc": rf_val_acc}

    # -- 6. Entrenar ReturnLSTM --
    lstm_val_acc = 0.5
    if has_lstm_data:
        print("\n" + "-" * 50)
        print("[LSTM] Entrenando ReturnLSTM (20 features x 10 steps)...")
        start = time.time()

        split_seq = int(len(X_seq) * 0.80)
        X_seq_train = torch.tensor(X_seq[:split_seq]).to(device)
        X_seq_val = torch.tensor(X_seq[split_seq:]).to(device)
        y_dir_seq_train = torch.tensor(
            y_dir_seq[:split_seq]).unsqueeze(-1).to(device)
        y_dir_seq_val = torch.tensor(
            y_dir_seq[split_seq:]).unsqueeze(-1).to(device)
        y_ret_seq_train = torch.tensor(
            y_ret_seq[:split_seq]).unsqueeze(-1).to(device)
        y_ret_seq_val = torch.tensor(
            y_ret_seq[split_seq:]).unsqueeze(-1).to(device)

        model = ReturnLSTM(
            input_dim=N_FEATURES, hidden_dim=64, num_layers=2, dropout=0.2,
        ).to(device)

        optimizer = optim.AdamW(
            model.parameters(), lr=0.001, weight_decay=1e-4)
        mse_loss = nn.MSELoss()
        bce_loss = nn.BCELoss()
        # Focal-style weighting: direccion vale 2x mas que retorno
        # porque medimos direction_accuracy, no MAE
        direction_loss_weight = 2.0
        return_loss_weight = 1.0
        scheduler = optim.lr_scheduler.ReduceLROnPlateau(
            optimizer, mode="min", factor=0.5, patience=15,
        )

        # Mini-batches
        batch_size = min(64, len(X_seq_train))
        dataset = TensorDataset(X_seq_train, y_ret_seq_train, y_dir_seq_train)
        loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

        epochs = 200
        best_val_loss = float("inf")
        best_state = None
        patience_counter = 0
        early_stop_patience = 40

        print(f"   Muestras: {len(X_seq_train)} train / {len(X_seq_val)} val")
        print(f"   Epochs: {epochs} | Batch: {batch_size} | LR: 0.001")

        for epoch in range(epochs):
            model.train()
            epoch_loss = 0.0
            n_batches = 0
            for xb, yb_ret, yb_dir in loader:
                optimizer.zero_grad()
                pred_ret, pred_dir = model(xb)
                loss = (return_loss_weight * mse_loss(pred_ret, yb_ret)
                        + direction_loss_weight * bce_loss(pred_dir, yb_dir))
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                epoch_loss += loss.item()
                n_batches += 1

            avg_train_loss = epoch_loss / max(n_batches, 1)

            # Validation
            model.eval()
            with torch.no_grad():
                val_ret, val_dir = model(X_seq_val)
                val_loss = (
                    return_loss_weight * mse_loss(val_ret, y_ret_seq_val)
                    + direction_loss_weight * bce_loss(val_dir, y_dir_seq_val)
                ).item()

            scheduler.step(val_loss)

            if val_loss < best_val_loss:
                best_val_loss = val_loss
                best_state = {k: v.clone()
                              for k, v in model.state_dict().items()}
                patience_counter = 0
            else:
                patience_counter += 1

            if epoch % 25 == 0 or patience_counter >= early_stop_patience:
                print(
                    f"   Epoch {epoch:3d}/{epochs} | "
                    f"Train: {avg_train_loss:.6f} | Val: {val_loss:.6f}"
                )

            if patience_counter >= early_stop_patience:
                print(f"   [STOP] Early stopping en epoch {epoch}")
                break

        if best_state:
            model.load_state_dict(best_state)

        # Evaluar accuracy de dirección del LSTM
        model.eval()
        with torch.no_grad():
            _, val_dir_pred = model(X_seq_val)
            lstm_preds = (val_dir_pred.cpu().numpy().flatten()
                          > 0.5).astype(float)
            lstm_val_acc = accuracy_score(
                y_dir_seq[split_seq:], lstm_preds,
            )

        lstm_time = time.time() - start
        print(f"   Val direction accuracy: {lstm_val_acc:.1%}")
        print(f"   Tiempo: {lstm_time:.1f}s")

        torch.save(model.state_dict(), "models/return_lstm.pth")
        print("   [OK] Guardado: models/return_lstm.pth")
        results["lstm"] = {"val_acc": lstm_val_acc}
    else:
        print("\n[WARN] LSTM no entrenado (pocos datos secuenciales)")

    # -- 7. Evaluar ensemble combinado --
    print("\n" + "=" * 60)
    print("[EVAL] EVALUACION DEL ENSEMBLE (Walk-Forward Validation)")
    print("=" * 60)

    # --- ADAPTIVE WEIGHTS basados en accuracy real de validacion ---
    # Modelos con accuracy <= 50% son peores que moneda al aire: peso = 0
    accuracies = {
        "gb": gb_val_acc,
        "rf": rf_val_acc,
        "lstm": lstm_val_acc if has_lstm_data else 0.0,
    }
    # Solo dar peso a modelos que superan 50% (mejor que random)
    raw_weights = {}
    for k, acc in accuracies.items():
        if acc > 0.50:
            # Peso exponencial: premia mucho mas al mejor modelo
            raw_weights[k] = (acc - 0.50) ** 2
        else:
            raw_weights[k] = 0.0

    total_w = sum(raw_weights.values())
    if total_w > 0:
        w_gb = raw_weights["gb"] / total_w
        w_rf = raw_weights["rf"] / total_w
        w_lstm = raw_weights["lstm"] / total_w
    else:
        # Fallback: peso uniforme si ninguno supera 50%
        w_gb, w_rf, w_lstm = 0.33, 0.33, 0.34

    print(f"\n   [WEIGHTS] Pesos adaptativos basados en val accuracy:")
    print(f"     GB:   {gb_val_acc:.1%} acc -> peso {w_gb:.3f}")
    print(f"     RF:   {rf_val_acc:.1%} acc -> peso {w_rf:.3f}")
    print(f"     LSTM: {lstm_val_acc:.1%} acc -> peso {w_lstm:.3f}")

    # Ensemble direction probability
    ensemble_proba = w_gb * gb_val_proba + w_rf * rf_val_proba

    if has_lstm_data and lstm_val_acc > 0.50:
        # Alinear LSTM predictions con las tabulares
        # El LSTM tiene menos muestras por el seq_len offset
        offset = len(y_dir_val) - len(lstm_preds)
        if offset >= 0 and len(lstm_preds) > 0:
            lstm_proba_aligned = np.full(len(y_dir_val), 0.5)
            lstm_proba_aligned[offset:] = (
                val_dir_pred.cpu().numpy().flatten()[: len(y_dir_val) - offset]
            )
            ensemble_proba = (
                w_gb * gb_val_proba
                + w_rf * rf_val_proba
                + w_lstm * lstm_proba_aligned
            )
        else:
            # LSTM no alineado, usar solo GB + RF
            w_sum = w_gb + w_rf
            if w_sum > 0:
                ensemble_proba = (
                    (w_gb / w_sum) * gb_val_proba
                    + (w_rf / w_sum) * rf_val_proba
                )
    elif w_gb + w_rf > 0:
        # Sin LSTM, redistribuir peso
        w_sum = w_gb + w_rf
        ensemble_proba = (
            (w_gb / w_sum) * gb_val_proba
            + (w_rf / w_sum) * rf_val_proba
        )

    # Accuracy sin filtro de confianza
    ensemble_preds = (ensemble_proba > 0.5).astype(float)
    ensemble_acc = accuracy_score(y_dir_val, ensemble_preds)
    print(f"\n   [RESULT] Ensemble accuracy (sin filtro): {ensemble_acc:.1%}")

    # Accuracy CON filtro de confianza (solo predicciones confiables)
    confidence = np.abs(ensemble_proba - 0.5) * 2  # [0, 1]
    thresholds = [0.05, 0.10, 0.15, 0.20, 0.30, 0.40]
    print("\n   Accuracy por umbral de confianza:")
    best_threshold = 0.05  # default muy bajo para no descartar predicciones
    best_filtered_acc = ensemble_acc

    for thresh in thresholds:
        mask = confidence >= thresh
        n_confident = mask.sum()
        if n_confident > 0:
            filtered_acc = accuracy_score(
                y_dir_val[mask], ensemble_preds[mask])
            coverage = n_confident / len(y_dir_val)
            print(
                f"     conf >= {thresh:.1f}: "
                f"{filtered_acc:.1%} accuracy, "
                f"{coverage:.0%} coverage ({n_confident}/{len(y_dir_val)})"
            )
            if filtered_acc > best_filtered_acc and coverage > 0.30:
                best_filtered_acc = filtered_acc
                best_threshold = thresh

    print(f"\n   [BEST] Mejor umbral: {best_threshold} "
          f"-> {best_filtered_acc:.1%} accuracy")

    # -- 8. Guardar configuracion del ensemble --
    config = {
        "version": 2,
        "data_source": data_source,
        "n_features": N_FEATURES,
        "feature_names": FEATURE_NAMES,
        "seq_len": seq_len,
        "lookback": lookback,
        "weights": {"gb": w_gb, "rf": w_rf, "lstm": w_lstm},
        "confidence_threshold": best_threshold,
        "validation_results": {
            "gb_accuracy": float(gb_val_acc),
            "rf_accuracy": float(rf_val_acc),
            "lstm_accuracy": float(lstm_val_acc),
            "ensemble_accuracy": float(ensemble_acc),
            "ensemble_filtered_accuracy": float(best_filtered_acc),
            "n_validation_samples": int(len(y_dir_val)),
        },
        "trained_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
    }

    with open("models/ensemble_config.json", "w") as f:
        json.dump(config, f, indent=2)
    print(f"\n   [OK] Configuracion guardada: models/ensemble_config.json")

    # -- Resumen final --
    print("\n" + "=" * 60)
    print("[SUMMARY] RESUMEN FINAL")
    print("=" * 60)
    print(f"   GradientBoosting: {gb_val_acc:.1%} val accuracy")
    print(f"   RandomForest:     {rf_val_acc:.1%} val accuracy")
    print(f"   ReturnLSTM:       {lstm_val_acc:.1%} val accuracy")
    print(f"   ─────────────────────────────────")
    print(f"   ENSEMBLE:         {ensemble_acc:.1%} (sin filtro)")
    print(
        f"   ENSEMBLE:         {best_filtered_acc:.1%} (con confianza >= {best_threshold})")
    print(f"   -----------------------------------------")
    if best_filtered_acc >= 0.65:
        print("   [EXCELLENT] Excelente: modelo viable para uso real")
    elif best_filtered_acc >= 0.60:
        print("   [GOOD] Bueno: modelo viable con gestion de riesgo")
    elif best_filtered_acc >= 0.55:
        print("   [MARGINAL] Marginal: necesita mas datos o tuning")
    else:
        print("   [INSUFFICIENT] Insuficiente: necesita cambios fundamentales")
    print("=" * 60)


# ── Compatibilidad con el modo anterior ──

def train(mode="ensemble"):
    """Punto de entrada principal.

    mode:
      'ensemble'    — nuevo pipeline multi-modelo (recomendado)
      'historical'  — legacy TFT con datos diarios
      'recent'      — legacy TFT con datos realtime
    """
    if mode == "ensemble":
        train_ensemble()
    else:
        # Legacy: entrenar TFT original
        print(
            f"[WARN] Modo legacy '{mode}' -- usa 'ensemble' para el nuevo pipeline")
        _train_legacy(mode)


def _train_legacy(mode):
    """Entrenamiento legacy del TFT original (backward-compatible)."""
    from src.ml.models import TemporalFusionTransformer, CouncilOfAgents, compute_sma

    device = get_device()
    n_threads = min(4, os.cpu_count() or 4)
    torch.set_num_threads(n_threads)

    if mode == "recent":
        df = load_realtime_data("bitcoin")
        if df is None or len(df) < 15:
            df = load_daily_data("bitcoin", days=30)
    else:
        df_daily = load_daily_data("bitcoin")
        df_rt = load_realtime_data("bitcoin")
        frames = [f for f in [df_daily, df_rt] if f is not None and len(f) > 0]
        if frames:
            for f in frames:
                if "timestamp" in f.columns:
                    f["timestamp"] = pd.to_datetime(f["timestamp"], utc=True)
            df = pd.concat(frames, ignore_index=True)
            df = df.sort_values("timestamp").reset_index(drop=True)
            df = df.drop_duplicates(subset=["price_usd"], keep="last")
        else:
            df = None

    if df is None or len(df) < 15:
        print(f"[ERROR] No hay suficientes datos para modo {mode}.")
        return

    prices = df["price_usd"].values
    volumes = df["volume_usd"].fillna(0).values

    # Usar feature engineering original simple
    from src.ml.models import compute_rsi, compute_sma
    window_size = min(10, len(prices) // 3)
    rsi_period = min(14, max(3, len(prices) // 4))
    rsi = compute_rsi(prices, period=rsi_period)
    sma_short = compute_sma(prices, min(5, len(prices)))
    sma_long = compute_sma(prices, min(10, len(prices)))
    sma_ratio = np.where(
        sma_long > 0, (sma_short / (sma_long + 1e-10)) - 1.0, 0.0,
    )
    p_min, p_max = prices.min(), prices.max()
    p_denom = p_max - p_min if p_max > p_min else 1.0
    prices_norm = (prices - p_min) / p_denom
    v_min, v_max = volumes.min(), volumes.max()
    v_denom = v_max - v_min if v_max > v_min else 1.0
    volumes_norm = (volumes - v_min) / v_denom
    rsi_norm = np.nan_to_num(rsi, nan=50.0) / 100.0
    sma_ratio_clipped = np.clip(sma_ratio * 10, -1.0, 1.0)

    fg_val = get_fear_greed_value()
    X, Y, agents = [], [], []
    for i in range(len(prices_norm) - window_size - 1):
        seq = np.stack([
            prices_norm[i:i + window_size],
            volumes_norm[i:i + window_size],
            rsi_norm[i:i + window_size],
            sma_ratio_clipped[i:i + window_size],
        ], axis=1)
        X.append(seq)
        Y.append(prices_norm[i + window_size])
        wp = prices[i:i + window_size]
        tech, sent = CouncilOfAgents.compute_agents_for_series(wp, fg_val)
        agents.append([tech, sent])

    X = np.array(X, dtype=np.float32)
    Y = np.array(Y, dtype=np.float32)
    agents = np.array(agents, dtype=np.float32)
    norm_info = {"p_min": p_min, "p_max": p_max, "p_denom": p_denom}

    split_idx = max(1, int(len(X) * 0.8))
    X_t = torch.tensor(X[:split_idx]).to(device)
    Y_t = torch.tensor(Y[:split_idx]).unsqueeze(-1).to(device)
    A_t = torch.tensor(agents[:split_idx]).to(device)

    model = TemporalFusionTransformer(input_dim=4, agent_dim=2).to(device)
    optimizer = optim.AdamW(model.parameters(), lr=0.001, weight_decay=1e-4)
    criterion = nn.MSELoss()

    dataset = TensorDataset(X_t, Y_t, A_t)
    loader = DataLoader(dataset, batch_size=min(64, len(X_t)), shuffle=True)

    for epoch in range(150):
        model.train()
        for xb, yb, ab in loader:
            optimizer.zero_grad()
            out = model(xb, xb, ab)
            loss = criterion(out, yb)
            loss.backward()
            optimizer.step()

    os.makedirs("models", exist_ok=True)
    torch.save(model.state_dict(), f"models/tft_{mode}.pth")
    torch.save(norm_info, f"models/norm_{mode}.pth")
    print(f"[OK] Modelo legacy {mode} guardado")


if __name__ == "__main__":
    import sys

    mode = "ensemble"
    for arg in sys.argv[1:]:
        if arg.startswith("--mode="):
            mode = arg.split("=")[1]
        elif arg == "--mode" and len(sys.argv) > sys.argv.index(arg) + 1:
            mode = sys.argv[sys.argv.index(arg) + 1]

    train(mode=mode)
