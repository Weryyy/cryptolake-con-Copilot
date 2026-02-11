"""Pytest configuration and fixtures."""
import pytest


@pytest.fixture
def sample_binance_trade():
    """Sample Binance aggTrade message."""
    return {
        "e": "aggTrade",
        "s": "BTCUSDT",
        "p": "67432.10",
        "q": "0.123",
        "T": 1708900000000,
        "E": 1708900000001,
        "m": False,
    }


@pytest.fixture
def sample_coingecko_response():
    """Sample CoinGecko market_chart response."""
    return {
        "prices": [
            [1708819200000, 67000.0],
            [1708905600000, 67500.0],
            [1708992000000, 68000.0],
        ],
        "market_caps": [
            [1708819200000, 1300000000000.0],
            [1708905600000, 1310000000000.0],
            [1708992000000, 1320000000000.0],
        ],
        "total_volumes": [
            [1708819200000, 25000000000.0],
            [1708905600000, 26000000000.0],
            [1708992000000, 27000000000.0],
        ],
    }


@pytest.fixture
def sample_fear_greed_response():
    """Sample Fear & Greed API response."""
    return {
        "data": [
            {
                "value": "72",
                "value_classification": "Greed",
                "timestamp": "1708819200",
                "time_until_update": "43200",
            },
            {
                "value": "25",
                "value_classification": "Extreme Fear",
                "timestamp": "1708732800",
                "time_until_update": "43200",
            },
        ],
    }
