# 🏗️ CryptoLake — Real-Time Crypto Analytics Lakehouse

## Proyecto End-to-End de Data Engineering para Portfolio

> **Un pipeline de datos completo que ingesta precios de criptomonedas en tiempo real y datos históricos, los procesa con arquitectura Lakehouse sobre Apache Iceberg, los transforma con dbt, orquesta con Airflow, y los sirve a través de un dashboard analítico — todo containerizado con Docker, provisionado con Terraform, y desplegado con CI/CD.**

---

## 1. Visión General del Proyecto

### ¿Qué construimos?

Una plataforma de inteligencia de mercado crypto que:

- **Ingesta en streaming** precios en tiempo real desde Binance WebSocket → Kafka
- **Ingesta batch** datos históricos, métricas on-chain y Fear & Greed Index via APIs REST
- **Almacena** en formato Lakehouse con Apache Iceberg sobre MinIO (S3-compatible)
- **Procesa** con Apache Spark (PySpark) tanto batch como streaming
- **Transforma** con dbt aplicando modelado dimensional (Kimball)
- **Orquesta** todos los pipelines con Apache Airflow
- **Valida** calidad de datos con Great Expectations
- **Sirve** resultados via API REST (FastAPI) + Dashboard interactivo (Streamlit)
- **Despliega** todo con Docker Compose (local) y Terraform (cloud)
- **Automatiza** testing y deploy con GitHub Actions CI/CD

### ¿Por qué este proyecto te hace destacar?

La mayoría de juniors presentan proyectos con pandas leyendo un CSV y cargándolo en PostgreSQL. Este proyecto demuestra:

1. **Arquitectura Lakehouse real** con Apache Iceberg (la tendencia más fuerte de 2025-2026)
2. **Streaming + Batch** en el mismo proyecto (dual pipeline)
3. **Modelado dimensional** profesional (star schema con SCDs)
4. **Orquestación de producción** con Airflow DAGs
5. **Data quality automatizada** (no solo "esperar que funcione")
6. **Infrastructure as Code** (Terraform + Docker)
7. **CI/CD completo** (tests, linting, deploy automático)
8. **Documentación de nivel profesional** (data contracts, data dictionary, ADRs)

---

## 2. Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────────────────┐
│                        DATA SOURCES                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────────┐ │
│  │ Binance WS   │  │ CoinGecko    │  │ Alternative.me            │ │
│  │ (Real-time)  │  │ (Historical) │  │ (Fear & Greed Index)      │ │
│  └──────┬───────┘  └──────┬───────┘  └─────────────┬─────────────┘ │
└─────────┼─────────────────┼────────────────────────┼────────────────┘
          │                 │                        │
          ▼                 ▼                        ▼
┌─────────────────┐  ┌─────────────────────────────────────┐
│   KAFKA          │  │   PYTHON EXTRACTORS                 │
│   ┌───────────┐  │  │   (Batch ingestion via Airflow)     │
│   │ Topic:    │  │  │   - historical_prices               │
│   │ prices.   │  │  │   - market_metrics                  │
│   │ realtime  │  │  │   - fear_greed_index                │
│   └─────┬─────┘  │  └──────────────┬──────────────────────┘
│         │        │                 │
└─────────┼────────┘                 │
          │                          │
          ▼                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    LAKEHOUSE (MinIO + Apache Iceberg)                │
│                                                                     │
│  ┌─────────────┐    ┌──────────────┐    ┌────────────────────────┐ │
│  │   BRONZE     │    │   SILVER      │    │   GOLD                 │ │
│  │   (Raw)      │───▶│  (Cleaned)    │───▶│  (Business-ready)      │ │
│  │              │    │              │    │  Star Schema (Kimball)  │ │
│  │ Iceberg      │    │ Iceberg      │    │  Iceberg tables         │ │
│  │ tables       │    │ tables       │    │                         │ │
│  └─────────────┘    └──────────────┘    └────────────────────────┘ │
│         ▲                  ▲                       ▲                │
│         │                  │                       │                │
│    Spark Streaming    Spark Batch              dbt models           │
└─────────────────────────────────────────────────────────────────────┘
          │                                          │
          │         ┌──────────────────┐             │
          │         │   AIRFLOW         │             │
          └────────▶│   (Orchestration) │◀────────────┘
                    │   DAGs            │
                    └──────────────────┘
                             │
                    ┌────────┴────────┐
                    ▼                 ▼
          ┌──────────────┐  ┌──────────────────┐
          │  FastAPI      │  │  Streamlit        │
          │  REST API     │  │  Dashboard        │
          └──────────────┘  └──────────────────┘
                    │
          ┌────────┴────────┐
          ▼                 ▼
  ┌──────────────┐  ┌──────────────────┐
  │  Great        │  │  GitHub Actions   │
  │  Expectations │  │  CI/CD            │
  └──────────────┘  └──────────────────┘
```

### Medallion Architecture (Bronze → Silver → Gold)

| Capa | Contenido | Formato | Procesamiento |
|------|-----------|---------|---------------|
| **Bronze** | Datos raw sin modificar, tal cual llegan | Iceberg (append-only) | Spark Streaming + Batch |
| **Silver** | Datos limpios, deduplicados, tipados, con schema enforcement | Iceberg (merge) | Spark Batch |
| **Gold** | Modelo dimensional (facts + dimensions), métricas pre-calculadas | Iceberg | dbt |

---

## 3. Tech Stack Completo

| Categoría | Tecnología | Versión | Justificación |
|-----------|-----------|---------|---------------|
| **Lenguaje** | Python | 3.11+ | 70% de ofertas DE, ecosistema data completo |
| **SQL** | SQL (vía dbt + Spark SQL) | — | 69-79% de ofertas, transformaciones declarativas |
| **Streaming** | Apache Kafka | 3.7+ | 24% de ofertas, estándar de streaming |
| **Processing** | Apache Spark (PySpark) | 3.5+ | 39% de ofertas, motor unificado batch+stream |
| **Table Format** | Apache Iceberg | 1.5+ | Formato lakehouse dominante 2025-26 |
| **Storage** | MinIO | Latest | S3-compatible local, migrable a AWS S3 |
| **Transformation** | dbt-core + dbt-spark | 1.8+ | Estándar de transformación ELT |
| **Orchestration** | Apache Airflow | 2.9+ | 16% ofertas, estándar de orquestación |
| **Data Quality** | Great Expectations | 1.0+ | Framework de validación más popular |
| **API** | FastAPI | 0.110+ | API REST moderna, async, auto-docs |
| **Dashboard** | Streamlit | 1.35+ | Dashboard rápido en Python |
| **Containers** | Docker + Docker Compose | 24+ | Despliegue reproducible |
| **IaC** | Terraform | 1.8+ | Infrastructure as Code, multi-cloud |
| **CI/CD** | GitHub Actions | — | Integrado con GitHub |
| **Monitoring** | Prometheus + Grafana | — | Observabilidad de pipelines |
| **Code Quality** | Ruff + mypy + pre-commit | — | Linting + type checking |

---

## 4. Estructura del Repositorio

```
cryptolake/
├── .github/
│   └── workflows/
│       ├── ci.yml                    # Tests + linting on PR
│       ├── cd.yml                    # Deploy on merge to main
│       └── data-quality.yml          # Scheduled data quality checks
│
├── docker/
│   ├── airflow/
│   │   └── Dockerfile
│   ├── spark/
│   │   └── Dockerfile
│   ├── kafka/
│   │   └── Dockerfile
│   └── api/
│       └── Dockerfile
│
├── terraform/
│   ├── modules/
│   │   ├── storage/                  # S3/MinIO buckets
│   │   ├── compute/                  # Spark cluster
│   │   └── networking/               # VPC, security groups
│   ├── environments/
│   │   ├── local/
│   │   │   └── main.tf
│   │   └── aws/
│   │       └── main.tf
│   ├── variables.tf
│   └── outputs.tf
│
├── src/
│   ├── __init__.py
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.py               # Pydantic settings
│   │   └── logging.py
│   │
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── streaming/
│   │   │   ├── __init__.py
│   │   │   ├── binance_producer.py    # WebSocket → Kafka
│   │   │   └── kafka_config.py
│   │   └── batch/
│   │       ├── __init__.py
│   │       ├── coingecko_extractor.py # Historical prices
│   │       ├── fear_greed_extractor.py
│   │       └── base_extractor.py      # Abstract base class
│   │
│   ├── processing/
│   │   ├── __init__.py
│   │   ├── streaming/
│   │   │   └── stream_to_bronze.py    # Kafka → Iceberg Bronze
│   │   ├── batch/
│   │   │   ├── bronze_to_silver.py    # Clean + deduplicate
│   │   │   └── api_to_bronze.py       # API data → Iceberg Bronze
│   │   └── schemas/
│   │       ├── __init__.py
│   │       ├── bronze.py              # StructType definitions
│   │       ├── silver.py
│   │       └── contracts.py           # Data contracts (YAML-backed)
│   │
│   ├── transformation/
│   │   └── dbt_cryptolake/
│   │       ├── dbt_project.yml
│   │       ├── profiles.yml
│   │       ├── models/
│   │       │   ├── staging/
│   │       │   │   ├── stg_prices.sql
│   │       │   │   ├── stg_market_metrics.sql
│   │       │   │   └── stg_fear_greed.sql
│   │       │   ├── intermediate/
│   │       │   │   ├── int_price_daily_agg.sql
│   │       │   │   └── int_market_enriched.sql
│   │       │   └── marts/
│   │       │       ├── dim_coins.sql
│   │       │       ├── dim_dates.sql
│   │       │       ├── fact_market_daily.sql
│   │       │       └── fact_price_hourly.sql
│   │       ├── macros/
│   │       │   └── generate_schema_name.sql
│   │       ├── seeds/
│   │       │   └── coin_metadata.csv
│   │       └── tests/
│   │           ├── assert_positive_prices.sql
│   │           └── assert_no_future_dates.sql
│   │
│   ├── quality/
│   │   ├── __init__.py
│   │   ├── expectations/
│   │   │   ├── bronze_prices_suite.json
│   │   │   └── silver_prices_suite.json
│   │   └── checkpoints/
│   │       └── daily_validation.yml
│   │
│   ├── orchestration/
│   │   └── dags/
│   │       ├── dag_batch_ingestion.py
│   │       ├── dag_bronze_to_silver.py
│   │       ├── dag_dbt_transform.py
│   │       ├── dag_data_quality.py
│   │       └── dag_full_pipeline.py   # Master DAG
│   │
│   └── serving/
│       ├── api/
│       │   ├── __init__.py
│       │   ├── main.py                # FastAPI app
│       │   ├── routes/
│       │   │   ├── prices.py
│       │   │   ├── analytics.py
│       │   │   └── health.py
│       │   └── models/
│       │       └── schemas.py         # Pydantic response models
│       └── dashboard/
│           ├── app.py                 # Streamlit dashboard
│           └── components/
│               ├── price_charts.py
│               ├── market_overview.py
│               └── fear_greed_gauge.py
│
├── tests/
│   ├── unit/
│   │   ├── test_extractors.py
│   │   ├── test_schemas.py
│   │   └── test_transformations.py
│   ├── integration/
│   │   ├── test_kafka_pipeline.py
│   │   └── test_spark_jobs.py
│   └── conftest.py                    # Pytest fixtures
│
├── docs/
│   ├── architecture.md                # Architecture Decision Records
│   ├── data_dictionary.md             # Every field documented
│   ├── data_contracts/
│   │   ├── bronze_prices.yml
│   │   └── silver_prices.yml
│   ├── setup_guide.md
│   └── diagrams/
│       └── architecture.mermaid
│
├── scripts/
│   ├── setup_local.sh                 # One-command local setup
│   ├── seed_data.py                   # Load initial seed data
│   └── health_check.py                # Verify all services running
│
├── docker-compose.yml                 # Full local environment
├── docker-compose.override.yml        # Dev overrides
├── Makefile                           # Developer commands
├── pyproject.toml                     # Python project config (uv/poetry)
├── .pre-commit-config.yaml
├── .env.example
├── LICENSE
└── README.md                          # Project showcase README
```

---

## 5. Implementación Paso a Paso

---

### FASE 1: Infraestructura Base (Semana 1)

**Objetivo**: Levantar todo el entorno local con un solo comando.

#### Paso 1.1: Inicializar el repositorio

```bash
mkdir cryptolake && cd cryptolake
git init
```

Crea el `pyproject.toml`:

```toml
[project]
name = "cryptolake"
version = "0.1.0"
description = "Real-time crypto analytics lakehouse"
requires-python = ">=3.11"
dependencies = [
    "pyspark>=3.5.0",
    "kafka-python>=2.0.2",
    "confluent-kafka>=2.3.0",
    "websockets>=12.0",
    "requests>=2.31.0",
    "pydantic>=2.5.0",
    "pydantic-settings>=2.1.0",
    "fastapi>=0.110.0",
    "uvicorn>=0.27.0",
    "streamlit>=1.35.0",
    "great-expectations>=1.0.0",
    "pyiceberg>=0.7.0",
    "pyarrow>=15.0.0",
    "dbt-core>=1.8.0",
    "dbt-spark>=1.8.0",
    "structlog>=24.1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-cov>=4.1",
    "pytest-asyncio>=0.23",
    "ruff>=0.3.0",
    "mypy>=1.8",
    "pre-commit>=3.6",
]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP", "S", "B", "A", "C4", "PT"]

[tool.mypy]
python_version = "3.11"
strict = true

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-v --cov=src --cov-report=term-missing"
```

#### Paso 1.2: Docker Compose — El corazón del entorno local

```yaml
# docker-compose.yml
version: "3.9"

x-common-env: &common-env
  MINIO_ENDPOINT: http://minio:9000
  MINIO_ACCESS_KEY: cryptolake
  MINIO_SECRET_KEY: cryptolake123
  KAFKA_BOOTSTRAP_SERVERS: kafka:29092
  ICEBERG_CATALOG_URI: http://iceberg-rest:8181

