"""
Spark Batch job: Bronze → Silver.

Transformaciones:
1. Deduplicación por (coin_id, timestamp)
2. Casting de tipos (timestamps de ms a Timestamp)
3. Null handling con defaults
4. Schema enforcement (rechaza records malformados)
5. Merge incremental (MERGE INTO para no reprocessar todo)
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col,
    current_timestamp,
    from_unixtime,
    row_number,
    when,
)
from pyspark.sql.window import Window

from src.config.settings import settings


def create_spark_session() -> SparkSession:
    return (
        SparkSession.builder.appName("CryptoLake-BronzeToSilver")
        .config("spark.sql.catalog.cryptolake", "org.apache.iceberg.spark.SparkCatalog")
        .config("spark.sql.catalog.cryptolake.type", "rest")
        .config("spark.sql.catalog.cryptolake.uri", settings.iceberg_catalog_uri)
        .config("spark.sql.catalog.cryptolake.io-impl", "org.apache.iceberg.aws.s3.S3FileIO")
        .config("spark.sql.catalog.cryptolake.s3.endpoint", settings.minio_endpoint)
        .config("spark.sql.catalog.cryptolake.s3.path-style-access", "true")
        .config("spark.sql.catalog.cryptolake.s3.access-key-id", settings.minio_access_key)
        .config("spark.sql.catalog.cryptolake.s3.secret-access-key", settings.minio_secret_key)
        .config(
            "spark.sql.extensions",
            "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions",
        )
        .config("spark.sql.defaultCatalog", "cryptolake")
        .getOrCreate()
    )


def process_historical_prices(spark: SparkSession):
    """
    Transforma precios históricos de Bronze a Silver.
    """
    # Asegurar que los namespaces existan
    spark.sql("CREATE NAMESPACE IF NOT EXISTS cryptolake.bronze")
    spark.sql("CREATE NAMESPACE IF NOT EXISTS cryptolake.silver")

    # Leer Bronze
    bronze_df = spark.table("cryptolake.bronze.historical_prices")

    # 1. Convertir timestamp de milisegundos a fecha
    typed_df = bronze_df.withColumn(
        "price_date", from_unixtime(col("timestamp_ms") / 1000).cast("date")
    )

    # 2. Deduplicar: quedarse con el registro más reciente por (coin_id, date)
    dedup_window = Window.partitionBy("coin_id", "price_date").orderBy(col("_ingested_at").desc())
    deduped_df = (
        typed_df.withColumn("_row_num", row_number().over(dedup_window))
        .filter(col("_row_num") == 1)
        .drop("_row_num")
    )

    # 3. Limpiar nulls y valores inválidos
    cleaned_df = (
        deduped_df.filter(col("price_usd") > 0)
        .withColumn(
            "market_cap_usd", when(col("market_cap_usd") > 0, col("market_cap_usd")).otherwise(None)
        )
        .withColumn(
            "volume_24h_usd", when(col("volume_24h_usd") > 0, col("volume_24h_usd")).otherwise(None)
        )
    )

    # 4. Select final Silver columns
    silver_df = cleaned_df.withColumn("_processed_at", current_timestamp()).select(
        "coin_id",
        "price_date",
        "price_usd",
        "market_cap_usd",
        "volume_24h_usd",
        "_processed_at",
    )

    # 5. MERGE INTO Iceberg (upsert incremental)
    silver_df.createOrReplaceTempView("silver_updates")

    spark.sql("""
        CREATE TABLE IF NOT EXISTS cryptolake.silver.daily_prices (
            coin_id         STRING      NOT NULL,
            price_date      DATE        NOT NULL,
            price_usd       DOUBLE      NOT NULL,
            market_cap_usd  DOUBLE,
            volume_24h_usd  DOUBLE,
            _processed_at   TIMESTAMP   NOT NULL
        )
        USING iceberg
        PARTITIONED BY (coin_id)
        TBLPROPERTIES (
            'write.format.default' = 'parquet',
            'write.parquet.compression-codec' = 'zstd'
        )
    """)
    spark.sql("ALTER TABLE cryptolake.silver.daily_prices WRITE ORDERED BY price_date")

    spark.sql("""
        MERGE INTO cryptolake.silver.daily_prices AS target
        USING silver_updates AS source
        ON target.coin_id = source.coin_id
           AND target.price_date = source.price_date
        WHEN MATCHED THEN UPDATE SET *
        WHEN NOT MATCHED THEN INSERT *
    """)

    print(f"✅ Silver daily_prices updated: {silver_df.count()} records")


def process_fear_greed(spark: SparkSession):
    """Transforma Fear & Greed Index de Bronze a Silver."""
    spark.sql("CREATE NAMESPACE IF NOT EXISTS cryptolake.silver")
    bronze_df = spark.table("cryptolake.bronze.fear_greed_index")

    # 1. Deduplicar en Bronze antes de pasar a Silver
    dedup_window = Window.partitionBy("timestamp").orderBy(col("_ingested_at").desc())
    deduped_bronze = (
        bronze_df.withColumn("_row_num", row_number().over(dedup_window))
        .filter(col("_row_num") == 1)
        .drop("_row_num")
    )

    silver_df = (
        deduped_bronze.withColumn("index_date", from_unixtime(col("timestamp")).cast("date"))
        .withColumn("_processed_at", current_timestamp())
        .select(
            col("value").alias("fear_greed_value"),
            "classification",
            "index_date",
            "_processed_at",
        )
    )

    silver_df.createOrReplaceTempView("fg_updates")

    spark.sql("""
        CREATE TABLE IF NOT EXISTS cryptolake.silver.fear_greed (
            fear_greed_value  INT         NOT NULL,
            classification    STRING      NOT NULL,
            index_date        DATE        NOT NULL,
            _processed_at     TIMESTAMP   NOT NULL
        )
        USING iceberg
    """)

    spark.sql("""
        MERGE INTO cryptolake.silver.fear_greed AS target
        USING fg_updates AS source
        ON target.index_date = source.index_date
        WHEN MATCHED THEN UPDATE SET *
        WHEN NOT MATCHED THEN INSERT *
    """)

    print("✅ Silver fear_greed updated")


if __name__ == "__main__":
    spark = create_spark_session()
    process_historical_prices(spark)
    process_fear_greed(spark)
    spark.stop()
