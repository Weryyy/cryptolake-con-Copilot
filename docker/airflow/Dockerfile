# ============================================================
# Apache Airflow con proveedores para Spark y nuestras dependencias
# ============================================================
FROM apache/airflow:2.9.3-python3.11

USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

USER airflow

# Instalar dependencias Python para los DAGs
RUN pip install --no-cache-dir \
    apache-airflow-providers-apache-spark==4.7.1 \
    requests==2.31.0 \
    pydantic==2.5.0 \
    pydantic-settings==2.1.0 \
    structlog==24.1.0
