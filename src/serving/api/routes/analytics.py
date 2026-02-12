"""Analytics endpoints."""
import json
from fastapi import APIRouter
from src.serving.api.models.schemas import FearGreedResponse, MarketOverview, PredictionResponse, OHLCResponse
from src.serving.api.utils import get_iceberg_catalog, get_redis_client
import pyarrow.compute as pc

router = APIRouter(tags=["Analytics"])


@router.get("/analytics/prediction", response_model=PredictionResponse)
async def get_prediction():
    """Última predicción del consejo de agentes ML."""
    redis = get_redis_client()
    data = redis.get("live_prediction")
    if not data:
        return PredictionResponse(
            timestamp=0, predicted_price=0, current_price=0, sentiment_bias="Neutral"
        )
    return PredictionResponse(**json.loads(data))


@router.get("/analytics/market-overview", response_model=list[MarketOverview])
async def get_market_overview():
    """Overview del mercado crypto con últimos precios y cambios."""
    redis = get_redis_client()

    # Intentar leer de caché primero
    cached_data = redis.get("market_overview")
    if cached_data:
        return [MarketOverview(**item) for item in json.loads(cached_data)]

    try:
        catalog = get_iceberg_catalog()
        table = catalog.load_table("silver.daily_prices")

        # Obtenemos todos los datos recientes (simplificado)
        # En producción haríamos una query más eficiente
        df_arrow = table.scan().to_arrow()

        if len(df_arrow) == 0:
            return []

        # Agrupamos por coin_id para obtener el último registro de cada uno
        # Usamos pyarrow para procesar los datos
        # Nota: En una app real esto se haría en el motor (Spark/Trino) o con caché

        coins = df_arrow.column("coin_id").unique().to_pylist()
        overview = []

        for coin in coins:
            # Filtramos por moneda
            coin_data = df_arrow.filter(pc.equal(df_arrow["coin_id"], coin))

            if len(coin_data) == 0:
                continue

            # Ordenamos por price_date descendente y tomamos el primero
            # (Simplificado usando to_pylist y sort manual para evitar problemas de API de pyarrow)
            rows = coin_data.to_pylist()
            latest_row = sorted(
                rows, key=lambda x: x["price_date"], reverse=True)[0]

            overview.append(MarketOverview(
                coin_id=latest_row["coin_id"],
                current_price=latest_row["price_usd"],
                price_change_24h_pct=latest_row.get("price_change_pct_1d"),
                market_cap_usd=latest_row.get("market_cap_usd"),
                volume_24h_usd=latest_row.get("volume_24h_usd")
            ))

        # Guardar en caché por 1 minuto
        redis.set("market_overview", json.dumps(
            [item.dict() for item in overview]), ex=60)

        return overview
    except Exception as e:
        print(f"Error analytical query: {e}")
        return []


@router.get("/analytics/fear-greed", response_model=FearGreedResponse)
async def get_fear_greed():
    """Último valor del Fear & Greed Index."""
    try:
        catalog = get_iceberg_catalog()
        table = catalog.load_table("bronze.fear_greed_index")

        # Obtenemos el último registro
        rows = table.scan().to_arrow().to_pylist()
        if not rows:
            return FearGreedResponse(value=50, classification="Neutral", timestamp=0)

        latest_row = sorted(
            rows, key=lambda x: x["timestamp"], reverse=True)[0]

        return FearGreedResponse(
            value=int(latest_row["value"]),
            classification=latest_row["classification"],
            timestamp=int(latest_row["timestamp"])
        )
    except Exception as e:
        print(f"Error FearGreed query: {e}")
        return FearGreedResponse(value=50, classification="Neutral", timestamp=0)


@router.get("/analytics/realtime-ohlc/{coin_id}", response_model=list[OHLCResponse])
async def get_realtime_ohlc(coin_id: str):
    """Obtiene datos OHLC en tiempo real para un asset."""
    try:
        catalog = get_iceberg_catalog()
        table = catalog.load_table("silver.realtime_vwap")
        # Filtrar por coin_id y traer últimos registros
        # Para simplificar en el PoC, traemos los últimos 60 minutos
        df = table.scan().to_arrow()

        # Filtro pyarrow
        mask = pc.equal(df.column("coin_id"), coin_id)
        filtered_df = df.filter(mask).to_pylist()

        # Mapear a esquema de respuesta
        result = [
            OHLCResponse(
                timestamp=str(row["window_start"]),
                open=row["open"],
                high=row["high"],
                low=row["low"],
                close=row["close"],
                volume=row["total_volume"],
                is_anomaly=row["is_anomaly"]
            )
            for row in sorted(filtered_df, key=lambda x: x["window_start"])
        ]
        return result
    except Exception as e:
        print(f"Error fetching OHLC: {e}")
        return []
