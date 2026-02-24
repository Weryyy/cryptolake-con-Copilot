"""Pydantic response models for the API."""

from datetime import date

from pydantic import BaseModel


class PriceResponse(BaseModel):
    coin_id: str
    price_date: date
    price_usd: float
    market_cap_usd: float | None = None
    volume_24h_usd: float | None = None
    price_change_pct_1d: float | None = None
    moving_avg_7d: float | None = None
    moving_avg_30d: float | None = None
    ma30_signal: str | None = None


class MarketOverview(BaseModel):
    coin_id: str
    current_price: float
    price_change_24h_pct: float | None = None
    market_cap_usd: float | None = None
    volume_24h_usd: float | None = None


class FearGreedResponse(BaseModel):
    value: int
    classification: str
    timestamp: int


class HealthResponse(BaseModel):
    status: str
    version: str
    services: dict


class PredictionResponse(BaseModel):
    timestamp: float
    coin_id: str = "bitcoin"
    predicted_price: float
    current_price: float
    sentiment_bias: str
    memory_details: dict | None = None
    model_version: str | None = None
    confidence: float | None = None
    direction_probability: float | None = None
    prediction_curve: list | None = None


class DualPredictionResponse(BaseModel):
    """Respuesta con predicciones de ambos modelos para comparacion."""

    legacy: PredictionResponse | None = None
    ensemble: PredictionResponse | None = None
    primary_model: str = "legacy"


class ModelAccuracyComparison(BaseModel):
    """Precision de ambos modelos para comparacion lado a lado."""

    legacy: dict | None = None
    ensemble: dict | None = None


class OHLCResponse(BaseModel):
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    is_anomaly: int


class SystemAlert(BaseModel):
    timestamp: float
    level: str
    dag_id: str
    task_id: str
    message: str


class DQReport(BaseModel):
    table_name: str
    success_rate: float
    total_expectations: int
    successful_expectations: int
    timestamp: float


class FearGreedHistoryItem(BaseModel):
    value: int
    classification: str
    timestamp: int
    date_str: str | None = None


class PredictionAccuracy(BaseModel):
    total_evaluated: int = 0
    mae: float = 0.0
    mape: float = 0.0
    direction_accuracy: float = 0.0
    correct_direction: int = 0
    total_direction: int = 0
    recent_errors: list | None = None
