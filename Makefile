.PHONY: help up down down-clean logs logs-kafka logs-spark status spark-shell kafka-topics kafka-create-topics kafka-describe test lint format dbt-run dbt-test quality-check seed pipeline

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
	    /opt/spark/bin/pyspark

kafka-topics: ## Listar topics de Kafka
	docker exec cryptolake-kafka kafka-topics --bootstrap-server localhost:9092 --list

init-iceberg: ## Inicializar tablas Iceberg
	docker exec -w /opt/spark/work cryptolake-spark-master python3 -m src.processing.batch.init_iceberg

seed: ## Load seed data
	python scripts/seed_data.py

pipeline: ## Run full pipeline manually
	@echo "🚀 Running full CryptoLake pipeline..."
	docker exec -w /opt/spark/work cryptolake-spark-master python3 -m src.processing.batch.api_to_bronze
	docker exec -w /opt/spark/work cryptolake-spark-master python3 -m src.processing.batch.bronze_to_silver
	@echo "✅ Pipeline complete!"
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
	docker exec -w /opt/spark/work cryptolake-spark-master python3 -m src.processing.batch.api_to_bronze
	docker exec -w /opt/spark/work cryptolake-spark-master python3 -m src.processing.batch.bronze_to_silver
	@echo "✅ Pipeline complete!"
