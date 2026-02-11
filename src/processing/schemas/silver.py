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

SILVER_DAILY_PRICES_SCHEMA = StructType([
    StructField("coin_id", StringType(), nullable=False),
    StructField("price_date", DateType(), nullable=False),
    StructField("price_usd", DoubleType(), nullable=False),
    StructField("market_cap_usd", DoubleType(), nullable=True),
    StructField("volume_24h_usd", DoubleType(), nullable=True),
    StructField("_processed_at", TimestampType(), nullable=False),
])

SILVER_FEAR_GREED_SCHEMA = StructType([
    StructField("fear_greed_value", IntegerType(), nullable=False),
    StructField("classification", StringType(), nullable=False),
    StructField("index_date", DateType(), nullable=False),
    StructField("_processed_at", TimestampType(), nullable=False),
])
