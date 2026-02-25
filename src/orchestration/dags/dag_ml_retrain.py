"""
DAG de Reentrenamiento Periodico de Modelos ML.

Programa reentrenamiento automatico de los modelos de prediccion:
- Ensemble (GB + RF + LSTM): cada 6 horas
- Legacy TFT: diario a las 00:00 UTC (opcional)

El DAG llama al endpoint /api/v1/ml/retrain del API service,
que ejecuta el entrenamiento en background y reporta estado via Redis.
Despues de entrenar, verifica el status y reinicia el servicio de
inferencia si el entrenamiento fue exitoso.

Schedule: Cada 6 horas (0 */6 * * *)
"""

import json
import os
import sys
import time
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.task_group import TaskGroup

sys.path.append("/opt/airflow")

API_URL = os.getenv("API_URL", "http://api:8000")
MAX_WAIT_SECONDS = 1800  # 30 min max para entrenamiento


def _alert_to_redis(context):
    """Envia alerta de fallo a Redis."""
    ti = context.get("task_instance")
    dag_id = context.get("dag").dag_id
    msg = f"[ERROR] DAG {dag_id} | Task: {ti.task_id} fallo"
    print(msg)
    try:
        import redis

        r = redis.Redis(
            host=os.getenv("REDIS_HOST", "redis"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            decode_responses=True,
        )
        alert = {
            "timestamp": datetime.now().timestamp(),
            "level": "WARNING",
            "dag_id": dag_id,
            "task_id": ti.task_id,
            "message": msg,
        }
        r.lpush("system_alerts", json.dumps(alert))
    except Exception as e:
        print(f"No se pudo enviar alerta a Redis: {e}")


def trigger_retrain(mode: str = "ensemble", **kwargs):
    """Dispara el reentrenamiento via API REST.

    Args:
        mode: 'ensemble' o 'legacy'
    """
    import requests

    print(f"[RETRAIN] Disparando reentrenamiento mode={mode}")
    print(f"[RETRAIN] API URL: {API_URL}")

    try:
        resp = requests.post(
            f"{API_URL}/api/v1/ml/retrain",
            params={"mode": mode},
            timeout=30,
        )
        result = resp.json()
        print(f"[RETRAIN] Respuesta: {result}")

        if result.get("status") == "already_running":
            print("[RETRAIN] Ya hay un entrenamiento en curso, esperando...")
        elif result.get("status") != "started":
            raise Exception(f"Error al disparar retrain: {result}")

        return result
    except requests.ConnectionError:
        raise Exception(
            f"No se pudo conectar al API ({API_URL}). "
            "Verifica que el servicio 'api' este corriendo."
        ) from None


def wait_for_completion(mode: str = "ensemble", **kwargs):
    """Espera a que el entrenamiento termine y verifica resultado.

    Hace polling cada 30s al endpoint /ml/retrain-status.
    Falla si el entrenamiento no termina en MAX_WAIT_SECONDS
    o si termina con error.
    """
    import requests

    print(f"[WAIT] Esperando finalizacion del entrenamiento ({mode})...")
    start = time.time()
    last_status = "unknown"

    while (time.time() - start) < MAX_WAIT_SECONDS:
        try:
            resp = requests.get(
                f"{API_URL}/api/v1/ml/retrain-status",
                timeout=15,
            )
            status = resp.json()
            current = status.get("status", "unknown")

            if current != last_status:
                elapsed = int(time.time() - start)
                print(f"[WAIT] Status: {current} (elapsed: {elapsed}s)")
                last_status = current

            if current == "success":
                print(f"[OK] Entrenamiento {mode} completado exitosamente")
                stdout = status.get("stdout_tail", "")
                if stdout:
                    print(f"[OK] Ultimas lineas: {stdout[-200:]}")
                return status

            if current in ("failed", "error", "timeout"):
                stderr = status.get("stderr_tail", "")
                error = status.get("error", "")
                raise Exception(
                    f"Entrenamiento fallo (status={current}). "
                    f"stderr: {stderr[-300:]} error: {error}"
                )

        except requests.ConnectionError:
            print("[WARN] API no disponible, reintentando...")

        time.sleep(30)

    raise Exception(f"Timeout: entrenamiento no termino en {MAX_WAIT_SECONDS}s")


def log_retrain_result(mode: str = "ensemble", **kwargs):
    """Registra resultado del reentrenamiento en Redis para auditoria."""
    import redis as redis_lib

    r = redis_lib.Redis(
        host=os.getenv("REDIS_HOST", "redis"),
        port=int(os.getenv("REDIS_PORT", 6379)),
        decode_responses=True,
    )

    entry = {
        "timestamp": datetime.now().timestamp(),
        "mode": mode,
        "dag_run_id": kwargs.get("run_id", "unknown"),
        "status": "completed",
    }

    # Leer metricas del ultimo entrenamiento desde Redis
    try:
        import requests

        resp = requests.get(f"{API_URL}/api/v1/ml/retrain-status", timeout=15)
        status = resp.json()
        entry["retrain_details"] = status
    except Exception:
        pass

    r.lpush("ml_retrain_history", json.dumps(entry))
    r.ltrim("ml_retrain_history", 0, 99)  # Ultimos 100
    print(f"[LOG] Reentrenamiento registrado: {entry}")


# ──────────────────────────────────────────────────────────────
# DAG Definition
# ──────────────────────────────────────────────────────────────

default_args = {
    "owner": "cryptolake-ml",
    "depends_on_past": False,
    "email_on_failure": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=10),
    "on_failure_callback": _alert_to_redis,
}

