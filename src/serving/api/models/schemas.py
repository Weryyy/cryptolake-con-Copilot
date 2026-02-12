"""Pydantic response models for the API."""
from datetime import date
from typing import Optional

from pydantic import BaseModel


class PriceResponse(BaseModel):
    coin_id: str
    price_date: date
    price_usd: float
    market_cap_usd: Optional[float] = None
    volume_24h_usd: Optional[float] = None
    price_change_pct_1d: Optional[float] = None
    moving_avg_7d: Optional[float] = None
    moving_avg_30d: Optional[float] = None
    ma30_signal: Optional[str] = None


class MarketOverview(BaseModel):
    coin_id: str
    current_price: float
    price_change_24h_pct: Optional[float] = None
    market_cap_usd: Optional[float] = None
    volume_24h_usd: Optional[float] = None


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
    predicted_price: float
    current_price: float
    sentiment_bias: str
    memory_details: Optional[dict] = None


class OHLCResponse(BaseModel):
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    is_anomaly: int
