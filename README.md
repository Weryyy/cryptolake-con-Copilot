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

## 🎯 Objetivo del Proyecto
El objetivo principal de **CryptoLake** es proporcionar una plataforma de datos robusta, escalable y de baja latencia para el análisis del mercado de criptomonedas. El proyecto demuestra la implementación de patrones modernos de ingeniería de datos, integrando:
*   **Ingesta Híbrida**: Captura de eventos en tiempo real (Binance) y lotes históricos (CoinGecko).
*   **Eficiencia de Almacenamiento**: Uso de **Apache Iceberg** para manejar transacciones ACID, evolución de esquemas y compactación de datos.
*   **Gobernanza y Calidad**: Transformaciones estructuradas con **dbt** y validaciones de calidad con **Great Expectations** en cada capa.
*   **Machine Learning**: Sistema Ensemble multi-modelo con predicción dual (Legacy TFT + Ensemble) y reentrenamiento automático.
*   **Servicio de Datos**: Provisión de métricas refinadas a través de una API de alto rendimiento y un dashboard interactivo.

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
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
    │  FastAPI      │  │  Streamlit    │  │  ML Pipeline │
    │  REST API     │  │  Dashboard    │  │  (Ensemble)  │
    └──────────────┘  └──────────────┘  └──────────────┘
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
| **Data Quality** | Great Expectations | Automated data validation per layer |
| **ML** | PyTorch + scikit-learn | Ensemble predictive models (GB + RF + LSTM) |
| **API** | FastAPI | REST API for analytics + ML inference |
| **Dashboard** | Streamlit + Plotly | Interactive visualizations with line toggles |
| **Containers** | Docker + Docker Compose | Reproducible deployment |
| **IaC** | Terraform | Infrastructure as Code |
| **CI/CD** | GitHub Actions | Automated linting, testing and builds |
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

## 🧠 Machine Learning: Ensemble Multi-Modelo

CryptoLake utiliza un sistema **Ensemble multi-modelo** con predicción dual para máxima fiabilidad:

### Modelo Ensemble (Principal)
| Componente | Peso | Descripción |
|------------|------|-------------|
| **GradientBoosting** | ~47% | Clasificación de dirección (sube/baja) con probabilidad |
| **RandomForest** | ~15% | Confirmación y diversidad |
| **ReturnLSTM** | ~38% | Magnitud del retorno + dirección con self-attention |

### Modelo Legacy TFT (A/B Testing)
- **Temporal Fusion Transformer** con dos memorias:
  - **Memoria Histórica** (`--mode historical`): 200 épocas. Estabilidad macro.
  - **Memoria Reciente** (`--mode recent`): 400 épocas. Sensibilidad micro.

### Features (20 indicadores engineered)
Retornos multi-lag, volatilidad, RSI, MACD, Bandas de Bollinger, ratio de volumen, momentum, Fear & Greed normalizado, y codificación cíclica de hora del día.

### Precisión
- **Ensemble**: ~60% dirección (71% filtrando por confianza > 0.2)
- **Reentrenamiento automático**: Cada 6 horas vía Airflow + API async

### Training Commands
```bash
make train-ml-all      # Ensemble + TFT + restart inference
make train-ensemble    # Solo ensemble
make train-tft         # Solo TFT (historical + recent)
```

## 📊 Dashboard Interactivo

El dashboard Streamlit incluye **7 secciones** con auto-refresco y controles de visibilidad:

| Página | Descripción |
|--------|-------------|
| **Market Overview** | Precios actuales, predicción AI dual, candlestick BTC real-time, accuracy del mejor modelo |
| **Price Charts** | Velas intradía OHLC + precio histórico por criptomoneda |
| **Coin Comparison** | Precio normalizado, métricas lado a lado, volumen comparativo |
| **Fear & Greed Index** | Gauge de sentimiento + gráfico de barras histórico |
| **Trading Signals** | Señales combinadas: AI + sentimiento + fiabilidad del modelo |
| **Logs & System** | Data Quality (GX), alertas del sistema tipo Slack, info de hardware |

**Funcionalidades clave:**
- 🔀 Toggles para mostrar/ocultar líneas individuales del gráfico
- 📈 Línea verde EMA (Exponential Moving Average) como mejora de predicción
- 🏆 Gauge automático del mejor modelo del día
- 🔍 Zoom persistente con rendering HTML nativo de Plotly

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

## 🔌 API Endpoints

| Endpoint | Method | Descripción |
|----------|--------|-------------|
| `/api/v1/analytics/market-overview` | GET | Vista general del mercado |
| `/api/v1/analytics/prediction` | GET | Predicción principal |
| `/api/v1/analytics/dual-prediction` | GET | Legacy vs Ensemble side-by-side |
| `/api/v1/analytics/model-comparison` | GET | Accuracy metrics por modelo |
| `/api/v1/analytics/prediction-history/{model}` | GET | Historial de predicciones |
| `/api/v1/analytics/realtime-ohlc/{coin_id}` | GET | Velas intradía 4h |
| `/api/v1/analytics/fear-greed-history` | GET | Histórico Fear & Greed |
| `/api/v1/analytics/dq-reports` | GET | Reportes Data Quality |
| `/api/v1/analytics/system-alerts` | GET | Alertas del sistema |
| `/api/v1/ml/retrain?mode=ensemble` | POST | Trigger reentrenamiento async |
| `/api/v1/ml/retrain-status` | GET | Estado del reentrenamiento |
| `/api/v1/health/latency` | GET | Latencia por capa del lakehouse |

