# 🚀 CryptoLake Setup Guide

## Prerequisites

- Docker Desktop 24+ with at least 6 CPU cores, 8 GB RAM, 40 GB disk
- Python 3.11+
- Git
- make (usually pre-installed on macOS/Linux)

## Quick Start

```bash
# Clone the repository
git clone https://github.com/tu-usuario/cryptolake.git
cd cryptolake

# Copy environment variables
cp .env.example .env

# Start all services
make up

# Create Kafka topics
make kafka-create-topics
```

## Services

| Service | URL | Credentials |
|---------|-----|-------------|
| MinIO Console | http://localhost:9001 | cryptolake / cryptolake123 |
| Kafka UI | http://localhost:8080 | — |
| Spark UI | http://localhost:8082 | — |
| Airflow | http://localhost:8083 | admin / admin |
| API Docs | http://localhost:8000/docs | — |
| Dashboard | http://localhost:8501 | — |
| Grafana | http://localhost:3000 | admin / cryptolake |

## Running the Pipeline

```bash
# Run the streaming producer
python -m src.ingestion.streaming.binance_producer

# Run batch extractors
python -m src.ingestion.batch.coingecko_extractor
python -m src.ingestion.batch.fear_greed_extractor

# Health check
python scripts/health_check.py
```

## Development

```bash
# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e ".[dev]"

# Run tests
make test

# Run linting
make lint

# Format code
make format
```

## Stopping Services

```bash
# Stop (keep data)
make down

# Stop and delete all data
make down-clean
```
