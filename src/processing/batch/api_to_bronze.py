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
        .config("spark.sql.extensions",
                "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions")
        .config("spark.sql.defaultCatalog", "cryptolake")
        .getOrCreate()
    )


def load_historical_prices(spark: SparkSession):
    """Extrae precios históricos de CoinGecko y los carga a Bronze."""
    extractor = CoinGeckoExtractor(days=90)
    records = extractor.run()

    if not records:
        return

    df = spark.createDataFrame(records, schema=BRONZE_HISTORICAL_PRICES_SCHEMA)
    df = df.withColumn("_spark_ingested_at", current_timestamp())

    df.writeTo("cryptolake.bronze.historical_prices").append()

    print(f"✅ Loaded {df.count()} historical price records to Bronze")


def load_fear_greed(spark: SparkSession):
    """Extrae Fear & Greed Index y lo carga a Bronze."""
    extractor = FearGreedExtractor(days=90)
    records = extractor.run()

    if not records:
        return

    df = spark.createDataFrame(records, schema=BRONZE_FEAR_GREED_SCHEMA)
    df = df.withColumn("_spark_ingested_at", current_timestamp())

    df.writeTo("cryptolake.bronze.fear_greed_index").append()

    print(f"✅ Loaded {df.count()} Fear & Greed records to Bronze")


if __name__ == "__main__":
    spark = create_spark_session()
    load_historical_prices(spark)
    load_fear_greed(spark)
    spark.stop()
