"""
Consejo de Agentes y Modelos Predictivos.

Arquitectura:
- Long-Term Model: Analiza tendencias macro (capa Gold).
- Short-Term Model: Analiza volatilidad micro (capa Silver Realtime).
- Agents: Opiniones técnicas y de sentimiento REALES.

Hardware objetivo: Xeon E5-1620 v3 (4C/8T), 32GB RAM, CPU-only.
"""

import numpy as np
import torch
import torch.nn as nn

# ──────────────────────────────────────────────────────────────
# Indicadores técnicos
# ──────────────────────────────────────────────────────────────


def compute_rsi(prices, period=14):
    """Calcula RSI (Relative Strength Index) sobre un array de precios.

    Retorna un array del mismo largo con NaN para las primeras `period` posiciones.
    """
    prices = np.asarray(prices, dtype=np.float64)
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)

    rsi = np.full(len(prices), np.nan)
    if len(gains) < period:
        return rsi

    avg_gain = gains[:period].mean()
    avg_loss = losses[:period].mean()

    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        rs = avg_gain / (avg_loss + 1e-10)
        rsi[i + 1] = 100.0 - (100.0 / (1.0 + rs))

    # Rellenar los primeros valores con el primer RSI válido
    first_valid = period
    if first_valid < len(rsi) and not np.isnan(rsi[first_valid]):
        rsi[:first_valid] = rsi[first_valid]
    return rsi


def compute_sma(prices, period):
    """Simple Moving Average. Rellena inicio con el primer valor disponible."""
    prices = np.asarray(prices, dtype=np.float64)
    sma = np.full(len(prices), np.nan)
    for i in range(period - 1, len(prices)):
        sma[i] = prices[i - period + 1 : i + 1].mean()
    # Rellenar NaN iniciales
    first_valid = period - 1
    if first_valid < len(sma) and not np.isnan(sma[first_valid]):
        sma[:first_valid] = sma[first_valid]
    return sma


# ──────────────────────────────────────────────────────────────
# Council of Agents — ahora con indicadores REALES
# ──────────────────────────────────────────────────────────────


