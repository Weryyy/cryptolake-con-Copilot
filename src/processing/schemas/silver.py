"""Silver layer schemas for cleaned and deduplicated data."""

from pyspark.sql.types import (
    DateType,
    DoubleType,
    IntegerType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)

SILVER_DAILY_PRICES_SCHEMA = StructType(
    [
        StructField("coin_id", StringType(), nullable=False),
        StructField("price_date", DateType(), nullable=False),
        StructField("price_usd", DoubleType(), nullable=False),
        StructField("market_cap_usd", DoubleType(), nullable=True),
        StructField("volume_24h_usd", DoubleType(), nullable=True),
        StructField("_processed_at", TimestampType(), nullable=False),
    ]
)

SILVER_FEAR_GREED_SCHEMA = StructType(
    [
        StructField("fear_greed_value", IntegerType(), nullable=False),
        StructField("classification", StringType(), nullable=False),
        StructField("index_date", DateType(), nullable=False),
        StructField("_processed_at", TimestampType(), nullable=False),
    ]
)

SILVER_REALTIME_VWAP_SCHEMA = StructType(
    [
        StructField("coin_id", StringType(), nullable=False),
        StructField("window_start", TimestampType(), nullable=False),
        StructField("window_end", TimestampType(), nullable=False),
        StructField("vwap", DoubleType(), nullable=False),
        StructField("total_volume", DoubleType(), nullable=False),
        StructField("avg_price", DoubleType(), nullable=False),
        StructField("stddev_price", DoubleType(), nullable=True),
        StructField("z_score", DoubleType(), nullable=True),
        StructField("is_anomaly", IntegerType(), nullable=False),
    ]
)
