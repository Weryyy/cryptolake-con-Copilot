FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    fastapi>=0.110.0 \
    uvicorn>=0.27.0 \
    pydantic>=2.5.0 \
    pydantic-settings>=2.1.0 \
    structlog>=24.1.0 \
    requests>=2.31.0

COPY . .

CMD ["uvicorn", "src.serving.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
