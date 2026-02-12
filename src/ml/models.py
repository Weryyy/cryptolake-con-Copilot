"""
Consejo de Agentes y Modelos Predictivos.

Arquitectura:
- Long-Term Model: Analiza tendencias macro (capa Gold).
- Short-Term Model: Analiza volatilidad micro (capa Silver Realtime).
- Agents: Opiniones técnicas y de sentimiento.
"""
import torch
import torch.nn as nn
import os


class CouncilOfAgents:
    """Calcula opiniones discretas basadas en datos técnicos."""

    @staticmethod
    def technical_agent(data):
        """Opinion basada en RSI y Medias Móviles."""
        # Lógica simplificada: 1 (compra), -1 (venta), 0 (neutral)
        return 1.0  # Placeholder

    @staticmethod
    def sentiment_agent(fear_greed_val):
        """Opinion basada en el Fear & Greed Index."""
        if fear_greed_val < 20:
            return -0.5  # Miedo extremo
        if fear_greed_val > 80:
            return 0.5  # Codicia extrema
        return 0.0


class TemporalFusionTransformer(nn.Module):
    """
    Simplificación del TFT para predicción de precios.
    Soporta entradas de series temporales y opiniones de agentes.
    """

    def __init__(self, input_dim=5, agent_dim=2):
        super(TemporalFusionTransformer, self).__init__()
        # Definir arquitectura (Simplificada para CPU/GPU)
        self.lstm_long = nn.LSTM(input_dim, 64, batch_first=True)
        self.lstm_short = nn.LSTM(input_dim, 32, batch_first=True)
        self.fc_agents = nn.Linear(agent_dim, 16)

        self.regressor = nn.Sequential(
            nn.Linear(64 + 32 + 16, 64),
            nn.ReLU(),
            nn.Linear(64, 1)  # Predicción de precio
        )

    def forward(self, x_long, x_short, agent_opinions):
        _, (h_l, _) = self.lstm_long(x_long)
        _, (h_s, _) = self.lstm_short(x_short)
        a_op = torch.relu(self.fc_agents(agent_opinions))

        combined = torch.cat((h_l[-1], h_s[-1], a_op), dim=1)
        return self.regressor(combined)


def get_device():
    """Retorna CUDA si está disponible, sino CPU."""
    if torch.cuda.is_available():
        print("🚀 GPU detectada. Usando CUDA.")
        return torch.device("cuda")
    print("💻 Usando CPU para inferencia.")
    return torch.device("cpu")
