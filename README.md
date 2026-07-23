# NYC Taxi Batch Ingestion Pipeline

A Python batch pipeline that downloads NYC Taxi Yellow and Green trip data, processes it using a Medallion Architecture and stores validated data in PostgreSQL.

## Architecture

```text
NYC TLC
   ↓
Bronze raw Parquet files
   ↓
Silver validated PostgreSQL tables
   ↓
Gold final deduplicated PostgreSQL tables