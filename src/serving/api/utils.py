try:
    from pyiceberg.catalog import load_catalog
except ImportError:
    load_catalog = None
import os
try:
    import redis
except ImportError:
    redis = None


def get_iceberg_catalog():
    if load_catalog is None:
        raise ImportError("pyiceberg is not installed.")
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
    if redis is None:
        print("⚠️ redis-py no instalado, simulando cliente...")

        class MockRedis:
            def get(self, *args): return None
            def set(self, *args, **kwargs): pass
            def lpush(self, *args): pass
            def lrange(self, *args): return []
            def keys(self, *args): return []
        return MockRedis()
    return redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", 6379)),
        db=0,
        decode_responses=True
    )