## 🔁 Orchestración (Airflow DAGs)

| DAG | Schedule | Descripción |
|-----|----------|-------------|
| **`dag_full_pipeline`** | Diario @06:00 UTC | Batch extractors → Bronze → Silver → dbt Gold → DQ gates |
| **`dag_ml_retrain`** | Cada 6 horas | Retrain ensemble vía API → polling status → log resultados |
| **`dag_ml_training`** | Manual | Training separado (legacy) |
| **`iceberg_maintenance`** | Diario @02:00 UTC | Compactación de micro-archivos + expiración de snapshots |

## 🛡️ Troubleshooting

Si encuentras problemas al levantar el entorno (errores de Spark, fallos de dependencias en Airflow o el Dashboard), consulta el documento de [Troubleshooting Log](docs/troubleshooting_log.md). Contiene una lista de errores comunes y sus soluciones técnicas.

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
- **`market_ohlc`** — Multi-period OHLC (1h, 4h, 1d candles pre-computed)
- **`dim_coins`** — Cryptocurrency metadata and statistics
- **`dim_dates`** — Calendar dimension

### dbt Models (10 SQL models)

| Layer | Models |
|-------|--------|
| **Staging** | `stg_prices`, `stg_market_metrics`, `stg_fear_greed` |
| **Intermediate** | `int_market_enriched`, `int_price_daily_agg` |
| **Marts** | `fact_market_daily`, `fact_price_hourly`, `market_ohlc`, `dim_coins`, `dim_dates` |

## 📈 Key Features

- **Dual Pipeline**: Real-time streaming (Kafka → Spark Streaming) + daily batch
- **Lakehouse Architecture**: Apache Iceberg with Medallion pattern (Bronze → Silver → Gold)
- **Dimensional Modeling**: Kimball star schema with facts and dimensions
- **Ensemble ML**: Multi-model predictions with dual A/B testing (Ensemble + Legacy TFT)
- **Data Contracts**: Schema versioning and quality agreements between layers
- **Incremental Processing**: `MERGE INTO` for efficient Silver layer updates
- **Data Quality Gates**: Great Expectations validation suites with dashboard reporting
- **Interactive Dashboard**: 7 pages, line toggles, zoom persistence, auto-refresh
- **Automated Retraining**: Airflow DAG triggers ensemble retrain every 6 hours
- **Production-Ready**: CI/CD, monitoring, alerting, structured logging

## 🗂️ Project Structure

```
cryptolake/
├── .github/workflows/       # CI/CD pipelines (lint, test, dbt, docker)
├── docker/                  # Dockerfiles (Spark, Airflow, API, Prometheus)
├── terraform/               # Infrastructure as Code
├── src/
│   ├── config/              # Centralized settings (Pydantic)
│   ├── ingestion/           # Streaming (Kafka) + Batch extractors
│   ├── processing/          # Spark jobs (Bronze, Silver, VWAP)
│   ├── transformation/      # dbt models (10 SQL: staging, intermediate, marts)
│   ├── orchestration/       # Airflow DAGs (pipeline, ML retrain, maintenance)
│   ├── quality/             # Great Expectations DQ engine + validators
│   ├── serving/             # FastAPI + Streamlit dashboard
│   └── ml/                  # Ensemble training, inference, features (20)
├── models/                  # Pre-trained ML models (TFT, GB, RF, LSTM)
├── tests/                   # Unit + Integration tests
├── docs/                    # Architecture, data dictionary, contracts
├── scripts/                 # Setup and utility scripts
├── docker-compose.yml       # Full local environment (12+ services)
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
*   **Compaction DAG**: ✅ Automatización con Airflow para ejecutar `rewriteDataFiles`, consolidando micro-archivos de streaming.

### 2. Algoritmos de Rendimiento
*   **VWAP en Tiempo Real**: ✅ Cálculo distribuido del precio promedio ponderado por volumen en ventanas deslizantes (`silver.realtime_vwap`).
*   **Detección de Anomalías**: Capa de QA que utiliza Z-Score para identificar variaciones sospechosas.

### 3. Analytics Avanzado (Gold Layer)
*   **Modelos OHLC**: ✅ Agregaciones dbt para velas de 1h, 4h y 1d en `market_ohlc`.
*   **API Hot-Path**: Migración de consultas pesadas a tablas Gold pre-agregadas.

### 4. Caché de Baja Latencia
*   **Redis Integration**: ✅ Almacenamiento en caché de alertas, DQ reports y estado de reentrenamiento.

---

## 📜 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
