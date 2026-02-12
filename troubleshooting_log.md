# 📓 Registro de Errores y Lecciones Aprendidas — CryptoLake

Este documento detalla los fallos técnicos, errores de configuración y problemas de compatibilidad encontrados durante el desarrollo del proyecto y cómo se resolvieron.

## 1. Capa de Serving (FastAPI)

### ❌ Error de Dependencias en el Contenedor
- **Problema**: El contenedor `api` no tenía instaladas las librerías necesarias para conectarse a Iceberg (`pyiceberg`) ni para procesar datos tabulares (`pyarrow`, `s3fs`).
- **Error**: `ModuleNotFoundError: No module named 'pyiceberg'`.
- **Solución**: Se actualizaron los requerimientos en `docker/api/Dockerfile` y se reconstruyó la imagen incluyendo `pyiceberg[s3fs,pyarrow]`.

### ❌ Incompatibilidad de Atributos en PyArrow
- **Problema**: Se intentó usar `pyarrow.compute.max_element_index()` para encontrar el registro más reciente, pero la versión instalada en el contenedor no incluía ese atributo.
- **Error**: `AttributeError: module 'pyarrow.compute' has no attribute 'max_element_index'`.
- **Solución**: Se cambió la lógica técnica a un ordenamiento manual basado en Python (`sorted(rows, key=lambda x: x["date"], reverse=True)[0]`), garantizando robustez entre versiones.

### ❌ Schema Mismatch (Fear & Greed)
- **Problema**: La API esperaba una columna `value_classification`, pero la tabla en Iceberg (creada por Spark) usaba simplemente `classification`.
- **Error**: `KeyError: 'value_classification'`.
- **Solución**: Se ejecutó un `DESCRIBE TABLE` en Spark para validar el schema real y se actualizó el código de la ruta en `src/serving/api/routes/analytics.py`.

---

## 2. Ingesta y Procesamiento (Spark/Iceberg)

### ❌ Error de Resolución de Host
- **Problema**: Los scripts intentaban conectar al catálogo de Iceberg usando `localhost:8181`, lo cual fallaba desde dentro de los contenedores Docker.
- **Error**: `ConnectionRefusedError` o nombres de host no encontrados (`spark-iceberg`).
- **Solución**: Se estandarizaron los nombres de los servicios en `docker-compose.yml` (ej: `iceberg-rest` y `spark-master`) y se usaron las variables de entorno para inyectar los nombres de host correctos.

### ❌ Límite de Velocidad de API (Rate Limiting)
- **Problema**: CoinGecko devolvía errores al intentar descargar 365 días de historia para múltiples monedas simultáneamente.
- **Error**: `HTTP 429 Too Many Requests`.
- **Solución**: Se redujo el rango de descarga inicial a 90 días y se añadió lógica de espera (`time.sleep`) entre llamadas en los extractores batch.

### ❌ Falta de JARs para Streaming
- **Problema**: Spark no podía leer de Kafka porque faltaba el conector Maven necesario.
- **Error**: `java.lang.ClassNotFoundException: org.apache.spark.sql.kafka010.KafkaSourceProvider`.
- **Solución**: Se añadió el parámetro `--packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0` al comando `spark-submit` en el job de streaming.

---

## 3. Infraestructura y Docker

### ❌ Configuración de S3 (MinIO)
- **Problema**: PyIceberg y Spark tenían problemas para encontrar los buckets si no se especificaba el `path-style access`.
- **Solución**: Se forzó `s3.path-style-access: "true"` en todas las configuraciones de catálogo para asegurar compatibilidad con MinIO.

### ❌ Persistencia de Datos
- **Problema**: Al reiniciar los contenedores sin volúmenes definidos, el catálogo de Iceberg perdía el estado de las tablas aunque los archivos estuvieran en MinIO.
- **Solución**: Se aseguraron volúmenes persistentes para `minio-data` y se configuró el catálogo REST para ser la "fuente de verdad".