services:
  # ============================================================
  # STORAGE LAYER
  # ============================================================
  minio:
    image: minio/minio:latest
    container_name: cryptolake-minio
    ports:
      - "9000:9000"    # API
      - "9001:9001"    # Console
    environment:
      MINIO_ROOT_USER: cryptolake
      MINIO_ROOT_PASSWORD: cryptolake123
    command: server /data --console-address ":9001"
    volumes:
      - minio-data:/data
    healthcheck:
      test: ["CMD", "mc", "ready", "local"]
      interval: 10s
      timeout: 5s
      retries: 5

  minio-init:
    image: minio/mc:latest
    depends_on:
      minio:
        condition: service_healthy
    entrypoint: >
      /bin/sh -c "
      mc alias set local http://minio:9000 cryptolake cryptolake123;
      mc mb local/cryptolake-bronze --ignore-existing;
      mc mb local/cryptolake-silver --ignore-existing;
      mc mb local/cryptolake-gold --ignore-existing;
      mc mb local/cryptolake-checkpoints --ignore-existing;
      echo 'Buckets created successfully';
      "

  # ============================================================
  # ICEBERG REST CATALOG
  # ============================================================
  iceberg-rest:
    image: tabulario/iceberg-rest:1.5.0
    container_name: cryptolake-iceberg-rest
    ports:
      - "8181:8181"
    environment:
      CATALOG_WAREHOUSE: s3://cryptolake-bronze/
      CATALOG_IO__IMPL: org.apache.iceberg.aws.s3.S3FileIO
      CATALOG_S3_ENDPOINT: http://minio:9000
      CATALOG_S3_PATH__STYLE__ACCESS: "true"
      AWS_ACCESS_KEY_ID: cryptolake
      AWS_SECRET_ACCESS_KEY: cryptolake123
      AWS_REGION: us-east-1
    depends_on:
      minio:
        condition: service_healthy

  # ============================================================
  # KAFKA (Streaming)
  # ============================================================
  kafka:
    image: confluentinc/cp-kafka:7.6.0
    container_name: cryptolake-kafka
    ports:
      - "9092:9092"
    environment:
      KAFKA_NODE_ID: 1
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT,EXTERNAL:PLAINTEXT
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:29092,EXTERNAL://localhost:9092
      KAFKA_LISTENERS: PLAINTEXT://0.0.0.0:29092,CONTROLLER://0.0.0.0:29093,EXTERNAL://0.0.0.0:9092
      KAFKA_CONTROLLER_LISTENER_NAMES: CONTROLLER
      KAFKA_CONTROLLER_QUORUM_VOTERS: 1@kafka:29093
      KAFKA_PROCESS_ROLES: broker,controller
      KAFKA_GROUP_INITIAL_REBALANCE_DELAY_MS: 0
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
      KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR: 1
      CLUSTER_ID: MkU3OEVBNTcwNTJENDM2Qk
    volumes:
      - kafka-data:/var/lib/kafka/data
    healthcheck:
      test: kafka-topics --bootstrap-server localhost:29092 --list
      interval: 10s
      timeout: 10s
      retries: 5

  kafka-ui:
    image: provectuslabs/kafka-ui:latest
    container_name: cryptolake-kafka-ui
    ports:
      - "8080:8080"
    environment:
      KAFKA_CLUSTERS_0_NAME: cryptolake
      KAFKA_CLUSTERS_0_BOOTSTRAPSERVERS: kafka:29092
    depends_on:
      kafka:
        condition: service_healthy

  # ============================================================
  # SPARK (Processing)
  # ============================================================
  spark-master:
    build:
      context: ./docker/spark
      dockerfile: Dockerfile
    container_name: cryptolake-spark-master
    ports:
      - "8082:8080"    # Spark UI
      - "7077:7077"    # Spark master
    environment:
      <<: *common-env
      SPARK_MODE: master
    volumes:
      - ./src:/opt/spark/work/src
      - spark-data:/opt/spark/work/data

  spark-worker:
    build:
      context: ./docker/spark
      dockerfile: Dockerfile
    container_name: cryptolake-spark-worker
    environment:
      <<: *common-env
      SPARK_MODE: worker
      SPARK_MASTER_URL: spark://spark-master:7077
      SPARK_WORKER_MEMORY: 2g
      SPARK_WORKER_CORES: 2
    depends_on:
      - spark-master
    volumes:
      - ./src:/opt/spark/work/src

  # ============================================================
  # AIRFLOW (Orchestration)
  # ============================================================
  airflow-postgres:
    image: postgres:16-alpine
    container_name: cryptolake-airflow-db
    environment:
      POSTGRES_USER: airflow
      POSTGRES_PASSWORD: airflow
      POSTGRES_DB: airflow
    volumes:
      - airflow-db-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U airflow"]
      interval: 5s
      timeout: 5s
      retries: 5

  airflow-webserver:
    build:
      context: ./docker/airflow
      dockerfile: Dockerfile
    container_name: cryptolake-airflow-webserver
    ports:
      - "8083:8080"
    environment:
      <<: *common-env
      AIRFLOW__CORE__EXECUTOR: LocalExecutor
      AIRFLOW__DATABASE__SQL_ALCHEMY_CONN: postgresql+psycopg2://airflow:airflow@airflow-postgres/airflow
      AIRFLOW__CORE__FERNET_KEY: ''
      AIRFLOW__WEBSERVER__SECRET_KEY: cryptolake-secret
      AIRFLOW__CORE__DAGS_ARE_PAUSED_AT_CREATION: 'true'
      AIRFLOW__CORE__LOAD_EXAMPLES: 'false'
    volumes:
      - ./src/orchestration/dags:/opt/airflow/dags
      - ./src:/opt/airflow/src
      - airflow-logs:/opt/airflow/logs
    depends_on:
      airflow-postgres:
        condition: service_healthy
    command: >
      bash -c "
      airflow db migrate &&
      airflow users create --username admin --password admin --firstname Admin --lastname User --role Admin --email admin@cryptolake.dev &&
      airflow webserver
      "

  airflow-scheduler:
    build:
      context: ./docker/airflow
      dockerfile: Dockerfile
    container_name: cryptolake-airflow-scheduler
    environment:
      <<: *common-env
      AIRFLOW__CORE__EXECUTOR: LocalExecutor
      AIRFLOW__DATABASE__SQL_ALCHEMY_CONN: postgresql+psycopg2://airflow:airflow@airflow-postgres/airflow
      AIRFLOW__CORE__FERNET_KEY: ''
      AIRFLOW__WEBSERVER__SECRET_KEY: cryptolake-secret
      AIRFLOW__CORE__LOAD_EXAMPLES: 'false'
    volumes:
      - ./src/orchestration/dags:/opt/airflow/dags
      - ./src:/opt/airflow/src
      - airflow-logs:/opt/airflow/logs
    depends_on:
      airflow-postgres:
        condition: service_healthy
    command: airflow scheduler

  # ============================================================
  # SERVING LAYER
  # ============================================================
  api:
    build:
      context: ./docker/api
      dockerfile: Dockerfile
    container_name: cryptolake-api
    ports:
      - "8000:8000"
    environment:
      <<: *common-env
    volumes:
      - ./src:/app/src

  dashboard:
    image: python:3.11-slim
    container_name: cryptolake-dashboard
    ports:
      - "8501:8501"
    environment:
      <<: *common-env
      API_URL: http://api:8000
    volumes:
      - ./src/serving/dashboard:/app
    command: >
      bash -c "pip install streamlit requests plotly pandas &&
      streamlit run /app/app.py --server.address 0.0.0.0"
    depends_on:
      - api

  # ============================================================
  # MONITORING
  # ============================================================
  prometheus:
    image: prom/prometheus:latest
    container_name: cryptolake-prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./docker/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml

  grafana:
    image: grafana/grafana:latest
    container_name: cryptolake-grafana
    ports:
      - "3000:3000"
    environment:
      GF_SECURITY_ADMIN_PASSWORD: cryptolake
    volumes:
      - grafana-data:/var/lib/grafana

volumes:
  minio-data:
  kafka-data:
  spark-data:
  airflow-db-data:
  airflow-logs:
  grafana-data:
```

#### Paso 1.3: Dockerfile de Spark con Iceberg

```dockerfile
# docker/spark/Dockerfile
FROM bitnami/spark:3.5

USER root

# Instalar dependencias de Iceberg y AWS
RUN pip install --no-cache-dir \
    pyspark==3.5.0 \
    pyiceberg[s3fs]==0.7.1 \
    pyarrow==15.0.1 \
    kafka-python==2.0.2 \
    requests==2.31.0 \
    structlog==24.1.0

# Descargar JARs de Iceberg para Spark
ENV ICEBERG_VERSION=1.5.2
ENV AWS_SDK_VERSION=2.24.6

RUN curl -L -o /opt/bitnami/spark/jars/iceberg-spark-runtime-3.5_2.12-${ICEBERG_VERSION}.jar \
    https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-spark-runtime-3.5_2.12/${ICEBERG_VERSION}/iceberg-spark-runtime-3.5_2.12-${ICEBERG_VERSION}.jar && \
    curl -L -o /opt/bitnami/spark/jars/iceberg-aws-bundle-${ICEBERG_VERSION}.jar \
    https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-aws-bundle/${ICEBERG_VERSION}/iceberg-aws-bundle-${ICEBERG_VERSION}.jar

# Configuración de Spark para Iceberg
COPY spark-defaults.conf /opt/bitnami/spark/conf/spark-defaults.conf

USER 1001
```

Crea `docker/spark/spark-defaults.conf`:

```properties
# Iceberg catalog configuration
spark.sql.catalog.cryptolake=org.apache.iceberg.spark.SparkCatalog
spark.sql.catalog.cryptolake.type=rest
spark.sql.catalog.cryptolake.uri=http://iceberg-rest:8181
spark.sql.catalog.cryptolake.io-impl=org.apache.iceberg.aws.s3.S3FileIO
spark.sql.catalog.cryptolake.s3.endpoint=http://minio:9000
spark.sql.catalog.cryptolake.s3.path-style-access=true

# S3/MinIO credentials
spark.hadoop.fs.s3a.endpoint=http://minio:9000
spark.hadoop.fs.s3a.access.key=cryptolake
spark.hadoop.fs.s3a.secret.key=cryptolake123
spark.hadoop.fs.s3a.path.style.access=true
spark.hadoop.fs.s3a.impl=org.apache.hadoop.fs.s3a.S3AFileSystem

# Iceberg extensions
spark.sql.extensions=org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions
spark.sql.defaultCatalog=cryptolake
```

#### Paso 1.4: Makefile — Comandos para el desarrollador

```makefile
# Makefile
.PHONY: help up down logs spark-shell kafka-topics test lint

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
	awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

up: ## Start all services
	docker compose up -d
	@echo "⏳ Waiting for services to be healthy..."
	@sleep 15
	@echo "✅ CryptoLake is running!"
	@echo "   MinIO Console:  http://localhost:9001"
	@echo "   Kafka UI:       http://localhost:8080"
	@echo "   Spark UI:       http://localhost:8082"
	@echo "   Airflow:        http://localhost:8083"
	@echo "   API Docs:       http://localhost:8000/docs"
	@echo "   Dashboard:      http://localhost:8501"
	@echo "   Grafana:        http://localhost:3000"

down: ## Stop all services
	docker compose down

down-clean: ## Stop and remove volumes
	docker compose down -v

logs: ## Tail logs for all services
	docker compose logs -f

spark-shell: ## Open PySpark shell with Iceberg
	docker exec -it cryptolake-spark-master \
	    /opt/bitnami/spark/bin/pyspark

kafka-topics: ## List Kafka topics
	docker exec cryptolake-kafka \
	    kafka-topics --bootstrap-server localhost:29092 --list

kafka-create-topics: ## Create required Kafka topics
	docker exec cryptolake-kafka \
	    kafka-topics --bootstrap-server localhost:29092 \
	    --create --topic prices.realtime \
	    --partitions 6 --replication-factor 1 \
	    --config retention.ms=86400000

test: ## Run all tests
	pytest tests/ -v --cov=src

lint: ## Run linting
	ruff check src/ tests/
	mypy src/

format: ## Format code
	ruff format src/ tests/

dbt-run: ## Run dbt transformations
	cd src/transformation/dbt_cryptolake && dbt run

dbt-test: ## Run dbt tests
	cd src/transformation/dbt_cryptolake && dbt test

quality-check: ## Run Great Expectations validation
	python -m src.quality.run_checkpoint

seed: ## Load seed data
	python scripts/seed_data.py

pipeline: ## Run full pipeline manually
	@echo "🚀 Running full CryptoLake pipeline..."
	python -m src.ingestion.batch.coingecko_extractor
	python -m src.processing.batch.api_to_bronze
	python -m src.processing.batch.bronze_to_silver
	cd src/transformation/dbt_cryptolake && dbt run
	@echo "✅ Pipeline complete!"
```

---

### FASE 2: Ingesta de Datos (Semana 2)

#### Paso 2.1: Configuración centralizada con Pydantic

```python
# src/config/settings.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración centralizada del proyecto. 
    Lee de variables de entorno o archivo .env"""
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # MinIO / S3
    minio_endpoint: str = "http://localhost:9000"
    minio_access_key: str = "cryptolake"
    minio_secret_key: str = "cryptolake123"
    
    # Kafka
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_topic_prices: str = "prices.realtime"
    
    # Iceberg
    iceberg_catalog_uri: str = "http://localhost:8181"
    
    # APIs
    coingecko_base_url: str = "https://api.coingecko.com/api/v3"
    fear_greed_url: str = "https://api.alternative.me/fng/"
    
    # Coins to track
    tracked_coins: list[str] = [
        "bitcoin", "ethereum", "solana", "cardano", 
        "polkadot", "chainlink", "avalanche-2", "polygon"
    ]
    
    # Spark
    spark_master: str = "spark://localhost:7077"
    
    # Buckets
    bronze_bucket: str = "cryptolake-bronze"
    silver_bucket: str = "cryptolake-silver"
    gold_bucket: str = "cryptolake-gold"


settings = Settings()
```

#### Paso 2.2: Productor Kafka — Streaming de precios en tiempo real

```python
# src/ingestion/streaming/binance_producer.py
"""
Productor Kafka que se conecta al WebSocket de Binance
y envía precios de criptomonedas en tiempo real a un topic de Kafka.

