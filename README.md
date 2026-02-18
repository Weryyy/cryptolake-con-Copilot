# 🏔️ CryptoLake — Real-Time Crypto Analytics Lakehouse

[![CI Pipeline](https://github.com/Weryyy/cryptolake-con-Copilot/actions/workflows/ci.yml/badge.svg)](https://github.com/Weryyy/cryptolake-con-Copilot/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![dbt](https://img.shields.io/badge/dbt-1.8-FF694B?logo=dbt)](https://www.getdbt.com/)
[![Apache Iceberg](https://img.shields.io/badge/Apache_Iceberg-1.5-blue)](https://iceberg.apache.org/)

> An end-to-end data engineering platform that ingests real-time and historical
> cryptocurrency data, processes it through a **Medallion Architecture** (Bronze → Silver → Gold)
> on **Apache Iceberg**, transforms with **dbt**, orchestrates with **Airflow**, and serves
> analytics via **REST API** and interactive **dashboard** — all containerized with Docker.

---

## � Objetivo del Proyecto
El objetivo principal de **CryptoLake** es proporcionar una plataforma de datos robusta, escalable y de baja latencia para el análisis del mercado de criptomonedas. El proyecto demuestra la implementación de patrones modernos de ingeniería de datos, integrando:
*   **Ingesta Híbrida**: Captura de eventos en tiempo real (Binance) y lotes históricos (CoinGecko).
*   **Eficiencia de Almacenamiento**: Uso de **Apache Iceberg** para manejar transacciones ACID, evolución de esquemas y compactación de datos.
*   **Gobernanza y Calidad**: Transformaciones estructuradas con **dbt** y validaciones de calidad en cada capa.
*   **Servicio de Datos**: Provisión de métricas refinadas a través de una API de alto rendimiento lista para ser consumida por aplicaciones finales.

---

## �🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                         DATA SOURCES                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────────┐  │
│  │ Binance WS   │  │ CoinGecko    │  │ Alternative.me            │  │
│  │ (Real-time)  │  │ (Historical) │  │ (Fear & Greed Index)      │  │
│  └──────┬───────┘  └──────┬───────┘  └─────────────┬─────────────┘  │
└─────────┼─────────────────┼────────────────────────┼─────────────────┘
          │                 │                        │
          ▼                 ▼                        ▼
┌─────────────────┐  ┌──────────────────────────────────────┐
│   KAFKA          │  │   PYTHON EXTRACTORS                  │
│   (Streaming)    │  │   (Batch via Airflow)                │
└────────┬────────┘  └──────────────┬───────────────────────┘
         │                          │
         ▼                          ▼
┌──────────────────────────────────────────────────────────────────────┐
│                 LAKEHOUSE (MinIO + Apache Iceberg)                    │
│                                                                      │
│  ┌─────────────┐    ┌──────────────┐    ┌────────────────────────┐  │
│  │ 🥉 BRONZE   │    │ 🥈 SILVER    │    │ 🥇 GOLD               │  │
│  │ (Raw)       │───▶│ (Cleaned)    │───▶│ (Star Schema)         │  │
│  │ Iceberg     │    │ Iceberg      │    │ Iceberg + dbt         │  │
│  └─────────────┘    └──────────────┘    └────────────────────────┘  │
│         ▲                  ▲                       ▲                 │
│    Spark Streaming    Spark Batch              dbt models            │
└──────────────────────────────────────────────────────────────────────┘
                              │
                     ┌────────┴────────┐
                     ▼                 ▼
           ┌──────────────┐  ┌──────────────────┐
           │  FastAPI      │  │  Streamlit        │
           │  REST API     │  │  Dashboard        │
           └──────────────┘  └──────────────────┘
```

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Streaming** | Apache Kafka | Real-time price ingestion from Binance |
| **Processing** | Apache Spark (PySpark) | Batch + stream processing |
| **Table Format** | Apache Iceberg | ACID transactions, time travel, schema evolution |
| **Storage** | MinIO (S3-compatible) | Object storage for Lakehouse |
| **Transformation** | dbt-core + dbt-spark | SQL-based dimensional modeling (Kimball) |
| **Orchestration** | Apache Airflow | Pipeline scheduling and monitoring |
| **Data Quality** | Great Expectations | Automated data validation |
| **API** | FastAPI | REST API for analytics |
| **Dashboard** | Streamlit | Interactive visualizations |
| **Containers** | Docker + Docker Compose | Reproducible deployment |
| **IaC** | Terraform | Infrastructure as Code |
| **CI/CD** | GitHub Actions | Automated testing and deployment |
| **Monitoring** | Prometheus + Grafana | Pipeline observability |
| **Code Quality** | Ruff + mypy + pre-commit | Linting + type checking |

## 🚀 Quick Start

```bash
# Clone the repository
git clone https://github.com/Weryyy/cryptolake-con-Copilot.git
cd cryptolake-con-Copilot

# Copy environment variables
cp .env.example .env

# Start all 12+ services with one command
make up

# Create Kafka topics
make kafka-create-topics

# Verify everything is running
python scripts/health_check.py
```

## 🧠 Machine Learning: Dual Memory Council

CryptoLake utiliza un enfoque de **Consejo de Agentes** basado en **Temporal Fusion Transformers (TFT)** con dos modelos de entrenamiento:

1.  **Memoria Histórica** (`--mode historical`): 200 épocas. Estabilidad macro.
2.  **Memoria Reciente** (`--mode recent`): 400 épocas. Sensibilidad micro (volatilidad).

Los modelos son **multivariados** (utilizan Precio + Volumen) y se sincronizan automáticamente con el contenedor de la API mediante volúmenes de Docker.

### Services Dashboard

| Service | URL | Credentials |
|---------|-----|-------------|
| **MinIO Console** | http://localhost:9001 | `cryptolake` / `cryptolake123` |
| **Kafka UI** | http://localhost:8080 | — |
| **Spark UI** | http://localhost:8082 | — |
| **Airflow** | http://localhost:8083 | `admin` / `admin` |
| **API Docs** | http://localhost:8000/docs | — |
| **Dashboard** | http://localhost:8501 | — |
| **Grafana** | http://localhost:3000 | `admin` / `cryptolake` |

## 📊 Data Model

### Medallion Architecture

| Layer | Content | Format | Processing |
|-------|---------|--------|------------|
| **Bronze** | Raw data, unmodified | Iceberg (append-only) | Spark Streaming + Batch |
| **Silver** | Cleaned, deduplicated, typed | Iceberg (merge) | Spark Batch |
| **Gold** | Dimensional model (star schema) | Iceberg | dbt |

### Star Schema (Gold Layer)

- **`fact_market_daily`** — Daily crypto market metrics (price, volume, MAs, sentiment)
- **`fact_price_hourly`** — Hourly OHLCV from streaming data
- **`dim_coins`** — Cryptocurrency metadata and statistics
- **`dim_dates`** — Calendar dimension

## 📈 Key Features

- **Dual Pipeline**: Real-time streaming (Kafka → Spark Streaming) + daily batch
- **Lakehouse Architecture**: Apache Iceberg with Medallion pattern (Bronze → Silver → Gold)
- **Dimensional Modeling**: Kimball star schema with facts and dimensions
- **Data Contracts**: Schema versioning and quality agreements between layers
- **Incremental Processing**: `MERGE INTO` for efficient Silver layer updates
- **Data Quality Gates**: Great Expectations validation suites
- **Production-Ready**: CI/CD, monitoring, alerting, structured logging

## 🗂️ Project Structure

```
cryptolake/
├── .github/workflows/       # CI/CD pipelines
├── docker/                  # Dockerfiles (Spark, Airflow, API)
├── terraform/               # Infrastructure as Code
├── src/
│   ├── config/              # Centralized settings (Pydantic)
│   ├── ingestion/           # Streaming (Kafka) + Batch extractors
│   ├── processing/          # Spark jobs (Bronze, Silver)
│   ├── transformation/      # dbt models (Gold layer)
│   ├── orchestration/       # Airflow DAGs
│   ├── quality/             # Great Expectations suites
│   └── serving/             # FastAPI + Streamlit
├── tests/                   # Unit + Integration tests
├── docs/                    # Architecture, data dictionary, contracts
├── scripts/                 # Setup and utility scripts
├── docker-compose.yml       # Full local environment
├── Makefile                 # Developer commands
└── pyproject.toml           # Python project configuration
```

## 🧪 Development

```bash
# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# Install dependencies (including dev tools)
pip install -e ".[dev]"

# Run tests
make test

# Run linting
make lint

# Format code
make format

# Run the full pipeline manually
make pipeline
```

## 📝 Documentation

- [Architecture Decision Records](docs/architecture.md)
- [Data Dictionary](docs/data_dictionary.md)
- [Setup Guide](docs/setup_guide.md)
- [Data Contracts](docs/data_contracts/)
- [Troubleshooting Log](troubleshooting_log.md)

---

## 🚀 Roadmap y Optimizaciones
Estamos evolucionando el proyecto con las siguientes mejoras críticas:

### 1. Optimización del Almacenamiento (Iceberg Tuning)
*   **Hidden Partitioning & Sort Orders**: Implementación de `SORTED BY (timestamp)` en archivos Iceberg para maximizar el *data skipping* con PyArrow.
*   **Compaction DAG**: Automatización con Airflow para ejecutar `rewriteDataFiles`, consolidando micro-archivos de streaming en archivos optimizados.

### 2. Algoritmos de Rendimiento
*   **VWAP en Tiempo Real**: Cálculo distribuido del precio promedio ponderado por volumen en ventanas deslizantes.
*   **Detección de Anomalías**: Capa de QA que utiliza Z-Score para identificar y marcar variaciones sospechosas en tiempo real.

### 3. Analytics Avanzado (Gold Layer)
*   **Modelos OHLC**: Agregaciones dbt para velas de 1h, 4h y 1d directamente en la capa Gold.
*   **API Hot-Path**: Migración de las consultas pesadas del dashboard a tablas Gold pre-agregadas.

### 4. Caché de Baja Latencia
*   **Redis Integration**: Almacenamiento en caché de los "últimos 5 minutos" de precios para reducir la carga sobre el Storage Layer y permitir una respuesta de API sub-10ms.

---

## 📜 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
