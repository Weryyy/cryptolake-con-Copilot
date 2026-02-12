# ============================================================
# Spark 3.5 con soporte para Apache Iceberg y S3 (MinIO)
# ============================================================
# Base: imagen oficial de Spark 3.5
FROM apache/spark:3.5.0

USER root

# Instalar librerías Python que usaremos en nuestros jobs de Spark
RUN pip install --no-cache-dir \
    pyspark==3.5.0 \
    pyiceberg[s3fs]==0.7.1 \
    pyarrow==15.0.1 \
    kafka-python==2.0.2 \
    requests==2.31.0 \
    pydantic==2.5.0 \
    pydantic-settings==2.1.0 \
    structlog==24.1.0

# ── Descargar JARs de Iceberg ──────────────────────────────
# Spark es un proyecto Java/Scala. Para que sepa "hablar" con
# Iceberg y S3, necesita librerías .jar en su classpath.
ENV ICEBERG_VERSION=1.5.2

# iceberg-spark-runtime: El "driver" de Iceberg para Spark
RUN curl -L -o /opt/spark/jars/iceberg-spark-runtime-3.5_2.12-${ICEBERG_VERSION}.jar \
    https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-spark-runtime-3.5_2.12/${ICEBERG_VERSION}/iceberg-spark-runtime-3.5_2.12-${ICEBERG_VERSION}.jar

# iceberg-aws-bundle: Para que Iceberg hable con S3/MinIO
RUN curl -L -o /opt/spark/jars/iceberg-aws-bundle-${ICEBERG_VERSION}.jar \
    https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-aws-bundle/${ICEBERG_VERSION}/iceberg-aws-bundle-${ICEBERG_VERSION}.jar

# Configuración por defecto de Spark
COPY spark-defaults.conf /opt/spark/conf/spark-defaults.conf

# Hadoop/Spark a veces necesitan que el usuario tenga un nombre definido
ENV USER=root

# Mantener como root para evitar problemas de permisos en /opt/spark en esta imagen base
USER root