Binance envía actualizaciones cada ~1 segundo por par de trading.
"""
import asyncio
import json
from datetime import datetime, timezone

import structlog
import websockets
from confluent_kafka import Producer

from src.config.settings import settings

logger = structlog.get_logger()

# Mapeo de symbols Binance a IDs estándar
BINANCE_SYMBOLS = {
    "btcusdt": "bitcoin",
    "ethusdt": "ethereum", 
    "solusdt": "solana",
    "adausdt": "cardano",
    "dotusdt": "polkadot",
    "linkusdt": "chainlink",
    "avaxusdt": "avalanche-2",
    "maticusdt": "polygon",
}

BINANCE_WS_URL = "wss://stream.binance.com:9443/ws"


def create_kafka_producer() -> Producer:
    """Crea un productor Kafka con configuración optimizada."""
    return Producer({
        "bootstrap.servers": settings.kafka_bootstrap_servers,
        "client.id": "binance-price-producer",
        "acks": "all",                    # Durabilidad: espera confirmación de todas las réplicas
        "compression.type": "snappy",     # Compresión eficiente
        "linger.ms": 100,                 # Agrupa mensajes durante 100ms para mayor throughput
        "batch.size": 65536,              # 64KB batch size
        "retries": 3,
        "retry.backoff.ms": 500,
    })


def delivery_callback(err, msg):
    """Callback para confirmar entrega de mensajes."""
    if err:
        logger.error("delivery_failed", error=str(err), topic=msg.topic())
    else:
        logger.debug(
            "message_delivered",
            topic=msg.topic(),
            partition=msg.partition(),
            offset=msg.offset(),
        )


def transform_binance_trade(data: dict) -> dict:
    """
    Transforma un mensaje raw de Binance al schema estándar de CryptoLake.
    
    Input (Binance aggTrade):
        {"e": "aggTrade", "s": "BTCUSDT", "p": "67432.10", "q": "0.123", "T": 1708900000000, ...}
    
    Output (CryptoLake schema):
        {"coin_id": "bitcoin", "symbol": "BTCUSDT", "price_usd": 67432.10, ...}
    """
    symbol = data.get("s", "").lower()
    coin_id = BINANCE_SYMBOLS.get(symbol, symbol)
    
    return {
        "coin_id": coin_id,
        "symbol": data.get("s", ""),
        "price_usd": float(data.get("p", 0)),
        "quantity": float(data.get("q", 0)),
        "trade_time_ms": data.get("T", 0),
        "event_time_ms": data.get("E", 0),
        "ingested_at": datetime.now(timezone.utc).isoformat(),
        "source": "binance_websocket",
        "is_buyer_maker": data.get("m", False),
    }


async def stream_prices():
    """
    Conecta al WebSocket de Binance y produce mensajes a Kafka.
    
    Usa el endpoint de aggTrade (trades agregados) para cada par.
    Se reconecta automáticamente ante desconexiones.
    """
    producer = create_kafka_producer()
    
    # Construir URL de streams combinados
    streams = [f"{symbol}@aggTrade" for symbol in BINANCE_SYMBOLS.keys()]
    ws_url = f"{BINANCE_WS_URL}/{'/'.join(streams)}"
    
    logger.info("connecting_to_binance", symbols=list(BINANCE_SYMBOLS.keys()))
    
    message_count = 0
    
    while True:  # Reconnection loop
        try:
            async with websockets.connect(ws_url) as ws:
                logger.info("websocket_connected")
                
                async for raw_message in ws:
                    try:
                        data = json.loads(raw_message)
                        
                        # Binance combined streams wrap data in {"stream": ..., "data": {...}}
                        if "data" in data:
                            data = data["data"]
                        
                        # Solo procesar aggTrade events
                        if data.get("e") != "aggTrade":
                            continue
                        
                        # Transformar al schema de CryptoLake
                        record = transform_binance_trade(data)
                        
                        # Producir a Kafka con coin_id como key (para particionado)
                        producer.produce(
                            topic=settings.kafka_topic_prices,
                            key=record["coin_id"].encode("utf-8"),
                            value=json.dumps(record).encode("utf-8"),
                            callback=delivery_callback,
                        )
                        
                        message_count += 1
                        if message_count % 1000 == 0:
                            producer.flush()
                            logger.info("progress", messages_produced=message_count)
                            
                    except (json.JSONDecodeError, KeyError, ValueError) as e:
                        logger.warning("message_parse_error", error=str(e))
                        continue
                        
        except websockets.exceptions.ConnectionClosed:
            logger.warning("websocket_disconnected", reconnecting_in="5s")
            producer.flush()
            await asyncio.sleep(5)
        except Exception as e:
            logger.error("unexpected_error", error=str(e), reconnecting_in="10s")
            producer.flush()
            await asyncio.sleep(10)


if __name__ == "__main__":
    asyncio.run(stream_prices())
```

#### Paso 2.3: Extractores Batch — CoinGecko y Fear & Greed

```python
# src/ingestion/batch/base_extractor.py
"""Clase base abstracta para todos los extractores batch."""
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

import requests
import structlog

logger = structlog.get_logger()


class BaseExtractor(ABC):
    """
    Template Method Pattern: define el flujo extract → validate → save.
    Cada extractor concreto implementa los métodos abstractos.
    """
    
    def __init__(self, source_name: str):
        self.source_name = source_name
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "CryptoLake/1.0"})
    
    def run(self) -> list[dict[str, Any]]:
        """Ejecuta el pipeline completo de extracción."""
        logger.info("extraction_started", source=self.source_name)
        
        raw_data = self.extract()
        validated_data = self.validate(raw_data)
        enriched_data = self.enrich(validated_data)
        
        logger.info(
            "extraction_completed",
            source=self.source_name,
            records=len(enriched_data),
        )
        return enriched_data
    
    @abstractmethod
    def extract(self) -> list[dict[str, Any]]:
        """Extrae datos de la fuente. Debe ser implementado."""
        ...
    
    def validate(self, data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Validación básica. Override para validación específica."""
        if not data:
            logger.warning("no_data_extracted", source=self.source_name)
        return [r for r in data if r is not None]
    
    def enrich(self, data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Añade metadata de ingesta a cada record."""
        now = datetime.now(timezone.utc).isoformat()
        for record in data:
            record["_ingested_at"] = now
            record["_source"] = self.source_name
        return data
```

```python
# src/ingestion/batch/coingecko_extractor.py
"""
Extractor de datos históricos de precios desde CoinGecko API.

CoinGecko free tier: 30 calls/min, sin API key.
Endpoint usado: /coins/{id}/market_chart para obtener 
price, market_cap y volume históricos.
"""
import time
from typing import Any

import structlog

from src.config.settings import settings
from src.ingestion.batch.base_extractor import BaseExtractor

logger = structlog.get_logger()


class CoinGeckoExtractor(BaseExtractor):
    """Extrae precios históricos y métricas de mercado de CoinGecko."""
    
    def __init__(self, days: int = 90):
        super().__init__(source_name="coingecko")
        self.days = days
        self.base_url = settings.coingecko_base_url
    
    def extract(self) -> list[dict[str, Any]]:
        """
        Extrae datos de todos los coins configurados.
        
        Para cada coin obtiene:
        - Precios históricos (USD)
        - Market cap histórico
        - Volumen de trading histórico
        
        Respeta rate limiting con sleep entre requests.
        """
        all_records = []
        
        for coin_id in settings.tracked_coins:
            try:
                logger.info("extracting_coin", coin=coin_id, days=self.days)
                
                # GET /coins/{id}/market_chart
                response = self.session.get(
                    f"{self.base_url}/coins/{coin_id}/market_chart",
                    params={
                        "vs_currency": "usd",
                        "days": str(self.days),
                        "interval": "daily",
                    },
                    timeout=30,
                )
                response.raise_for_status()
                data = response.json()
                
                # CoinGecko devuelve arrays: [[timestamp_ms, value], ...]
                prices = data.get("prices", [])
                market_caps = data.get("market_caps", [])
                volumes = data.get("total_volumes", [])
                
                # Combinar las tres series por timestamp
                for i, price_point in enumerate(prices):
                    timestamp_ms, price = price_point
                    record = {
                        "coin_id": coin_id,
                        "timestamp_ms": timestamp_ms,
                        "price_usd": price,
                        "market_cap_usd": (
                            market_caps[i][1] if i < len(market_caps) else None
                        ),
                        "volume_24h_usd": (
                            volumes[i][1] if i < len(volumes) else None
                        ),
                    }
                    all_records.append(record)
                
                logger.info(
                    "coin_extracted",
                    coin=coin_id,
                    datapoints=len(prices),
                )
                
                # Rate limiting: CoinGecko free = 30 calls/min
                time.sleep(2.5)
                
            except Exception as e:
                logger.error("extraction_failed", coin=coin_id, error=str(e))
                continue
        
        return all_records
    
    def validate(self, data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Valida que los precios sean positivos y los timestamps válidos."""
        valid = []
        for record in data:
            if (
                record.get("price_usd") is not None
                and record["price_usd"] > 0
                and record.get("timestamp_ms") is not None
                and record["timestamp_ms"] > 0
            ):
                valid.append(record)
            else:
                logger.warning("invalid_record", record=record)
        
        logger.info("validation_complete", total=len(data), valid=len(valid))
        return valid


if __name__ == "__main__":
    extractor = CoinGeckoExtractor(days=90)
    data = extractor.run()
    print(f"Extracted {len(data)} records")
```

```python
# src/ingestion/batch/fear_greed_extractor.py
"""
Extractor del Crypto Fear & Greed Index desde Alternative.me.

El índice mide el sentimiento del mercado crypto en una escala de 0-100:
- 0-24: Extreme Fear
- 25-49: Fear  
- 50-74: Greed
- 75-100: Extreme Greed
"""
from typing import Any

import structlog

from src.config.settings import settings
from src.ingestion.batch.base_extractor import BaseExtractor

logger = structlog.get_logger()


class FearGreedExtractor(BaseExtractor):
    """Extrae el índice Fear & Greed histórico."""
    
    def __init__(self, days: int = 90):
        super().__init__(source_name="fear_greed_index")
        self.days = days
    
    def extract(self) -> list[dict[str, Any]]:
        """Extrae datos históricos del Fear & Greed Index."""
        response = self.session.get(
            settings.fear_greed_url,
            params={"limit": str(self.days), "format": "json"},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        
        records = []
        for entry in data.get("data", []):
            records.append({
                "value": int(entry["value"]),
                "classification": entry["value_classification"],
                "timestamp": int(entry["timestamp"]),
                "time_until_update": entry.get("time_until_update"),
            })
        
        logger.info("fear_greed_extracted", records=len(records))
        return records


if __name__ == "__main__":
    extractor = FearGreedExtractor(days=90)
    data = extractor.run()
    print(f"Extracted {len(data)} Fear & Greed records")
```

---

### FASE 3: Lakehouse — Bronze Layer con Iceberg (Semana 3)

#### Paso 3.1: Schemas tipados y Data Contracts

```python
# src/processing/schemas/bronze.py
"""
Schemas de la capa Bronze definidos como StructType de Spark.
Bronze = datos raw sin transformar, append-only, particionados por fecha de ingesta.
"""
from pyspark.sql.types import (
    BooleanType,
    DoubleType,
    IntegerType,
    LongType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)

# Schema para precios en tiempo real (streaming desde Kafka)
BRONZE_REALTIME_PRICES_SCHEMA = StructType([
    StructField("coin_id", StringType(), nullable=False),
    StructField("symbol", StringType(), nullable=False),
    StructField("price_usd", DoubleType(), nullable=False),
    StructField("quantity", DoubleType(), nullable=True),
    StructField("trade_time_ms", LongType(), nullable=False),
    StructField("event_time_ms", LongType(), nullable=True),
    StructField("ingested_at", StringType(), nullable=False),
    StructField("source", StringType(), nullable=False),
    StructField("is_buyer_maker", BooleanType(), nullable=True),
])

# Schema para precios históricos (batch desde CoinGecko)
BRONZE_HISTORICAL_PRICES_SCHEMA = StructType([
    StructField("coin_id", StringType(), nullable=False),
    StructField("timestamp_ms", LongType(), nullable=False),
    StructField("price_usd", DoubleType(), nullable=False),
    StructField("market_cap_usd", DoubleType(), nullable=True),
    StructField("volume_24h_usd", DoubleType(), nullable=True),
    StructField("_ingested_at", StringType(), nullable=False),
    StructField("_source", StringType(), nullable=False),
])

# Schema para Fear & Greed Index
BRONZE_FEAR_GREED_SCHEMA = StructType([
    StructField("value", IntegerType(), nullable=False),
    StructField("classification", StringType(), nullable=False),
    StructField("timestamp", LongType(), nullable=False),
    StructField("time_until_update", StringType(), nullable=True),
    StructField("_ingested_at", StringType(), nullable=False),
    StructField("_source", StringType(), nullable=False),
])
```

```yaml
# docs/data_contracts/bronze_prices.yml
# Data Contract: Define el acuerdo entre productor y consumidor
# Si el schema cambia, AMBOS lados deben acordar y versionar el cambio.
contract:
  name: bronze_realtime_prices
  version: "1.0.0"
  owner: ingestion-team
  description: >
    Precios de criptomonedas en tiempo real desde Binance WebSocket.
    Datos raw sin transformar, append-only.

schema:
  type: record
  fields:
    - name: coin_id
      type: string
      required: true
      description: "Identificador único del coin (ej: bitcoin, ethereum)"
    - name: price_usd
      type: double
      required: true
      constraints:
        minimum: 0
        description: "Precio en USD, siempre positivo"
    - name: trade_time_ms
      type: long
      required: true
      description: "Timestamp del trade en milisegundos epoch"

quality:
  freshness:
    max_delay: "5 minutes"
    description: "Datos no deben tener más de 5 min de retraso"
  completeness:
    required_fields_not_null: ["coin_id", "price_usd", "trade_time_ms"]
  volume:
    min_records_per_hour: 1000
    description: "Al menos 1000 trades/hora durante mercado activo"

sla:
  availability: "99.5%"
  support_channel: "#data-engineering"
```

#### Paso 3.2: Spark Streaming — Kafka a Iceberg Bronze

```python
# src/processing/streaming/stream_to_bronze.py
"""
Spark Structured Streaming job: Kafka → Iceberg Bronze.

Lee mensajes en tiempo real de Kafka, los parsea al schema Bronze,
y los escribe como tabla Iceberg con append mode.

Uso: spark-submit --master spark://spark-master:7077 stream_to_bronze.py
"""
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col,
    current_timestamp,
    from_json,
    to_timestamp,
    window,
)

from src.config.settings import settings
from src.processing.schemas.bronze import BRONZE_REALTIME_PRICES_SCHEMA


def create_spark_session() -> SparkSession:
    """Crea SparkSession configurada para Iceberg + Kafka."""
    return (
        SparkSession.builder
        .appName("CryptoLake-StreamToBronze")
        .config("spark.sql.catalog.cryptolake", "org.apache.iceberg.spark.SparkCatalog")
        .config("spark.sql.catalog.cryptolake.type", "rest")
        .config("spark.sql.catalog.cryptolake.uri", settings.iceberg_catalog_uri)
        .config("spark.sql.catalog.cryptolake.io-impl", 
                "org.apache.iceberg.aws.s3.S3FileIO")
        .config("spark.sql.catalog.cryptolake.s3.endpoint", settings.minio_endpoint)
        .config("spark.sql.catalog.cryptolake.s3.path-style-access", "true")
        .config("spark.sql.extensions", 
                "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions")
        .config("spark.sql.defaultCatalog", "cryptolake")
        .getOrCreate()
    )


def ensure_bronze_table(spark: SparkSession):
    """Crea la tabla Iceberg Bronze si no existe."""
    spark.sql("""
        CREATE TABLE IF NOT EXISTS cryptolake.bronze.realtime_prices (
            coin_id         STRING      NOT NULL,
            symbol          STRING      NOT NULL,
            price_usd       DOUBLE      NOT NULL,
            quantity         DOUBLE,
            trade_time_ms   BIGINT      NOT NULL,
            event_time_ms   BIGINT,
            ingested_at     STRING      NOT NULL,
            source          STRING      NOT NULL,
            is_buyer_maker  BOOLEAN,
            _spark_ingested_at TIMESTAMP NOT NULL
        )
        USING iceberg
        PARTITIONED BY (days(trade_time_ts))
        TBLPROPERTIES (
            'write.format.default' = 'parquet',
            'write.parquet.compression-codec' = 'zstd',
            'write.metadata.delete-after-commit.enabled' = 'true',
            'write.metadata.previous-versions-max' = '10'
        )
    """)


def run_streaming_job():
    """
    Job principal de streaming.
    
    Flujo:
    1. Lee de Kafka (topic: prices.realtime)
    2. Parsea JSON al schema Bronze
    3. Añade metadata de procesamiento
    4. Escribe a Iceberg Bronze (append mode, micro-batch cada 30s)
    """
    spark = create_spark_session()
    ensure_bronze_table(spark)
    
    # 1. Leer de Kafka
    kafka_df = (
        spark.readStream
        .format("kafka")
        .option("kafka.bootstrap.servers", settings.kafka_bootstrap_servers)
        .option("subscribe", settings.kafka_topic_prices)
        .option("startingOffsets", "latest")
        .option("failOnDataLoss", "false")
        .load()
    )
    
    # 2. Parsear JSON del value de Kafka
    parsed_df = (
        kafka_df
        .selectExpr("CAST(value AS STRING) as json_value")
        .select(
            from_json(col("json_value"), BRONZE_REALTIME_PRICES_SCHEMA)
            .alias("data")
        )
        .select("data.*")
    )
    
    # 3. Añadir metadata de Spark
    enriched_df = parsed_df.withColumn(
        "_spark_ingested_at", current_timestamp()
    )
    
    # 4. Escribir a Iceberg Bronze
    query = (
        enriched_df.writeStream
        .format("iceberg")
        .outputMode("append")
        .option("path", "cryptolake.bronze.realtime_prices")
        .option("checkpointLocation", 
                f"s3a://{settings.bronze_bucket}/checkpoints/stream_to_bronze")
        .trigger(processingTime="30 seconds")  # Micro-batch cada 30s
        .start()
    )
    
    query.awaitTermination()


if __name__ == "__main__":
    run_streaming_job()
```

#### Paso 3.3: Batch — API data a Iceberg Bronze

```python
# src/processing/batch/api_to_bronze.py
"""
Spark Batch job: Carga datos de extractores batch a Iceberg Bronze.

Lee los datos extraídos por los extractores (CoinGecko, Fear & Greed),
los convierte a DataFrame con schema Bronze, y los inserta en Iceberg.
"""
import json

from pyspark.sql import SparkSession
from pyspark.sql.functions import current_timestamp, lit

from src.config.settings import settings
from src.ingestion.batch.coingecko_extractor import CoinGeckoExtractor
from src.ingestion.batch.fear_greed_extractor import FearGreedExtractor
from src.processing.schemas.bronze import (
    BRONZE_FEAR_GREED_SCHEMA,
    BRONZE_HISTORICAL_PRICES_SCHEMA,
)


def create_spark_session() -> SparkSession:
    """Crea SparkSession para jobs batch."""
    return (
        SparkSession.builder
        .appName("CryptoLake-APIToBronze")
        .config("spark.sql.catalog.cryptolake", "org.apache.iceberg.spark.SparkCatalog")
        .config("spark.sql.catalog.cryptolake.type", "rest")
        .config("spark.sql.catalog.cryptolake.uri", settings.iceberg_catalog_uri)
        .config("spark.sql.extensions",
                "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions")
        .config("spark.sql.defaultCatalog", "cryptolake")
        .getOrCreate()
    )


def load_historical_prices(spark: SparkSession):
    """Extrae precios históricos de CoinGecko y los carga a Bronze."""
    # Extraer datos
    extractor = CoinGeckoExtractor(days=90)
    records = extractor.run()
    
    if not records:
        return
    
    # Crear DataFrame con schema tipado
    df = spark.createDataFrame(records, schema=BRONZE_HISTORICAL_PRICES_SCHEMA)
    
    # Añadir metadata de procesamiento Spark
    df = df.withColumn("_spark_ingested_at", current_timestamp())
    
    # Escribir a Iceberg Bronze (append para preservar historial)
    df.writeTo("cryptolake.bronze.historical_prices").append()
    
    print(f"✅ Loaded {df.count()} historical price records to Bronze")


def load_fear_greed(spark: SparkSession):
    """Extrae Fear & Greed Index y lo carga a Bronze."""
    extractor = FearGreedExtractor(days=90)
    records = extractor.run()
    
    if not records:
        return
    
    df = spark.createDataFrame(records, schema=BRONZE_FEAR_GREED_SCHEMA)
    df = df.withColumn("_spark_ingested_at", current_timestamp())
    
    df.writeTo("cryptolake.bronze.fear_greed_index").append()
    
    print(f"✅ Loaded {df.count()} Fear & Greed records to Bronze")


if __name__ == "__main__":
    spark = create_spark_session()
    load_historical_prices(spark)
    load_fear_greed(spark)
    spark.stop()
```

---

### FASE 4: Silver Layer — Limpieza y Calidad (Semana 4)

#### Paso 4.1: Bronze to Silver — Spark Batch

```python
# src/processing/batch/bronze_to_silver.py
"""
Spark Batch job: Bronze → Silver.

Transformaciones:
1. Deduplicación por (coin_id, timestamp)
2. Casting de tipos (timestamps de ms a Timestamp)
3. Null handling con defaults
4. Schema enforcement (rechaza records malformados)
5. Merge incremental (MERGE INTO para no reprocessar todo)
"""
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col,
    current_timestamp,
    from_unixtime,
    row_number,
    when,
)
from pyspark.sql.window import Window


def create_spark_session() -> SparkSession:
    return (
        SparkSession.builder
        .appName("CryptoLake-BronzeToSilver")
        .config("spark.sql.extensions",
                "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions")
        .config("spark.sql.defaultCatalog", "cryptolake")
        .getOrCreate()
    )


