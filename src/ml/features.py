"""
Feature Engineering Avanzado para CryptoLake ML v2.

Genera 20 features técnico-estadísticas desde datos de precio/volumen/tiempo.
Todas las features están pre-normalizadas a rangos ~[-1, 1] o [0, 1]
para entrada consistente a los modelos.

Features:
   1-4:   Returns multi-lag (1, 3, 5, 10 pasos)
   5-7:   Volatilidad multi-periodo (5, 10, 20 pasos)
   8-9:   RSI a periodos 7 y 14
  10-12:  MACD (línea, señal, histograma)
  13:     Posición en Bandas de Bollinger
  14-15:  Ratios de volumen (5, 10 periodos)
  16-17:  Momentum de precio (5, 10 periodos)
  18:     Fear & Greed normalizado
  19-20:  Hora del día cíclica (sin, cos)

Hardware objetivo: Xeon E5-1620 v3, 32GB RAM, CPU-only.
"""
import numpy as np
import pandas as pd
from src.ml.models import compute_rsi


# ──────────────────────────────────────────────────────────────
# Lista ordenada de features
# ──────────────────────────────────────────────────────────────

FEATURE_NAMES = [
    "return_1", "return_3", "return_5", "return_10",
    "volatility_5", "volatility_10", "volatility_20",
    "rsi_7", "rsi_14",
    "macd", "macd_signal", "macd_hist",
    "bb_position",
    "volume_ratio_5", "volume_ratio_10",
    "momentum_5", "momentum_10",
    "fear_greed_norm",
    "hour_sin", "hour_cos",
]

N_FEATURES = len(FEATURE_NAMES)  # 20


# ──────────────────────────────────────────────────────────────
# Indicadores individuales
# ──────────────────────────────────────────────────────────────

def compute_returns(prices, lag=1):
    """Retornos porcentuales con lag dado, clipped a [-0.5, 0.5]."""
    prices = np.asarray(prices, dtype=np.float64)
    ret = np.zeros_like(prices)
    if lag < len(prices):
        ret[lag:] = (prices[lag:] - prices[:-lag]) / (prices[:-lag] + 1e-10)
    return np.clip(ret, -0.5, 0.5)


def compute_volatility(prices, window=5):
    """Desviación estándar móvil de retornos de 1 paso."""
    ret = compute_returns(prices, 1)
    vol = np.zeros_like(prices)
    for i in range(window, len(prices)):
        vol[i] = ret[i - window + 1: i + 1].std()
    if window < len(vol) and vol[window] > 0:
        vol[:window] = vol[window]
    return vol


def compute_ema(data, period):
    """Exponential Moving Average."""
    data = np.asarray(data, dtype=np.float64)
    alpha = 2.0 / (period + 1)
    result = np.zeros_like(data)
    result[0] = data[0]
    for i in range(1, len(data)):
        result[i] = alpha * data[i] + (1 - alpha) * result[i - 1]
    return result


def compute_macd(prices, fast=12, slow=26, signal=9):
    """MACD normalizado por nivel de precio.

    Returns:
        (macd_line, signal_line, histogram) todos en escala relativa.
    """
    prices = np.asarray(prices, dtype=np.float64)
    ema_fast = compute_ema(prices, fast)
    ema_slow = compute_ema(prices, slow)
    macd_line = ema_fast - ema_slow
    signal_line = compute_ema(macd_line, signal)
    histogram = macd_line - signal_line
    # Normalizar por nivel de precio
    scale = prices.mean() if prices.mean() > 0 else 1.0
    return macd_line / scale, signal_line / scale, histogram / scale


def compute_bollinger_position(prices, window=20, num_std=2):
    """Posición dentro de Bandas de Bollinger (0=inferior, 0.5=media, 1=superior)."""
    prices = np.asarray(prices, dtype=np.float64)
    position = np.full_like(prices, 0.5)
    for i in range(window, len(prices)):
        window_data = prices[i - window + 1: i + 1]
        middle = window_data.mean()
        std = window_data.std()
        if std > 0:
            upper = middle + num_std * std
            lower = middle - num_std * std
            pos = (prices[i] - lower) / (upper - lower + 1e-10)
            position[i] = np.clip(pos, 0.0, 1.0)
    if window < len(position):
        position[:window] = position[window]
    return position


