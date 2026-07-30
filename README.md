# NYC Taxi Batch Pipeline

A Python batch pipeline that downloads NYC TLC Yellow and Green trip data,
normalizes and validates it in chunks, and stores it in PostgreSQL using a
Bronze/Silver/Gold architecture.

## Data flow

```text
NYC TLC → Bronze Parquet → validation → Silver PostgreSQL
                                      ↘ rejected records
                        Silver → deduplicated Gold → monthly summary
```

Every execution is recorded in `pipeline.batch_runs`. File checksums and
row-level failures are retained for auditability, while Gold uses a stable
`trip_key` to make reruns idempotent.

## Setup

1. Copy `.env.example` to `.env` and choose a secure database password.
2. Start PostgreSQL:

   ```powershell
   docker compose up -d postgres
   ```

3. Create a virtual environment and install dependencies:

   ```powershell
   python -m venv .venv
   .venv\Scripts\python -m pip install -r requirements.txt
   ```

For host execution, set `POSTGRES_HOST=localhost` and
`BRONZE_DATA_PATH=data/bronze`. Docker Compose supplies its own container
values (`postgres` and `/app/data/bronze`).

## Run one batch

```powershell
python -m taxi_pipeline ingest --taxi-type yellow --year 2025 --month 1
```

Use `--taxi-type both` for Yellow and Green. Add `--overwrite` to download an
existing Bronze file again.

## Backfill

```powershell
python -m taxi_pipeline backfill --taxi-type both --start 2025-01 --end 2025-03
```

Each month is an independent batch. A failed month is reported while the
remaining requested batches continue.

## Test

```powershell
python -m pytest -q
```

## Important database note

The SQL files mounted at `/docker-entrypoint-initdb.d` run only when Docker
creates a new PostgreSQL data volume. After changing the SQL schema, use a
migration for an existing database or recreate the development volume
deliberately.