def process_historical_prices(spark: SparkSession):
    """
    Transforma precios históricos de Bronze a Silver.
    
    Silver schema:
    - coin_id (STRING, PK part 1)
    - price_date (DATE, PK part 2) 
    - price_usd (DOUBLE, cleaned)
    - market_cap_usd (DOUBLE, cleaned)
    - volume_24h_usd (DOUBLE, cleaned)
    - price_change_pct (DOUBLE, calculated)
    - _processed_at (TIMESTAMP)
    """
    # Leer Bronze
    bronze_df = spark.table("cryptolake.bronze.historical_prices")
    
    # 1. Convertir timestamp de milisegundos a fecha
    typed_df = bronze_df.withColumn(
        "price_date",
        from_unixtime(col("timestamp_ms") / 1000).cast("date")
    )
    
    # 2. Deduplicar: quedarse con el registro más reciente por (coin_id, date)
    dedup_window = Window.partitionBy("coin_id", "price_date").orderBy(
        col("_ingested_at").desc()
    )
    deduped_df = (
        typed_df
        .withColumn("_row_num", row_number().over(dedup_window))
        .filter(col("_row_num") == 1)
        .drop("_row_num")
    )
    
    # 3. Limpiar nulls y valores inválidos
    cleaned_df = (
        deduped_df
        .filter(col("price_usd") > 0)
        .withColumn(
            "market_cap_usd",
            when(col("market_cap_usd") > 0, col("market_cap_usd")).otherwise(None)
        )
        .withColumn(
            "volume_24h_usd",
            when(col("volume_24h_usd") > 0, col("volume_24h_usd")).otherwise(None)
        )
    )
    
    # 4. Calcular price change % (day over day)
    price_window = Window.partitionBy("coin_id").orderBy("price_date")
    
    silver_df = (
        cleaned_df
        .withColumn("_prev_price", col("price_usd"))  # Simplificado; lag real abajo
        .withColumn("_processed_at", current_timestamp())
        .select(
            "coin_id",
            "price_date",
            "price_usd",
            "market_cap_usd",
            "volume_24h_usd",
            "_processed_at",
        )
    )
    
    # 5. MERGE INTO Iceberg (upsert incremental)
    silver_df.createOrReplaceTempView("silver_updates")
    
    spark.sql("""
        CREATE TABLE IF NOT EXISTS cryptolake.silver.daily_prices (
            coin_id         STRING      NOT NULL,
            price_date      DATE        NOT NULL,
            price_usd       DOUBLE      NOT NULL,
            market_cap_usd  DOUBLE,
            volume_24h_usd  DOUBLE,
            _processed_at   TIMESTAMP   NOT NULL
        )
        USING iceberg
        PARTITIONED BY (coin_id)
    """)
    
    spark.sql("""
        MERGE INTO cryptolake.silver.daily_prices AS target
        USING silver_updates AS source
        ON target.coin_id = source.coin_id 
           AND target.price_date = source.price_date
        WHEN MATCHED THEN UPDATE SET *
        WHEN NOT MATCHED THEN INSERT *
    """)
    
    print(f"✅ Silver daily_prices updated: {silver_df.count()} records")


def process_fear_greed(spark: SparkSession):
    """Transforma Fear & Greed Index de Bronze a Silver."""
    bronze_df = spark.table("cryptolake.bronze.fear_greed_index")
    
    silver_df = (
        bronze_df
        .withColumn("index_date", from_unixtime(col("timestamp")).cast("date"))
        .withColumn("_processed_at", current_timestamp())
        .select(
            col("value").alias("fear_greed_value"),
            "classification",
            "index_date",
            "_processed_at",
        )
    )
    
    silver_df.createOrReplaceTempView("fg_updates")
    
    spark.sql("""
        CREATE TABLE IF NOT EXISTS cryptolake.silver.fear_greed (
            fear_greed_value  INT         NOT NULL,
            classification    STRING      NOT NULL,
            index_date        DATE        NOT NULL,
            _processed_at     TIMESTAMP   NOT NULL
        )
        USING iceberg
    """)
    
    spark.sql("""
        MERGE INTO cryptolake.silver.fear_greed AS target
        USING fg_updates AS source
        ON target.index_date = source.index_date
        WHEN MATCHED THEN UPDATE SET *
        WHEN NOT MATCHED THEN INSERT *
    """)
    
    print(f"✅ Silver fear_greed updated")


if __name__ == "__main__":
    spark = create_spark_session()
    process_historical_prices(spark)
    process_fear_greed(spark)
    spark.stop()
```

---

### FASE 5: Gold Layer — dbt + Modelado Dimensional (Semana 5)

#### Paso 5.1: Configuración dbt

```yaml
# src/transformation/dbt_cryptolake/dbt_project.yml
name: cryptolake
version: '1.0.0'
config-version: 2

profile: cryptolake

model-paths: ["models"]
analysis-paths: ["analyses"]
test-paths: ["tests"]
seed-paths: ["seeds"]
macro-paths: ["macros"]

clean-targets:
  - target
  - dbt_packages

models:
  cryptolake:
    staging:
      +materialized: view
      +schema: staging
    intermediate:
      +materialized: ephemeral
    marts:
      +materialized: table
      +schema: gold
```

#### Paso 5.2: Modelos dbt — Staging

```sql
-- models/staging/stg_prices.sql
-- Staging layer: interfaz limpia sobre la capa Silver.
-- Renombra columnas, aplica business logic mínima.

WITH source AS (
    SELECT * FROM {{ source('silver', 'daily_prices') }}
),

renamed AS (
    SELECT
        coin_id,
        price_date,
        price_usd,
        market_cap_usd,
        volume_24h_usd,
        _processed_at,
        
        -- Calculated fields
        LAG(price_usd) OVER (
            PARTITION BY coin_id ORDER BY price_date
        ) AS prev_day_price,
        
        ROW_NUMBER() OVER (
            PARTITION BY coin_id ORDER BY price_date DESC
        ) AS recency_rank
        
    FROM source
    WHERE price_usd > 0
)

SELECT
    *,
    CASE 
        WHEN prev_day_price IS NOT NULL AND prev_day_price > 0
        THEN ROUND(((price_usd - prev_day_price) / prev_day_price) * 100, 4)
        ELSE NULL
    END AS price_change_pct_1d
FROM renamed
```

```sql
-- models/staging/stg_fear_greed.sql
WITH source AS (
    SELECT * FROM {{ source('silver', 'fear_greed') }}
)

SELECT
    fear_greed_value,
    classification,
    index_date,
    -- Clasificación numérica para análisis
    CASE classification
        WHEN 'Extreme Fear' THEN 1
        WHEN 'Fear' THEN 2
        WHEN 'Neutral' THEN 3
        WHEN 'Greed' THEN 4
        WHEN 'Extreme Greed' THEN 5
    END AS sentiment_score,
    _processed_at
FROM source
```

#### Paso 5.3: Modelos dbt — Marts (Star Schema)

```sql
-- models/marts/dim_coins.sql
-- DIMENSION: Información estática de cada criptomoneda.
-- Type 1 SCD (se sobrescribe con nuevos datos).

{{ config(
    materialized='table',
    unique_key='coin_id'
) }}

WITH coin_stats AS (
    SELECT
        coin_id,
        MIN(price_date) AS first_tracked_date,
        MAX(price_date) AS last_tracked_date,
        COUNT(DISTINCT price_date) AS total_days_tracked,
        MIN(price_usd) AS all_time_low,
        MAX(price_usd) AS all_time_high,
        AVG(price_usd) AS avg_price,
        AVG(volume_24h_usd) AS avg_daily_volume
    FROM {{ ref('stg_prices') }}
    GROUP BY coin_id
)

SELECT
    coin_id,
    -- Metadata de tracking
    first_tracked_date,
    last_tracked_date,
    total_days_tracked,
    -- Price stats
    all_time_low,
    all_time_high,
    avg_price,
    avg_daily_volume,
    -- Calculated
    ROUND(((all_time_high - all_time_low) / all_time_low) * 100, 2) AS price_range_pct,
    CURRENT_TIMESTAMP() AS _loaded_at
FROM coin_stats
```

```sql
-- models/marts/dim_dates.sql
-- DIMENSION: Calendario con atributos útiles para análisis.

{{ config(materialized='table') }}

WITH date_spine AS (
    SELECT DISTINCT price_date AS date_day
    FROM {{ ref('stg_prices') }}
)

SELECT
    date_day,
    YEAR(date_day) AS year,
    MONTH(date_day) AS month,
    DAY(date_day) AS day_of_month,
    DAYOFWEEK(date_day) AS day_of_week,
    WEEKOFYEAR(date_day) AS week_of_year,
    QUARTER(date_day) AS quarter,
    
    -- Flags útiles para análisis
    CASE WHEN DAYOFWEEK(date_day) IN (1, 7) THEN TRUE ELSE FALSE END AS is_weekend,
    
    -- Formato legible
    DATE_FORMAT(date_day, 'EEEE') AS day_name,
    DATE_FORMAT(date_day, 'MMMM') AS month_name
    
FROM date_spine
```

```sql
-- models/marts/fact_market_daily.sql
-- FACT TABLE: Métricas de mercado diarias por coin.
-- Grain: 1 row = 1 coin × 1 día.
-- Este es el modelo central del star schema.

{{ config(
    materialized='incremental',
    unique_key=['coin_id', 'price_date'],
    incremental_strategy='merge'
) }}

WITH prices AS (
    SELECT * FROM {{ ref('stg_prices') }}
    {% if is_incremental() %}
    WHERE price_date > (SELECT MAX(price_date) FROM {{ this }})
    {% endif %}
),

fear_greed AS (
    SELECT * FROM {{ ref('stg_fear_greed') }}
),

-- Rolling metrics con window functions
enriched AS (
    SELECT
        p.coin_id,
        p.price_date,
        p.price_usd,
        p.market_cap_usd,
        p.volume_24h_usd,
        p.price_change_pct_1d,
        
        -- Rolling averages (indicadores técnicos básicos)
        AVG(p.price_usd) OVER (
            PARTITION BY p.coin_id 
            ORDER BY p.price_date 
            ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
        ) AS moving_avg_7d,
        
        AVG(p.price_usd) OVER (
            PARTITION BY p.coin_id 
            ORDER BY p.price_date 
            ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
        ) AS moving_avg_30d,
        
        -- Volatilidad (desviación estándar 7 días)
        STDDEV(p.price_usd) OVER (
            PARTITION BY p.coin_id 
            ORDER BY p.price_date 
            ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
        ) AS volatility_7d,
        
        -- Volume trend
        AVG(p.volume_24h_usd) OVER (
            PARTITION BY p.coin_id 
            ORDER BY p.price_date 
            ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
        ) AS avg_volume_7d,
        
        -- Fear & Greed del día
        fg.fear_greed_value,
        fg.classification AS market_sentiment,
        fg.sentiment_score,
        
        -- Signal: ¿está por encima de la media de 30d?
        CASE 
            WHEN p.price_usd > AVG(p.price_usd) OVER (
                PARTITION BY p.coin_id 
                ORDER BY p.price_date 
                ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
            ) THEN 'ABOVE_MA30'
            ELSE 'BELOW_MA30'
        END AS ma30_signal

    FROM prices p
    LEFT JOIN fear_greed fg
        ON p.price_date = fg.index_date
)

SELECT
    coin_id,
    price_date,
    price_usd,
    market_cap_usd,
    volume_24h_usd,
    price_change_pct_1d,
    moving_avg_7d,
    moving_avg_30d,
    volatility_7d,
    avg_volume_7d,
    fear_greed_value,
    market_sentiment,
    sentiment_score,
    ma30_signal,
    CURRENT_TIMESTAMP() AS _loaded_at
FROM enriched
```

#### Paso 5.4: Tests dbt

```sql
-- tests/assert_positive_prices.sql
-- Test custom: Verifica que no hay precios negativos en la fact table.
SELECT
    coin_id,
    price_date,
    price_usd
FROM {{ ref('fact_market_daily') }}
WHERE price_usd <= 0
```

```yaml
# models/marts/schema.yml
version: 2

models:
  - name: fact_market_daily
    description: "Tabla de hechos con métricas de mercado crypto diarias"
    columns:
      - name: coin_id
        description: "Identificador único del cryptocurrency"
        tests:
          - not_null
      - name: price_date
        description: "Fecha del registro"
        tests:
          - not_null
      - name: price_usd
        description: "Precio en USD"
        tests:
          - not_null
      - name: fear_greed_value
        description: "Índice Fear & Greed (0-100)"
        tests:
          - accepted_values:
              values: [0, 100]
              config:
                where: "fear_greed_value IS NOT NULL"

  - name: dim_coins
    description: "Dimensión con estadísticas de cada criptomoneda"
    columns:
      - name: coin_id
        tests:
          - unique
          - not_null
```

---

### FASE 6: Orquestación con Airflow (Semana 6)

#### Paso 6.1: DAG Master — Pipeline Completo

```python
# src/orchestration/dags/dag_full_pipeline.py
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
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator
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
    schedule="0 6 * * *",  # Diario a las 06:00 UTC
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
        
        load_to_bronze = SparkSubmitOperator(
            task_id="api_to_bronze",
            application="/opt/airflow/src/processing/batch/api_to_bronze.py",
            conn_id="spark_default",
            name="CryptoLake-APIToBronze",
        )
    
    # ── GRUPO 3: Silver Processing ─────────────────────────────
    with TaskGroup("silver_processing") as silver_group:
        
        bronze_to_silver = SparkSubmitOperator(
            task_id="bronze_to_silver",
            application="/opt/airflow/src/processing/batch/bronze_to_silver.py",
            conn_id="spark_default",
            name="CryptoLake-BronzeToSilver",
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
            # En producción: great_expectations checkpoint run daily_validation
        )
    
    # ── DEPENDENCIAS ───────────────────────────────────────────
    ingestion_group >> bronze_group >> silver_group >> gold_group >> quality_group
