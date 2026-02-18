"""
Spark Batch job: Carga datos de extractores batch a Iceberg Bronze.

Lee los datos extraídos por los extractores (CoinGecko, Fear & Greed),
los convierte a DataFrame con schema Bronze, y los inserta en Iceberg.
"""
from pyspark.sql import SparkSession
from pyspark.sql.functions import current_timestamp

from src.config.settings import settings
from src.ingestion.batch.coingecko_extractor import CoinGeckoExtractor
from src.ingestion.batch.fear_greed_extractor import FearGreedExtractor
from src.processing.schemas.bronze import (
    BRONZE_FEAR_GREED_SCHEMA,
    BRONZE_HISTORICAL_PRICES_SCHEMA,
)


def create_spark_session() -> SparkSession:
    """Crea SparkSession para jobs batch."""
    return (
        SparkSession.builder
        .appName("CryptoLake-APIToBronze")
        .config("spark.sql.catalog.cryptolake", "org.apache.iceberg.spark.SparkCatalog")
        .config("spark.sql.catalog.cryptolake.type", "rest")
        .config("spark.sql.catalog.cryptolake.uri", settings.iceberg_catalog_uri)
        .config("spark.sql.catalog.cryptolake.io-impl", "org.apache.iceberg.aws.s3.S3FileIO")
        .config("spark.sql.catalog.cryptolake.s3.endpoint", settings.minio_endpoint)
        .config("spark.sql.catalog.cryptolake.s3.path-style-access", "true")
        .config("spark.sql.catalog.cryptolake.s3.access-key-id", settings.minio_access_key)
        .config("spark.sql.catalog.cryptolake.s3.secret-access-key", settings.minio_secret_key)
        .config("spark.sql.extensions",
                "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions")
        .config("spark.sql.defaultCatalog", "cryptolake")
        .getOrCreate()
    )


def load_historical_prices(spark: SparkSession):
    """Extrae precios históricos de CoinGecko y los carga a Bronze."""
    # Asegurar que el namespace existe
    spark.sql("CREATE NAMESPACE IF NOT EXISTS cryptolake.bronze")
    
    # Crear tabla si no existe (con schema explícito)
    spark.sql("""
        CREATE TABLE IF NOT EXISTS cryptolake.bronze.historical_prices (
            coin_id STRING,
            timestamp_ms BIGINT,
            price_usd DOUBLE,
            market_cap_usd DOUBLE,
            volume_24h_usd DOUBLE,
            _ingested_at STRING,
            _source STRING,
            _spark_ingested_at TIMESTAMP
        )
        USING iceberg
        PARTITIONED BY (coin_id)
    """)

    extractor = CoinGeckoExtractor(days=90)
    records = extractor.run()

    if not records:
        print("⚠️ No historical price records extracted from CoinGecko (check rate limits)")
        return

    df = spark.createDataFrame(records, schema=BRONZE_HISTORICAL_PRICES_SCHEMA)
    df = df.withColumn("_spark_ingested_at", current_timestamp())

    df.writeTo("cryptolake.bronze.historical_prices").append()

    print(f"✅ Loaded {df.count()} historical price records to Bronze")


def load_fear_greed(spark: SparkSession):
    """Extrae Fear & Greed Index y lo carga a Bronze."""
    spark.sql("CREATE NAMESPACE IF NOT EXISTS cryptolake.bronze")
    
    spark.sql("""
        CREATE TABLE IF NOT EXISTS cryptolake.bronze.fear_greed_index (
            value INT,
            classification STRING,
            timestamp BIGINT,
            time_until_update STRING,
            _ingested_at STRING,
            _source STRING,
            _spark_ingested_at TIMESTAMP
        )
        USING iceberg
    """)

    extractor = FearGreedExtractor(days=90)
    records = extractor.run()

    if not records:
        print("⚠️ No Fear & Greed records extracted")
        return

    df = spark.createDataFrame(records, schema=BRONZE_FEAR_GREED_SCHEMA)
    df = df.withColumn("_spark_ingested_at", current_timestamp())

    df.writeTo("cryptolake.bronze.fear_greed_index").append()
    print(f"✅ Loaded {df.count()} Fear & Greed records to Bronze")

    print(f"✅ Loaded {df.count()} Fear & Greed records to Bronze")


if __name__ == "__main__":
    spark = create_spark_session()
    load_historical_prices(spark)
    load_fear_greed(spark)
    spark.stop()