with DAG(
    dag_id="cryptolake_ml_retrain",
    default_args=default_args,
    description=("Reentrenamiento periodico de modelos ML (Ensemble cada 6h, Legacy diario)"),
    schedule="0 */6 * * *",
    start_date=datetime(2025, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["cryptolake", "ml", "retraining"],
    doc_md=__doc__,
) as dag:
    # ── Ensemble Retrain ──────────────────────────────────────
    with TaskGroup("ensemble_retrain") as ensemble_group:
        trigger_ensemble = PythonOperator(
            task_id="trigger_ensemble_retrain",
            python_callable=trigger_retrain,
            op_kwargs={"mode": "ensemble"},
        )

        wait_ensemble = PythonOperator(
            task_id="wait_ensemble_completion",
            python_callable=wait_for_completion,
            op_kwargs={"mode": "ensemble"},
            execution_timeout=timedelta(minutes=35),
        )

        log_ensemble = PythonOperator(
            task_id="log_ensemble_result",
            python_callable=log_retrain_result,
            op_kwargs={"mode": "ensemble"},
        )

        trigger_ensemble >> wait_ensemble >> log_ensemble

    # ── Legacy Retrain (solo si es la ejecucion de las 00:00) ─
    with TaskGroup("legacy_retrain") as legacy_group:

        def should_retrain_legacy(**kwargs):
            """Solo reentrenar legacy en la ejecucion de las 00:00 UTC."""
            logical_date = kwargs.get("logical_date", datetime.utcnow())
            hour = logical_date.hour
            if hour != 0:
                print(f"[SKIP] Legacy retrain: hora={hour}, solo a las 00:00")
                return "skip"
            print("[OK] Hora 00:00, procediendo con legacy retrain")
            return "proceed"

        check_legacy_schedule = PythonOperator(
            task_id="check_legacy_schedule",
            python_callable=should_retrain_legacy,
        )

        trigger_legacy = PythonOperator(
            task_id="trigger_legacy_retrain",
            python_callable=trigger_retrain,
            op_kwargs={"mode": "legacy"},
        )

        wait_legacy = PythonOperator(
            task_id="wait_legacy_completion",
            python_callable=wait_for_completion,
            op_kwargs={"mode": "legacy"},
            execution_timeout=timedelta(minutes=35),
        )

        log_legacy = PythonOperator(
            task_id="log_legacy_result",
            python_callable=log_retrain_result,
            op_kwargs={"mode": "legacy"},
        )

        check_legacy_schedule >> trigger_legacy >> wait_legacy >> log_legacy

    # ── Dependencias: primero ensemble, luego legacy ──────────
    ensemble_group >> legacy_group
