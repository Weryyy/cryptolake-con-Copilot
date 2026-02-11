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

## 🏗️ Architecture

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

## 📜 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
