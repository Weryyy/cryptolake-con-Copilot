# Troubleshooting Log — CryptoLake

Este documento registra los errores críticos encontrados durante el despliegue y sus resoluciones para facilitar el mantenimiento del sistema.

### 1. Spark Resource Deadlock
- **Problema**: Los trabajos de Spark (Thrift Server, Streaming Jobs, Batch) se quedaban en estado "PENDING" indefinidamente.
- **Causa**: El cluster standalone tiene recursos limitados (4 CPUs). Por defecto, cada aplicación intentaba usar todos los recursos disponibles, impidiendo que otras arrancaran.
- **Resolución**: Se configuró `--conf spark.cores.max=1` en todos los comandos de `spark-submit` y Thrift Server para permitir la ejecución paralela en un entorno local.

### 2. Airflow "Dependency Hell"
- **Problema**: `ImportError` al intentar usar Great Expectations o PyIceberg dentro de los contenedores de Airflow.
- **Causa**: La imagen base no incluía librerías de sistema necesarias para compilar `sasl` (requerido por `pyhive`) ni paquetes específicos de Iceberg/GX.
- **Resolución**: Se instaló `libsasl2-dev` y GCC en el Dockerfile de Airflow y se añadieron `great_expectations`, `pyiceberg[s3fs]`, y `dbt-spark[session]` a los requerimientos.

### 3. Schema Mismatch en Streaming (Bronze)
- **Problema**: `pyspark.sql.utils.AnalysisException` indicando que el campo `symbol` no existía o el esquema no coincidía.
- **Causa**: La tabla Iceberg se creó inicialmente con un esquema incompleto y los nuevos mensajes de Kafka contenían campos adicionales.
- **Resolución**: Se eliminó la tabla corrupta (`DROP TABLE bronze.realtime_prices`) y se borraron los checkpoints de S3/MinIO para forzar una recreación limpia con el esquema completo definido en `src/processing/schemas/bronze.py`.

### 4. Dashboard Crash (NoneType Error)
- **Problema**: El Dashboard (Streamlit) mostraba una pantalla roja de error: `TypeError: 'NoneType' object is not ...`.
- **Causa**: Al formatear la tabla de `Market Overview`, los campos de `price_change_24h_pct` venían como `null` desde la API de CoinGecko (por límites de rate o datos nuevos), y el estilizador de Pandas fallaba.
- **Resolución**: Se añadió `df.fillna(0)` antes de aplicar `.style.format` en `app.py`.

### 5. AI Wave: Predicciones Extremas
- **Problema**: El modelo de ML predecía precios absurdos (ej. BTC a $500k en 1 minuto).
- **Causa**: Falta de normalización robusta en la capa de salida y sesgos acumulativos en el `CouncilOfAgents`.
- **Resolución**: Se implementó un "clipping" en `inference_service.py` para limitar la salida normalizada entre -0.5 y 1.5, y una guarda lógica que impide cambios de precio superiores al 10% por predicción.

### 6. Latencia de Datos (Data Lag)
- **Problema**: Los datos en tiempo real llegaban al Dashboard con más de 1 hora de retraso y en intervalos de 1 minuto.
- **Causa**: Frecuencia de triggers streaming demasiado alta (30s-1m) y sobrecarga de tareas Spark (200 particiones de shuffle por defecto) en un entorno de un solo núcleo.
- **Resolución**: se redujeron los triggers a 10s, se bajó la ventana de agregación a 30s y se optimizó `spark.sql.shuffle.partitions=2` para acelerar el procesamiento de micro-batches.
- **Estatus**: RESUELTO (Latencia reducida a <2 mins).

### 7. Gold Transformation Stalled (dbt Errors)
- **Problema**: La transformación final (Gold) se quedaba en estado de ejecución infinito o mostraba datos desactualizados en el dashboard.
- **Causa**:
    1. Error de esquema: dbt intentaba mapear `volume_24h_usd` desde Bronze, cuando el campo se llama `quantity`.
    2. Lógica incremental: `WHERE _spark_ingested_at > (SELECT MAX(...) FROM ...)` devolvía `null` en tablas vacías, bloqueando la carga inicial.
    3. Falta de comunicación: La API consultaba la capa Silver (sin métricas avanzadas) en lugar de la Gold.
- **Resolución**: Se corrigió el modelo dbt `market_ohlc.sql`, se añadió `COALESCE` para cargas iniciales, se habilitó el Spark Thrift Server con cores limitados y se re-apuntó la API (`prices.py`) a la tabla `gold.fact_market_daily`.
- **Estatus**: RESUELTO.

---
**Nota**: En caso de errores no listados aquí, consultar los logs de Docker:
`docker-compose logs -f [service_name]`