def compute_volume_ratio(volumes, window=5):
    """Volumen actual / promedio móvil del volumen, normalizado a [0, 1]."""
    volumes = np.asarray(volumes, dtype=np.float64)
    ratio = np.ones_like(volumes)
    for i in range(window, len(volumes)):
        avg = volumes[i - window: i].mean()
        if avg > 0:
            ratio[i] = volumes[i] / avg
    if window < len(ratio):
        ratio[:window] = ratio[window]
    return np.clip(ratio, 0, 5) / 5.0  # normalizar a [0, 1]


def compute_momentum(prices, period=5):
    """Rate of change sobre el periodo, clipped a [-0.5, 0.5]."""
    prices = np.asarray(prices, dtype=np.float64)
    mom = np.zeros_like(prices)
    if period < len(prices):
        mom[period:] = (prices[period:] - prices[:-period]) / (
            prices[:-period] + 1e-10
        )
        mom[:period] = mom[period]
    return np.clip(mom, -0.5, 0.5)


# ──────────────────────────────────────────────────────────────
# Constructor de matriz de features completa
# ──────────────────────────────────────────────────────────────

def build_feature_matrix(prices, volumes, timestamps=None, fear_greed=50):
    """Construye la matriz completa de 20 features.

    Args:
        prices: array de precios (mínimo 30 puntos para features estables).
        volumes: array de volúmenes (mismo largo).
        timestamps: opcional, array de datetime para codificación horaria.
        fear_greed: valor Fear & Greed (0-100).

    Returns:
        np.ndarray de forma [N, 20] con todas las features.
    """
    n = len(prices)
    prices = np.asarray(prices, dtype=np.float64)
    volumes = np.asarray(volumes, dtype=np.float64)

    features = {}

    # 1-4: Returns multi-lag
    features["return_1"] = compute_returns(prices, 1)
    features["return_3"] = compute_returns(prices, min(3, max(1, n - 1)))
    features["return_5"] = compute_returns(prices, min(5, max(1, n - 1)))
    features["return_10"] = compute_returns(prices, min(10, max(1, n - 1)))

    # 5-7: Volatilidad multi-ventana
    features["volatility_5"] = compute_volatility(prices, min(5, max(2, n - 1)))
    features["volatility_10"] = compute_volatility(prices, min(10, max(2, n - 1)))
    features["volatility_20"] = compute_volatility(prices, min(20, max(2, n - 1)))

    # 8-9: RSI a dos periodos
    rsi_7 = compute_rsi(prices, min(7, max(3, n // 4)))
    rsi_14 = compute_rsi(prices, min(14, max(3, n // 4)))
    features["rsi_7"] = np.nan_to_num(rsi_7, nan=50.0) / 100.0
    features["rsi_14"] = np.nan_to_num(rsi_14, nan=50.0) / 100.0

    # 10-12: MACD
    fast = min(12, max(2, n // 3))
    slow = min(26, max(fast + 1, n // 2))
    sig = min(9, max(2, n // 4))
    macd_l, macd_s, macd_h = compute_macd(prices, fast, slow, sig)
    features["macd"] = np.clip(macd_l, -0.1, 0.1)
    features["macd_signal"] = np.clip(macd_s, -0.1, 0.1)
    features["macd_hist"] = np.clip(macd_h, -0.1, 0.1)

    # 13: Posición en Bollinger Bands
    bb_window = min(20, max(5, n // 3))
    features["bb_position"] = compute_bollinger_position(prices, bb_window)

    # 14-15: Ratios de volumen
    features["volume_ratio_5"] = compute_volume_ratio(
        volumes, min(5, max(2, n - 1))
    )
    features["volume_ratio_10"] = compute_volume_ratio(
        volumes, min(10, max(2, n - 1))
    )

    # 16-17: Momentum
    features["momentum_5"] = compute_momentum(prices, min(5, max(1, n - 1)))
    features["momentum_10"] = compute_momentum(prices, min(10, max(1, n - 1)))

    # 18: Fear & Greed normalizado
    features["fear_greed_norm"] = np.full(
        n, np.clip((fear_greed - 50) / 50.0, -1.0, 1.0)
    )

    # 19-20: Hora del día (codificación cíclica)
    if timestamps is not None:
        try:
            hours = np.array([
                pd.Timestamp(t).hour + pd.Timestamp(t).minute / 60.0
                for t in timestamps
            ])
        except Exception:
            hours = np.zeros(n)
    else:
        hours = np.zeros(n)
    features["hour_sin"] = np.sin(2 * np.pi * hours / 24.0)
    features["hour_cos"] = np.cos(2 * np.pi * hours / 24.0)

    # Ensamblar en orden correcto
    matrix = np.column_stack([features[name] for name in FEATURE_NAMES])
    matrix = np.nan_to_num(matrix, nan=0.0, posinf=0.5, neginf=-0.5)
    return matrix.astype(np.float32)


# ──────────────────────────────────────────────────────────────
# Constructores de muestras para entrenamiento
# ──────────────────────────────────────────────────────────────

def build_training_samples(
    prices, volumes, timestamps=None, fear_greed=50, lookback=30,
):
    """Construye muestras (X, y_direction, y_return) para modelos tabulares.

    Para cada timestep t (desde lookback hasta N-1):
      X[i] = vector de 20 features al tiempo t
      y_direction[i] = 1 si price[t+1] > price[t], 0 si no
      y_return[i] = (price[t+1] - price[t]) / price[t]

    Args:
        prices, volumes, timestamps: arrays de datos crudos.
        fear_greed: valor Fear & Greed (0-100).
        lookback: periodo de warmup mínimo para que features sean estables.

    Returns:
        X: [N, 20] matriz de features.
        y_dir: [N] etiquetas binarias de dirección.
        y_ret: [N] retornos porcentuales.
    """
    features = build_feature_matrix(prices, volumes, timestamps, fear_greed)
    n = len(features)
    prices = np.asarray(prices, dtype=np.float64)

    start = max(lookback, 1)
    end = n - 1  # necesitamos t+1 para target
    if end <= start:
        return None, None, None

    X = features[start:end]  # [N_samples, 20]

    y_return = (prices[start + 1: end + 1] - prices[start: end]) / (
        prices[start: end] + 1e-10
    )
    y_direction = (y_return > 0).astype(np.float32)

    return X, y_direction, y_return.astype(np.float32)


def build_sequence_samples(
    prices, volumes, timestamps=None, fear_greed=50,
    lookback=30, seq_len=10,
):
    """Construye muestras secuenciales para LSTM.

    X[i] = features[t-seq_len:t] → forma [seq_len, 20]
    y_return[i] = retorno en tiempo t+1

    Returns:
        X_seq: [N, seq_len, 20]
        y_dir: [N]
        y_ret: [N]
    """
    features = build_feature_matrix(prices, volumes, timestamps, fear_greed)
    prices = np.asarray(prices, dtype=np.float64)
    n = len(features)

    start = max(lookback, seq_len)
    end = n - 1

    if end <= start:
        return None, None, None

    X_seqs = []
    y_dirs = []
    y_rets = []

    for t in range(start, end):
        seq = features[t - seq_len: t]  # [seq_len, 20]
        X_seqs.append(seq)
        ret = (prices[t + 1] - prices[t]) / (prices[t] + 1e-10)
        y_rets.append(ret)
        y_dirs.append(1.0 if ret > 0 else 0.0)

    return (
        np.array(X_seqs, dtype=np.float32),
        np.array(y_dirs, dtype=np.float32),
        np.array(y_rets, dtype=np.float32),
    )
