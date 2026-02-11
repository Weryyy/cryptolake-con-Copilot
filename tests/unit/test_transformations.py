"""Unit tests for the Binance producer transformations."""
from src.ingestion.streaming.binance_producer import (
    BINANCE_SYMBOLS,
    transform_binance_trade,
)


class TestTransformBinanceTrade:
    """Tests for transform_binance_trade function."""

    def test_basic_transformation(self, sample_binance_trade):
        result = transform_binance_trade(sample_binance_trade)

        assert result["coin_id"] == "bitcoin"
        assert result["symbol"] == "BTCUSDT"
        assert result["price_usd"] == 67432.10
        assert result["quantity"] == 0.123
        assert result["trade_time_ms"] == 1708900000000
        assert result["event_time_ms"] == 1708900000001
        assert result["source"] == "binance_websocket"
        assert result["is_buyer_maker"] is False
        assert "ingested_at" in result

    def test_unknown_symbol_passthrough(self):
        data = {
            "e": "aggTrade",
            "s": "UNKNOWNUSDT",
            "p": "100.0",
            "q": "1.0",
            "T": 1708900000000,
            "E": 1708900000001,
            "m": True,
        }
        result = transform_binance_trade(data)
        assert result["coin_id"] == "unknownusdt"
        assert result["symbol"] == "UNKNOWNUSDT"

    def test_all_symbols_mapped(self):
        expected_coins = {
            "bitcoin", "ethereum", "solana", "cardano",
            "polkadot", "chainlink", "avalanche-2", "matic-network",
        }
        assert set(BINANCE_SYMBOLS.values()) == expected_coins

    def test_price_conversion_to_float(self):
        data = {
            "s": "ETHUSDT",
            "p": "3500.50",
            "q": "10.5",
            "T": 1708900000000,
            "E": 1708900000001,
            "m": False,
        }
        result = transform_binance_trade(data)
        assert isinstance(result["price_usd"], float)
        assert result["price_usd"] == 3500.50

    def test_missing_fields_default(self):
        data = {}
        result = transform_binance_trade(data)
        assert result["coin_id"] == ""
        assert result["price_usd"] == 0.0
        assert result["quantity"] == 0.0
        assert result["trade_time_ms"] == 0
