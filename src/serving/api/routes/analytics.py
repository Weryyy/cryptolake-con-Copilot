"""Analytics endpoints."""
import json
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter
from src.serving.api.models.schemas import FearGreedResponse, FearGreedHistoryItem, MarketOverview, PredictionResponse, OHLCResponse, SystemAlert, DQReport, PredictionAccuracy
from src.serving.api.utils import get_redis_client, load_fresh_table, make_iso_filter
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


@router.get("/analytics/prediction-accuracy", response_model=PredictionAccuracy)
async def get_prediction_accuracy():
    """Métricas de precisión del modelo de predicción ML.

    Incluye: MAE, MAPE, precisión direccional, y últimos errores
    para visualización en el dashboard.
    """
    redis = get_redis_client()
    data = redis.get("prediction_accuracy")
    if not data:
        return PredictionAccuracy()
    return PredictionAccuracy(**json.loads(data))


@router.get("/analytics/market-overview", response_model=list[MarketOverview])
async def get_market_overview():
    """Overview del mercado crypto con últimos precios y cambios.

    Optimizado: solo lee los últimos 7 días en vez de toda la tabla,
    y selecciona únicamente las columnas necesarias.
    """
    redis = get_redis_client()

    # Intentar leer de caché primero
    cached_data = redis.get("market_overview")
    if cached_data:
        return [MarketOverview(**item) for item in json.loads(cached_data)]

    try:
        from datetime import date, timedelta
        table = load_fresh_table("silver.daily_prices")
        recent_date = (date.today() - timedelta(days=7)).isoformat()
        row_filter = f"price_date >= '{recent_date}'"
        # Solo leer columnas que existen en la tabla
        available_cols = {f.name for f in table.schema().fields}
        want_cols = ["coin_id", "price_date", "price_usd",
                     "price_change_pct_1d", "market_cap_usd", "volume_24h_usd"]
        fields = tuple(c for c in want_cols if c in available_cols)
        df_arrow = table.scan(
            row_filter=row_filter,
            selected_fields=fields,
        ).to_arrow()

        if len(df_arrow) == 0:
            raise Exception("No data in table for last 7 days")

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
        return []


@router.get("/analytics/fear-greed", response_model=FearGreedResponse)
async def get_fear_greed():
    """Último valor del Fear & Greed Index.

    Optimizado: solo lee las columnas necesarias.
    """
    try:
        table = load_fresh_table("bronze.fear_greed_index")

        # Solo seleccionar columnas que necesitamos
        rows = table.scan(
            selected_fields=("value", "classification", "timestamp"),
        ).to_arrow().to_pylist()
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


@router.get("/analytics/fear-greed-history", response_model=list[FearGreedHistoryItem])
async def get_fear_greed_history():
    """Historial completo del Fear & Greed Index para gráfico de barras.

    Devuelve todos los registros ordenados por timestamp ascendente.
    """
    try:
        table = load_fresh_table("bronze.fear_greed_index")
        rows = table.scan(
            selected_fields=("value", "classification", "timestamp"),
        ).to_arrow().to_pylist()
        if not rows:
            return []

        rows.sort(key=lambda x: x["timestamp"])

        from datetime import datetime as dt
        # Deduplicate by date (keep latest value per day)
        seen_dates = {}
        for r in rows:
            ts = int(r["timestamp"])
            date_str = dt.utcfromtimestamp(ts).strftime(
                "%Y-%m-%d") if ts > 0 else "N/A"
            seen_dates[date_str] = FearGreedHistoryItem(
                value=int(r["value"]),
                classification=r["classification"],
                timestamp=ts,
                date_str=date_str,
            )
        # Return sorted by date
        result = sorted(seen_dates.values(), key=lambda x: x.date_str or "")
        return result
    except Exception as e:
        print(f"Error FearGreed history: {e}")
        return []


@router.get("/analytics/realtime-ohlc/{coin_id}", response_model=list[OHLCResponse])
async def get_realtime_ohlc(coin_id: str):
    """Obtiene datos OHLC en tiempo real para un asset (últimas 4 horas).

    Lee directamente de silver.realtime_vwap con refresh forzado
    para garantizar datos con máximo 5 minutos de lag.
    Optimizado: ambos filtros (tiempo + coin_id) se aplican en el scan.
    """
    now_utc = datetime.now(timezone.utc)
    since_dt = now_utc - timedelta(hours=4)
    time_filter = make_iso_filter("window_start", ">=", since_dt)
    row_filter = f"coin_id == '{coin_id}' AND {time_filter}"

    ohlc_fields = ("window_start", "coin_id", "open", "high", "low",
                   "close", "total_volume", "is_anomaly")

    try:
        table = load_fresh_table("silver.realtime_vwap")
        available_cols = {f.name for f in table.schema().fields}
        fields = tuple(f for f in ohlc_fields if f in available_cols)
        filtered_df = table.scan(
            row_filter=row_filter,
            selected_fields=fields,
        ).to_arrow().to_pylist()

        if not filtered_df:
            # Sin filtro de tiempo como respaldo
            fallback_filter = f"coin_id == '{coin_id}'"
            filtered_df = table.scan(
                row_filter=fallback_filter,
                selected_fields=fields,
            ).to_arrow().to_pylist()

    except Exception as e:
        print(f"ERROR realtime-ohlc [{coin_id}]: {type(e).__name__}: {e}")
        return []

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
