try:
    from pyiceberg.catalog import load_catalog
except ImportError:
    load_catalog = None
import os
from datetime import UTC, datetime

try:
    import redis
except ImportError:
    redis = None


# Cache del catálogo (el catálogo se puede reutilizar)
_catalog = None
_table_cache: dict = {}


def get_iceberg_catalog():
    """Devuelve el catálogo Iceberg REST (singleton cacheado)."""
    global _catalog
    if load_catalog is None:
        raise ImportError("pyiceberg is not installed.")
    if _catalog is None:
        _catalog = load_catalog(
            "cryptolake",
            **{
                "uri": os.getenv("ICEBERG_CATALOG_URI", "http://iceberg-rest:8181"),
                "s3.endpoint": os.getenv("MINIO_ENDPOINT", "http://minio:9000"),
                "s3.access-key-id": os.getenv("AWS_ACCESS_KEY_ID", "cryptolake"),
                "s3.secret-access-key": os.getenv("AWS_SECRET_ACCESS_KEY", "cryptolake123"),
                "s3.region": os.getenv("AWS_REGION", "us-east-1"),
                "s3.path-style-access": "true",
            },
        )
    return _catalog


def load_fresh_table(table_name: str):
    """Carga una tabla Iceberg forzando refresh del snapshot más reciente.

    Cachea el objeto Table para evitar re-cargar toda la metadata en cada
    petición. Solo refresh() es necesario para ver nuevos datos.
    En el primer acceso carga la tabla completa; en los siguientes solo
    llama a refresh() que es mucho más rápido.
    """
    global _table_cache
    if table_name in _table_cache:
        table = _table_cache[table_name]
        table.refresh()
        return table
    catalog = get_iceberg_catalog()
    table = catalog.load_table(table_name)
    table.refresh()
    _table_cache[table_name] = table
    return table


def make_iso_filter(column: str, operator: str, dt: datetime) -> str:
    """Construye un filtro row_filter compatible con PyIceberg para columnas timestamptz.

    PyIceberg requiere formato ISO-8601 estricto (con 'T' y zona horaria)
    para columnas de tipo timestamptz. strftime('%Y-%m-%d %H:%M:%S') NO funciona
    y lanza: ValueError: Invalid timestamp with zone (must be ISO-8601).

    Uso:
        make_iso_filter("window_start", ">=", some_datetime)
        # -> "window_start >= '2026-02-19T14:00:00+00:00'"
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return f"{column} {operator} '{dt.isoformat()}'"


def get_redis_client():
    if redis is None:
        print("⚠️ redis-py no instalado, simulando cliente...")

        class MockRedis:
            def get(self, *args):
                return None

            def set(self, *args, **kwargs):
                pass

            def lpush(self, *args):
                pass

            def lrange(self, *args):
                return []

            def keys(self, *args):
                return []

        return MockRedis()
    return redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", 6379)),
        db=0,
        decode_responses=True,
    )
