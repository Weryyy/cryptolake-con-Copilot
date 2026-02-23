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

---

## 4. Dashboard & Serving (Streamlit / FastAPI) — Fase 5

### ❌ Gráficos de Precio Histórico Desordenados para Non-BTC Coins
- **Problema**: Los gráficos de precio histórico para ethereum, solana y otras monedas distintas de bitcoin aparecían con un aspecto "raro" — las líneas zigzagueaban de forma caótica.
- **Causa raíz**: El endpoint `/prices/{coin_id}` devolvía datos de Iceberg sin ordenar. Los datos del scan de PyIceberg no garantizan orden, y las filas salían mezcladas (ej: Feb 20, 21, 22, 23, 13, 14, 15...). Al renderizar un `px.line()` con fechas desordenadas, la línea iba y venía.
- **Error visual**: El chart de Ethereum mostraba una línea que saltaba entre fechas de forma aleatoria en vez de una curva suave.
- **Solución**: Se añadió `df.sort(key=lambda x: str(x.get("price_date", "")))` en `src/serving/api/routes/prices.py` antes de devolver los resultados, tanto en la query principal (Gold) como en el fallback (Silver).

### ❌ Error OHLC Read Timeout en Dashboard
- **Problema**: El dashboard mostraba frecuentemente el error `Error OHLC: HTTPConnectionPool(host='api', port=8000): Read timed out. (read timeout=5)` en la barra lateral.
- **Causa raíz**: El timeout de `requests.get()` para el endpoint OHLC en tiempo real estaba configurado a solo 5 segundos. Las queries a Iceberg (especialmente `silver.realtime_vwap` con filtros de timestamp ISO-8601) pueden tardar más de 5s en responder, especialmente si el catálogo REST necesita refrescar metadatos o la tabla tiene muchos snapshots.
- **Solución**: Se incrementó el timeout de todas las llamadas HTTP del dashboard de 5s a 15s (o se añadió `timeout=15` donde no existía). Archivos afectados: `src/serving/dashboard/app.py` — `fetch_realtime_ohlc()`, `fetch_market_overview()`, `fetch_fear_greed()`, `fetch_price_history()`, `fetch_prediction()`, `fetch_prediction_accuracy()`, `fetch_system_alerts()`, `fetch_dq_reports()`.

### ⚠️ Model Accuracy Panel Muestra 0 Evaluaciones
- **Problema**: El panel de precisión del modelo (Model Accuracy) en Market Overview mostraba "Recopilando datos de precisión..." permanentemente con `total_evaluated: 0`.
- **Causa raíz**: La función `_evaluate_past_predictions()` en `inference_service.py` evalúa predicciones de 30-120 segundos de antigüedad. Si el servicio ML se reinició recientemente o no ha acumulado suficientes predicciones en Redis (key `prediction_history`), no hay nada que evaluar. Además, el timeout de 5s anterior impedía que la llamada al endpoint de accuracy completara correctamente.
- **Solución**: (1) Se aumentó el timeout a 15s para dar tiempo a la API. (2) El panel ahora muestra un mensaje informativo indicando que las métricas aparecerán tras ~2 minutos de predicciones continuas. No es un error — es comportamiento esperado cuando el servicio ML acaba de arrancar.

### ❌ Alertas del Sistema Sin Fecha
- **Problema**: En la sección "Logs & System Status", las alertas del sistema solo mostraban la hora (`HH:MM:SS`) sin la fecha, haciendo imposible saber si un error era de hoy o de días anteriores.
- **Solución**: Se cambió el formato de timestamp de `'%H:%M:%S'` a `'%Y-%m-%d %H:%M:%S'` en `src/serving/dashboard/app.py` para mostrar fecha y hora completa.

### ❌ Falta de Datos Históricos en Fear & Greed Index
- **Problema**: La página de Fear & Greed Index solo mostraba el valor actual con un gauge, sin contexto histórico. Era imposible entender la tendencia que llevó al índice a su estado actual.
- **Solución**: Se creó un nuevo endpoint `/api/v1/analytics/fear-greed-history` que devuelve todos los registros de `bronze.fear_greed_index` ordenados por timestamp. Se añadió un gráfico de barras con color-coding (rojo oscuro = extreme fear, verde = extreme greed) y líneas de referencia horizontales en 25, 50 y 75.

### ⚠️ Falta de Descripciones en Navegación del Dashboard
- **Problema**: Las secciones del dashboard no tenían descripción, y el usuario no sabía qué podía ver en cada apartado sin entrar.
- **Solución**: Se añadió un cuadro informativo (`st.info()`) al inicio de cada página explicando qué se puede ver, y una descripción corta en el sidebar debajo del selector de navegación.

### ❌ Model Accuracy Siempre en 0 — Evaluación Duplicada y Contenedor Sin Reiniciar
- **Problema**: El panel de precisión del modelo (Model Accuracy) nunca mostraba datos reales; siempre aparecía "Recopilando datos de precisión..." o `total_evaluated: 0`. Cuando finalmente funcionó, las métricas estaban infladas (9 evaluaciones de lo que deberían ser 3 predicciones) con `direction_accuracy: 0%`.
- **Causa raíz (doble)**:
  1. **Contenedor no reiniciado**: El servicio `ml-inference` monta `./src:/app/src` como volumen, por lo que el *archivo* `.py` se actualiza en caliente. Sin embargo, el *proceso Python* que ya está corriendo cargó el módulo en memoria al arrancar. Un simple `docker compose restart ml-inference` era necesario para que Python reimportara el código actualizado con `prediction_history` y `_evaluate_past_predictions`. El auto-refresh de Streamlit (30s) NO causa este problema — solo refresca el frontend.
  2. **Evaluación duplicada**: La función `_evaluate_past_predictions()` comprobaba `entry.get("evaluated")` pero NUNCA marcaba las entradas como evaluadas en Redis. En cada ciclo de 30s, el bucle volvía a leer las mismas predicciones de `prediction_history` (que están en la ventana 30-120s) y las contaba otra vez, inflando `total_evaluated` y haciendo que `direction_accuracy` convergiera incorrectamente a 0%.
- **Solución**:
  1. Se reinició el contenedor ML con `docker compose restart ml-inference`.
  2. Se reemplazó el check inútil `entry.get("evaluated")` por un Redis Set llamado `evaluated_timestamps`. Cada predicción evaluada se marca con `SADD evaluated_timestamps <ts>` y se verifica con `SISMEMBER` antes de evaluar. Los timestamps viejos (>5 min) se limpian automáticamente para no crecer infinitamente.
  3. Se limpiaron las keys contaminadas: `DEL prediction_history prediction_accuracy evaluated_timestamps`.
- **Verificación**: Tras 90 segundos, `total_evaluated: 2` (correcto), `direction_accuracy: 50%` (dato real), `evaluated_timestamps: 2` (sin duplicados).
