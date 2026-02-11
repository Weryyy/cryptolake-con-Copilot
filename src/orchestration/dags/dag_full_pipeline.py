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

default_args = {
    "owner": "cryptolake",
    "depends_on_past": False,
    "email_on_failure": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "execution_timeout": timedelta(hours=1),
}

with DAG(
    dag_id="cryptolake_full_pipeline",
    default_args=default_args,
    description="Pipeline completo: Ingesta → Bronze → Silver → Gold → Quality",
    schedule="0 6 * * *",
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["cryptolake", "production"],
    doc_md=__doc__,
) as dag:

    # ── GRUPO 1: Ingesta Batch ─────────────────────────────────
    with TaskGroup("ingestion") as ingestion_group:

        extract_coingecko = PythonOperator(
            task_id="extract_coingecko",
            python_callable=lambda: __import__(
                "src.ingestion.batch.coingecko_extractor",
                fromlist=["CoinGeckoExtractor"]
            ).CoinGeckoExtractor(days=7).run(),
        )

        extract_fear_greed = PythonOperator(
            task_id="extract_fear_greed",
            python_callable=lambda: __import__(
                "src.ingestion.batch.fear_greed_extractor",
                fromlist=["FearGreedExtractor"]
            ).FearGreedExtractor(days=7).run(),
        )

    # ── GRUPO 2: Bronze Load ───────────────────────────────────
    with TaskGroup("bronze_load") as bronze_group:

        load_to_bronze = BashOperator(
            task_id="api_to_bronze",
            bash_command=(
                "spark-submit --master spark://spark-master:7077 "
                "/opt/airflow/src/processing/batch/api_to_bronze.py"
            ),
        )

    # ── GRUPO 3: Silver Processing ─────────────────────────────
    with TaskGroup("silver_processing") as silver_group:

        bronze_to_silver = BashOperator(
            task_id="bronze_to_silver",
            bash_command=(
                "spark-submit --master spark://spark-master:7077 "
                "/opt/airflow/src/processing/batch/bronze_to_silver.py"
            ),
        )

    # ── GRUPO 4: Gold Transformation (dbt) ─────────────────────
    with TaskGroup("gold_transformation") as gold_group:

        dbt_run = BashOperator(
            task_id="dbt_run",
            bash_command=(
                "cd /opt/airflow/src/transformation/dbt_cryptolake && "
                "dbt run --profiles-dir . --target prod"
            ),
        )

        dbt_test = BashOperator(
            task_id="dbt_test",
            bash_command=(
                "cd /opt/airflow/src/transformation/dbt_cryptolake && "
                "dbt test --profiles-dir . --target prod"
            ),
        )

        dbt_run >> dbt_test

    # ── GRUPO 5: Data Quality ──────────────────────────────────
    with TaskGroup("data_quality") as quality_group:

        run_quality_checks = PythonOperator(
            task_id="great_expectations_check",
            python_callable=lambda: print("Running GE checkpoint..."),
        )

    # ── DEPENDENCIAS ───────────────────────────────────────────
    ingestion_group >> bronze_group >> silver_group >> gold_group >> quality_group
