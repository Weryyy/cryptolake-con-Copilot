
from pyiceberg.catalog import load_catalog
import pandas as pd


def test_query():
    catalog = load_catalog(
        "cryptolake",
        **{
            "type": "rest",
            "uri": "http://localhost:8181",
            "s3.endpoint": "http://localhost:9000",
            "s3.access-key-id": "cryptolake",
            "s3.secret-access-key": "cryptolake123",
        }
    )

    table = catalog.load_table("silver.daily_prices")
    df = table.scan().to_pandas()
    print(df.head())


if __name__ == "__main__":
    test_query()
