"""
Quality Check Runner.

Runs all data quality validators (Bronze, Silver, Gold) via Spark
and optionally persists results to the quality.check_results Iceberg table.

Usage:
    docker exec -w /opt/spark/work cryptolake-spark-master \
        /opt/spark/bin/spark-submit src/quality/run_quality_checks.py [--layer bronze|silver|gold|all]
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime

from pyspark.sql import SparkSession

from src.quality.validators import (
    BronzeValidator,
    CheckResult,
    GoldValidator,
    SilverValidator,
)


def persist_results(spark: SparkSession, results: list[CheckResult]):
    """Persist quality check results to Iceberg table."""
    try:
        spark.sql("""
            CREATE NAMESPACE IF NOT EXISTS cryptolake.quality
            LOCATION 's3://cryptolake-gold/quality/'
        """)

        rows = [r.to_dict() for r in results]
        df = spark.createDataFrame(rows)

        # Create or append
        try:
            spark.sql("DESCRIBE TABLE cryptolake.quality.check_results")
            df.writeTo("cryptolake.quality.check_results").append()
        except Exception:
            df.writeTo("cryptolake.quality.check_results").using(
                "iceberg").createOrReplace()

        print(f"✅ {len(rows)} check results persisted to quality.check_results")
    except Exception as e:
        print(f"⚠️ Could not persist results: {e}")


def publish_to_redis(results: list[CheckResult]):
    """Publish DQ summary to Redis for dashboard consumption."""
    try:
        import os

        import redis

        r = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            decode_responses=True,
        )

        # Group by table
        tables: dict[str, list] = {}
        for res in results:
            tables.setdefault(res.table_name, []).append(res)

        for table_name, checks in tables.items():
            total = len(checks)
            passed = sum(1 for c in checks if c.status.value == "passed")
            report = {
                "table_name": table_name.split(".")[-1],
                "success_rate": round(passed / total, 3) if total > 0 else 0,
                "total_expectations": total,
                "successful_expectations": passed,
                "timestamp": datetime.now(UTC).timestamp(),
            }
            key = f"dq_report:{table_name}"
            r.set(key, json.dumps(report))

        print(f"✅ DQ reports published to Redis for {len(tables)} tables")
    except ImportError:
        print("⚠️ redis-py not installed, skipping Redis publish")
    except Exception as e:
        print(f"⚠️ Redis publish failed: {e}")


def main(layer: str = "all"):
    print("=" * 60)
    print(f"CryptoLake — Data Quality Checks (layer={layer})")
    print(f"Time: {datetime.now(UTC).isoformat()}")
    print("=" * 60)

    spark = SparkSession.builder.appName(
        "CryptoLake-QualityChecks").getOrCreate()

    all_results: list[CheckResult] = []

    try:
        if layer in ("all", "bronze"):
            print("\n🟤 BRONZE Layer Checks")
            print("-" * 40)
            bv = BronzeValidator(spark)
            bv.check_all()
            all_results.extend(bv.results)
            summary = bv.get_summary()
            print(f"  Summary: {summary['passed']}/{summary['total']} passed "
                  f"({summary['pass_rate']}%)")

        if layer in ("all", "silver"):
            print("\n⚪ SILVER Layer Checks")
            print("-" * 40)
            sv = SilverValidator(spark)
            sv.check_all()
            all_results.extend(sv.results)
            summary = sv.get_summary()
            print(f"  Summary: {summary['passed']}/{summary['total']} passed "
                  f"({summary['pass_rate']}%)")

        if layer in ("all", "gold"):
            print("\n🟡 GOLD Layer Checks")
            print("-" * 40)
            gv = GoldValidator(spark)
            gv.check_all()
            all_results.extend(gv.results)
            summary = gv.get_summary()
            print(f"  Summary: {summary['passed']}/{summary['total']} passed "
                  f"({summary['pass_rate']}%)")

        # Overall summary
        total = len(all_results)
        passed = sum(1 for r in all_results if r.status.value == "passed")
        failed = sum(1 for r in all_results if r.status.value == "failed")
        warnings = sum(1 for r in all_results if r.status.value == "warning")

        print("\n" + "=" * 60)
        print("OVERALL SUMMARY")
        print("=" * 60)
        print(f"  Total checks:  {total}")
        print(f"  ✅ Passed:     {passed}")
        print(f"  ❌ Failed:     {failed}")
        print(f"  ⚠️  Warnings:   {warnings}")
        print(
            f"  Pass rate:     {round(passed / total * 100, 1) if total > 0 else 0}%")

        # Persist results
        persist_results(spark, all_results)
        publish_to_redis(all_results)

        # Exit code
        if failed > 0:
            print(f"\n❌ {failed} checks FAILED")
            sys.exit(1)
        else:
            print("\n✅ All checks passed!")

    finally:
        spark.stop()


if __name__ == "__main__":
    layer_arg = "all"
    for arg in sys.argv[1:]:
        if arg.startswith("--layer="):
            layer_arg = arg.split("=")[1]
        elif arg == "--layer" and len(sys.argv) > sys.argv.index(arg) + 1:
            layer_arg = sys.argv[sys.argv.index(arg) + 1]
    main(layer=layer_arg)
