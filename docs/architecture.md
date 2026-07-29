# NYC Taxi Batch Pipeline Architecture

## Architecture pattern

The project uses a Medallion Architecture:

1. Bronze: raw NYC TLC Parquet files.
2. Silver: cleaned and validated PostgreSQL staging tables.
3. Gold: final deduplicated PostgreSQL tables.

## Data flow

```mermaid
flowchart LR
    A[NYC TLC Yellow and Green Taxi Data]
    B[Python Requests Downloader]
    C[Bronze Raw Parquet Files]
    D[PyArrow Batch Reader]
    E[Pandas Transformation]
    F[Data Quality Validation]
    G[Silver PostgreSQL Tables]
    H[Transactional Promotion]
    I[Gold PostgreSQL Tables]
    J[Rejected Records]
    K[Pipeline Metadata]

    A --> B
    B --> C
    C --> D
    D --> E
    E --> F
    F -->|Valid| G
    F -->|Invalid| J
    G --> H
    H --> I

    B --> K
    F --> K
    H --> K