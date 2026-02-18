"""Analytics endpoints."""
import json
from fastapi import APIRouter
from src.serving.api.models.schemas import FearGreedResponse, MarketOverview, PredictionResponse, OHLCResponse, SystemAlert, DQReport
from src.serving.api.utils import get_iceberg_catalog, get_redis_client
import pyarrow.compute as pc

router = APIRouter(tags=["Analytics"])


@router.get("/analytics/system-alerts", response_model=list[SystemAlert])
async def get_system_alerts():
    """Obtiene alertas de sistema (fallos de DAGs, etc) desde Redis."""
    redis = get_redis_client()
    raw_alerts = redis.lrange("system_alerts", 0, 19)  # Últimas 20
    alerts = []
    for a in raw_alerts:
        try:
            alerts.append(SystemAlert(**json.loads(a)))
        except Exception as e:
            print(f"Error parsing alert: {e}")
            continue
    return alerts


@router.get("/analytics/dq-reports", response_model=list[DQReport])
async def get_dq_reports():
    """Resumen de calidad de datos (Great Expectations) por tabla."""
    redis = get_redis_client()
    keys = redis.keys("dq_report:*")
    reports = []
    for k in keys:
        data = redis.get(k)
        if data:
            reports.append(DQReport(**json.loads(data)))
    return reports


@router.get("/analytics/prediction", response_model=PredictionResponse)
async def get_prediction():
    """Última predicción del consejo de agentes ML."""
    redis = get_redis_client()
    data = redis.get("live_prediction")
    if not data:
        return PredictionResponse(
            timestamp=0,
            coin_id="unknown",
            predicted_price=0,
            current_price=0,
            sentiment_bias="Neutral"
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
        df_arrow = table.scan().to_arrow()

        if len(df_arrow) == 0:
            raise Exception("No data in table")

        coins = df_arrow.column("coin_id").unique().to_pylist()
        overview = []
        for coin in coins:
            coin_data = df_arrow.filter(pc.equal(df_arrow["coin_id"], coin))
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
        return overview
    except Exception as e:
        print(f"Error querying Lake: {e}")
        # Retornar vacío para forzar la visualización de datos reales una vez ingestados
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
    filtered_df = []
    try:
        catalog = get_iceberg_catalog()
        table = catalog.load_table("silver.realtime_vwap")
        df = table.scan().to_arrow()

        mask = pc.equal(df.column("coin_id"), coin_id)
        filtered_df = df.filter(mask).to_pylist()
        if not filtered_df:
            raise Exception("No data")
    except Exception:
        # FALLBACK: Generar velas sintéticas para la demo
        import numpy as np
        from datetime import datetime, timedelta
        base_p = 52100.0 if coin_id == "bitcoin" else 2800.0
        now = datetime.now()
        for i in range(30):
            t = (now - timedelta(minutes=30-i)).isoformat()
            o = base_p + np.random.normal(0, 100)
            c = o + np.random.normal(0, 100)
            filtered_df.append({
                "window_start": t,
                "open": o,
                "high": max(o, c) + 50,
                "low": min(o, c) - 50,
                "close": c,
                "total_volume": 5000,
                "is_anomaly": 0
            })

    # Mapear a esquema de respuesta
    return [
        OHLCResponse(
            timestamp=str(row["window_start"]),
            open=row["open"],
            high=row["high"],
            low=row["low"],
            close=row["close"],
            volume=row["total_volume"],
            is_anomaly=row.get("is_anomaly", 0)
        )
        for row in sorted(filtered_df, key=lambda x: str(x["window_start"]))
    ]
