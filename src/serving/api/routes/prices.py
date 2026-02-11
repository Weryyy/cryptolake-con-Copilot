"""Price endpoints."""
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Query

from src.serving.api.models.schemas import PriceResponse

router = APIRouter(tags=["Prices"])


@router.get("/prices/{coin_id}", response_model=list[PriceResponse])
async def get_prices(
    coin_id: str,
    start_date: Optional[date] = Query(
        default=None,
        description="Start date (default: 30 days ago)"
    ),
    end_date: Optional[date] = Query(
        default=None,
        description="End date (default: today)"
    ),
    limit: int = Query(default=100, le=1000),
):
    """
    Obtiene precios históricos de un cryptocurrency.

    Incluye métricas calculadas: moving averages, volatilidad,
    señales técnicas y sentimiento de mercado.
    """
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=30)

    # In production: query Iceberg via PyIceberg or Spark Thrift Server
    return []
