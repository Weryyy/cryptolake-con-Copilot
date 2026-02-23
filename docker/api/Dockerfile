FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    fastapi>=0.110.0 \
    uvicorn>=0.27.0 \
    pydantic>=2.5.0 \
    pydantic-settings>=2.1.0 \
    structlog>=24.1.0 \
    requests>=2.31.0 \
    confluent-kafka==2.3.0 \
    websockets==12.0 \
    "pyiceberg[s3fs,pyarrow]>=0.7.0" \
    prometheus-fastapi-instrumentator>=7.0.0 \
    redis \
    pandas \
    redis>=5.0.0 \
    scikit-learn>=1.4.0 \
    joblib>=1.3.0

RUN pip install --no-cache-dir \
    torch --extra-index-url https://download.pytorch.org/whl/cpu

COPY . .

CMD ["uvicorn", "src.serving.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--reload-dir", "src"]
