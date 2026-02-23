.PHONY: help up down down-clean logs logs-kafka logs-spark status spark-shell kafka-topics kafka-create-topics kafka-describe test lint format dbt-run dbt-test quality-check seed pipeline init-iceberg init-namespaces bronze-load silver-transform gold-transform train-ml train-ml-legacy

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
	@echo "   API Docs:        http://localhost:8000/docs"
	@echo "   Dashboard:       http://localhost:8501"
	@echo "   Grafana:         http://localhost:3000"
	@echo "   Iceberg Catalog: http://localhost:8181"
	@echo ""

down: ## Parar todos los servicios (conserva datos)
	docker compose down

down-clean: ## Parar y BORRAR todos los datos
	docker compose down -v
	@echo "🗑️  Todos los volumes eliminados"

rebuild: ## Rebuild y restart todos los servicios
	docker compose down
	docker compose up -d --build

logs: ## Ver logs de todos los servicios
	docker compose logs -f

logs-kafka: ## Ver logs solo de Kafka
	docker compose logs -f kafka

logs-spark: ## Ver logs solo de Spark
	docker compose logs -f spark-master spark-worker

logs-ml: ## Ver logs del servicio ML
	docker compose logs -f ml-inference

logs-api: ## Ver logs de la API
	docker compose logs -f api

logs-dashboard: ## Ver logs del dashboard
	docker compose logs -f dashboard

status: ## Ver estado de los servicios
	docker compose ps

spark-shell: ## Abrir consola PySpark interactiva
	docker exec -it cryptolake-spark-master \
	    /opt/spark/bin/pyspark

kafka-topics: ## Listar topics de Kafka
	docker exec cryptolake-kafka kafka-topics --bootstrap-server localhost:9092 --list

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

# ==========================================================
# PIPELINE COMMANDS
# ==========================================================

init-iceberg: ## Inicializar tablas y namespaces Iceberg
	docker exec -w /opt/spark/work cryptolake-spark-master python3 -m src.processing.batch.init_iceberg

bronze-load: ## Cargar datos desde APIs a Bronze
	@echo "🟤 Loading data to Bronze..."
	docker exec -w /opt/spark/work cryptolake-spark-master python3 -m src.processing.batch.api_to_bronze
	@echo "✅ Bronze load complete"

silver-transform: ## Transformar Bronze a Silver
	@echo "⚪ Transforming Bronze to Silver..."
	docker exec -w /opt/spark/work cryptolake-spark-master python3 -m src.processing.batch.bronze_to_silver
	@echo "✅ Silver transform complete"

gold-transform: ## Construir Star Schema en Gold (PySpark)
	@echo "🟡 Building Gold Star Schema..."
	docker exec -w /opt/spark/work cryptolake-spark-master \
	    /opt/spark/bin/spark-submit /opt/spark/work/src/processing/batch/silver_to_gold.py
	@echo "✅ Gold transform complete"

pipeline: ## Run full pipeline: init → bronze → silver → gold → dbt → quality
	@echo "🚀 Running full CryptoLake pipeline..."
	@echo ""
	@echo "Step 1/6: Init Iceberg namespaces"
	$(MAKE) init-iceberg
	@echo ""
	@echo "Step 2/6: Bronze load"
	$(MAKE) bronze-load
	@echo ""
	@echo "Step 3/6: Silver transform"
	$(MAKE) silver-transform
	@echo ""
	@echo "Step 4/6: Gold Star Schema (PySpark)"
	$(MAKE) gold-transform
	@echo ""
	@echo "Step 5/6: dbt run + test"
	$(MAKE) dbt-run
	$(MAKE) dbt-test || true
	@echo ""
	@echo "Step 6/6: Quality checks"
	$(MAKE) quality-check || true
	@echo ""
	@echo "✅ Full pipeline complete!"

# ==========================================================
# DBT
# ==========================================================

dbt-run: ## Run dbt transformations
	cd src/transformation/dbt_cryptolake && dbt run

dbt-test: ## Run dbt tests
	cd src/transformation/dbt_cryptolake && dbt test

# ==========================================================
# QUALITY
# ==========================================================

quality-check: ## Run data quality checks (Bronze + Silver + Gold)
	@echo "🔍 Running quality checks..."
	docker exec -w /opt/spark/work cryptolake-spark-master \
	    /opt/spark/bin/spark-submit /opt/spark/work/src/quality/run_quality_checks.py --layer=all
	@echo "✅ Quality checks complete"

quality-bronze: ## Run only Bronze quality checks
	docker exec -w /opt/spark/work cryptolake-spark-master \
	    /opt/spark/bin/spark-submit /opt/spark/work/src/quality/run_quality_checks.py --layer=bronze

quality-silver: ## Run only Silver quality checks
	docker exec -w /opt/spark/work cryptolake-spark-master \
	    /opt/spark/bin/spark-submit /opt/spark/work/src/quality/run_quality_checks.py --layer=silver

quality-gold: ## Run only Gold quality checks
	docker exec -w /opt/spark/work cryptolake-spark-master \
	    /opt/spark/bin/spark-submit /opt/spark/work/src/quality/run_quality_checks.py --layer=gold

# ==========================================================
# ML
# ==========================================================

train-ml: ## Train ML ensemble (GradientBoosting + RandomForest + LSTM)
	@echo "🧠 Training ML ensemble v2..."
	docker exec -w /app cryptolake-ml python -m src.ml.train --mode=ensemble
	@echo "✅ ML ensemble training complete"

train-ml-legacy: ## Train legacy TFT models (historical + recent)
	@echo "🧠 Training legacy TFT models..."
	docker exec -w /app cryptolake-ml python -m src.ml.train --mode=historical
	docker exec -w /app cryptolake-ml python -m src.ml.train --mode=recent
	@echo "✅ Legacy ML training complete"

# ==========================================================
# DEVELOPMENT
# ==========================================================

test: ## Run all tests
	pytest tests/ -v --cov=src

lint: ## Run linting
	ruff check src/ tests/
	mypy src/

format: ## Format code
	ruff format src/ tests/

seed: ## Load seed data
	python scripts/seed_data.py
