"""
Schemas de la capa Bronze definidos como StructType de Spark.
Bronze = datos raw sin transformar, append-only, particionados por fecha de ingesta.
"""
from pyspark.sql.types import (
    BooleanType,
    DoubleType,
    IntegerType,
    LongType,
    StringType,
    StructField,
    StructType,
)

# Schema para precios en tiempo real (streaming desde Kafka)
BRONZE_REALTIME_PRICES_SCHEMA = StructType([
    StructField("coin_id", StringType(), nullable=False),
    StructField("symbol", StringType(), nullable=False),
    StructField("price_usd", DoubleType(), nullable=False),
    StructField("quantity", DoubleType(), nullable=True),
    StructField("trade_time_ms", LongType(), nullable=False),
    StructField("event_time_ms", LongType(), nullable=True),
    StructField("ingested_at", StringType(), nullable=False),
    StructField("source", StringType(), nullable=False),
    StructField("is_buyer_maker", BooleanType(), nullable=True),
])

# Schema para precios históricos (batch desde CoinGecko)
BRONZE_HISTORICAL_PRICES_SCHEMA = StructType([
    StructField("coin_id", StringType(), nullable=False),
    StructField("timestamp_ms", LongType(), nullable=False),
    StructField("price_usd", DoubleType(), nullable=False),
    StructField("market_cap_usd", DoubleType(), nullable=True),
    StructField("volume_24h_usd", DoubleType(), nullable=True),
    StructField("_ingested_at", StringType(), nullable=False),
    StructField("_source", StringType(), nullable=False),
])

# Schema para Fear & Greed Index
BRONZE_FEAR_GREED_SCHEMA = StructType([
    StructField("value", IntegerType(), nullable=False),
    StructField("classification", StringType(), nullable=False),
    StructField("timestamp", LongType(), nullable=False),
    StructField("time_until_update", StringType(), nullable=True),
    StructField("_ingested_at", StringType(), nullable=False),
    StructField("_source", StringType(), nullable=False),
])
