"""
Servicio de Inferencia v4 -- Dual Model Parallel con Multi-Point Prediction.

Ejecuta AMBOS modelos en paralelo:
- Legacy TFT: prediccion unica (precio target)
- Ensemble (GB + RF + LSTM): prediccion multi-punto (curva)

Publica en Redis por separado para comparacion en dashboard:
- live_prediction_legacy  -> prediccion TFT
- live_prediction_ensemble -> prediccion ensemble (multi-punto)
- live_prediction -> alias al modelo primario
- model_comparison_log -> log estructurado para analisis

Optimizado para CPU (Xeon E5-1620 v3).
"""

import json
import os
import time
from datetime import UTC

import joblib
import numpy as np
import torch

from src.ml.features import (
    N_FEATURES,
    build_feature_matrix,
)
from src.ml.models import ReturnLSTM, get_device
from src.serving.api.utils import get_iceberg_catalog, get_redis_client

# ----------------------------------------------------------------------
# Carga de modelos
# ----------------------------------------------------------------------


def load_ensemble_models(device):
    """Carga los 3 modelos del ensemble + configuracion.

    Returns:
        dict con modelos y config, o None si falla.
    """
    config_path = "models/ensemble_config.json"
    if not os.path.exists(config_path):
        print("[WARN] models/ensemble_config.json no encontrado")
        print("   -> Ejecuta primero: make train-ml")
        return None

    with open(config_path) as f:
        config = json.load(f)

    models = {"config": config}

    # GradientBoosting
    gb_path = "models/gb_direction.pkl"
    if os.path.exists(gb_path):
        models["gb"] = joblib.load(gb_path)
        print(f"[OK] GradientBoosting cargado: {gb_path}")
    else:
        print(f"[WARN] {gb_path} no encontrado")
        models["gb"] = None

    # RandomForest
    rf_path = "models/rf_direction.pkl"
    if os.path.exists(rf_path):
        models["rf"] = joblib.load(rf_path)
        print(f"[OK] RandomForest cargado: {rf_path}")
    else:
        print(f"[WARN] {rf_path} no encontrado")
        models["rf"] = None

    # ReturnLSTM
    lstm_path = "models/return_lstm.pth"
    if os.path.exists(lstm_path):
        # Intentar cargar con la arquitectura nueva (hidden_dim=128 + attention)
        # Si falla (pesos viejos de hidden_dim=64), usar arquitectura legacy
        loaded = False
        for hidden_dim in [64, 128]:
            try:
                lstm = ReturnLSTM(
                    input_dim=N_FEATURES,
                    hidden_dim=hidden_dim,
                    num_layers=2,
                    dropout=0.2,
                ).to(device)
                lstm.load_state_dict(torch.load(lstm_path, map_location=device))
                lstm.eval()
                models["lstm"] = lstm
                print(f"[OK] ReturnLSTM cargado (hidden={hidden_dim}): {lstm_path}")
                loaded = True
                break
            except RuntimeError:
                continue
        if not loaded:
            print("[WARN] ReturnLSTM incompatible, requiere retrain")
            models["lstm"] = None
    else:
        print(f"[WARN] {lstm_path} no encontrado")
        models["lstm"] = None

    # Verificar que al menos GB o RF esten disponibles
    if models["gb"] is None and models["rf"] is None:
        print("[ERROR] Sin modelos tabulares, no se puede hacer ensemble")
        return None

    return models


# ----------------------------------------------------------------------
# Fallback: cargar modelos legacy TFT si ensemble no existe
# ----------------------------------------------------------------------


def load_legacy_models(device):
    """Carga modelos TFT legacy como fallback."""
    from src.ml.models import TemporalFusionTransformer

    models = {"type": "legacy"}
    for mode in ["historical", "recent"]:
        path = f"models/tft_{mode}.pth"
        if os.path.exists(path):
            model = TemporalFusionTransformer(input_dim=4, agent_dim=2).to(device)
            model.load_state_dict(torch.load(path, map_location=device))
            model.eval()
            models[mode] = model
            print(f"[OK] TFT legacy cargado: {path}")
        else:
            models[mode] = None
    return models


# ----------------------------------------------------------------------
# Obtencion de datos
# ----------------------------------------------------------------------


