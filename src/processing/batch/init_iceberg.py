from pyspark.sql import SparkSession

from src.config.settings import settings


def init_iceberg():
    spark = (
        SparkSession.builder
        .appName("CryptoLake-InitIceberg")
        .config("spark.sql.catalog.cryptolake", "org.apache.iceberg.spark.SparkCatalog")
        .config("spark.sql.catalog.cryptolake.type", "rest")
        .config("spark.sql.catalog.cryptolake.uri", settings.iceberg_catalog_uri)
        .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions")
        .config("spark.sql.defaultCatalog", "cryptolake")
        .getOrCreate()
    )

    print("Creating namespaces...")
    spark.sql("CREATE NAMESPACE IF NOT EXISTS cryptolake.bronze")
    spark.sql("CREATE NAMESPACE IF NOT EXISTS cryptolake.silver")
    spark.sql("CREATE NAMESPACE IF NOT EXISTS cryptolake.gold")

    print("Creating Bronze tables...")
    spark.sql("""
        CREATE TABLE IF NOT EXISTS cryptolake.bronze.historical_prices (
            coin_id STRING,
            timestamp_ms LONG,
            price_usd DOUBLE,
            market_cap_usd DOUBLE,
            volume_24h_usd DOUBLE,
            _ingested_at STRING,
            _source STRING,
            _spark_ingested_at TIMESTAMP
        ) USING iceberg
        PARTITIONED BY (days(_spark_ingested_at))
    """)

    spark.sql("""
        CREATE TABLE IF NOT EXISTS cryptolake.bronze.fear_greed_index (
            value INT,
            classification STRING,
            timestamp LONG,
            time_until_update STRING,
            _ingested_at STRING,
            _source STRING,
            _spark_ingested_at TIMESTAMP
        ) USING iceberg
        PARTITIONED BY (days(_spark_ingested_at))
    """)

    spark.sql("""
        CREATE TABLE IF NOT EXISTS cryptolake.bronze.realtime_prices (
            coin_id STRING,
            symbol STRING,
            price_usd DOUBLE,
            quantity DOUBLE,
            trade_time_ms LONG,
            event_time_ms LONG,
            ingested_at STRING,
            source STRING,
            is_buyer_maker BOOLEAN,
            _spark_ingested_at TIMESTAMP
        ) USING iceberg
        PARTITIONED BY (days(_spark_ingested_at))
    """)

    print("Iceberg initialization complete!")
    spark.stop()

if __name__ == "__main__":
    init_iceberg()