class CouncilOfAgents:
    """Calcula señales cuantitativas basadas en indicadores técnicos reales."""

    @staticmethod
    def technical_agent(prices):
        """Señal basada en RSI y cruce de SMAs.

        Args:
            prices: array-like de precios (mínimo 10 valores).

        Returns:
            float entre -1.0 (venta fuerte) y 1.0 (compra fuerte).
        """
        prices = np.asarray(prices, dtype=np.float64)
        if len(prices) < 5:
            return 0.0

        # RSI con periodo adaptado al largo disponible
        rsi_period = min(14, max(3, len(prices) // 3))
        rsi = compute_rsi(prices, period=rsi_period)
        current_rsi = rsi[-1] if not np.isnan(rsi[-1]) else 50.0

        # Señal RSI: -1 (sobrecomprado > 70) a +1 (sobrevendido < 30)
        rsi_signal = (50.0 - current_rsi) / 50.0  # [-1, +1]
        rsi_signal = np.clip(rsi_signal, -1.0, 1.0)

        # Cruce de SMAs
        sma_short = compute_sma(prices, min(5, len(prices)))
        sma_long = compute_sma(prices, min(10, len(prices)))
        if not np.isnan(sma_short[-1]) and not np.isnan(sma_long[-1]):
            sma_diff = (sma_short[-1] - sma_long[-1]) / (sma_long[-1] + 1e-10)
            sma_signal = np.clip(sma_diff * 10, -1.0, 1.0)
        else:
            sma_signal = 0.0

        # Combinación 60% RSI + 40% SMA
        return float(np.clip(rsi_signal * 0.6 + sma_signal * 0.4, -1.0, 1.0))

    @staticmethod
    def sentiment_agent(fear_greed_val):
        """Señal continua basada en el Fear & Greed Index.

        Mapea 0-100 a [-1.0, +1.0] de forma suave.
        """
        # Sigmoide centrada en 50
        val = float(fear_greed_val)
        return float(np.clip((val - 50.0) / 50.0, -1.0, 1.0))

    @staticmethod
    def compute_agents_for_series(prices, fear_greed_val=50):
        """Calcula ambas señales de agentes para una serie de precios.

        Args:
            prices: array de precios.
            fear_greed_val: valor Fear & Greed (0-100).

        Returns:
            tuple (technical_signal, sentiment_signal)
        """
        tech = CouncilOfAgents.technical_agent(prices)
        sent = CouncilOfAgents.sentiment_agent(fear_greed_val)
        return tech, sent


# ──────────────────────────────────────────────────────────────
# Modelo — optimizado para CPU (Xeon E5-1620 v3)
# ──────────────────────────────────────────────────────────────


class TemporalFusionTransformer(nn.Module):
    """
    TFT simplificado para predicción de precios.

    Cambios vs versión anterior:
    - input_dim=4: [precio_norm, volumen_norm, rsi_norm, sma_ratio]
    - agent_dim=2: [señal_técnica_real, señal_sentimiento_real]
    - LSTM hidden reducido para velocidad en CPU
    - Dropout para regularización
    """

    def __init__(self, input_dim=4, agent_dim=2):
        super().__init__()
        self.lstm_long = nn.LSTM(input_dim, 48, batch_first=True, num_layers=1)
        self.lstm_short = nn.LSTM(input_dim, 24, batch_first=True, num_layers=1)
        self.fc_agents = nn.Linear(agent_dim, 12)
        self.dropout = nn.Dropout(0.1)

        self.regressor = nn.Sequential(
            nn.Linear(48 + 24 + 12, 48),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(48, 1),
        )

    def forward(self, x_long, x_short, agent_opinions):
        _, (h_l, _) = self.lstm_long(x_long)
        _, (h_s, _) = self.lstm_short(x_short)
        a_op = torch.relu(self.fc_agents(agent_opinions))

        combined = torch.cat((h_l[-1], h_s[-1], a_op), dim=1)
        combined = self.dropout(combined)
        return self.regressor(combined)


# ──────────────────────────────────────────────────────────────
# ReturnLSTM — modelo mejorado para predicción de retornos
# ──────────────────────────────────────────────────────────────


class ReturnLSTM(nn.Module):
    """LSTM con Attention para predecir retornos (cambio porcentual).

    Mejoras v3:
    - hidden_dim=128 (vs 64) -> mas capacidad para patrones complejos
    - Self-attention sobre estados LSTM -> foco en timesteps relevantes
    - 2 capas LSTM con dropout -> mejor generalizacion
    - Cabeza de clasificacion + regresion separadas
    - LayerNorm para estabilidad del training

    Input: secuencia de 20 features x seq_len timesteps
    Output: retorno predicho (escalar) + probabilidad de direccion
    """

    def __init__(self, input_dim=20, hidden_dim=64, num_layers=2, dropout=0.2):
        super().__init__()
        self.hidden_dim = hidden_dim
        self.lstm = nn.LSTM(
            input_dim,
            hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0,
        )
        # Self-attention: aprende que timesteps importan mas
        self.attention = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.Tanh(),
            nn.Linear(hidden_dim // 2, 1),
        )
        self.layer_norm = nn.LayerNorm(hidden_dim)
        # Cabeza de regresion (predice retorno %)
        self.return_head = nn.Sequential(
            nn.Linear(hidden_dim, 32),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(32, 1),
        )
        # Cabeza de clasificacion (predice direccion)
        self.direction_head = nn.Sequential(
            nn.Linear(hidden_dim, 32),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(32, 1),
            nn.Sigmoid(),
        )

    def forward(self, x):
        """
        x: [batch, seq_len, 20] -> (return_pred, direction_prob)

        Returns:
            return_pred: [batch, 1] retorno predicho
            direction_prob: [batch, 1] probabilidad de subida
        """
        lstm_out, (h, _) = self.lstm(x)  # lstm_out: [batch, seq_len, hidden]

        # Self-attention sobre todos los timesteps
        attn_scores = self.attention(lstm_out)  # [batch, seq_len, 1]
        attn_weights = torch.softmax(attn_scores, dim=1)  # [batch, seq_len, 1]
        context = (lstm_out * attn_weights).sum(dim=1)  # [batch, hidden]

        # Combinar context con ultimo estado oculto
        h_last = h[-1]  # [batch, hidden]
        combined = context + h_last  # residual connection
        combined = self.layer_norm(combined)

        return_pred = self.return_head(combined)
        direction_prob = self.direction_head(combined)
        return return_pred, direction_prob


def get_device():
    """Retorna CPU (Quadro K4200 Kepler no soporta PyTorch CUDA moderno)."""
    if torch.cuda.is_available():
        print("[INFO] GPU detectada. Usando CUDA.")
        return torch.device("cuda")
    print("[INFO] Usando CPU (Xeon E5-1620 v3 @ 3.50GHz).")
    return torch.device("cpu")