def get_btc_data(catalog, n_points=60):
    """Obtiene ultimos N puntos de BTC desde Iceberg.

    Pide 6 horas de datos para tener suficiente historial
    para las 20 features.
    """
    table = catalog.load_table("silver.realtime_vwap")
    table.refresh()

    from datetime import datetime, timedelta

    since = datetime.now(UTC) - timedelta(hours=6)
    row_filter = f"coin_id == 'bitcoin' AND window_start >= '{since.isoformat()}'"

    df = (
        table.scan(
            row_filter=row_filter,
            selected_fields=("window_start", "close", "total_volume"),
        )
        .to_arrow()
        .to_pylist()
    )

    return sorted(df, key=lambda x: str(x["window_start"]))


def get_fear_greed(catalog):
    """Obtiene ultimo Fear & Greed value."""
    try:
        table = catalog.load_table("bronze.fear_greed_index")
        rows = (
            table.scan(
                selected_fields=("value", "timestamp"),
            )
            .to_arrow()
            .to_pylist()
        )
        if rows:
            latest = sorted(rows, key=lambda x: x["timestamp"], reverse=True)[0]
            return int(latest["value"])
    except Exception:
        pass
    return 50


# ----------------------------------------------------------------------
# Inferencia ensemble (punto unico)
# ----------------------------------------------------------------------


