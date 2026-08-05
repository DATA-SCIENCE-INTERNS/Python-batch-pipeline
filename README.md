# NYC Taxi Batch Pipeline

A local Python batch pipeline for NYC TLC Yellow and Green taxi trip data. It
downloads monthly Parquet files, processes them in bounded-memory chunks,
validates each record, and loads PostgreSQL using a Bronze/Silver/Gold model.

This is a working portfolio and learning project. It demonstrates batch
ingestion, schema normalization, data-quality handling, lineage, transactions,
and idempotent loading. It is not yet a production-scale data platform; see
[Known limitations](docs/limitations.md).

## Architecture

```text
NYC TLC source
    |
    v
Bronze: immutable monthly Parquet files
    |
    v
PyArrow chunks -> Pandas normalization -> validation
                                      |          |
                                      |          +-> pipeline.rejected_records
                                      v
Silver: canonical validated trips
    |
    v
Gold: deduplicated Yellow/Green tables
    |
    v
gold.monthly_summary
```

Operational metadata is stored in `pipeline.batch_runs` and
`pipeline.file_ingestions`. A SHA-256 checksum identifies each Bronze file.
Gold tables use a deterministic `trip_key` primary key, so rerunning a batch
does not duplicate existing Gold records.

See [Architecture](docs/architecture.md) and
[Data model](docs/data-model.md) for details.

## Requirements

- Docker Desktop with Docker Compose
- PowerShell examples assume Windows
- Approximately 20 GB or more of free space for a full year, depending on
  PostgreSQL overhead and retained layers
- Python 3.12+ only if running or testing outside Docker

## Quick start

From the directory containing `docker-compose.yml`:

```powershell
cd "C:\Users\ekica\Documents\python pipeline\Python-batch-pipeline"
Copy-Item .env.example .env
docker compose up -d postgres
docker compose build pipeline
```

Change the example password before using the project outside an isolated local
development environment.

Run one monthly batch:

```powershell
docker compose run --rm pipeline ingest `
  --taxi-type yellow `
  --year 2025 `
  --month 1
```

Run an inclusive backfill:

```powershell
docker compose run --rm pipeline backfill `
  --taxi-type green `
  --start 2025-02 `
  --end 2025-12
```

Options:

- `--taxi-type yellow|green|both`
- `--overwrite` downloads an existing Bronze file again
- Backfill dates use `YYYY-MM`

## Host execution

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
```

For host execution, use:

```dotenv
POSTGRES_HOST=localhost
POSTGRES_PORT=5433
BRONZE_DATA_PATH=data/bronze
```

Compose execution must use:

```dotenv
POSTGRES_HOST=postgres
BRONZE_DATA_PATH=/app/data/bronze
```

The Compose file supplies these container-specific values automatically.
Port `5433` is used on the Windows host to avoid conflicts with a separately
installed PostgreSQL server on the default port `5432`.

## Tests

```powershell
python -m pytest tests -q
```

The current tests cover path/URL construction, month ranges, schema
normalization, deterministic keys, validation, and required-column checks.
Database integration tests are still a documented gap.

## Operations

For monitoring, table inspection, interruption recovery, and common errors,
see the [Operations runbook](docs/operations.md).

## Streamlit dashboard

The read-only dashboard presents pipeline health, run history, data quality,
Gold analytics, and file lineage. Start it with:

```powershell
docker compose up -d dashboard
```

Open `http://localhost:8502`. The dashboard queries PostgreSQL through the
internal Compose network and never launches ingestion jobs.

Useful status query:

```powershell
docker exec nyc_taxi_postgres psql -U taxi_user -d nyc_taxi `
  -c "SELECT run_id,taxi_type,source_year,source_month,status,extracted_rows,loaded_rows,rejected_rows FROM pipeline.batch_runs ORDER BY run_id DESC;"
```

## Repository map

```text
taxi_pipeline/
  __main__.py       CLI and backfill control
  config.py         Environment configuration
  extract.py        Download and Bronze paths
  transform.py      Canonical schema, trip key, validation
  database.py       PostgreSQL transactions and loading
  pipeline.py       End-to-end monthly orchestration
sql/                Initial PostgreSQL schemas and tables
tests/              Unit tests
docs/               Architecture, operations, decisions, and limitations
data/bronze/        Raw monthly source files
```

## Database initialization warning

Files under `sql/` are mounted into `/docker-entrypoint-initdb.d`. PostgreSQL
runs them only when it creates a new, empty data volume. Editing those files
does not migrate an existing database. Use a migration tool before treating
this project as a long-lived service.
