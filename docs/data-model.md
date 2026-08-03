# Data model

## Schemas

| Schema | Object | Purpose |
| --- | --- | --- |
| `pipeline` | `batch_runs` | One audit record per batch attempt |
| `pipeline` | `file_ingestions` | Bronze path, checksum, status, and row count |
| `pipeline` | `rejected_records` | Invalid rows and rejection reasons |
| `silver` | `trips` | Canonical validated Yellow and Green records |
| `gold` | `yellow_trips` | Deduplicated Yellow trips |
| `gold` | `green_trips` | Deduplicated Green trips |
| `gold` | `monthly_summary` | Trips, average distance, and revenue by month |

## Run statuses

`pipeline.batch_runs.status` is one of:

- `running`: run header exists but the monthly transaction has not committed
- `success`: Silver, rejected rows, Gold, summary, and counts committed
- `failed`: the batch failed or was deliberately interrupted

Row counters are written at the end of a successful transaction. A running
record can therefore show zero while Python logs show millions of processed
rows. This is expected, although incremental progress metadata is a future
improvement.

## Canonical trip key

The deterministic MD5 key combines:

- Taxi type
- Pickup and drop-off timestamps
- Pickup and drop-off location IDs
- Trip distance
- Fare amount
- Total amount
- Vendor ID

This is an inferred business key because the source has no universally unique
trip identifier. It makes exact reruns idempotent, but it may merge two
legitimate trips whose selected fields happen to match. Changing formatting or
business-key fields may also change the key.

MD5 is used for compact deterministic identity, not security.

## Lineage

Every Silver and Gold row retains:

- Source filename
- Source year and month
- Ingestion timestamp
- Taxi type, represented by the destination table in Gold

The file-level SHA-256 checksum provides a stronger identity for the Bronze
artifact.

## Common queries

Latest runs:

```sql
SELECT run_id, taxi_type, source_year, source_month, status,
       extracted_rows, loaded_rows, rejected_rows, started_at, finished_at
FROM pipeline.batch_runs
ORDER BY run_id DESC;
```

Loaded months:

```sql
SELECT taxi_type, source_year, source_month, COUNT(*) AS rows
FROM silver.trips
GROUP BY taxi_type, source_year, source_month
ORDER BY source_year, source_month, taxi_type;
```

Rejected records:

```sql
SELECT run_id, reject_reason, COUNT(*) AS rows
FROM pipeline.rejected_records
GROUP BY run_id, reject_reason
ORDER BY run_id DESC, rows DESC;
```

Gold counts:

```sql
SELECT 'yellow' AS taxi_type, COUNT(*) FROM gold.yellow_trips
UNION ALL
SELECT 'green', COUNT(*) FROM gold.green_trips;
```
