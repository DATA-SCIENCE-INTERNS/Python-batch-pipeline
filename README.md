## NYC Taxi Batch Data Pipeline
A robust, containerized batch data pipeline for ingesting **NYC Taxi & Limousine Commission (TLC)** Yellow and Green taxi trip datasets into PostgreSQL.

The pipeline downloads monthly datasets, validates and cleans the data, stages it, performs quality checks, and promotes validated records into production tables while maintaining complete pipeline execution metadata.

## Project Overview
This project was developed as part of the Data Science Internship assignment.
The pipeline is designed to:

- Download NYC TLC Yellow and Green taxi datasets
- Process data in memory-efficient chunks
- Validate and clean records
- Load data into staging tables
- Perform data quality checks
- Promote valid data into production tables
- Prevent duplicate loads
- Record every pipeline execution
- Support both single-month ingestion and multi-month backfills

## Architecture

```
                NYC TLC Data
                     │
                     ▼
          Download Monthly Dataset
                     │
                     ▼
          Extract & Validate Records
                     │
                     ▼
             Staging Tables
                     │
        Data Quality Validation
                     │
         ┌───────────┴───────────┐
         │                       │
      Validation Pass       Validation Fail
         │                       │
         ▼                       ▼
   Production Tables      Log Failure
         │
         ▼
 Pipeline Run Metadata
```
## Tech Stack

- Python 3.11+
- PostgreSQL
- SQLAlchemy
- Pandas
- Docker
- Docker Compose
- Psycopg2
- Python Dotenv
- Pytest

# Project Structure

```
taxi-pipeline/
│
├── taxi_pipeline/
│   ├── cli.py
│   ├── extractor.py
│   ├── transformer.py
│   ├── validator.py
│   ├── loader.py
│   ├── database.py
│   ├── metadata.py
│   ├── config.py
│   └── utils.py
│
├── sql/
│   ├── create_tables.sql
│   └── migrations/
│
├── tests/
│
├── docker/
│
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```

# Database Schema

## Staging Tables
- staging_yellow_trips
- staging_green_trips

These temporarily hold newly downloaded data before validation.

## Production Tables
- yellow_trips
- green_trips

Only validated records are promoted here.

## Metadata Table

pipeline_runs

Stores:

- Run ID
- Taxi type
- Batch period
- Pipeline start time
- Pipeline end time
- Status
- Extracted rows
- Loaded rows
- Rejected rows
- Error messages

# Features

## Monthly Ingestion

Load a single month.
Example:

```bash
python -m taxi_pipeline ingest \
    --taxi-type yellow \
    --year 2021 \
    --month 1
```
## Backfill
Load multiple months.
Example
```bash
python -m taxi_pipeline backfill \
    --taxi-type both \
    --start 2021-01 \
    --end 2021-03
```
## Docker Execution

Run everything inside Docker.

```bash
docker compose run --rm pipeline ingest \
    --taxi-type yellow \
    --year 2021 \
    --month 1
```
# Installation

## Clone Repository

```bash
git clone https://github.com/<username>/taxi-pipeline.git

cd taxi-pipeline
```

## Create Environment

```bash
cp .env.example .env
```
Update

```
POSTGRES_HOST=db
POSTGRES_PORT=5432
POSTGRES_DB=taxi_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password
```
## Build Containers

```bash
docker compose build
```


## Start PostgreSQL

```bash
docker compose up -d
```
## Install Python Dependencies

```bash
pip install -r requirements.txt
```

# Running the Pipeline

## Yellow Taxi

```bash
python -m taxi_pipeline ingest \
--taxi-type yellow \
--year 2021 \
--month 1
```


## Green Taxi

```bash
python -m taxi_pipeline ingest \
--taxi-type green \
--year 2021 \
--month 1
```


## Both Taxi Types

```bash
python -m taxi_pipeline backfill \
--taxi-type both \
--start 2021-01 \
--end 2021-03
```


# Data Quality Checks

Before promoting data to production, the pipeline verifies:

- Source file exists
- Source file is readable
- Source file is not empty
- Required columns exist
- Pickup datetime precedes dropoff datetime
- Trip distance is non-negative
- Monetary values are non-negative
- Extracted rows equal loaded rows plus rejected rows
- No duplicate business keys exist

If any critical validation fails:

- Transaction is rolled back
- Final tables remain unchanged
- Error is logged
- Pipeline exits with a non-zero status code

# Idempotency

The pipeline is safe to rerun.

Duplicate records are prevented using a documented business key/hash strategy. Reprocessing the same batch does not increase the number of records in production tables.


# Logging

Each pipeline execution records:

- Run ID
- Taxi type
- Batch period
- Start time
- End time
- Duration
- Status
- Records extracted
- Records loaded
- Records rejected
- Error details

# Testing

Run tests using:

```bash
pytest
```

Tests include:

- Extraction
- Validation
- Database loading
- Duplicate prevention
- Transaction rollback
- Backfill execution

# Sample Validation Queries

## Total Yellow Trips

```sql
SELECT COUNT(*)
FROM yellow_trips;
```

## Total Green Trips

```sql
SELECT COUNT(*)
FROM green_trips;
```

## Duplicate Check

```sql
SELECT business_key,
COUNT(*)
FROM yellow_trips
GROUP BY business_key
HAVING COUNT(*) > 1;
```

## Pipeline Runs

```sql
SELECT *
FROM pipeline_runs
ORDER BY start_time DESC;
```

# Troubleshooting

## PostgreSQL Connection Failed

Verify:

- PostgreSQL container is running

```bash
docker compose ps
```

Check environment variables.

##Duplicate Rows

Ensure:

- Business key is correctly defined.
- Upsert/MERGE strategy is enabled.

## Pipeline Stops During Validation

Review:

- Pipeline logs
- Validation report
- Metadata table

Correct the source data before rerunning.

# Design Decisions

| Decision | Reason |
|-----------|--------|
| Staging tables | Prevent invalid data from reaching production |
| Transactional promotion | Ensures atomic updates |
| Chunk processing | Supports large datasets without excessive memory use |
| Metadata table | Enables auditing and monitoring |
| Docker Compose | Provides reproducible local environment |
| Idempotent loading | Prevents duplicate records during reruns |

# Future Improvements

- Apache Airflow orchestration
- Incremental loading
- Data versioning
- Cloud object storage integration (AWS S3 / Azure Blob)
- Great Expectations for advanced data validation
- Grafana dashboard for monitoring
- CI/CD pipeline using GitHub Actions

# Team Responsibilities

The project can be divided into the following areas:

- Data Extraction
- Data Validation
- Database Design
- Pipeline Development
- Docker & Deployment
- Testing
- Documentation

All team members should contribute code, participate in reviews, and understand the complete data flow.

# References

- NYC Taxi & Limousine Commission Trip Record Data
- DataTalksClub Docker & PostgreSQL Workshop
- DataTalksClub Workflow Orchestration Module

# License

This project was developed for educational purposes as part of the Data Science Internship assignment.



