from pyspark.sql import SparkSession


def verify():
    spark = SparkSession.builder.getOrCreate()
    print("\n--- DATA VERIFICATION ---")

    tables = [
        "cryptolake.bronze.historical_prices",
        "cryptolake.bronze.fear_greed_index",
        "cryptolake.bronze.realtime_prices",
        "cryptolake.silver.daily_prices"
    ]

    for table in tables:
        try:
            count = spark.table(table).count()
            print(f"Table {table}: {count} records")
            if count > 0:
                spark.table(table).show(5)
        except Exception as e:
            print(f"Error reading {table}: {e}")

    spark.stop()


if __name__ == "__main__":
    verify()
