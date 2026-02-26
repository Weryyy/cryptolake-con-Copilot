"""Unit tests for batch extractors."""

from unittest.mock import MagicMock, patch

from src.ingestion.batch.base_extractor import BaseExtractor
from src.ingestion.batch.coingecko_extractor import CoinGeckoExtractor
from src.ingestion.batch.fear_greed_extractor import FearGreedExtractor


class ConcreteExtractor(BaseExtractor):
    """Concrete implementation for testing the abstract base."""

    def __init__(self):
        super().__init__(source_name="test_source")
        self._data = []

    def extract(self):
        return self._data


class TestBaseExtractor:
    """Tests for BaseExtractor."""

    def test_run_with_empty_data(self):
        extractor = ConcreteExtractor()
        extractor._data = []
        result = extractor.run()
        assert result == []

    def test_run_enriches_data(self):
        extractor = ConcreteExtractor()
        extractor._data = [{"key": "value"}]
        result = extractor.run()
        assert len(result) == 1
        assert "_ingested_at" in result[0]
        assert result[0]["_source"] == "test_source"

    def test_validate_filters_none(self):
        extractor = ConcreteExtractor()
        data = [{"a": 1}, None, {"b": 2}, None]
        result = extractor.validate(data)
        assert len(result) == 2

    def test_enrich_adds_metadata(self):
        extractor = ConcreteExtractor()
        data = [{"key": "value"}]
        result = extractor.enrich(data)
        assert "_ingested_at" in result[0]
        assert result[0]["_source"] == "test_source"


class TestCoinGeckoExtractor:
    """Tests for CoinGeckoExtractor."""

    def test_init_defaults(self):
        extractor = CoinGeckoExtractor()
        assert extractor.days == 90
        assert extractor.source_name == "coingecko"

    def test_init_custom_days(self):
        extractor = CoinGeckoExtractor(days=30)
        assert extractor.days == 30

    def test_validate_filters_invalid_prices(self):
        extractor = CoinGeckoExtractor()
        data = [
            {"coin_id": "bitcoin", "price_usd": 67000.0, "timestamp_ms": 1708819200000},
            {"coin_id": "bitcoin", "price_usd": -1.0, "timestamp_ms": 1708819200000},
            {"coin_id": "bitcoin", "price_usd": 0, "timestamp_ms": 1708819200000},
            {"coin_id": "", "price_usd": 100.0, "timestamp_ms": 1708819200000},
            {"coin_id": "bitcoin", "price_usd": 100.0, "timestamp_ms": 0},
        ]
        result = extractor.validate(data)
        assert len(result) == 1
        assert result[0]["price_usd"] == 67000.0

    @patch("src.ingestion.batch.coingecko_extractor.settings")
    def test_extract_with_mock(self, mock_settings, sample_coingecko_response):
        mock_settings.tracked_coins = ["bitcoin"]
        mock_settings.coingecko_base_url = "https://api.coingecko.com/api/v3"

        extractor = CoinGeckoExtractor(days=3)
        extractor.base_url = mock_settings.coingecko_base_url

        mock_response = MagicMock()
        mock_response.json.return_value = sample_coingecko_response
        mock_response.raise_for_status = MagicMock()

        extractor.session.get = MagicMock(return_value=mock_response)
        result = extractor.extract()

        assert len(result) == 3
        assert result[0]["coin_id"] == "bitcoin"
        assert result[0]["price_usd"] == 67000.0


class TestFearGreedExtractor:
    """Tests for FearGreedExtractor."""

    def test_init_defaults(self):
        extractor = FearGreedExtractor()
        assert extractor.days == 90
        assert extractor.source_name == "fear_greed_index"

    def test_validate_filters_out_of_range(self):
        extractor = FearGreedExtractor()
        data = [
            {"value": 50, "timestamp": 1708819200},
            {"value": -1, "timestamp": 1708819200},
            {"value": 101, "timestamp": 1708819200},
            {"value": 0, "timestamp": 0},
            {"value": 100, "timestamp": 1708819200},
        ]
        result = extractor.validate(data)
        assert len(result) == 2

    @patch("src.ingestion.batch.fear_greed_extractor.settings")
    def test_extract_with_mock(self, mock_settings, sample_fear_greed_response):
        mock_settings.fear_greed_url = "https://api.alternative.me/fng/"

        extractor = FearGreedExtractor(days=2)

        mock_response = MagicMock()
        mock_response.json.return_value = sample_fear_greed_response
        mock_response.raise_for_status = MagicMock()

        extractor.session.get = MagicMock(return_value=mock_response)
        result = extractor.extract()

        assert len(result) == 2
        assert result[0]["value"] == 72
        assert result[0]["classification"] == "Greed"
