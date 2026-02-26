"""Kafka configuration utilities."""

from src.config.settings import settings


def get_kafka_config() -> dict:
    """Returns base Kafka configuration."""
    return {
        "bootstrap.servers": settings.kafka_bootstrap_servers,
    }