```

---

### FASE 7: Data Quality + Serving (Semana 7)

#### Paso 7.1: FastAPI — REST API

```python
# src/serving/api/main.py
"""
API REST de CryptoLake.

Endpoints:
- GET /api/v1/prices/{coin_id} — Precios históricos
- GET /api/v1/analytics/market-overview — Overview del mercado
- GET /api/v1/analytics/fear-greed — Fear & Greed actual
- GET /api/v1/health — Health check
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from src.serving.api.routes import analytics, health, prices


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup: inicializar conexiones
    yield
    # Shutdown: cerrar conexiones


app = FastAPI(
    title="CryptoLake API",
    description="Real-time crypto analytics powered by a Lakehouse architecture",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(prices.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")
app.include_router(health.router, prefix="/api/v1")
```

```python
# src/serving/api/routes/prices.py
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter(tags=["Prices"])


class PriceResponse(BaseModel):
    coin_id: str
    price_date: date
    price_usd: float
    market_cap_usd: Optional[float]
    volume_24h_usd: Optional[float]
    price_change_pct_1d: Optional[float]
    moving_avg_7d: Optional[float]
    moving_avg_30d: Optional[float]
    ma30_signal: Optional[str]


@router.get("/prices/{coin_id}", response_model=list[PriceResponse])
async def get_prices(
    coin_id: str,
    start_date: Optional[date] = Query(
        default=None, 
        description="Start date (default: 30 days ago)"
    ),
    end_date: Optional[date] = Query(
        default=None, 
        description="End date (default: today)"
    ),
    limit: int = Query(default=100, le=1000),
):
    """
    Obtiene precios históricos de un cryptocurrency.
    
    Incluye métricas calculadas: moving averages, volatilidad, 
    señales técnicas y sentimiento de mercado.
    """
    # En producción: query a Iceberg via PyIceberg o Spark Thrift Server
    # Aquí simplificado para demostración
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    # Query logic aquí...
    return []
```

---

### FASE 8: CI/CD + Terraform (Semana 8)

#### Paso 8.1: GitHub Actions CI

```yaml
# .github/workflows/ci.yml
name: CI Pipeline

on:
  pull_request:
    branches: [main, develop]
  push:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install ruff mypy
      - run: ruff check src/ tests/
      - run: ruff format --check src/ tests/

  test:
    runs-on: ubuntu-latest
    needs: lint
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_PASSWORD: test
        ports: ["5432:5432"]
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -e ".[dev]"
      - run: pytest tests/unit/ -v --cov=src --cov-report=xml
      - uses: codecov/codecov-action@v4
        with:
          file: coverage.xml

  dbt-test:
    runs-on: ubuntu-latest
    needs: lint
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install dbt-core dbt-spark
      - run: |
          cd src/transformation/dbt_cryptolake
          dbt deps
          dbt compile --profiles-dir . --target ci

  docker-build:
    runs-on: ubuntu-latest
    needs: [test, dbt-test]
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - run: |
          docker compose build --parallel
          echo "✅ All images built successfully"
```

#### Paso 8.2: Terraform — Infrastructure as Code

```hcl
# terraform/modules/storage/main.tf
# Módulo para provisionar storage en AWS S3 (producción)
# En local usamos MinIO que es S3-compatible

variable "environment" {
  type = string
}

variable "project_name" {
  type    = string
  default = "cryptolake"
}

# S3 Buckets para cada capa del Lakehouse
resource "aws_s3_bucket" "bronze" {
  bucket = "${var.project_name}-${var.environment}-bronze"
  
  tags = {
    Project     = var.project_name
    Environment = var.environment
    Layer       = "bronze"
  }
}

resource "aws_s3_bucket" "silver" {
  bucket = "${var.project_name}-${var.environment}-silver"
  
  tags = {
    Project     = var.project_name
    Environment = var.environment
    Layer       = "silver"
  }
}

resource "aws_s3_bucket" "gold" {
  bucket = "${var.project_name}-${var.environment}-gold"
  
  tags = {
    Project     = var.project_name
    Environment = var.environment
    Layer       = "gold"
  }
}

# Lifecycle rules: mover datos viejos a storage más barato
resource "aws_s3_bucket_lifecycle_configuration" "bronze_lifecycle" {
  bucket = aws_s3_bucket.bronze.id
  
  rule {
    id     = "archive-old-data"
    status = "Enabled"
    
    transition {
      days          = 90
      storage_class = "GLACIER"
    }
  }
}

# Versionado para Bronze (raw data protection)
resource "aws_s3_bucket_versioning" "bronze_versioning" {
  bucket = aws_s3_bucket.bronze.id
  
  versioning_configuration {
    status = "Enabled"
  }
}
```

---

### FASE 9: README y Documentación (Semana 9)

#### El README que impresiona a recruiters

```markdown
# 🏔️ CryptoLake — Real-Time Crypto Analytics Lakehouse

[![CI Pipeline](https://github.com/tu-usuario/cryptolake/actions/workflows/ci.yml/badge.svg)](...)
[![codecov](https://codecov.io/gh/tu-usuario/cryptolake/branch/main/graph/badge.svg)](...)
[![dbt](https://img.shields.io/badge/dbt-1.8-FF694B?logo=dbt)](...)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](...)

> An end-to-end data engineering platform that ingests real-time and historical 
> cryptocurrency data, processes it through a Medallion Architecture (Bronze → Silver → Gold) 
> on Apache Iceberg, transforms with dbt, orchestrates with Airflow, and serves 
> analytics via REST API and interactive dashboard.

## 🏗️ Architecture

[Diagrama Mermaid aquí]

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Streaming | Apache Kafka | Real-time price ingestion from Binance |
| Processing | Apache Spark | Batch + stream processing |
| Table Format | Apache Iceberg | ACID transactions, time travel, schema evolution |
| Storage | MinIO (S3) | Object storage (S3-compatible) |
| Transformation | dbt | SQL-based dimensional modeling |
| Orchestration | Apache Airflow | Pipeline scheduling and monitoring |
| Data Quality | Great Expectations | Automated data validation |
| API | FastAPI | REST API for analytics |
| Dashboard | Streamlit | Interactive visualizations |
| Infrastructure | Docker, Terraform | Containerization, IaC |
| CI/CD | GitHub Actions | Automated testing and deployment |

## 🚀 Quick Start

​```bash
git clone https://github.com/tu-usuario/cryptolake.git
cd cryptolake
cp .env.example .env
make up  # Starts all 12+ services
​```

## 📊 Data Model

### Star Schema (Gold Layer)

[Diagrama del star schema]

- **fact_market_daily**: Daily crypto market metrics (price, volume, MAs, sentiment)
- **dim_coins**: Cryptocurrency metadata and stats
- **dim_dates**: Calendar dimension

## 📈 Key Features

- **Dual Pipeline**: Real-time streaming (Kafka → Spark Streaming) + daily batch
- **Lakehouse Architecture**: Apache Iceberg with Medallion pattern
- **Data Contracts**: Schema versioning and quality agreements
- **Incremental Processing**: MERGE INTO for efficient updates
- **Production-Ready**: CI/CD, monitoring, alerting, data quality gates
```

---

## 6. Checklist Final de Calidad

Antes de publicar tu proyecto, verifica:

### Código
- [ ] Todos los archivos tienen docstrings explicando qué hacen y por qué
- [ ] Type hints en todas las funciones
- [ ] Logging estructurado con structlog (no print statements)
- [ ] Error handling con excepciones específicas
- [ ] Configuración externalizada (no hardcoded values)
- [ ] Tests unitarios con >70% coverage

### Arquitectura  
- [ ] Diagrama de arquitectura claro y profesional
- [ ] Data dictionary documentando CADA campo
- [ ] Data contracts para las interfaces entre capas
- [ ] ADRs (Architecture Decision Records) explicando por qué elegiste cada tecnología

### DevOps
- [ ] `make up` levanta todo el entorno en un comando
- [ ] CI pasa verde en GitHub Actions
- [ ] Docker images optimizadas (multi-stage builds)
- [ ] `.env.example` con todas las variables documentadas

### Git
- [ ] Commits atómicos con mensajes descriptivos (conventional commits)
- [ ] Branching strategy (main + develop + feature branches)
- [ ] PR template con checklist
- [ ] .gitignore completo

### README
- [ ] Badges de CI, coverage, tecnologías
- [ ] Screenshot del dashboard
- [ ] GIF/video del pipeline en acción
- [ ] Sección "What I Learned" con reflexiones personales
- [ ] Instrucciones de setup que FUNCIONAN (testa desde cero)

                                                                                                                              
                                                                                                                              
                                                                                                                              
                                                                                                                              
                                                                                                                              
                                                                                                                              
                                                                                                                              
# CryptoLake — Fase 1 y Fase 2: Guía Paso a Paso desde Cero

> **Contexto**: Tienes un MacBook Pro M4 sin nada instalado.  
> Al terminar esta guía tendrás un ecosistema completo de data engineering  
> corriendo en tu máquina con datos de criptomonedas fluyendo en tiempo real.

---

## PARTE 0: Preparar tu Mac desde cero

### 0.1 — Instalar Homebrew (el gestor de paquetes de macOS)

Homebrew es como un `apt-get` para macOS. Te permite instalar software desde
la terminal sin descargar instaladores manualmente.

Abre la app **Terminal** (Cmd + Espacio → escribe "Terminal") y ejecuta:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Cuando termine, te pedirá ejecutar dos comandos para añadir Homebrew al PATH.
Serán algo como:

```bash
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv)"
```

Verifica que funciona:

```bash
brew --version
# Homebrew 4.x.x
```

### 0.2 — Instalar herramientas esenciales

```bash
# Git (control de versiones - ya lo conoces)
brew install git

# Python 3.11 (el lenguaje principal de data engineering)
brew install python@3.11

# Docker Desktop (contenedores - lo explicamos abajo)
brew install --cask docker
```

**Ahora abre Docker Desktop** desde Launchpad o Spotlight (Cmd + Espacio →
"Docker"). La primera vez tardará un poco en iniciar. Necesitas que el icono
de la ballena en la barra superior esté activo (sin animación) antes de
continuar.

Configura Docker con suficientes recursos para nuestro proyecto:
1. Abre Docker Desktop → Settings (⚙️) → Resources
2. Asigna al menos: **CPU: 6 cores**, **Memory: 8 GB**, **Disk: 40 GB**
3. Click "Apply & Restart"

Verifica que todo funciona:

```bash
git --version
python3.11 --version
docker --version
docker compose version
```

### 0.3 — Instalar herramientas de desarrollo adicionales

```bash
# Editor de código (si no lo tienes)
brew install --cask visual-studio-code

# jq: utilidad para formatear JSON en terminal (muy útil para debugging)
brew install jq

# make: para ejecutar nuestro Makefile (normalmente ya viene en macOS)
# Si no lo tienes:
xcode-select --install
```

### 0.4 — Configurar Git (si no lo tienes configurado)

```bash
git config --global user.name "Tu Nombre"
git config --global user.email "tu@email.com"
```

---

## PARTE 1: Entender los Conceptos Fundamentales

Antes de escribir código, necesitas entender QUÉ estamos construyendo y POR
QUÉ. Lee esta sección con calma — es la base para todo lo que viene después.

### 1.1 — ¿Qué es un pipeline de datos?

Imagina una fábrica de coches:
- La **materia prima** (acero, plástico) llega de proveedores → **Ingesta**
- Se **limpia y prepara** en el almacén → **Procesamiento**
- Se **ensambla** en el producto final → **Transformación**
- El coche terminado se **entrega** al cliente → **Serving**

Un pipeline de datos es exactamente lo mismo pero con datos:

```
[Fuentes de datos] → [Ingesta] → [Almacenamiento] → [Procesamiento] → [Transformación] → [Consumo]
     Binance           Kafka       MinIO/Iceberg        Spark              dbt            API/Dashboard
```

### 1.2 — ¿Qué es Docker y por qué lo usamos?

**El problema**: Nuestro proyecto necesita Kafka, Spark, Airflow, MinIO,
PostgreSQL... Instalar todo eso en tu Mac sería una pesadilla de
configuración, versiones incompatibles y conflictos.

**La solución**: Docker crea "mini-ordenadores virtuales" (contenedores) dentro
de tu Mac. Cada servicio corre en su propio contenedor aislado, con sus
propias dependencias, sin afectar a los demás.

```
Tu MacBook Pro M4
├── Contenedor 1: Kafka         (mensajería en streaming)
├── Contenedor 2: Spark         (procesamiento de datos)
├── Contenedor 3: MinIO         (almacenamiento tipo S3)
├── Contenedor 4: Airflow       (orquestación de tareas)
├── Contenedor 5: PostgreSQL    (base de datos de Airflow)
└── ...y más
```

**Docker Compose** es un archivo YAML que describe TODOS los contenedores y
cómo se conectan entre sí. Con un solo comando (`docker compose up`)
levantamos todo el ecosistema.

**Conceptos clave de Docker:**
- **Imagen**: La "receta" o "plantilla" (como una clase en Java)
- **Contenedor**: Una instancia ejecutándose (como un objeto)
- **Volume**: Disco persistente para que los datos sobrevivan a reinicios
- **Port mapping**: Conectar un puerto del contenedor a tu Mac (ej: 9092:9092)
- **Network**: Red virtual donde los contenedores se ven entre sí por nombre

### 1.3 — ¿Qué es Apache Kafka?

Piensa en Kafka como un **buzón de correos inteligente para datos**.

En un sistema tradicional, cuando la app A quiere enviar datos a la app B,
se conectan directamente (como una llamada telefónica). Pero si tienes 10
apps que necesitan datos, se convierte en un lío de conexiones.

Kafka resuelve esto con un modelo de **publicar/suscribir**:
- **Productores** publican mensajes en un **topic** (como un canal de Slack)
- **Consumidores** se suscriben al topic y reciben los mensajes
- Los mensajes se **persisten** en disco (no se pierden si un consumidor cae)
- Múltiples consumidores pueden leer el mismo topic independientemente

```
Binance WebSocket ──▶ [Productor] ──▶ KAFKA Topic "prices.realtime" ──▶ [Consumidor: Spark]
                                                                    ──▶ [Consumidor: Dashboard]
                                                                    ──▶ [Consumidor: Alertas]
```

**Conceptos clave de Kafka:**
- **Topic**: Un canal/categoría de mensajes (como una tabla, pero append-only)
- **Partition**: Subdivisión del topic para paralelismo. Los mensajes con la
  misma key van a la misma partición (garantiza orden)
- **Offset**: Posición de un mensaje en la partición (como un ID autoincremental)
- **Broker**: Un servidor Kafka. En producción hay varios; nosotros usamos 1
- **Producer**: Programa que envía mensajes a Kafka
- **Consumer**: Programa que lee mensajes de Kafka

### 1.4 — ¿Qué es MinIO y por qué lo usamos?

**Amazon S3** es el servicio de almacenamiento más usado en data engineering.
Es un "disco duro infinito" en la nube donde guardas archivos (llamados
"objetos") organizados en "buckets" (como carpetas raíz).

**MinIO** es un clon de S3 que corre en tu máquina local. Usa exactamente la
misma API que S3, así que todo el código que escribas funcionará tanto en
MinIO (local) como en S3 real (producción) sin cambiar nada.

```
LOCAL (desarrollo):     MinIO      → s3://cryptolake-bronze/
PRODUCCIÓN (AWS):       Amazon S3  → s3://cryptolake-bronze/
                        ↑ Mismo código, misma API ↑
```

**Nuestros buckets:**
- `cryptolake-bronze`: Datos raw sin modificar (la "verdad" original)
- `cryptolake-silver`: Datos limpios y deduplicados
- `cryptolake-gold`: Datos transformados listos para consumo

### 1.5 — ¿Qué es Apache Iceberg?

Los archivos Parquet en S3 son geniales para almacenar datos, pero les faltan
cosas que las bases de datos tienen: transacciones ACID, actualizar filas
individuales, viajar en el tiempo a versiones anteriores...

**Apache Iceberg** añade esas capacidades encima de archivos Parquet en S3.
Es un "table format" — una capa de metadata que convierte archivos estáticos
en tablas con superpoderes:

```
Sin Iceberg:  S3 bucket → miles de archivos Parquet sueltos → caos
Con Iceberg:  S3 bucket → Iceberg metadata → tablas organizadas con:
              ✓ Transacciones ACID (no datos corruptos)
              ✓ Time travel (volver a versiones anteriores)
              ✓ Schema evolution (añadir columnas sin romper nada)
              ✓ MERGE INTO (actualizar filas, como SQL)
              ✓ Partitioning oculto (rendimiento automático)
```

Iceberg es **LA tendencia más fuerte** en data engineering 2025-2026. Tanto
Snowflake como Databricks lo soportan nativamente.

### 1.6 — Arquitectura Medallion (Bronze → Silver → Gold)

Es un patrón de organización de datos en capas de calidad creciente:

```
BRONZE (Raw)                    SILVER (Clean)                  GOLD (Business)
─────────────                   ──────────────                  ───────────────
• Datos tal cual llegan         • Deduplicados                  • Modelo dimensional
• Sin modificar                 • Tipos correctos               • Métricas calculadas
• Puede tener duplicados        • Nulls tratados                • Listo para dashboards
• Puede tener errores           • Schema validado               • Listo para APIs
• Append-only                   • Merge incremental             • Star schema
```

¿Por qué no limpiar todo directamente? Porque si te equivocas en la
limpieza, siempre puedes volver a Bronze y reprocesar. Bronze es tu
"copia de seguridad" de la realidad.

---

## PARTE 2 (FASE 1): Crear la Infraestructura

Ahora sí, manos a la obra. Vamos a crear el proyecto paso a paso.

### 2.1 — Crear la estructura del proyecto

Abre Terminal y ejecuta:

```bash
# Crear el directorio del proyecto
mkdir -p ~/Projects/cryptolake
cd ~/Projects/cryptolake

# Inicializar Git
git init

# Crear la estructura de directorios
mkdir -p .github/workflows
mkdir -p docker/spark
mkdir -p docker/airflow
mkdir -p src/config
mkdir -p src/ingestion/streaming
mkdir -p src/ingestion/batch
mkdir -p src/processing/streaming
mkdir -p src/processing/batch
mkdir -p src/processing/schemas
mkdir -p src/orchestration/dags
mkdir -p src/serving/api/routes
mkdir -p src/serving/dashboard
mkdir -p src/transformation/dbt_cryptolake/models/staging
mkdir -p src/transformation/dbt_cryptolake/models/marts
mkdir -p src/quality
mkdir -p tests/unit
mkdir -p tests/integration
mkdir -p docs/data_contracts
mkdir -p terraform/modules/storage
mkdir -p scripts

# Crear archivos __init__.py para que Python reconozca los paquetes
touch src/__init__.py
touch src/config/__init__.py
touch src/ingestion/__init__.py
touch src/ingestion/streaming/__init__.py
touch src/ingestion/batch/__init__.py
touch src/processing/__init__.py
touch src/processing/streaming/__init__.py
touch src/processing/batch/__init__.py
touch src/processing/schemas/__init__.py
touch src/orchestration/__init__.py
touch src/serving/__init__.py
touch src/serving/api/__init__.py
touch src/serving/api/routes/__init__.py
touch src/quality/__init__.py
touch tests/__init__.py
touch tests/unit/__init__.py
touch tests/integration/__init__.py
```

**¿Qué es `__init__.py`?** Es un archivo vacío que le dice a Python "este
directorio es un paquete". Sin él, no podrías hacer `from src.config import settings`.
Lo conoces de Java como la estructura de packages.

### 2.2 — Crear el archivo .gitignore

```bash
cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.egg-info/
dist/
build/
.eggs/
*.egg
.venv/
venv/

# Environment
.env
.env.local

# IDE
.vscode/
.idea/
*.swp
*.swo

# Docker
docker/*/data/

# Airflow
airflow-logs/
logs/

# dbt
src/transformation/dbt_cryptolake/target/
src/transformation/dbt_cryptolake/dbt_packages/
src/transformation/dbt_cryptolake/logs/

# Terraform
terraform/.terraform/
terraform/*.tfstate
terraform/*.tfstate.backup
terraform/*.tfplan

# OS
.DS_Store
Thumbs.db

# Data (no commiteamos datos locales)
data/
*.parquet
*.avro
EOF
```

### 2.3 — Crear el archivo .env.example

Este archivo documenta TODAS las variables de entorno que necesita el proyecto.
Cada desarrollador copia este archivo a `.env` y lo personaliza.

```bash
cat > .env.example << 'EOF'
# ============================================
# CryptoLake - Variables de Entorno
# ============================================
# Copia este archivo a .env:  cp .env.example .env
# NUNCA commitees el archivo .env (contiene secretos)

# MinIO (S3-compatible storage)
MINIO_ENDPOINT=http://localhost:9000
MINIO_ACCESS_KEY=cryptolake
MINIO_SECRET_KEY=cryptolake123

# Kafka
KAFKA_BOOTSTRAP_SERVERS=localhost:9092

# Iceberg REST Catalog
ICEBERG_CATALOG_URI=http://localhost:8181

# Airflow
AIRFLOW_ADMIN_USER=admin
AIRFLOW_ADMIN_PASSWORD=admin

# APIs externas
COINGECKO_BASE_URL=https://api.coingecko.com/api/v3
FEAR_GREED_URL=https://api.alternative.me/fng/

# Coins a trackear (separados por coma)
TRACKED_COINS=bitcoin,ethereum,solana,cardano,polkadot,chainlink,avalanche-2,matic-network
EOF
```

Ahora crea tu `.env` real:

```bash
cp .env.example .env
```

### 2.4 — Crear el Dockerfile de Spark con soporte para Iceberg

Este es el Dockerfile más complejo. Spark necesita JARs (librerías Java)
específicos para hablar con Iceberg y con S3/MinIO.

```bash
cat > docker/spark/Dockerfile << 'DOCKERFILE'
# ============================================================
# Spark 3.5 con soporte para Apache Iceberg y S3 (MinIO)
# ============================================================
# Base: imagen oficial de Bitnami con Spark 3.5 preinstalado
# Añadimos: JARs de Iceberg + librerías Python para data engineering
FROM bitnami/spark:3.5

USER root

# Instalar librerías Python que usaremos en nuestros jobs de Spark
RUN pip install --no-cache-dir \
    pyspark==3.5.0 \
    pyiceberg[s3fs]==0.7.1 \
    pyarrow==15.0.1 \
    kafka-python==2.0.2 \
    requests==2.31.0 \
    pydantic==2.5.0 \
    pydantic-settings==2.1.0 \
    structlog==24.1.0

# ── Descargar JARs de Iceberg ──────────────────────────────
# Spark es un proyecto Java/Scala. Para que sepa "hablar" con
# Iceberg y S3, necesita librerías .jar en su classpath.
# Estos JARs se descargan de Maven Central (el npm de Java).

ENV ICEBERG_VERSION=1.5.2

# iceberg-spark-runtime: El "driver" de Iceberg para Spark
RUN curl -L -o /opt/bitnami/spark/jars/iceberg-spark-runtime-3.5_2.12-${ICEBERG_VERSION}.jar \
    https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-spark-runtime-3.5_2.12/${ICEBERG_VERSION}/iceberg-spark-runtime-3.5_2.12-${ICEBERG_VERSION}.jar

# iceberg-aws-bundle: Para que Iceberg hable con S3/MinIO
RUN curl -L -o /opt/bitnami/spark/jars/iceberg-aws-bundle-${ICEBERG_VERSION}.jar \
    https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-aws-bundle/${ICEBERG_VERSION}/iceberg-aws-bundle-${ICEBERG_VERSION}.jar

# Configuración por defecto de Spark
COPY spark-defaults.conf /opt/bitnami/spark/conf/spark-defaults.conf

# Volver al usuario no-root por seguridad
USER 1001
DOCKERFILE
```

Ahora el archivo de configuración de Spark:

```bash
cat > docker/spark/spark-defaults.conf << 'EOF'
# ============================================================
# Configuración de Spark para CryptoLake
# ============================================================

# ── Catálogo Iceberg ───────────────────────────────────────
# Le decimos a Spark: "cuando uses el catálogo llamado 'cryptolake',
# usa Iceberg como formato de tabla, y habla con el REST catalog
# para saber dónde están las tablas."

spark.sql.catalog.cryptolake=org.apache.iceberg.spark.SparkCatalog
spark.sql.catalog.cryptolake.type=rest
spark.sql.catalog.cryptolake.uri=http://iceberg-rest:8181
spark.sql.catalog.cryptolake.io-impl=org.apache.iceberg.aws.s3.S3FileIO
spark.sql.catalog.cryptolake.s3.endpoint=http://minio:9000
spark.sql.catalog.cryptolake.s3.path-style-access=true

# ── Conexión S3/MinIO ─────────────────────────────────────
# Spark usa la librería Hadoop para acceder a S3.
# "s3a://" es el protocolo de Hadoop para S3.

spark.hadoop.fs.s3a.endpoint=http://minio:9000
spark.hadoop.fs.s3a.access.key=cryptolake
spark.hadoop.fs.s3a.secret.key=cryptolake123
spark.hadoop.fs.s3a.path.style.access=true
spark.hadoop.fs.s3a.impl=org.apache.hadoop.fs.s3a.S3AFileSystem

# ── Extensiones de Iceberg para Spark SQL ─────────────────
# Habilita sintaxis especial como MERGE INTO, ALTER TABLE ADD COLUMN, etc.
spark.sql.extensions=org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions
spark.sql.defaultCatalog=cryptolake
EOF
```

### 2.5 — Crear el Dockerfile de Airflow

```bash
cat > docker/airflow/Dockerfile << 'DOCKERFILE'
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
DOCKERFILE
```

### 2.6 — Crear el Docker Compose completo

Este es el archivo más importante de la Fase 1. Define todos los servicios
y cómo se conectan.

**Lee los comentarios línea por línea** — cada decisión tiene un motivo.

```bash
cat > docker-compose.yml << 'YAMLEOF'
# ============================================================
# CryptoLake — Docker Compose
# ============================================================
# Levanta todo el ecosistema de data engineering con:
#   docker compose up -d
#
# Servicios:
#   - MinIO (S3 local)        → Puerto 9000 (API), 9001 (Console)
#   - Iceberg REST Catalog    → Puerto 8181
#   - Kafka (KRaft mode)      → Puerto 9092
#   - Kafka UI                → Puerto 8080
#   - Spark Master + Worker   → Puerto 8082 (UI), 7077 (master)
#   - Airflow                 → Puerto 8083
#   - PostgreSQL (para Airflow)
# ============================================================

# "x-" es una extensión YAML: define variables reutilizables.
# Todos los servicios que necesitan conectarse a MinIO y Kafka
# comparten estas variables de entorno.
x-common-env: &common-env
  MINIO_ENDPOINT: http://minio:9000
  MINIO_ACCESS_KEY: cryptolake
  MINIO_SECRET_KEY: cryptolake123
  KAFKA_BOOTSTRAP_SERVERS: kafka:29092
  ICEBERG_CATALOG_URI: http://iceberg-rest:8181
  AWS_ACCESS_KEY_ID: cryptolake
  AWS_SECRET_ACCESS_KEY: cryptolake123
  AWS_REGION: us-east-1

services:

  # ==========================================================
  # CAPA DE ALMACENAMIENTO
  # ==========================================================

  # MinIO: Clon de Amazon S3 que corre localmente.
  # Almacena todos nuestros datos (Bronze, Silver, Gold).
  # En producción lo reemplazaríamos por S3 real sin cambiar código.
  minio:
    image: minio/minio:latest
    container_name: cryptolake-minio
    ports:
      - "9000:9000"   # API S3 (para que Spark, Iceberg etc. lean/escriban)
      - "9001:9001"   # Web Console (para ver los buckets visualmente)
    environment:
      MINIO_ROOT_USER: cryptolake
      MINIO_ROOT_PASSWORD: cryptolake123
    # "server /data" arranca MinIO con /data como directorio de almacenamiento
    command: server /data --console-address ":9001"
    volumes:
      # Volume nombrado: los datos persisten aunque pares el contenedor
      - minio-data:/data
    healthcheck:
      test: ["CMD", "mc", "ready", "local"]
      interval: 10s
      timeout: 5s
      retries: 5

  # minio-init: Contenedor efímero que crea los buckets al arrancar.
  # Se ejecuta una vez y termina. Como un script de setup.
  minio-init:
    image: minio/mc:latest
    container_name: cryptolake-minio-init
    depends_on:
      minio:
        condition: service_healthy   # Espera a que MinIO esté ready
    entrypoint: >
      /bin/sh -c "
      mc alias set local http://minio:9000 cryptolake cryptolake123;
      mc mb local/cryptolake-bronze --ignore-existing;
      mc mb local/cryptolake-silver --ignore-existing;
      mc mb local/cryptolake-gold --ignore-existing;
      mc mb local/cryptolake-checkpoints --ignore-existing;
      echo '✅ Buckets creados correctamente';
      "

  # Iceberg REST Catalog: Un servidor que gestiona los metadatos de las
  # tablas Iceberg. Cuando Spark hace "SELECT * FROM cryptolake.bronze.prices",
  # pregunta a este catalog dónde están los archivos en MinIO.
  iceberg-rest:
    image: tabulario/iceberg-rest:1.5.0
    container_name: cryptolake-iceberg-rest
    ports:
      - "8181:8181"
    environment:
      CATALOG_WAREHOUSE: s3://cryptolake-bronze/
      CATALOG_IO__IMPL: org.apache.iceberg.aws.s3.S3FileIO
      CATALOG_S3_ENDPOINT: http://minio:9000
      CATALOG_S3_PATH__STYLE__ACCESS: "true"
      AWS_ACCESS_KEY_ID: cryptolake
      AWS_SECRET_ACCESS_KEY: cryptolake123
      AWS_REGION: us-east-1
    depends_on:
      minio:
        condition: service_healthy

  # ==========================================================
  # CAPA DE STREAMING
  # ==========================================================

  # Apache Kafka en modo KRaft (sin ZooKeeper).
  # KRaft es el nuevo modo de Kafka donde no necesita ZooKeeper
  # como coordinador externo. Es más simple y moderno.
  kafka:
    image: confluentinc/cp-kafka:7.6.0
    container_name: cryptolake-kafka
    ports:
      - "9092:9092"     # Puerto para conexiones desde tu Mac
    environment:
      KAFKA_NODE_ID: 1
      # LISTENERS: define en qué interfaces escucha Kafka.
      # - PLAINTEXT (kafka:29092): para conexiones INTERNAS entre contenedores
      # - EXTERNAL (localhost:9092): para conexiones desde TU MAC
      # - CONTROLLER (kafka:29093): para el protocolo KRaft interno
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT,EXTERNAL:PLAINTEXT
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:29092,EXTERNAL://localhost:9092
      KAFKA_LISTENERS: PLAINTEXT://0.0.0.0:29092,CONTROLLER://0.0.0.0:29093,EXTERNAL://0.0.0.0:9092
      KAFKA_CONTROLLER_LISTENER_NAMES: CONTROLLER
      KAFKA_CONTROLLER_QUORUM_VOTERS: 1@kafka:29093
      KAFKA_PROCESS_ROLES: broker,controller
      KAFKA_GROUP_INITIAL_REBALANCE_DELAY_MS: 0
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
      KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR: 1
      CLUSTER_ID: MkU3OEVBNTcwNTJENDM2Qk  # ID fijo para que no cambie entre reinicios
    volumes:
      - kafka-data:/var/lib/kafka/data
    healthcheck:
      test: kafka-topics --bootstrap-server localhost:29092 --list
      interval: 10s
      timeout: 10s
      retries: 10

  # Kafka UI: Interfaz web para ver topics, mensajes, consumer groups...
  # No es necesario para producción pero es MUY útil para desarrollo.
  kafka-ui:
    image: provectuslabs/kafka-ui:latest
    container_name: cryptolake-kafka-ui
    ports:
      - "8080:8080"
    environment:
      KAFKA_CLUSTERS_0_NAME: cryptolake
      KAFKA_CLUSTERS_0_BOOTSTRAPSERVERS: kafka:29092
    depends_on:
      kafka:
        condition: service_healthy

  # ==========================================================
  # CAPA DE PROCESAMIENTO
  # ==========================================================

  # Spark Master: El coordinador del cluster de Spark.
  # Recibe los jobs y los distribuye a los workers.
  spark-master:
    build:
      context: ./docker/spark
      dockerfile: Dockerfile
    container_name: cryptolake-spark-master
    ports:
      - "8082:8080"   # Spark Web UI (ver jobs en ejecución)
      - "7077:7077"   # Puerto del master (los workers se conectan aquí)
    environment:
      <<: *common-env
      SPARK_MODE: master
    volumes:
      # Montamos nuestro código fuente dentro del contenedor.
      # Así podemos editar en nuestro Mac y Spark ve los cambios al instante.
      - ./src:/opt/spark/work/src

  # Spark Worker: El que ejecuta las tareas reales.
  # En producción tendrías muchos workers; aquí usamos 1.
  spark-worker:
    build:
      context: ./docker/spark
      dockerfile: Dockerfile
    container_name: cryptolake-spark-worker
    environment:
      <<: *common-env
      SPARK_MODE: worker
      SPARK_MASTER_URL: spark://spark-master:7077
      SPARK_WORKER_MEMORY: 2g
      SPARK_WORKER_CORES: 2
    depends_on:
      - spark-master
    volumes:
      - ./src:/opt/spark/work/src

  # ==========================================================
  # CAPA DE ORQUESTACIÓN
  # ==========================================================

  # PostgreSQL: Base de datos interna de Airflow.
  # Airflow necesita una DB para guardar el estado de los DAGs,
  # el historial de ejecuciones, variables, conexiones, etc.
  # NO es para nuestros datos de crypto — es solo para Airflow.
  airflow-postgres:
    image: postgres:16-alpine
    container_name: cryptolake-airflow-db
    environment:
      POSTGRES_USER: airflow
      POSTGRES_PASSWORD: airflow
      POSTGRES_DB: airflow
    volumes:
      - airflow-db-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U airflow"]
      interval: 5s
      timeout: 5s
      retries: 5

  # Airflow Webserver: La interfaz web donde ves y gestionas los DAGs.
  airflow-webserver:
    build:
      context: ./docker/airflow
      dockerfile: Dockerfile
    container_name: cryptolake-airflow-webserver
    ports:
      - "8083:8080"   # Web UI de Airflow
    environment:
      <<: *common-env
      AIRFLOW__CORE__EXECUTOR: LocalExecutor
      AIRFLOW__DATABASE__SQL_ALCHEMY_CONN: postgresql+psycopg2://airflow:airflow@airflow-postgres/airflow
      AIRFLOW__CORE__FERNET_KEY: ''
      AIRFLOW__WEBSERVER__SECRET_KEY: cryptolake-secret-key
      AIRFLOW__CORE__DAGS_ARE_PAUSED_AT_CREATION: 'true'
      AIRFLOW__CORE__LOAD_EXAMPLES: 'false'
    volumes:
      - ./src/orchestration/dags:/opt/airflow/dags
      - ./src:/opt/airflow/src
      - airflow-logs:/opt/airflow/logs
    depends_on:
      airflow-postgres:
        condition: service_healthy
    # El comando hace 3 cosas al arrancar:
    # 1. Migra la base de datos (crea las tablas de Airflow)
    # 2. Crea un usuario admin
    # 3. Arranca el servidor web
    command: >
      bash -c "
      airflow db migrate &&
      airflow users create
        --username admin
        --password admin
        --firstname Admin
        --lastname User
        --role Admin
        --email admin@cryptolake.dev || true &&
      airflow webserver
      "

  # Airflow Scheduler: El proceso que vigila los DAGs y lanza
  # las tareas cuando llega su hora programada.
  airflow-scheduler:
    build:
      context: ./docker/airflow
      dockerfile: Dockerfile
    container_name: cryptolake-airflow-scheduler
    environment:
      <<: *common-env
      AIRFLOW__CORE__EXECUTOR: LocalExecutor
      AIRFLOW__DATABASE__SQL_ALCHEMY_CONN: postgresql+psycopg2://airflow:airflow@airflow-postgres/airflow
      AIRFLOW__CORE__FERNET_KEY: ''
      AIRFLOW__WEBSERVER__SECRET_KEY: cryptolake-secret-key
      AIRFLOW__CORE__LOAD_EXAMPLES: 'false'
    volumes:
      - ./src/orchestration/dags:/opt/airflow/dags
      - ./src:/opt/airflow/src
      - airflow-logs:/opt/airflow/logs
    depends_on:
      airflow-postgres:
        condition: service_healthy
    command: airflow scheduler

# ==========================================================
# VOLUMES: Discos persistentes
# ==========================================================
# Sin volumes, los datos se pierden al parar los contenedores.
# Con volumes, sobreviven a docker compose down/up.
volumes:
  minio-data:
  kafka-data:
  airflow-db-data:
  airflow-logs:
YAMLEOF
```

### 2.7 — Crear el Makefile

El Makefile te da comandos cortos para operaciones frecuentes:

```bash
cat > Makefile << 'EOF'
.PHONY: help up down down-clean logs status spark-shell kafka-topics

help: ## Mostrar esta ayuda
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
	awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

up: ## Arrancar todos los servicios
	@echo "🚀 Arrancando CryptoLake..."
	docker compose up -d --build
	@echo ""
	@echo "⏳ Esperando a que los servicios estén listos (esto tarda ~60s la primera vez)..."
	@sleep 30
	@echo ""
	@echo "✅ CryptoLake está corriendo!"
	@echo ""
	@echo "📊 Servicios disponibles:"
	@echo "   MinIO Console:   http://localhost:9001  (user: cryptolake / pass: cryptolake123)"
	@echo "   Kafka UI:        http://localhost:8080"
	@echo "   Spark UI:        http://localhost:8082"
	@echo "   Airflow:         http://localhost:8083  (user: admin / pass: admin)"
	@echo "   Iceberg Catalog: http://localhost:8181"
	@echo ""

down: ## Parar todos los servicios (conserva datos)
	docker compose down

down-clean: ## Parar y BORRAR todos los datos
	docker compose down -v
	@echo "🗑️  Todos los volumes eliminados"

logs: ## Ver logs de todos los servicios
	docker compose logs -f

logs-kafka: ## Ver logs solo de Kafka
	docker compose logs -f kafka

logs-spark: ## Ver logs solo de Spark
	docker compose logs -f spark-master spark-worker

status: ## Ver estado de los servicios
	docker compose ps

spark-shell: ## Abrir consola PySpark interactiva
	docker exec -it cryptolake-spark-master \
	    /opt/bitnami/spark/bin/pyspark

kafka-topics: ## Listar topics de Kafka
	docker exec cryptolake-kafka \
	    kafka-topics --bootstrap-server localhost:29092 --list

kafka-create-topics: ## Crear los topics necesarios
	docker exec cryptolake-kafka \
	    kafka-topics --bootstrap-server localhost:29092 \
	    --create --topic prices.realtime \
	    --partitions 3 --replication-factor 1 \
	    --config retention.ms=86400000
	@echo "✅ Topic 'prices.realtime' creado (retención: 24h, 3 particiones)"

kafka-describe: ## Describir el topic de precios
	docker exec cryptolake-kafka \
	    kafka-topics --bootstrap-server localhost:29092 \
	    --describe --topic prices.realtime
EOF
```

### 2.8 — ¡Arrancar todo!

Este es el momento de la verdad. La primera vez tardará unos minutos porque
Docker tiene que descargar las imágenes y construir las nuestras.

```bash
cd ~/Projects/cryptolake

# Arrancar todo
make up
```

**¿Qué está pasando?** Docker está:
1. Descargando imágenes base (~3-5 GB en total la primera vez)
2. Construyendo nuestras imágenes custom (Spark, Airflow)
3. Creando la red virtual entre contenedores
4. Arrancando cada servicio en orden de dependencias
5. Esperando healthchecks

**Si algo falla**, revisa los logs:

```bash
# Ver logs de todos los servicios
make logs

# O de un servicio específico (Ctrl+C para salir)
docker compose logs -f kafka
docker compose logs -f spark-master
```

### 2.9 — Verificar que todo funciona

Abre cada una de estas URLs en tu navegador:

| Servicio | URL | Credenciales |
|----------|-----|-------------|
| **MinIO Console** | http://localhost:9001 | cryptolake / cryptolake123 |
| **Kafka UI** | http://localhost:8080 | (sin auth) |
| **Spark UI** | http://localhost:8082 | (sin auth) |
| **Airflow** | http://localhost:8083 | admin / admin |

**En MinIO** deberías ver 4 buckets: cryptolake-bronze, cryptolake-silver,
cryptolake-gold, cryptolake-checkpoints.

**En Kafka UI** deberías ver el cluster "cryptolake" conectado (aún sin
topics — los crearemos ahora).

Ahora crea el topic de Kafka:

```bash
make kafka-create-topics
```

Ve a Kafka UI (http://localhost:8080) → Topics. Deberías ver
`prices.realtime` con 3 particiones.

### 2.10 — Probar Spark con Iceberg

Vamos a verificar que Spark puede crear tablas Iceberg:

```bash
make spark-shell
```

Esto abre una consola PySpark interactiva. Ejecuta:

```python
# Crear un namespace (como un schema de base de datos)
spark.sql("CREATE NAMESPACE IF NOT EXISTS cryptolake.bronze")
spark.sql("CREATE NAMESPACE IF NOT EXISTS cryptolake.silver")
spark.sql("CREATE NAMESPACE IF NOT EXISTS cryptolake.gold")

# Verificar
spark.sql("SHOW NAMESPACES IN cryptolake").show()

# Crear una tabla de prueba
spark.sql("""
    CREATE TABLE IF NOT EXISTS cryptolake.bronze.test_table (
        id INT,
        name STRING,
        value DOUBLE
    ) USING iceberg
