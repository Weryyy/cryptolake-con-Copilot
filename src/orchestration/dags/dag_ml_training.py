from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

default_args = {
    'owner': 'cryptolake',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'ml_training_memory',
    default_args=default_args,
    description='Entrena modelos historicos y recientes (Memoria Dual)',
    schedule_interval='@daily',
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['ml', 'training'],
) as dag:

    # Entrenar Memoria Histórica (Largo Plazo)
    train_historical = BashOperator(
        task_id='train_historical_model',
        bash_command='docker exec cryptolake-ml python src/ml/train.py historical',
    )

    # Entrenar Memoria Reciente (Corto Plazo - Adaptación rápida)
    train_recent = BashOperator(
        task_id='train_recent_model',
        bash_command='docker exec cryptolake-ml python src/ml/train.py recent',
    )

    # El servicio de inferencia se reinicia para cargar los nuevos pesos
    restart_inference = BashOperator(
        task_id='restart_inference_service',
        bash_command='docker restart cryptolake-ml',
    )

    [train_historical, train_recent] >> restart_inference