def ensemble_predict(models, features_matrix, device, prices_array=None):
    """Genera prediccion del ensemble (punto unico).

    Estrategia hibrida: Trend-Following + ML
    1. Detecta micro-tendencia actual (momentum 3-10 candles)
    2. ML modelos votan si continua o revierte
    3. Combina: momentum * factor_continuacion_ML

    Fundamento: predecir "la tendencia continua" es mucho mas preciso
    que predecir direccion aleatoria de 1 candle de 30s.

    Args:
        models: dict con gb, rf, lstm, config.
        features_matrix: [N, 20] features de los ultimos N timesteps.
        device: torch device.
        prices_array: optional raw prices for momentum calculation.

    Returns:
        dict con direction_prob, confidence, predicted_return, model_details.
    """
    config = models["config"]
    weights = config.get("weights", {"gb": 0.45, "rf": 0.35, "lstm": 0.20})

    # ── Paso 1: Detectar micro-tendencia real (precio crudo) ──
    # Momentum sobre multiples ventanas: captura tendencia a distintas escalas
    returns_1 = features_matrix[:, 0]  # return_1 column
    momentum_3 = returns_1[-3:].mean() if len(returns_1) >= 3 else 0.0
    momentum_5 = returns_1[-5:].mean() if len(returns_1) >= 5 else 0.0
    momentum_10 = returns_1[-10:].mean() if len(returns_1) >= 10 else 0.0

    # Momentum ponderado: mas peso a lo reciente
    trend_momentum = 0.5 * momentum_3 + 0.3 * momentum_5 + 0.2 * momentum_10
    _trend_direction = 1.0 if trend_momentum > 0 else -1.0
    trend_strength = min(abs(trend_momentum) / 0.002, 1.0)  # normalizar

    # RSI para detectar sobrecompra/sobreventa -> mean reversion
    rsi_val = features_matrix[-1, 7] * 100  # rsi_7 (col 7), denormalize
    bb_pos = features_matrix[-1, 12]  # bollinger position (col 12)

    # Mean-reversion signal: si RSI extremo o BB extremo, ir contra la tendencia
    mean_reversion = 0.0
    if rsi_val > 70 or bb_pos > 0.9:
        mean_reversion = -0.3  # sobrecomprado -> bajar expectativa
    elif rsi_val < 30 or bb_pos < 0.1:
        mean_reversion = +0.3  # sobrevendido -> subir expectativa

    # ── Paso 2: ML modelos votan probabilidad de continuacion ──
    latest_features = features_matrix[-1:, :]  # [1, 20]
    gb_prob = None
    rf_prob = None
    lstm_prob = None
    lstm_return = None
    active_weight = 0.0

    if models.get("gb") is not None:
        try:
            gb_prob = models["gb"].predict_proba(latest_features)[0, 1]
            active_weight += weights["gb"]
        except Exception as e:
            print(f"[WARN] GB error: {e}")

    if models.get("rf") is not None:
        try:
            rf_prob = models["rf"].predict_proba(latest_features)[0, 1]
            active_weight += weights["rf"]
        except Exception as e:
            print(f"[WARN] RF error: {e}")

    if models.get("lstm") is not None:
        try:
            seq_len = config.get("seq_len", 10)
            if len(features_matrix) >= seq_len:
                x_seq = (
                    torch.tensor(features_matrix[-seq_len:], dtype=torch.float32)
                    .unsqueeze(0)
                    .to(device)
                )
                with torch.no_grad():
                    ret_pred, dir_pred = models["lstm"](x_seq)
                    lstm_prob = dir_pred.item()
                    lstm_return = ret_pred.item()
                    active_weight += weights["lstm"]
        except Exception as e:
            print(f"[WARN] LSTM error: {e}")

    if active_weight == 0:
        return None

    # ML consensus direction probability
    direction_prob = 0.0
    if gb_prob is not None:
        direction_prob += (weights["gb"] / active_weight) * gb_prob
    if rf_prob is not None:
        direction_prob += (weights["rf"] / active_weight) * rf_prob
    if lstm_prob is not None:
        direction_prob += (weights["lstm"] / active_weight) * lstm_prob

    ml_confidence = abs(direction_prob - 0.5) * 2.0  # [0, 1]

    # ── Paso 3: Combinar trend-following + ML ──
    #
    # Estrategia: ML lidera la DIRECCION, momentum escala la MAGNITUD.
    # Los modelos ML fueron entrenados con target_horizon=3 y 9500+ muestras
    # multi-coin → 64-65% val accuracy. Son la fuente de verdad para
    # "sube o baja en los proximos 90 segundos".
    #
    # El momentum real se usa SOLO para escalar cuanto sube/baja,
    # NO para decidir la direccion.

    ml_says_up = direction_prob > 0.5
    ml_direction = 1.0 if ml_says_up else -1.0

    # Magnitud base: volatilidad reciente (como proxy de cuanto se mueve)
    vol_recent = np.std(returns_1[-10:]) if len(returns_1) >= 10 else 0.001
    vol_recent = max(vol_recent, 0.0001)

    # El retorno base sigue la DIRECCION del ML, escalado por confianza
    base_return = ml_direction * vol_recent * (0.3 + 0.7 * ml_confidence)

    # Momentum amplifica o atenua (pero NO cambia direccion)
    trend_agrees = (trend_momentum > 0) == ml_says_up
    if trend_agrees and trend_strength > 0.2:
        # Momentum confirma ML → amplificar ligeramente
        continuation_factor = 1.0 + 0.3 * trend_strength
        raw_return = base_return * continuation_factor
    elif not trend_agrees and trend_strength > 0.3:
        # Momentum contradice ML → atenuar pero NO invertir
        continuation_factor = max(0.3, 1.0 - 0.5 * trend_strength)
        raw_return = base_return * continuation_factor
    else:
        # Momentum debil → confiar 100% en ML
        continuation_factor = 1.0
        raw_return = base_return

    # Aplicar mean-reversion suavemente
    raw_return += mean_reversion * abs(trend_momentum)

    # Clip realista para prediccion 30s (max ±0.3% = ~$190 en BTC $64k)
    predicted_return = np.clip(raw_return, -0.003, 0.003)

    # Confianza combinada: trend_strength * ml_confidence
    confidence = max(0.1, trend_strength * 0.6 + ml_confidence * 0.4)

    return {
        "direction_prob": float(direction_prob),
        "confidence": float(confidence),
        "predicted_return": float(predicted_return),
        "model_details": {
            "gb_prob": float(gb_prob) if gb_prob is not None else None,
            "rf_prob": float(rf_prob) if rf_prob is not None else None,
            "lstm_prob": float(lstm_prob) if lstm_prob is not None else None,
            "lstm_return": float(lstm_return) if lstm_return is not None else None,
            "trend_momentum": float(trend_momentum),
            "continuation_factor": float(continuation_factor),
            "mean_reversion": float(mean_reversion),
        },
    }


# ----------------------------------------------------------------------
# Inferencia ensemble multi-punto (curva de mercado)
# ----------------------------------------------------------------------