""")

# Insertar datos de prueba
spark.sql("""
    INSERT INTO cryptolake.bronze.test_table VALUES
    (1, 'bitcoin', 67000.0),
    (2, 'ethereum', 3500.0),
    (3, 'solana', 150.0)
""")

# Leer los datos
spark.sql("SELECT * FROM cryptolake.bronze.test_table").show()

# Time travel: ver el historial de snapshots
spark.sql("SELECT * FROM cryptolake.bronze.test_table.snapshots").show()

# Limpiar
spark.sql("DROP TABLE cryptolake.bronze.test_table")
```

Si ves los datos correctamente, **felicidades** — tienes un Lakehouse
funcionando con Spark + Iceberg + MinIO.

Sal de la consola PySpark con `exit()` o Ctrl+D.

### 2.11 — Primer commit

```bash
cd ~/Projects/cryptolake

git add .
git commit -m "feat: initial infrastructure setup

- Docker Compose with MinIO, Kafka, Spark, Airflow, Iceberg
- Spark configured with Iceberg REST Catalog
- Kafka in KRaft mode (no ZooKeeper)
- Makefile with developer commands
- Project structure following data engineering best practices"
```

---

## PARTE 3 (FASE 2): Ingesta de Datos

Ahora que la infraestructura funciona, vamos a hacer que fluyan datos reales.

### 3.1 — Configuración centralizada con Pydantic

**¿Por qué Pydantic Settings?** En lugar de leer variables de entorno
manualmente con `os.getenv()`, Pydantic Settings las lee automáticamente,
las valida, les pone tipos, y les da valores por defecto. Es como tener
un "contrato" para tu configuración.

```bash
cat > src/config/settings.py << 'PYEOF'
"""
Configuración centralizada del proyecto.

