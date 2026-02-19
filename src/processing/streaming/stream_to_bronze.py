"""
Spark Structured Streaming job: Kafka → Iceberg Bronze.

Lee mensajes en tiempo real de Kafka, los parsea al schema Bronze,
y los escribe como tabla Iceberg con append mode.

Uso: spark-submit --master spark://spark-master:7077 stream_to_bronze.py
"""
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col,
    current_timestamp,
    from_json,
)

from src.config.settings import settings
from src.processing.schemas.bronze import BRONZE_REALTIME_PRICES_SCHEMA


def create_spark_session() -> SparkSession:
    """Crea SparkSession configurada para Iceberg + Kafka."""
    return (
        SparkSession.builder
        .appName("CryptoLake-StreamToBronze")
        .config("spark.sql.catalog.cryptolake", "org.apache.iceberg.spark.SparkCatalog")
        .config("spark.sql.catalog.cryptolake.type", "rest")
        .config("spark.sql.catalog.cryptolake.uri", settings.iceberg_catalog_uri)
        .config("spark.sql.catalog.cryptolake.io-impl",
                "org.apache.iceberg.aws.s3.S3FileIO")
        .config("spark.sql.catalog.cryptolake.s3.endpoint", settings.minio_endpoint)
        .config("spark.sql.catalog.cryptolake.s3.path-style-access", "true")
        .config("spark.sql.catalog.cryptolake.s3.access-key-id", settings.minio_access_key)
        .config("spark.sql.catalog.cryptolake.s3.secret-access-key", settings.minio_secret_key)
        .config("spark.sql.extensions",
                "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions")
        .config("spark.sql.defaultCatalog", "cryptolake")
        .config("spark.sql.shuffle.partitions", "2")
        .config("spark.sql.session.timeZone", "UTC")
        .getOrCreate()
    )


def ensure_bronze_table(spark: SparkSession):
    """Crea la tabla Iceberg Bronze si no existe."""
    spark.sql("CREATE NAMESPACE IF NOT EXISTS bronze")
    spark.sql("""
        CREATE TABLE IF NOT EXISTS bronze.realtime_prices (
            coin_id         STRING,
            symbol          STRING,
            price_usd       DOUBLE,
            quantity         DOUBLE,
            trade_time_ms   BIGINT,
            event_time_ms   BIGINT,
            ingested_at     STRING,
            source          STRING,
            is_buyer_maker  BOOLEAN,
            _spark_ingested_at TIMESTAMP NOT NULL
        )
        USING iceberg
        PARTITIONED BY (coin_id)
        TBLPROPERTIES (
            'write.format.default' = 'parquet',
            'write.parquet.compression-codec' = 'zstd',
            'write.distribution-mode' = 'hash'
        )
    """)
    # Aplicar Sort Order (requiere Spark Iceberg extensions)
    # Esto ayuda a que PyIceberg lea menos datos al filtrar por tiempo
    spark.sql("ALTER TABLE bronze.realtime_prices WRITE ORDERED BY trade_time_ms")


def run_streaming_job():
    """
    Job principal de streaming.

    Flujo:
    1. Lee de Kafka (topic: prices.realtime)
    2. Parsea JSON al schema Bronze
    3. Añade metadata de procesamiento
    4. Escribe a Iceberg Bronze (append mode, micro-batch cada 30s)
    """
    spark = create_spark_session()
    ensure_bronze_table(spark)

    # 1. Leer de Kafka
    kafka_df = (
        spark.readStream
        .format("kafka")
        .option("kafka.bootstrap.servers", settings.kafka_bootstrap_servers)
        .option("subscribe", settings.kafka_topic_prices)
        .option("startingOffsets", "latest")
        .option("failOnDataLoss", "false")
        .load()
    )

    # 2. Parsear JSON del value de Kafka
    parsed_df = (
        kafka_df
        .selectExpr("CAST(value AS STRING) as json_value")
        .select(
            from_json(col("json_value"), BRONZE_REALTIME_PRICES_SCHEMA)
            .alias("data")
        )
        .select("data.*")
    )

    # 3. Añadir metadata de Spark
    enriched_df = parsed_df.withColumn(
        "_spark_ingested_at", current_timestamp()
    )

    # 4. Escribir a Iceberg Bronze
    query = (
        enriched_df.writeStream
        .format("iceberg")
        .outputMode("append")
        .option("path", "bronze.realtime_prices")
        .option("checkpointLocation", "checkpoints/stream_to_bronze")
        .trigger(processingTime="10 seconds")
        .start()
    )

    query.awaitTermination()


if __name__ == "__main__":
    run_streaming_job()
