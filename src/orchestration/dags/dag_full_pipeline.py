"""
DAG Master de CryptoLake.

Ejecuta el pipeline completo:
1. Ingesta batch (CoinGecko + Fear & Greed)
2. Bronze load (API → Iceberg Bronze)
3. Silver processing (Bronze → Silver con dedup/clean)
4. Gold transformation (dbt run)
5. Data quality checks (Great Expectations)

Schedule: Diario a las 06:00 UTC
"""
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.utils.task_group import TaskGroup
import json
import sys
import os

# Asegurar que el src está en el path para los workers de Airflow
sys.path.append("/opt/airflow")


def slack_alert(context):
    """Simula una alerta de Slack enviando el error a un log/redis central."""
    ti = context.get('task_instance')
    dag_id = context.get('dag').dag_id
    error_msg = f"❌ Error en DAG {dag_id} | Task: {ti.task_id} | Env: PROD"
    print(error_msg)

    try:
        from src.serving.api.utils import get_redis_client
        from datetime import datetime
        r = get_redis_client()
        alert = {
            "timestamp": datetime.now().timestamp(),
            "level": "CRITICAL",
            "dag_id": dag_id,
            "task_id": ti.task_id,
            "message": error_msg
        }
        r.lpush("system_alerts", json.dumps(alert))
    except Exception as e:
        print(f"No se pudo enviar alerta a Redis: {e}")


def run_extractor(extractor_type, days=7):
    """Función wrapper para evitar lambdas complejos en TaskGroup."""
    if extractor_type == "coingecko":
        from src.ingestion.batch.coingecko_extractor import CoinGeckoExtractor
        return CoinGeckoExtractor(days=days).run()
    elif extractor_type == "fear_greed":
        from src.ingestion.batch.fear_greed_extractor import FearGreedExtractor
        return FearGreedExtractor(days=days).run()


default_args = {
    "owner": "cryptolake",
    "depends_on_past": False,
    "email_on_failure": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "on_failure_callback": slack_alert,
}

with DAG(
    dag_id="cryptolake_full_pipeline",
    default_args=default_args,
    description="Pipeline completo: Ingesta → Bronze → Silver → Gold → Quality",
    schedule="0 6 * * *",
    start_date=datetime(2025, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["cryptolake", "production"],
    doc_md=__doc__,
) as dag:

    # ── GRUPO 1: Ingesta Batch ─────────────────────────────────
    with TaskGroup("ingestion") as ingestion_group:

        extract_coingecko = PythonOperator(
            task_id="extract_coingecko",
            python_callable=run_extractor,
            op_kwargs={"extractor_type": "coingecko", "days": 7}
        )

        extract_fear_greed = PythonOperator(
            task_id="extract_fear_greed",
            python_callable=run_extractor,
            op_kwargs={"extractor_type": "fear_greed", "days": 7}
        )

    # ── GRUPO 2: Bronze Load ───────────────────────────────────
    with TaskGroup("bronze_load") as bronze_group:

        load_to_bronze = BashOperator(
            task_id="api_to_bronze",
            bash_command=(
                "spark-submit --master spark://spark-master:7077 "
                "--conf spark.cores.max=1 --conf spark.executor.memory=1g "
                "--packages org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.5.2,"
                "org.apache.iceberg:iceberg-aws-bundle:1.5.2 "
                "/opt/airflow/src/processing/batch/api_to_bronze.py"
            ),
        )

    # ── GRUPO 3: Silver Processing ─────────────────────────────
    with TaskGroup("silver_processing") as silver_group:

        bronze_to_silver = BashOperator(
            task_id="bronze_to_silver",
            bash_command=(
                "spark-submit --master spark://spark-master:7077 "
                "--conf spark.cores.max=1 --conf spark.executor.memory=1g "
                "--packages org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.5.2,"
                "org.apache.iceberg:iceberg-aws-bundle:1.5.2 "
                "/opt/airflow/src/processing/batch/bronze_to_silver.py"
            ),
        )

    # ── GRUPO 4: Gold Transformation (dbt) ─────────────────────
    with TaskGroup("gold_transformation") as gold_group:

        dbt_run = BashOperator(
            task_id="dbt_run",
            bash_command=(
                "export PATH=$PATH:/home/airflow/.local/bin && "
                "cd /opt/airflow/src/transformation/dbt_cryptolake && "
                "dbt run --profiles-dir . --target prod"
            ),
        )

        dbt_test = BashOperator(
            task_id="dbt_test",
            bash_command=(
                "export PATH=$PATH:/home/airflow/.local/bin && "
                "cd /opt/airflow/src/transformation/dbt_cryptolake && "
                "dbt test --profiles-dir . --target prod"
            ),
        )

        dbt_run >> dbt_test

    # ── GRUPO 5: Data Quality (E2E Validation) ──────────────────
    with TaskGroup("data_quality") as quality_group:

        validate_bronze = BashOperator(
            task_id="validate_bronze",
            bash_command=(
                "python /opt/airflow/src/quality/dq_engine.py bronze.historical_prices bronze_prices_suite"
            ),
        )

        validate_silver = BashOperator(
            task_id="validate_silver",
            bash_command=(
                "python /opt/airflow/src/quality/dq_engine.py silver.daily_prices silver_prices_suite"
            ),
        )

        validate_gold = BashOperator(
            task_id="validate_gold",
            bash_command=(
                "python /opt/airflow/src/quality/dq_engine.py gold.fact_market_daily gold_market_suite"
            ),
        )

    # ── DEPENDENCIAS ───────────────────────────────────────────
    (
        ingestion_group >>
        bronze_group >>
        silver_group >>
        gold_group >>
        quality_group
    )