Pydantic Settings lee automáticamente de:
1. Variables de entorno del sistema
2. Archivo .env en la raíz del proyecto

Ejemplo: MINIO_ENDPOINT en .env → settings.minio_endpoint en Python
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Todas las configuraciones del proyecto.
    
    Cada campo es una variable de entorno.
    El nombre del campo en snake_case se convierte automáticamente
    al nombre de la variable en UPPER_CASE.
    
    Ejemplo: minio_endpoint → lee de MINIO_ENDPOINT
    """
    
    # Le dice a Pydantic dónde buscar el archivo .env
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # Ignora variables que no están definidas aquí
    )

    # ── MinIO / S3 ──────────────────────────────────────────
    minio_endpoint: str = "http://localhost:9000"
    minio_access_key: str = "cryptolake"
    minio_secret_key: str = "cryptolake123"
    
    # ── Kafka ───────────────────────────────────────────────
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_topic_prices: str = "prices.realtime"
    
    # ── Iceberg ─────────────────────────────────────────────
    iceberg_catalog_uri: str = "http://localhost:8181"
    
    # ── APIs externas ───────────────────────────────────────
    coingecko_base_url: str = "https://api.coingecko.com/api/v3"
    fear_greed_url: str = "https://api.alternative.me/fng/"
    
    # ── Coins a rastrear ────────────────────────────────────
    tracked_coins: list[str] = [
        "bitcoin",
        "ethereum", 
        "solana",
        "cardano",
        "polkadot",
        "chainlink",
        "avalanche-2",
        "matic-network",
    ]
    
    # ── Buckets S3 ──────────────────────────────────────────
    bronze_bucket: str = "cryptolake-bronze"
    silver_bucket: str = "cryptolake-silver"
    gold_bucket: str = "cryptolake-gold"


# Singleton: una sola instancia para todo el proyecto
# Importa así: from src.config.settings import settings
settings = Settings()
PYEOF
```

### 3.2 — Configurar logging estructurado

```bash
cat > src/config/logging.py << 'PYEOF'
"""
Logging estructurado con structlog.

¿Por qué structlog en vez de logging estándar?
- Logs en formato JSON (parseables por herramientas de monitorización)
- Context automático (timestamp, nivel, módulo)
- Mucho más legible en desarrollo

Ejemplo de output:
  2025-01-15 10:30:00 [info] message_produced  topic=prices.realtime  coin=bitcoin
"""
import structlog


def setup_logging():
    """Configura structlog para el proyecto."""
    structlog.configure(
        processors=[
            # Añade timestamp automáticamente
            structlog.processors.TimeStamper(fmt="iso"),
            # Añade el nivel (info, warning, error)
            structlog.processors.add_log_level,
            # Formatea bonito para la consola
            structlog.dev.ConsoleRenderer(),
        ],
        # El logger base de Python
        wrapper_class=structlog.make_filtering_bound_logger(0),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )


# Configurar al importar
setup_logging()
PYEOF
```

### 3.3 — Instalar dependencias Python en tu Mac

Para ejecutar los scripts de ingesta FUERA de Docker (en tu Mac directamente),
necesitas instalar las dependencias:

```bash
cd ~/Projects/cryptolake

# Crear entorno virtual de Python
python3.11 -m venv .venv

# Activar el entorno virtual
# (verás (.venv) al principio de tu prompt)
source .venv/bin/activate

# Instalar dependencias
pip install \
    pydantic==2.5.0 \
    pydantic-settings==2.1.0 \
    requests==2.31.0 \
    websockets==12.0 \
    confluent-kafka==2.3.0 \
    structlog==24.1.0
```

**¿Qué es un entorno virtual?** Es una carpeta (`.venv/`) que contiene una
copia aislada de Python con sus propias librerías. Así las dependencias de
CryptoLake no chocan con otros proyectos de tu Mac. Siempre que trabajes en
el proyecto, activa el entorno con `source .venv/bin/activate`.

### 3.4 — Productor Kafka: Precios en tiempo real desde Binance

Este es el componente más emocionante — conectamos con Binance WebSocket
para recibir precios de crypto en TIEMPO REAL y los publicamos en Kafka.

```bash
cat > src/ingestion/streaming/binance_producer.py << 'PYEOF'
"""
Productor Kafka: Binance WebSocket → Kafka topic "prices.realtime"

¿Cómo funciona?
1. Se conecta al WebSocket público de Binance (gratis, sin API key)
2. Se suscribe al stream "aggTrade" (trades agregados) de cada par
3. Cada vez que alguien compra/vende BTC, ETH, etc., Binance nos envía el precio
4. Transformamos el mensaje al formato de CryptoLake
5. Lo publicamos en el topic de Kafka "prices.realtime"

Binance envía ~50-200 mensajes por SEGUNDO dependiendo de la actividad del mercado.

Para ejecutar:
    python -m src.ingestion.streaming.binance_producer
"""
import asyncio
import json
import signal
import sys
from datetime import datetime, timezone

import structlog
from confluent_kafka import Producer

from src.config.settings import settings

# Configurar logger
logger = structlog.get_logger()

# ── Mapeo de símbolos ──────────────────────────────────────
# Binance usa "BTCUSDT", nosotros usamos "bitcoin" (formato CoinGecko).
# Este mapeo unifica los identificadores entre fuentes.
BINANCE_SYMBOLS = {
    "btcusdt": "bitcoin",
    "ethusdt": "ethereum",
    "solusdt": "solana",
    "adausdt": "cardano",
    "dotusdt": "polkadot",
    "linkusdt": "chainlink",
    "avaxusdt": "avalanche-2",
    "maticusdt": "matic-network",
}

# URL base del WebSocket de Binance
BINANCE_WS_URL = "wss://stream.binance.com:9443/ws"


def create_kafka_producer() -> Producer:
    """
    Crea y configura un productor de Kafka.
    
    Configuraciones importantes:
    - acks=all: El productor espera a que Kafka confirme que el mensaje
      fue escrito en TODAS las réplicas. Máxima durabilidad.
    - compression.type=snappy: Comprime los mensajes para reducir ancho 
      de banda y espacio en disco. Snappy es rápido con buena compresión.
    - linger.ms=100: En vez de enviar cada mensaje individualmente, 
      espera 100ms para agrupar varios mensajes en un solo envío (batch).
      Esto mejora el throughput a costa de 100ms de latencia extra.
    """
    config = {
        "bootstrap.servers": settings.kafka_bootstrap_servers,
        "client.id": "binance-price-producer",
        "acks": "all",
        "compression.type": "snappy",
        "linger.ms": 100,
        "batch.size": 65536,   # 64KB de batch máximo
        "retries": 3,
        "retry.backoff.ms": 500,
    }
    
    logger.info(
        "kafka_producer_created",
        bootstrap_servers=settings.kafka_bootstrap_servers,
    )
    return Producer(config)


def delivery_callback(err, msg):
    """
    Callback que Kafka llama cuando un mensaje se entrega (o falla).
    
    ¿Por qué un callback? Porque la producción es asíncrona.
    Cuando llamas a producer.produce(), el mensaje se pone en un buffer
    interno. Kafka lo envía en background y llama a este callback
    cuando sabe si se entregó o no.
    """
    if err:
        logger.error(
            "kafka_delivery_failed",
            error=str(err),
            topic=msg.topic(),
        )


def transform_binance_trade(raw_data: dict) -> dict:
    """
    Transforma un mensaje raw de Binance a nuestro schema estándar.
    
    Binance aggTrade format (lo que recibimos):
    {
        "e": "aggTrade",     // tipo de evento
        "s": "BTCUSDT",      // símbolo del par
        "p": "67432.10",     // precio (STRING, no número)
        "q": "0.123",        // cantidad
        "T": 1708900000000,  // timestamp del trade (milisegundos)
        "E": 1708900000001,  // timestamp del evento
        "m": false           // ¿el comprador es el maker?
    }
    
    CryptoLake format (lo que producimos a Kafka):
    {
        "coin_id": "bitcoin",
        "symbol": "BTCUSDT",
        "price_usd": 67432.10,    // Convertido a float
        "quantity": 0.123,
        "trade_time_ms": 1708900000000,
        "ingested_at": "2025-01-15T10:30:00+00:00",
        "source": "binance_websocket"
    }
    """
    symbol_lower = raw_data.get("s", "").lower()
    coin_id = BINANCE_SYMBOLS.get(symbol_lower, symbol_lower)
    
    return {
        "coin_id": coin_id,
        "symbol": raw_data.get("s", ""),
        "price_usd": float(raw_data.get("p", 0)),
        "quantity": float(raw_data.get("q", 0)),
        "trade_time_ms": raw_data.get("T", 0),
        "event_time_ms": raw_data.get("E", 0),
        "ingested_at": datetime.now(timezone.utc).isoformat(),
        "source": "binance_websocket",
        "is_buyer_maker": raw_data.get("m", False),
    }


async def stream_prices():
    """
    Loop principal: conecta a Binance WebSocket y produce a Kafka.
    
    Flujo:
    1. Construye la URL combinando todos los streams que queremos
    2. Se conecta al WebSocket
    3. Por cada mensaje recibido:
       a. Parsea el JSON
       b. Transforma al formato CryptoLake
       c. Produce a Kafka (con coin_id como key para particionado)
    4. Si se desconecta, espera 5 segundos y reconecta
    
    ¿Por qué coin_id como key de Kafka?
    Kafka garantiza que mensajes con la misma key van a la misma partición.
    Esto significa que todos los mensajes de "bitcoin" estarán en la misma
    partición, manteniendo el orden temporal de los trades de BTC.
    """
    # Importar websockets aquí para permitir importar el módulo sin tenerlo
    import websockets
    
    producer = create_kafka_producer()
    
    # Construir URL con todos los streams combinados
    # Formato: wss://stream.binance.com:9443/ws/btcusdt@aggTrade/ethusdt@aggTrade/...
    streams = "/".join(
        f"{symbol}@aggTrade" for symbol in BINANCE_SYMBOLS.keys()
    )
    ws_url = f"{BINANCE_WS_URL}/{streams}"
    
    logger.info(
        "connecting_to_binance",
        symbols=list(BINANCE_SYMBOLS.keys()),
        num_pairs=len(BINANCE_SYMBOLS),
    )
    
    message_count = 0
    
    # Loop de reconexión: si se cae, reconecta automáticamente
    while True:
        try:
            async with websockets.connect(ws_url) as websocket:
                logger.info("websocket_connected", url=BINANCE_WS_URL)
                
                # Loop de lectura: procesa cada mensaje que llega
                async for raw_message in websocket:
                    try:
                        data = json.loads(raw_message)
                        
                        # Binance combined streams envuelve en {"stream": ..., "data": {...}}
                        if "data" in data:
                            data = data["data"]
                        
                        # Ignorar mensajes que no son trades
                        if data.get("e") != "aggTrade":
                            continue
                        
                        # Transformar al formato CryptoLake
                        record = transform_binance_trade(data)
                        
                        # Producir a Kafka
                        producer.produce(
                            topic=settings.kafka_topic_prices,
                            # Key: determina la partición. Mismo coin → misma partición
                            key=record["coin_id"].encode("utf-8"),
                            # Value: el mensaje completo en JSON
                            value=json.dumps(record).encode("utf-8"),
                            callback=delivery_callback,
                        )
                        
                        message_count += 1
                        
                        # Cada 500 mensajes: flush (forzar envío) y log de progreso
                        if message_count % 500 == 0:
                            producer.flush()
                            logger.info(
                                "streaming_progress",
                                total_messages=message_count,
                                last_coin=record["coin_id"],
                                last_price=record["price_usd"],
                            )
                    
                    except json.JSONDecodeError as e:
                        logger.warning("json_parse_error", error=str(e))
                    except (KeyError, ValueError, TypeError) as e:
                        logger.warning("transform_error", error=str(e))
        
        except Exception as e:
            logger.warning(
                "websocket_disconnected",
                error=str(e),
                reconnecting_in="5s",
                total_messages_so_far=message_count,
            )
            # Flush mensajes pendientes antes de reconectar
            producer.flush()
            await asyncio.sleep(5)


def main():
    """Punto de entrada principal."""
    logger.info("binance_producer_starting")
    
    # Manejar Ctrl+C limpiamente
    def signal_handler(sig, frame):
        logger.info("shutting_down", total_messages=0)
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Ejecutar el loop de streaming
    asyncio.run(stream_prices())


if __name__ == "__main__":
    main()
PYEOF
```

### 3.5 — Probar el productor Kafka

Asegúrate de que los servicios están corriendo y el topic existe:

```bash
# Verificar servicios
make status

# El topic debería existir (lo creamos antes)
make kafka-topics
```

Ahora ejecuta el productor:

```bash
cd ~/Projects/cryptolake

# Asegúrate de que el entorno virtual está activo
source .venv/bin/activate

# Ejecutar el productor
python -m src.ingestion.streaming.binance_producer
```

Deberías ver algo como:

```
2025-01-15T10:30:00 [info] binance_producer_starting
2025-01-15T10:30:01 [info] kafka_producer_created  bootstrap_servers=localhost:9092
2025-01-15T10:30:01 [info] connecting_to_binance  symbols=['btcusdt', ...] num_pairs=8
2025-01-15T10:30:02 [info] websocket_connected
2025-01-15T10:30:15 [info] streaming_progress  total_messages=500  last_coin=bitcoin  last_price=67432.1
2025-01-15T10:30:28 [info] streaming_progress  total_messages=1000 last_coin=ethereum last_price=3501.2
```

**¡Déjalo corriendo!** Ahora abre otra pestaña de Terminal (Cmd+T) y ve a
Kafka UI (http://localhost:8080):

1. Click en "Topics" → `prices.realtime`
2. Click en "Messages"
3. Deberías ver mensajes JSON fluyendo en tiempo real

**Cada mensaje** se ve así:

```json
{
  "coin_id": "bitcoin",
  "symbol": "BTCUSDT",
  "price_usd": 67432.10,
  "quantity": 0.00234,
  "trade_time_ms": 1708900000000,
  "ingested_at": "2025-01-15T10:30:00+00:00",
  "source": "binance_websocket"
}
```

Para parar el productor: **Ctrl+C**

### 3.6 — Extractor Batch: Clase base (Template Method Pattern)

Ahora vamos con la ingesta batch. Usamos el patrón Template Method (que
conoces de Java): definimos el esqueleto del algoritmo en una clase base,
y cada extractor concreto implementa los pasos específicos.

```bash
cat > src/ingestion/batch/base_extractor.py << 'PYEOF'
"""
Clase base abstracta para extractores batch.

