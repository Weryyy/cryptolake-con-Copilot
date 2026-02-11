"""Analytics endpoints."""
from fastapi import APIRouter

from src.serving.api.models.schemas import FearGreedResponse, MarketOverview

router = APIRouter(tags=["Analytics"])


@router.get("/analytics/market-overview", response_model=list[MarketOverview])
async def get_market_overview():
    """Overview del mercado crypto con últimos precios y cambios."""
    # In production: query from Gold layer
    return []


@router.get("/analytics/fear-greed", response_model=FearGreedResponse)
async def get_fear_greed():
    """Último valor del Fear & Greed Index."""
    # In production: query from Silver/Gold layer
    return FearGreedResponse(
        value=50,
        classification="Neutral",
        timestamp=0,
    )
