"""Health check endpoint."""
from datetime import UTC

from fastapi import APIRouter

from src.serving.api.models.schemas import HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Verifica el estado de la API y sus dependencias."""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        services={
            "api": "running",
            "iceberg_catalog": "unknown",
            "kafka": "unknown",
        },
    )


@router.get("/health/latency")
async def latency_check():
    """Mide la latencia actual de datos en cada capa del pipeline.

    Usa metadatos del snapshot de Iceberg para bronze (evita escanear 400K+
    filas), y scan rápido para silver (solo ~2K filas).
    """
    from datetime import datetime

    from src.serving.api.utils import load_fresh_table

    now_utc = datetime.now(UTC)
    result = {"system_time_utc": now_utc.isoformat(), "layers": {}}

    # Bronze: usar snapshot metadata (instantáneo, sin leer datos)
    try:
        table = load_fresh_table("bronze.realtime_prices")
        snapshot = table.current_snapshot()
        if snapshot:
            committed_at = datetime.fromtimestamp(
                snapshot.timestamp_ms / 1000, tz=UTC
            )
            lag_seconds = (now_utc - committed_at).total_seconds()
            result["layers"]["bronze"] = {
                "latest_commit": committed_at.isoformat(),
                "lag_seconds": round(lag_seconds, 1),
                "status": "OK" if lag_seconds < 300 else "DELAYED",
                "snapshot_id": str(snapshot.snapshot_id),
            }
        else:
            result["layers"]["bronze"] = {"status": "EMPTY", "lag_seconds": -1}
    except Exception as e:
        result["layers"]["bronze"] = {
            "status": "ERROR",
            "error": f"{type(e).__name__}: {e}",
        }

    # Silver: scan rápido (~2K filas, tabla pequeña)
    try:
        table = load_fresh_table("silver.realtime_vwap")
        snapshot = table.current_snapshot()
        if snapshot:
            committed_at = datetime.fromtimestamp(
                snapshot.timestamp_ms / 1000, tz=UTC
            )
            lag_seconds = (now_utc - committed_at).total_seconds()
            result["layers"]["silver"] = {
                "latest_commit": committed_at.isoformat(),
                "lag_seconds": round(lag_seconds, 1),
                "status": "OK" if lag_seconds < 300 else "DELAYED",
                "snapshot_id": str(snapshot.snapshot_id),
            }
        else:
            result["layers"]["silver"] = {"status": "EMPTY", "lag_seconds": -1}
    except Exception as e:
        result["layers"]["silver"] = {
            "status": "ERROR",
            "error": f"{type(e).__name__}: {e}",
        }

    return result
