# 🏗️ CryptoLake Architecture

## Architecture Decision Records (ADRs)

### ADR-001: Apache Iceberg as Table Format

**Status**: Accepted

**Context**: We need a table format that supports ACID transactions, schema evolution, and time travel on top of object storage.

**Decision**: Use Apache Iceberg as the table format for our Lakehouse.

**Rationale**:
- Industry-leading table format for 2025-2026
- Native support in Spark, Flink, Trino, and other engines
- MERGE INTO for efficient incremental updates
- Time travel for debugging and auditing
- Schema evolution without rewriting data

### ADR-002: MinIO for Local Development

**Status**: Accepted

**Context**: We need S3-compatible storage for local development that mirrors production AWS S3.

**Decision**: Use MinIO as S3-compatible storage for local development.

**Rationale**:
- 100% S3 API compatible
- Same code works locally and in production
- Easy Docker deployment
- Free and open source

### ADR-003: Medallion Architecture (Bronze → Silver → Gold)

**Status**: Accepted

**Context**: We need a data organization pattern that provides data quality progression.

**Decision**: Implement the Medallion Architecture with three layers.

**Rationale**:
- Bronze preserves raw data (immutable source of truth)
- Silver provides clean, deduplicated data
- Gold delivers business-ready dimensional models
- Each layer can be reprocessed independently

### ADR-004: Kafka for Streaming Ingestion

**Status**: Accepted

**Context**: We need real-time price data from Binance with at-least-once delivery guarantees.

**Decision**: Use Apache Kafka as the streaming message broker.

**Rationale**:
- Industry standard for streaming data
- Persistent message storage (replay capability)
- High throughput with low latency
- Excellent Spark Structured Streaming integration

### ADR-005: dbt for Gold Layer Transformations

**Status**: Accepted

**Context**: We need SQL-based transformations for building the dimensional model.

**Decision**: Use dbt-core with dbt-spark for Gold layer transformations.

**Rationale**:
- Declarative SQL transformations
- Built-in testing and documentation
- Incremental processing support
- Industry standard for analytics engineering
