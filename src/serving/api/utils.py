from pyiceberg.catalog import load_catalog
import os
import redis


def get_iceberg_catalog():
    return load_catalog(
        "cryptolake",
        **{
            "uri": os.getenv("ICEBERG_CATALOG_URI", "http://iceberg-rest:8181"),
            "s3.endpoint": os.getenv("MINIO_ENDPOINT", "http://minio:9000"),
            "s3.access-key-id": os.getenv("AWS_ACCESS_KEY_ID", "cryptolake"),
            "s3.secret-access-key": os.getenv("AWS_SECRET_ACCESS_KEY", "cryptolake123"),
            "s3.region": os.getenv("AWS_REGION", "us-east-1"),
            "s3.path-style-access": "true",
        }
    )


def get_redis_client():
    return redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", 6379)),
        db=0,
        decode_responses=True
    )
