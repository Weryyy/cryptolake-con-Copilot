"""
Health Check: Verifica que todos los servicios de CryptoLake están funcionando.

Ejecutar: python scripts/health_check.py
"""
import sys

import requests


def check_service(name: str, url: str, expected_status: int = 200) -> bool:
    """Verifica que un servicio responde correctamente."""
    try:
        response = requests.get(url, timeout=5)
        ok = response.status_code == expected_status
        status = "✅" if ok else f"⚠️ (status {response.status_code})"
        print(f"  {status} {name}: {url}")
        return ok
    except requests.ConnectionError:
        print(f"  ❌ {name}: {url} — No responde")
        return False
    except Exception as e:
        print(f"  ❌ {name}: {url} — Error: {e}")
        return False


def main():
    print("\n🔍 CryptoLake Health Check")
    print("=" * 50)

    results = []

    # MinIO
    results.append(check_service("MinIO API", "http://localhost:9000/minio/health/live"))
    results.append(check_service("MinIO Console", "http://localhost:9001"))

    # Kafka UI
    results.append(check_service("Kafka UI", "http://localhost:8080"))

    # Iceberg REST Catalog
    results.append(check_service("Iceberg Catalog", "http://localhost:8181/v1/config"))

    # Spark UI
    results.append(check_service("Spark Master UI", "http://localhost:8082"))

    # Airflow
    results.append(check_service("Airflow UI", "http://localhost:8083/health"))

    # APIs externas
    print("\n  Fuentes externas:")
    results.append(check_service("CoinGecko API", "https://api.coingecko.com/api/v3/ping"))
    results.append(check_service("Fear & Greed API", "https://api.alternative.me/fng/?limit=1"))

    # Resumen
    total = len(results)
    passed = sum(results)
    print(f"\n{'=' * 50}")
    print(f"Resultado: {passed}/{total} servicios OK")

    if passed == total:
        print("🎉 ¡Todo funcionando correctamente!")
    else:
        print("⚠️  Algunos servicios tienen problemas")
        sys.exit(1)


if __name__ == "__main__":
    main()