def ensemble_predict_multipoint(models, features_matrix, device, current_price, n_points=5):
    """Genera prediccion multi-punto del ensemble (curva de mercado).

    Proyecta el momentum actual con decaimiento exponencial realista.
    Cada punto futuro asume que el momentum se reduce ~20% por paso
    (tendencias se desaceleran naturalmente).

    Args:
        models: dict ensemble con gb, rf, lstm, config.
        features_matrix: [N, 20] features actuales.
        device: torch device.
        current_price: precio actual BTC.
        n_points: cantidad de puntos futuros (default 5).

    Returns:
        list de dicts con {horizon_seconds, predicted_price, confidence, direction_prob}
        o None si no puede generar prediccion.
    """
    base_pred = ensemble_predict(models, features_matrix, device)
    if base_pred is None:
        return None

    base_return = base_pred["predicted_return"]
    base_confidence = base_pred["confidence"]
    base_dir_prob = base_pred["direction_prob"]

    points = []
    cumulative_return = 0.0

    for i in range(1, n_points + 1):
        horizon_seconds = i * 30

        # Momentum se desacelera naturalmente: 80% del paso anterior
        decay_factor = 0.80 ** (i - 1)
        step_return = base_return * decay_factor

        cumulative_return += step_return
        # Clip realista: max ±0.8% para curva completa de ~2.5 min
        cumulative_return = np.clip(cumulative_return, -0.008, 0.008)

        pred_price = current_price * (1.0 + cumulative_return)
        step_confidence = base_confidence * decay_factor

        points.append(
            {
                "horizon_seconds": horizon_seconds,
                "predicted_price": round(float(pred_price), 2),
                "confidence": round(float(max(step_confidence, 0.05)), 4),
                "direction_prob": round(float(base_dir_prob), 4),
            }
        )

    return points


# ----------------------------------------------------------------------
# Inferencia legacy
# ----------------------------------------------------------------------


