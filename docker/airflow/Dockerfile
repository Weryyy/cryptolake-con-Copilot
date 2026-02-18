# ============================================================
# Apache Airflow con Java y Spark para poder lanzar jobs
# ============================================================
FROM apache/airflow:2.9.3-python3.8

USER root
# Instalar Java (Requerido para spark-submit)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    openjdk-17-jre-headless \
    && rm -rf /var/lib/apt/lists/*

# Configurar JAVA_HOME
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64

USER airflow

# Instalar dependencias Python para los DAGs, Spark, dbt y Data Quality
RUN pip install --no-cache-dir \
    apache-airflow-providers-apache-spark==4.7.1 \
    pyspark==3.5.0 \
    requests==2.31.0 \
    pydantic==2.5.0 \
    pydantic-settings==2.1.0 \
    structlog==24.1.0 \
    redis==5.0.1 \
    dbt-spark[thrift]>=1.8.0 \
    great_expectations>=1.0.0 \
    pyiceberg>=0.7.0 \
    pyarrow>=15.0.0
