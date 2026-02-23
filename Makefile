.PHONY: help up down down-clean logs logs-kafka logs-spark status spark-shell kafka-topics kafka-create-topics kafka-describe test lint format dbt-run dbt-test quality-check seed pipeline init-iceberg init-namespaces bronze-load silver-transform gold-transform train-ml train-ml-legacy train-ml-all retrain-api restart-ml ml-status

help: ## Mostrar esta ayuda
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
	awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

up: ## Arrancar todos los servicios
	@echo "Starting CryptoLake..."
	docker compose up -d --build
	@echo ""
	@echo "Waiting for services to be ready (~60s first time)..."
	@sleep 30
	@echo ""
	@echo "[OK] CryptoLake is running!"
	@echo ""
	@echo "Available services:"
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
	@echo "[OK] All volumes removed"

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
	@echo "[OK] Topic 'prices.realtime' created (retention: 24h, 3 partitions)"

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
	@echo "[BRONZE] Loading data to Bronze..."
	docker exec -w /opt/spark/work cryptolake-spark-master python3 -m src.processing.batch.api_to_bronze
	@echo "[OK] Bronze load complete"

silver-transform: ## Transformar Bronze a Silver
	@echo "[SILVER] Transforming Bronze to Silver..."
	docker exec -w /opt/spark/work cryptolake-spark-master python3 -m src.processing.batch.bronze_to_silver
	@echo "[OK] Silver transform complete"

gold-transform: ## Construir Star Schema en Gold (PySpark)
	@echo "[GOLD] Building Gold Star Schema..."
	docker exec -w /opt/spark/work cryptolake-spark-master \
	    /opt/spark/bin/spark-submit /opt/spark/work/src/processing/batch/silver_to_gold.py
	@echo "[OK] Gold transform complete"

pipeline: ## Run full pipeline: init → bronze → silver → gold → dbt → quality
	@echo "Running full CryptoLake pipeline..."
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
	@echo "[OK] Full pipeline complete!"

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
	@echo "[DQ] Running quality checks..."
	docker exec -w /opt/spark/work cryptolake-spark-master \
	    /opt/spark/bin/spark-submit /opt/spark/work/src/quality/run_quality_checks.py --layer=all
	@echo "[OK] Quality checks complete"

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
	@echo "Training ML ensemble v2..."
	docker exec -w /app cryptolake-ml python -m src.ml.train --mode=ensemble
	@echo "ML ensemble training complete"

train-ml-legacy: ## Train legacy TFT models (historical + recent)
	@echo "Training legacy TFT models..."
	docker exec -w /app cryptolake-ml python -m src.ml.train --mode=historical
	docker exec -w /app cryptolake-ml python -m src.ml.train --mode=recent
	@echo "Legacy ML training complete"

train-ml-all: ## Train BOTH models (ensemble + legacy) and restart inference
	@echo "Training ALL ML models..."
	$(MAKE) train-ml
	$(MAKE) train-ml-legacy
	$(MAKE) restart-ml
	@echo "All models trained and inference restarted"

retrain-api: ## Trigger retrain via API (same as Airflow does)
	@echo "Triggering ensemble retrain via API..."
	curl -s -X POST "http://localhost:8000/api/v1/ml/retrain?mode=ensemble" | python -m json.tool
	@echo ""
	@echo "Check status: make ml-status"

restart-ml: ## Restart ML inference service (reload models)
	@echo "Restarting ML inference..."
	docker compose restart ml-inference
	@echo "ML inference restarted (models will be reloaded)"

ml-status: ## Check ML retrain status and model comparison
	@echo "=== Retrain Status ==="
	@curl -s "http://localhost:8000/api/v1/ml/retrain-status" | python -m json.tool 2>/dev/null || echo "API not available"
	@echo ""
	@echo "=== Model Comparison ==="
	@curl -s "http://localhost:8000/api/v1/analytics/model-comparison" | python -m json.tool 2>/dev/null || echo "API not available"

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
