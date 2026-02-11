"""Health check endpoint."""
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