Patrón Template Method:
    run() define el flujo: extract → validate → enrich
    Cada subclase implementa extract() y opcionalmente validate().

¿Por qué este patrón?
Todos nuestros extractores (CoinGecko, Fear & Greed, y futuros) siguen
el mismo flujo: extraer datos → validar → enriquecer con metadata.
En vez de repetir esa lógica, la centralizamos aquí.
"""
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

import requests
import structlog

logger = structlog.get_logger()


class BaseExtractor(ABC):
    """
    Clase base para todos los extractores de datos batch.
    
    Uso:
        class MiExtractor(BaseExtractor):
            def extract(self) -> list[dict]:
                # Lógica específica de extracción
                return [{"dato": "valor"}]
        
        extractor = MiExtractor("mi_fuente")
        datos = extractor.run()  # extract → validate → enrich
    """
    
    def __init__(self, source_name: str):
        self.source_name = source_name
        
        # requests.Session reutiliza la conexión HTTP entre requests.
        # Es más eficiente que crear una nueva conexión cada vez.
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "CryptoLake/1.0 (Educational Project)",
            "Accept": "application/json",
        })
    
    def run(self) -> list[dict[str, Any]]:
        """
        Ejecuta el pipeline completo: extract → validate → enrich.
        
        Returns:
            Lista de registros listos para cargar en Bronze.
        """
        logger.info("extraction_started", source=self.source_name)
        start_time = datetime.now(timezone.utc)
        
        # Paso 1: Extraer datos de la fuente
        raw_data = self.extract()
        logger.info("extraction_raw", source=self.source_name, raw_count=len(raw_data))
        
        # Paso 2: Validar (filtrar registros inválidos)
        validated_data = self.validate(raw_data)
        logger.info(
            "extraction_validated",
            source=self.source_name,
            valid_count=len(validated_data),
            dropped=len(raw_data) - len(validated_data),
        )
        
        # Paso 3: Enriquecer con metadata de ingesta
        enriched_data = self.enrich(validated_data)
        
        elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
        logger.info(
            "extraction_completed",
            source=self.source_name,
            total_records=len(enriched_data),
            elapsed_seconds=round(elapsed, 2),
        )
        
        return enriched_data
    
    @abstractmethod
    def extract(self) -> list[dict[str, Any]]:
        """
        Extrae datos de la fuente.
        Debe ser implementado por cada subclase.
        """
        ...
    
    def validate(self, data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Validación básica: filtra registros None.
        Las subclases pueden override para validación específica.
        """
        return [record for record in data if record is not None]
    
    def enrich(self, data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Añade metadata de ingesta a cada registro.
        
        _ingested_at: Cuándo se extrajeron los datos
        _source: De dónde vienen
        
        El prefijo _ indica "campo de metadata" (convención en data engineering).
        """
        now = datetime.now(timezone.utc).isoformat()
        for record in data:
            record["_ingested_at"] = now
            record["_source"] = self.source_name
        return data
PYEOF
```

### 3.7 — Extractor de CoinGecko (Precios Históricos)

```bash
cat > src/ingestion/batch/coingecko_extractor.py << 'PYEOF'
"""
Extractor de datos históricos desde CoinGecko API.

CoinGecko es una plataforma gratuita de datos de criptomonedas.
Su API pública (sin key) permite hasta 30 requests/minuto.

Endpoint que usamos:
    GET /coins/{id}/market_chart?vs_currency=usd&days=90&interval=daily
    
    Retorna 3 arrays con [timestamp_ms, valor] para:
    - prices: Precio en USD
    - market_caps: Capitalización de mercado
    - total_volumes: Volumen de trading 24h

Para ejecutar:
    python -m src.ingestion.batch.coingecko_extractor
"""
import time
from typing import Any

import structlog

from src.config.settings import settings
from src.ingestion.batch.base_extractor import BaseExtractor

logger = structlog.get_logger()


class CoinGeckoExtractor(BaseExtractor):
    """Extrae precios históricos y métricas de mercado de CoinGecko."""
    
    def __init__(self, days: int = 90):
        """
        Args:
            days: Número de días de histórico a extraer.
                  CoinGecko soporta hasta 365 en la versión gratuita.
        """
        super().__init__(source_name="coingecko")
        self.days = days
        self.base_url = settings.coingecko_base_url
    
    def extract(self) -> list[dict[str, Any]]:
        """
        Extrae datos históricos de todos los coins configurados.
        
        Para cada coin hace un GET request a la API de CoinGecko,
        y combina las tres series (precio, market cap, volumen)
        en registros individuales por timestamp.
        
        Respeta el rate limiting esperando 2.5 segundos entre requests
        (CoinGecko free tier: 30 calls/min ≈ 1 call cada 2 segundos).
        """
        all_records: list[dict[str, Any]] = []
        
        for i, coin_id in enumerate(settings.tracked_coins):
            try:
                logger.info(
                    "extracting_coin",
                    coin=coin_id,
                    progress=f"{i+1}/{len(settings.tracked_coins)}",
                    days=self.days,
                )
                
                # Llamada a la API
                response = self.session.get(
                    f"{self.base_url}/coins/{coin_id}/market_chart",
                    params={
                        "vs_currency": "usd",
                        "days": str(self.days),
                        "interval": "daily",
                    },
                    timeout=30,
                )
                
                # Si hay error HTTP (429 = rate limit, 500 = server error), lanzar excepción
                response.raise_for_status()
                
                data = response.json()
                
                # CoinGecko devuelve arrays de [timestamp_ms, value]
                prices = data.get("prices", [])
                market_caps = data.get("market_caps", [])
                volumes = data.get("total_volumes", [])
                
                # Combinar las tres series por índice
                # (CoinGecko garantiza que están alineadas por timestamp)
                for idx, price_point in enumerate(prices):
                    timestamp_ms, price = price_point
                    
                    record = {
                        "coin_id": coin_id,
                        "timestamp_ms": int(timestamp_ms),
                        "price_usd": float(price),
                        "market_cap_usd": (
                            float(market_caps[idx][1])
                            if idx < len(market_caps) and market_caps[idx][1]
                            else None
                        ),
                        "volume_24h_usd": (
                            float(volumes[idx][1])
                            if idx < len(volumes) and volumes[idx][1]
                            else None
                        ),
                    }
                    all_records.append(record)
                
                logger.info(
                    "coin_extracted",
                    coin=coin_id,
                    datapoints=len(prices),
                )
                
                # Rate limiting: esperar entre requests
                if i < len(settings.tracked_coins) - 1:
                    time.sleep(2.5)
                
            except Exception as e:
                logger.error(
                    "coin_extraction_failed",
                    coin=coin_id,
                    error=str(e),
                    error_type=type(e).__name__,
                )
                # Continuar con el siguiente coin en vez de abortar todo
                continue
        
        return all_records
    
    def validate(self, data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Valida que los registros tengan sentido:
        - Precio debe ser positivo
        - Timestamp debe ser válido (> 0)
        - coin_id no puede ser vacío
        """
        valid = []
        invalid_count = 0
        
        for record in data:
            price = record.get("price_usd")
            timestamp = record.get("timestamp_ms")
            coin = record.get("coin_id")
            
            if (
                coin
                and price is not None
                and price > 0
                and timestamp is not None
                and timestamp > 0
            ):
                valid.append(record)
            else:
                invalid_count += 1
                if invalid_count <= 3:  # Solo logear los primeros 3
                    logger.warning("invalid_record_dropped", record=record)
        
        if invalid_count > 3:
            logger.warning(
                "additional_invalid_records",
                count=invalid_count - 3,
            )
        
        return valid


# ── Punto de entrada ───────────────────────────────────────
if __name__ == "__main__":
    extractor = CoinGeckoExtractor(days=90)
    records = extractor.run()
    
    # Mostrar resumen
    if records:
        coins = set(r["coin_id"] for r in records)
        print(f"\n📊 Resumen de extracción:")
        print(f"   Total registros: {len(records)}")
        print(f"   Coins extraídos: {len(coins)}")
        for coin in sorted(coins):
            coin_records = [r for r in records if r["coin_id"] == coin]
            print(f"   - {coin}: {len(coin_records)} datapoints")
    else:
        print("⚠️  No se extrajeron datos")
PYEOF
```

### 3.8 — Extractor de Fear & Greed Index

```bash
cat > src/ingestion/batch/fear_greed_extractor.py << 'PYEOF'
"""
Extractor del Crypto Fear & Greed Index.

El Fear & Greed Index mide el sentimiento del mercado crypto:
- 0-24:  Extreme Fear   (pánico, la gente vende por miedo)
- 25-49: Fear           (cautela general)
- 50-74: Greed          (optimismo, la gente compra)
- 75-100: Extreme Greed (euforia, posible burbuja)

Es un indicador contrarian: Warren Buffett dice "compra cuando
otros tienen miedo, vende cuando otros son codiciosos".

API: https://api.alternative.me/fng/
Gratuita, sin límite de requests.

Para ejecutar:
    python -m src.ingestion.batch.fear_greed_extractor
"""
from typing import Any

import structlog

from src.config.settings import settings
from src.ingestion.batch.base_extractor import BaseExtractor

logger = structlog.get_logger()


class FearGreedExtractor(BaseExtractor):
    """Extrae el índice Fear & Greed histórico."""
    
    def __init__(self, days: int = 90):
        super().__init__(source_name="fear_greed_index")
        self.days = days
    
    def extract(self) -> list[dict[str, Any]]:
        """
        Extrae datos históricos del Fear & Greed Index.
        
        La API devuelve:
        {
            "data": [
                {
                    "value": "25",                    # Valor del índice (STRING)
                    "value_classification": "Extreme Fear",
                    "timestamp": "1708819200",        # Unix timestamp (STRING)
                    "time_until_update": "43200"      # Segundos hasta próxima actualización
                },
                ...
            ]
        }
        """
        logger.info("extracting_fear_greed", days=self.days)
        
        response = self.session.get(
            settings.fear_greed_url,
            params={
                "limit": str(self.days),
                "format": "json",
            },
            timeout=30,
        )
        response.raise_for_status()
        
        data = response.json()
        
        records = []
        for entry in data.get("data", []):
            records.append({
                "value": int(entry["value"]),
                "classification": entry["value_classification"],
                "timestamp": int(entry["timestamp"]),
                "time_until_update": entry.get("time_until_update"),
            })
        
        logger.info("fear_greed_extracted", total_records=len(records))
        return records
    
    def validate(self, data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Valida que el valor esté en rango 0-100."""
        return [
            r for r in data
            if 0 <= r.get("value", -1) <= 100
            and r.get("timestamp", 0) > 0
        ]


if __name__ == "__main__":
    extractor = FearGreedExtractor(days=90)
    records = extractor.run()
    
    if records:
        print(f"\n📊 Fear & Greed Index - Últimos {len(records)} días:")
        print(f"   Último valor: {records[0]['value']} ({records[0]['classification']})")
        
        # Distribución de sentimiento
        from collections import Counter
        dist = Counter(r["classification"] for r in records)
        for sentiment, count in dist.most_common():
            print(f"   {sentiment}: {count} días")
PYEOF
```

### 3.9 — Probar los extractores batch

```bash
cd ~/Projects/cryptolake
source .venv/bin/activate

# Probar CoinGecko (tardará ~20 segundos por rate limiting)
python -m src.ingestion.batch.coingecko_extractor

# Probar Fear & Greed
python -m src.ingestion.batch.fear_greed_extractor
```

Deberías ver algo como:

```
📊 Resumen de extracción:
   Total registros: 728
   Coins extraídos: 8
   - avalanche-2: 91 datapoints
   - bitcoin: 91 datapoints
   - cardano: 91 datapoints
   - chainlink: 91 datapoints
   - ethereum: 91 datapoints
   - matic-network: 91 datapoints
   - polkadot: 91 datapoints
   - solana: 91 datapoints
```

```
📊 Fear & Greed Index - Últimos 90 días:
   Último valor: 72 (Greed)
   Greed: 35 días
   Fear: 25 días
   Extreme Greed: 18 días
   Extreme Fear: 7 días
   Neutral: 5 días
```

### 3.10 — Script de verificación completa

Creamos un script que verifica que TODO funciona:

```bash
cat > scripts/health_check.py << 'PYEOF'
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
PYEOF
```

Ejecútalo:

```bash
python scripts/health_check.py
```

### 3.11 — Segundo commit

```bash
cd ~/Projects/cryptolake
git add .
git commit -m "feat: data ingestion layer (streaming + batch)

- Binance WebSocket producer → Kafka (real-time prices)
- CoinGecko batch extractor (historical prices, 90 days)
- Fear & Greed Index batch extractor (market sentiment)
- Centralized configuration with Pydantic Settings
- Structured logging with structlog
- Template Method pattern for batch extractors
- Health check script for all services"
```

---

## PARTE 4: ¿Qué has conseguido?

Recapitulemos todo lo que tienes funcionando:

```
TU MACBOOK PRO M4
│
├── Docker Desktop corriendo con:
│   ├── MinIO          → Almacenamiento S3-compatible (Bronze/Silver/Gold buckets)
│   ├── Iceberg REST   → Catálogo de tablas Lakehouse
│   ├── Kafka          → Mensajería en streaming (mode KRaft)
│   ├── Kafka UI       → Interfaz visual para inspeccionar mensajes
│   ├── Spark Master   → Coordinador del cluster de procesamiento
│   ├── Spark Worker   → Ejecutor de jobs de procesamiento
│   ├── Airflow Web    → Orquestador de pipelines (interfaz web)
│   ├── Airflow Sched  → Scheduler de Airflow
│   └── PostgreSQL     → Base de datos interna de Airflow
│
├── Productor Kafka (Python)
│   └── Binance WebSocket → prices.realtime topic (~100-200 msgs/seg)
│
├── Extractores Batch (Python)
│   ├── CoinGecko: ~728 registros de precios históricos (8 coins × 91 días)
│   └── Fear & Greed: ~90 registros de sentimiento de mercado
│
└── Verificación: Spark puede crear y consultar tablas Iceberg sobre MinIO
```

### Comandos rápidos que deberías recordar

```bash
# Arrancar todo
make up

# Parar todo (conservando datos)
make down

# Ver estado de los servicios
make status

# Abrir consola PySpark
make spark-shell

# Ver mensajes en Kafka
# → http://localhost:8080

# Lanzar el productor de streaming
python -m src.ingestion.streaming.binance_producer

# Extraer datos históricos
python -m src.ingestion.batch.coingecko_extractor
python -m src.ingestion.batch.fear_greed_extractor

# Verificar que todo funciona
python scripts/health_check.py
```

---

## Próximos pasos: Fase 3 y 4

En las próximas fases implementaremos:

1. **Fase 3**: Cargar los datos extraídos en tablas Iceberg Bronze con Spark,
   y crear el job de Spark Streaming que lee de Kafka y escribe a Bronze
   en tiempo real.

2. **Fase 4**: Procesar Bronze → Silver (limpieza, deduplicación, MERGE INTO)
   y configurar los modelos dbt para la capa Gold (modelado dimensional).

Dime cuando estés listo para continuar.
