"""
DAG de Mantenimiento de Iceberg.

Tareas:
1. Compaction (rewrite_data_files) — Combina archivos pequeños en grandes.
2. Snapshot expiration — Borra snapshots antiguos para liberar espacio.

Schedule: Diarios a las 02:00 UTC
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

default_args = {
    "owner": "cryptolake",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="iceberg_maintenance",
    default_args=default_args,
    schedule="0 2 * * *",
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["maintenance", "iceberg"],
) as dag:
    # Compactación de Bronze Realtime (donde el streaming genera muchos archivos)
    compact_bronze = BashOperator(
        task_id="compact_bronze_realtime",
        bash_command=(
            "spark-submit --master spark://spark-master:7077 "
            "--conf spark.sql.catalog.cryptolake.type=rest "
            "--conf spark.sql.catalog.cryptolake.uri=http://iceberg-rest:8181 "
            '--execute \'CALL cryptolake.system.rewrite_data_files(table => "bronze.realtime_prices", options => map("min-input-files","5"))\''
        ),
    )

    # Limpieza de snapshots antiguos (retener 7 días)
    expire_snapshots = BashOperator(
        task_id="expire_snapshots",
        bash_command=(
            "spark-submit --master spark://spark-master:7077 "
            "--execute 'CALL cryptolake.system.expire_snapshots(table => \"silver.daily_prices\", retain_last => 10)'"
        ),
    )

    compact_bronze >> expire_snapshots
