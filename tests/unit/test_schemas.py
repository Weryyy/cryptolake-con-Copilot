"""Unit tests for schema definitions."""
from src.processing.schemas.bronze import (
    BRONZE_FEAR_GREED_SCHEMA,
    BRONZE_HISTORICAL_PRICES_SCHEMA,
    BRONZE_REALTIME_PRICES_SCHEMA,
)


class TestBronzeSchemas:
    """Tests for Bronze layer schemas."""

    def test_realtime_prices_schema_fields(self):
        field_names = [f.name for f in BRONZE_REALTIME_PRICES_SCHEMA.fields]
        assert "coin_id" in field_names
        assert "price_usd" in field_names
        assert "trade_time_ms" in field_names
        assert "source" in field_names

    def test_realtime_prices_required_fields(self):
        required = [
            f.name for f in BRONZE_REALTIME_PRICES_SCHEMA.fields
            if not f.nullable
        ]
        assert "coin_id" in required
        assert "price_usd" in required
        assert "trade_time_ms" in required

    def test_historical_prices_schema_fields(self):
        field_names = [f.name for f in BRONZE_HISTORICAL_PRICES_SCHEMA.fields]
        assert "coin_id" in field_names
        assert "timestamp_ms" in field_names
        assert "price_usd" in field_names
        assert "market_cap_usd" in field_names
        assert "volume_24h_usd" in field_names

    def test_fear_greed_schema_fields(self):
        field_names = [f.name for f in BRONZE_FEAR_GREED_SCHEMA.fields]
        assert "value" in field_names
        assert "classification" in field_names
        assert "timestamp" in field_names

    def test_fear_greed_required_fields(self):
        required = [
            f.name for f in BRONZE_FEAR_GREED_SCHEMA.fields
            if not f.nullable
        ]
        assert "value" in required
        assert "classification" in required
        assert "timestamp" in required
