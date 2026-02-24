"""
API REST de CryptoLake.

Endpoints:
- GET /api/v1/prices/{coin_id} — Precios históricos
- GET /api/v1/analytics/market-overview — Overview del mercado
- GET /api/v1/analytics/fear-greed — Fear & Greed actual
- GET /api/v1/health — Health check
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from src.serving.api.routes import analytics, health, prices


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    yield


app = FastAPI(
    title="CryptoLake API",
    description="Real-time crypto analytics powered by a Lakehouse architecture",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(prices.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")
app.include_router(health.router, prefix="/api/v1")

# Instrument metrics
Instrumentator().instrument(app).expose(app)
