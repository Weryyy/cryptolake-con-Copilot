"""Price endpoints."""
from datetime import date, timedelta

from fastapi import APIRouter, Query

from src.serving.api.models.schemas import PriceResponse
from src.serving.api.utils import load_fresh_table

router = APIRouter(tags=["Prices"])


@router.get("/prices/{coin_id}", response_model=list[PriceResponse])
async def get_prices(
    coin_id: str,
    start_date: date | None = None,
    end_date: date | None = None,
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

    # Columnas que necesita PriceResponse
    price_fields = (
        "coin_id", "price_date", "price_usd", "market_cap_usd",
        "volume_24h_usd", "price_change_pct_1d",
        "moving_avg_7d", "moving_avg_30d", "ma30_signal",
    )

    try:
        # Gold table con métricas enriquecidas (MA7, MA30, señales)
        table = load_fresh_table("gold.fact_market_daily")
        row_filter = f"coin_id == '{coin_id}' AND price_date >= '{start_date}' AND price_date <= '{end_date}'"
        # Solo leer las columnas disponibles en esta tabla
        available_cols = {f.name for f in table.schema().fields}
        fields = tuple(f for f in price_fields if f in available_cols)
        df = table.scan(
            row_filter=row_filter,
            selected_fields=fields,
            limit=limit,
        ).to_arrow().to_pylist()
        # Sort by price_date to ensure correct chart rendering
        df.sort(key=lambda x: str(x.get("price_date", "")))
        return [PriceResponse(**row) for row in df]
    except Exception as e:
        print(f"Error querying Gold: {type(e).__name__}: {e}")
        # Fallback a Silver si Gold no está listo
        try:
            table = load_fresh_table("silver.daily_prices")
            row_filter = f"coin_id == '{coin_id}' AND price_date >= '{start_date}' AND price_date <= '{end_date}'"
            available_cols = {f.name for f in table.schema().fields}
            fields = tuple(f for f in price_fields if f in available_cols)
            df = table.scan(
                row_filter=row_filter,
                selected_fields=fields,
                limit=limit,
            ).to_arrow().to_pylist()
            df.sort(key=lambda x: str(x.get("price_date", "")))
            return [PriceResponse(**row) for row in df]
        except Exception as e2:
            print(f"Error querying Silver fallback: {type(e2).__name__}: {e2}")
            return []
