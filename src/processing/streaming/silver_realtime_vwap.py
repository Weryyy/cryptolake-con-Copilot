"""
Spark Structured Streaming: Bronze Realtime → Silver Aggregates (VWAP + Anomaly Detection).

Calcula VWAP y Z-Score sobre una ventana de 1 minuto para detectar anomalías.
"""
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, window, sum, avg, stddev,
    when, abs, max as max_, min as min_,
    first, last
)
from src.config.settings import settings


def create_spark_session():
    return (
        SparkSession.builder
        .appName("CryptoLake-SilverRealtimeVWAP")
        .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions")
        .config("spark.sql.catalog.cryptolake", "org.apache.iceberg.spark.SparkCatalog")
        .config("spark.sql.catalog.cryptolake.type", "rest")
        .config("spark.sql.catalog.cryptolake.uri", settings.iceberg_catalog_uri)
        .config("spark.sql.catalog.cryptolake.io-impl", "org.apache.iceberg.aws.s3.S3FileIO")
        .config("spark.sql.catalog.cryptolake.s3.endpoint", settings.minio_endpoint)
        .config("spark.sql.catalog.cryptolake.s3.path-style-access", "true")
        .config("spark.sql.catalog.cryptolake.warehouse", "s3://cryptolake-bronze/")
        .config("spark.hadoop.fs.s3a.endpoint", settings.minio_endpoint)
        .config("spark.hadoop.fs.s3a.access.key", settings.minio_access_key)
        .config("spark.hadoop.fs.s3a.secret.key", settings.minio_secret_key)
        .config("spark.hadoop.fs.s3a.path.style.access", "true")
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
        .config("spark.sql.defaultCatalog", "cryptolake")
        .config("spark.sql.shuffle.partitions", "2")
        .config("spark.sql.session.timeZone", "UTC")
        .getOrCreate()
    )


def run_vwap_job():
    spark = create_spark_session()

    # 1. Leer de la tabla Bronze Realtime (Streaming Source)
    # Iceberg soporta lectura incremental
    stream_df = (
        spark.readStream
        .format("iceberg")
        .load("bronze.realtime_prices")
    )

    # 2. Agregar por ventana de 30 segundos
    # Calculamos VWAP = Sum(Price * Volume) / Sum(Volume)
    aggregated_df = (
        stream_df
        .withColumn("timestamp", (col("trade_time_ms")/1000).cast("timestamp"))
        .withColumn("notional", col("price_usd") * col("quantity"))
        .withWatermark("timestamp", "1 minute")
        .groupBy(
            col("coin_id"),
            window(col("timestamp"), "30 seconds")
        )
        .agg(
            (sum("notional") / sum("quantity")).alias("vwap"),
            sum("quantity").alias("total_volume"),
            avg("price_usd").alias("avg_price"),
            stddev("price_usd").alias("stddev_price"),
            first("price_usd").alias("open"),
            max_("price_usd").alias("high"),
            min_("price_usd").alias("low"),
            last("price_usd").alias("close")
        )
    )

    # 3. Calcular Z-Score y marcar anomalías
    # Z-Score = (Price - Avg) / StdDev
    # Consideramos anomalía si abs(Z) > 3
    enriched_df = (
        aggregated_df
        .withColumn("z_score", (col("vwap") - col("avg_price")) / col("stddev_price"))
        .withColumn("is_anomaly", when(abs(col("z_score")) > 3, 1).otherwise(0))
        .select(
            "coin_id",
            col("window.start").alias("window_start"),
            col("window.end").alias("window_end"),
            "vwap",
            "total_volume",
            "avg_price",
            "stddev_price",
            "open",
            "high",
            "low",
            "close",
            "z_score",
            "is_anomaly"
        )
    )

    # 4. Escribir a Silver Realtime
    spark.sql("""
        CREATE TABLE IF NOT EXISTS silver.realtime_vwap (
            coin_id STRING,
            window_start TIMESTAMP,
            window_end TIMESTAMP,
            vwap DOUBLE,
            total_volume DOUBLE,
            avg_price DOUBLE,
            stddev_price DOUBLE,
            open DOUBLE,
            high DOUBLE,
            low DOUBLE,
            close DOUBLE,
            z_score DOUBLE,
            is_anomaly INT
        ) USING iceberg PARTITIONED BY (coin_id)
    """)

    query = (
        enriched_df.writeStream
        .format("iceberg")
        .outputMode("append")
        .option("path", "silver.realtime_vwap")
        .option("checkpointLocation", "s3a://cryptolake-checkpoints/silver_vwap")
        .trigger(processingTime="10 seconds")
        .start()
    )

    query.awaitTermination()


if __name__ == "__main__":
    run_vwap_job()