def legacy_predict(models, prices, volumes, fg_val, device):
    """Prediccion usando modelos TFT legacy."""
    from src.ml.models import CouncilOfAgents, compute_rsi, compute_sma

    prices_arr = np.asarray(prices, dtype=np.float64)
    volumes_arr = np.asarray(volumes, dtype=np.float64)

    rsi_period = min(14, max(3, len(prices_arr) // 3))
    rsi = compute_rsi(prices_arr, period=rsi_period)
    sma_short = compute_sma(prices_arr, min(5, len(prices_arr)))
    sma_long = compute_sma(prices_arr, min(10, len(prices_arr)))
    sma_ratio = np.where(
        sma_long > 0,
        (sma_short / (sma_long + 1e-10)) - 1.0,
        0.0,
    )

    p_min, p_max = prices_arr.min(), prices_arr.max()
    p_denom = p_max - p_min if p_max > p_min else 1.0
    prices_norm = (prices_arr - p_min) / p_denom
    v_min, v_max = volumes_arr.min(), volumes_arr.max()
    v_denom = v_max - v_min if v_max > v_min else 1.0
    volumes_norm = (volumes_arr - v_min) / v_denom
    rsi_norm = np.nan_to_num(rsi, nan=50.0) / 100.0
    sma_ratio_clipped = np.clip(sma_ratio * 10, -1.0, 1.0)

    window_size = 10
    feats = np.stack(
        [
            prices_norm[-window_size:],
            volumes_norm[-window_size:],
            rsi_norm[-window_size:],
            sma_ratio_clipped[-window_size:],
        ],
        axis=1,
    )

    tech = CouncilOfAgents.technical_agent(prices_arr)
    sent = CouncilOfAgents.sentiment_agent(fg_val)
    x = torch.tensor(feats, dtype=torch.float32).unsqueeze(0).to(device)
    a_op = torch.tensor([[tech, sent]], dtype=torch.float32).to(device)

    with torch.no_grad():
        preds = []
        for key in ["recent", "historical"]:
            if models.get(key) is not None:
                pred = models[key](x, x, a_op).item()
                preds.append(pred)
        if not preds:
            return None

    pred_norm = preds[0] * 0.8 + (preds[1] if len(preds) > 1 else preds[0]) * 0.2
    pred_norm = max(-0.5, min(1.5, pred_norm))
    pred_final = (pred_norm * p_denom) + p_min
    current_price = prices_arr[-1]
    max_change = current_price * 0.10
    pred_final = np.clip(pred_final, current_price - max_change, current_price + max_change)

    # Sin correccion de sesgo — dejar que el modelo prediga sin ajuste
    # La correccion de sesgo estatica empeora en mercados cambiantes

    return {
        "predicted_price": float(pred_final),
        "direction_prob": 0.5 + (0.5 if pred_final > current_price else -0.5) * 0.3,
        "confidence": 0.3,
        "model_details": {"type": "legacy"},
    }


# ----------------------------------------------------------------------
# Evaluacion de precision (por modelo)
# ----------------------------------------------------------------------


def _evaluate_past_predictions(redis_client, current_price: float, model_key: str):
    """Evalua predicciones pasadas de un modelo especifico.

    Para cada prediccion de hace ~30-120s, calcula el error y actualiza
    las metricas acumuladas de precision en Redis.

    Usa Redis Sets por modelo para evitar evaluar duplicados.

    Args:
        redis_client: conexion Redis.
        current_price: precio real actual.
        model_key: 'legacy' o 'ensemble' para separar metricas.
    """
    accuracy_redis_key = f"prediction_accuracy_{model_key}"
    history_redis_key = f"prediction_history_{model_key}"
    ts_set_key = f"evaluated_timestamps_{model_key}"

    try:
        raw = redis_client.get(accuracy_redis_key)
        if raw:
            acc = json.loads(raw)
        else:
            acc = {
                "model": model_key,
                "total_evaluated": 0,
                "total_abs_error": 0.0,
                "total_abs_pct_error": 0.0,
                "correct_direction": 0,
                "total_direction": 0,
                "recent_errors": [],
            }

        # Tomar predicciones recientes
        history = redis_client.lrange(history_redis_key, 0, 49)
        now = time.time()
        evaluated_count = 0

        for entry_raw in history:
            entry = json.loads(entry_raw)
            age = now - entry["timestamp"]

            # Evaluar predicciones de 60-300s de antiguedad
            # (coincide con target_horizon=3 pasos de 30s = ~90s,
            #  con ventana amplia para captar evaluaciones correctas)
            if age < 60 or age > 300:
                continue

            # Evitar re-evaluacion usando Set de timestamps evaluados
            ts_key = f"{entry['timestamp']:.4f}"
            if redis_client.sismember(ts_set_key, ts_key):
                continue

            predicted = entry["predicted_price"]
            actual_at_prediction = entry["current_price"]

            # Error absoluto y porcentual vs precio real actual
            abs_error = abs(predicted - current_price)
            pct_error = (abs_error / current_price) * 100

            # Direccion correcta?
            predicted_direction = "up" if predicted > actual_at_prediction else "down"
            actual_direction = "up" if current_price > actual_at_prediction else "down"
            direction_correct = predicted_direction == actual_direction

            acc["total_evaluated"] += 1
            acc["total_abs_error"] += abs_error
            acc["total_abs_pct_error"] += pct_error
            if direction_correct:
                acc["correct_direction"] += 1
            acc["total_direction"] += 1

            acc["recent_errors"].append(
                {
                    "timestamp": entry["timestamp"],
                    "pct_error": round(pct_error, 4),
                    "direction_correct": direction_correct,
                    "predicted": predicted,
                    "actual": current_price,
                }
            )
            acc["recent_errors"] = acc["recent_errors"][-100:]
            evaluated_count += 1

            redis_client.sadd(ts_set_key, ts_key)

        # Limpiar timestamps viejos del Set (>5 min)
        if evaluated_count > 0 or redis_client.scard(ts_set_key) > 200:
            all_ts = redis_client.smembers(ts_set_key)
            to_remove = [t for t in all_ts if (now - float(t)) > 300]
            if to_remove:
                redis_client.srem(ts_set_key, *to_remove)

        if evaluated_count > 0:
            n = acc["total_evaluated"]
            acc["mae"] = round(acc["total_abs_error"] / n, 2) if n > 0 else 0
            acc["mape"] = round(acc["total_abs_pct_error"] / n, 4) if n > 0 else 0
            acc["direction_accuracy"] = (
                round((acc["correct_direction"] / acc["total_direction"]) * 100, 1)
                if acc["total_direction"] > 0
                else 0
            )

            redis_client.set(accuracy_redis_key, json.dumps(acc))

    except Exception as e:
        print(f"[WARN] Error evaluando precision ({model_key}): {e}")


def _sync_primary_accuracy(redis_client):
    """Sincroniza el key original 'prediction_accuracy' con el primario (legacy).

    Mantiene compatibilidad con el dashboard existente.
    """
    try:
        raw = redis_client.get("prediction_accuracy_legacy")
        if raw:
            redis_client.set("prediction_accuracy", raw)
        else:
            raw_ens = redis_client.get("prediction_accuracy_ensemble")
            if raw_ens:
                redis_client.set("prediction_accuracy", raw_ens)
    except Exception:
        pass


# ----------------------------------------------------------------------
# Log estructurado de comparacion de modelos
# ----------------------------------------------------------------------


def _log_model_comparison(redis_client, legacy_result, ensemble_result, current_price):
    """Registra un log estructurado para comparar ambos modelos.

    Se almacena en Redis como lista (model_comparison_log) para
    posterior analisis de cual modelo es mejor.
    """
    entry = {
        "timestamp": time.time(),
        "current_price": float(current_price),
    }

    if legacy_result:
        entry["legacy"] = {
            "predicted_price": legacy_result.get("predicted_price"),
            "confidence": legacy_result.get("confidence"),
            "direction_prob": legacy_result.get("direction_probability"),
            "bias": legacy_result.get("sentiment_bias", "N/A"),
        }
    else:
        entry["legacy"] = None

    if ensemble_result:
        entry["ensemble"] = {
            "predicted_price": ensemble_result.get("predicted_price"),
            "confidence": ensemble_result.get("confidence"),
            "direction_prob": ensemble_result.get("direction_probability"),
            "bias": ensemble_result.get("sentiment_bias", "N/A"),
            "n_curve_points": len(ensemble_result.get("prediction_curve", [])),
            "model_details": ensemble_result.get("memory_details"),
        }
    else:
        entry["ensemble"] = None

    try:
        redis_client.lpush("model_comparison_log", json.dumps(entry))
        redis_client.ltrim("model_comparison_log", 0, 499)
    except Exception as e:
        print(f"[WARN] Error logging comparacion: {e}")


# ----------------------------------------------------------------------
# Loop principal de inferencia dual
# ----------------------------------------------------------------------


def run_inference():
    """Loop principal de inferencia v4 (Dual Model Parallel).

    Ejecuta AMBOS modelos en cada ciclo:
    1. Legacy TFT -> prediccion unica (punto)
    2. Ensemble (GB+RF+LSTM) -> prediccion multi-punto (curva)
    3. Publica por separado en Redis
    4. Evalua precision de cada modelo independientemente
    5. Log estructurado para comparacion
    """
    device = get_device()
    torch.set_num_threads(min(4, os.cpu_count() or 4))
    redis = get_redis_client()

    # Cargar ambos modelos
    legacy = load_legacy_models(device)
    has_legacy = legacy.get("recent") is not None or legacy.get("historical") is not None

    ensemble = load_ensemble_models(device)
    has_ensemble = ensemble is not None

    if not has_legacy and not has_ensemble:
        print("[ERROR] No hay modelos disponibles. Ejecuta: make train-ml-legacy")
        return

    # Determinar modelo primario (el que se publica como 'live_prediction')
    primary_model = "legacy" if has_legacy else "ensemble"

    print("=" * 60)
    print("[START] Servicio de Inferencia v4 (Dual Model Parallel)")
    print("=" * 60)
    print(f"   Legacy TFT:  {'ACTIVO' if has_legacy else 'NO DISPONIBLE'}")
    print(f"   Ensemble:    {'ACTIVO' if has_ensemble else 'NO DISPONIBLE'}")
    print(f"   Primario:    {primary_model.upper()}")
    if has_ensemble:
        config = ensemble["config"]
        conf_threshold = config.get("confidence_threshold", 0.3)
        print(f"   Ensemble conf threshold: {conf_threshold:.1%}")
        val_results = config.get("validation_results", {})
        if val_results:
            print(
                f"   Ensemble val accuracy: {val_results.get('ensemble_filtered_accuracy', 0):.1%}"
            )
    else:
        conf_threshold = 0.3
    print("=" * 60)

    catalog = get_iceberg_catalog()
    consecutive_errors = 0
    cycle_count = 0
    # Cache de prediccion ensemble: solo recalcular cada 5 ciclos
    cached_ensemble_curve = None
    cached_ensemble_base = None
    ensemble_refresh_interval = 5  # cada 5 ciclos (~2.5 min)

    while True:
        try:
            cycle_count += 1

            # 1. Obtener datos recientes de BTC
            btc_data = get_btc_data(catalog)

            if len(btc_data) < 15:
                print(f"[WAIT] Esperando datos BTC ({len(btc_data)}/15)...")
                time.sleep(10)
                continue

            # Usar hasta 120 puntos para features estables
            data_slice = btc_data[-120:]
            prices = [r["close"] for r in data_slice]
            volumes = [r["total_volume"] for r in data_slice]
            timestamps = [r["window_start"] for r in data_slice]
            current_price = prices[-1]

            # Fear & Greed
            fg_val = get_fear_greed(catalog)

            # ==========================================================
            # MODELO 1: Legacy TFT
            # ==========================================================
            legacy_result = None
            if has_legacy:
                try:
                    prediction = legacy_predict(
                        legacy,
                        prices,
                        volumes,
                        fg_val,
                        device,
                    )
                    if prediction is not None:
                        pred_final = prediction["predicted_price"]
                        bias = "Bullish" if pred_final > current_price else "Bearish"

                        legacy_result = {
                            "timestamp": time.time(),
                            "coin_id": "bitcoin",
                            "predicted_price": float(pred_final),
                            "current_price": float(current_price),
                            "confidence": float(prediction["confidence"]),
                            "direction_probability": float(prediction["direction_prob"]),
                            "memory_details": prediction["model_details"],
                            "agents": {"fear_greed": fg_val},
                            "sentiment_bias": bias,
                            "model_version": "legacy_tft",
                        }

                        # Publicar en Redis (legacy)
                        redis.set("live_prediction_legacy", json.dumps(legacy_result))

                        history_entry = {
                            "timestamp": time.time(),
                            "predicted_price": float(pred_final),
                            "current_price": float(current_price),
                            "confidence": float(prediction["confidence"]),
                            "sentiment_bias": bias,
                        }
                        redis.lpush("prediction_history_legacy", json.dumps(history_entry))
                        redis.ltrim("prediction_history_legacy", 0, 999)

                        # Evaluar precision legacy
                        _evaluate_past_predictions(redis, float(current_price), "legacy")

                except Exception as e:
                    print(f"[WARN] Error en legacy TFT: {e}")

            # ==========================================================
            # MODELO 2: Ensemble (multi-punto con cache de 5 ciclos)
            # ==========================================================
            ensemble_result = None
            if has_ensemble:
                try:
                    features = build_feature_matrix(
                        np.array(prices, dtype=np.float64),
                        np.array(volumes, dtype=np.float64),
                        timestamps=timestamps,
                        fear_greed=fg_val,
                    )

                    # Determinar si hay que recalcular la curva
                    should_refresh = (
                        cycle_count % ensemble_refresh_interval == 1
                        or cached_ensemble_curve is None
                    )

                    if should_refresh:
                        # Recalcular curva completa
                        curve_points = ensemble_predict_multipoint(
                            ensemble,
                            features,
                            device,
                            current_price,
                            n_points=5,
                        )
                        base_pred = ensemble_predict(ensemble, features, device)

                        if curve_points and base_pred:
                            cached_ensemble_curve = curve_points
                            cached_ensemble_base = base_pred
                            print(f"  [ENS] Curva recalculada en ciclo {cycle_count}")
                    else:
                        # Usar cache: ajustar precios por diferencia de
                        # precio actual vs cuando se calculo
                        curve_points = cached_ensemble_curve
                        base_pred = cached_ensemble_base

                    if base_pred is not None:
                        direction_prob = base_pred["direction_prob"]
                        confidence = base_pred["confidence"]
                        predicted_return = base_pred["predicted_return"]
                        pred_final_ens = current_price * (1.0 + predicted_return)

                        # Siempre predecir -- no filtrar por confianza
                        # La confianza se reporta como metrica informativa
                        bias_ens = (
                            "Bullish"
                            if pred_final_ens > current_price
                            else "Bearish"
                            if pred_final_ens < current_price
                            else "Neutral"
                        )

                        ensemble_result = {
                            "timestamp": time.time(),
                            "coin_id": "bitcoin",
                            "predicted_price": float(pred_final_ens),
                            "current_price": float(current_price),
                            "confidence": float(confidence),
                            "direction_probability": float(direction_prob),
                            "memory_details": base_pred["model_details"],
                            "agents": {"fear_greed": fg_val},
                            "sentiment_bias": bias_ens,
                            "model_version": "ensemble_v3",
                            "prediction_curve": curve_points or [],
                        }

                        # Publicar en Redis (ensemble)
                        redis.set("live_prediction_ensemble", json.dumps(ensemble_result))

                        history_entry = {
                            "timestamp": time.time(),
                            "predicted_price": float(pred_final_ens),
                            "current_price": float(current_price),
                            "confidence": float(confidence),
                            "sentiment_bias": bias_ens,
                        }
                        redis.lpush("prediction_history_ensemble", json.dumps(history_entry))
                        redis.ltrim("prediction_history_ensemble", 0, 999)

                        # Evaluar precision ensemble
                        _evaluate_past_predictions(redis, float(current_price), "ensemble")

                except Exception as e:
                    print(f"[WARN] Error en ensemble: {e}")

            # ==========================================================
            # Publicar prediccion primaria (backward-compatible)
            # ==========================================================
            primary_result = legacy_result if primary_model == "legacy" else ensemble_result
            if primary_result:
                redis.set("live_prediction", json.dumps(primary_result))
                hist = {
                    "timestamp": time.time(),
                    "predicted_price": primary_result["predicted_price"],
                    "current_price": primary_result["current_price"],
                    "confidence": primary_result["confidence"],
                    "sentiment_bias": primary_result["sentiment_bias"],
                }
                redis.lpush("prediction_history", json.dumps(hist))
                redis.ltrim("prediction_history", 0, 999)

            # Sincronizar metricas de precision con key global
            _sync_primary_accuracy(redis)

            # ==========================================================
            # Log de comparacion
            # ==========================================================
            _log_model_comparison(redis, legacy_result, ensemble_result, current_price)

            # ==========================================================
            # Print resumen del ciclo
            # ==========================================================
            parts = [f"[CYCLE {cycle_count}]"]
            if legacy_result:
                lp = legacy_result["predicted_price"]
                ld = ((lp - current_price) / current_price) * 100
                parts.append(f"TFT=${lp:,.2f}({ld:+.2f}%)")
            else:
                parts.append("TFT=N/A")

            if ensemble_result:
                ep = ensemble_result["predicted_price"]
                ed = ((ep - current_price) / current_price) * 100
                nc = len(ensemble_result.get("prediction_curve", []))
                md = ensemble_result.get("memory_details", {})
                mom = md.get("trend_momentum", 0) * 100
                cf = md.get("continuation_factor", 0)
                refresh = "🔄" if cycle_count % ensemble_refresh_interval == 1 else "📌"
                parts.append(
                    f"ENS=${ep:,.2f}({ed:+.2f}%,{nc}pts) mom={mom:+.3f}% cf={cf:.2f} {refresh}"
                )
            else:
                parts.append("ENS=N/A")

            parts.append(f"BTC=${current_price:,.2f}")
            print(" | ".join(parts))

            consecutive_errors = 0

        except Exception as e:
            consecutive_errors += 1
            print(f"[ERROR] Error inferencia ({consecutive_errors}): {e}")
            import traceback

            traceback.print_exc()
            if consecutive_errors > 5:
                print("[WARN] Demasiados errores, esperando 60s...")
                time.sleep(60)
                consecutive_errors = 0

        time.sleep(30)


if __name__ == "__main__":
    run_inference()
