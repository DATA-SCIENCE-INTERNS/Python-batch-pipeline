# Known limitations and downfalls

This document intentionally describes weaknesses as well as strengths. They
are useful boundaries for operating the project and a roadmap for improvement.

## 1. One large transaction per month

All Silver loading, rejections, Gold promotion, summary refresh, and metadata
completion occur in one monthly transaction.

Consequences:

- A database restart near the end loses all work for that month.
- Millions of inserted rows generate substantial WAL and disk I/O.
- Gold promotion can appear frozen because it emits no incremental Python log.
- Long transactions retain database resources and delay cleanup.

Improvement: use durable staging tables keyed by run ID, commit chunk loads,
then perform a smaller atomic publish step.

## 2. Gold promotion is insert-heavy

The pipeline first inserts all valid rows into Silver, then inserts them again
into Gold. PostgreSQL writes both copies plus indexes and WAL.

Improvement: use PostgreSQL `COPY`, partition tables by month, tune indexes and
WAL for bulk ingestion, or retain only one curated physical layer when the
project requirements allow it.

## 3. `execute_values` is not the fastest bulk loader

Multi-row INSERTs are reliable and simple but slower and more memory-intensive
than PostgreSQL `COPY` for multi-million-row datasets.

Improvement: stream CSV or binary COPY data into staging tables.

## 4. Materialized summary refreshes after every batch

`REFRESH MATERIALIZED VIEW` recalculates the full summary and can become more
expensive as Gold grows.

Improvement: maintain an incremental aggregate for the affected month or
refresh on a separate reporting schedule.

## 5. Progress metadata updates only at commit

`batch_runs.extracted_rows` and related counters remain zero while a batch is
running, even though logs show chunk progress.

Improvement: store heartbeats and chunk checkpoints in separately committed
metadata transactions.

## 6. No resumable chunk checkpoints

If a monthly transaction fails after processing most of the file, the whole
month is reread and reloaded.

Improvement: record durable chunk or row-group checkpoints and stage each
completed unit under a run ID.

## 7. Approximate business key

NYC TLC does not provide a universal trip ID. The project hashes selected trip
attributes. Two legitimate trips with identical selected values may be treated
as duplicates, while small source corrections can produce a new key.

Improvement: document acceptable collision semantics with data owners or use a
source-provided identifier if one becomes available.

## 8. Source schema evolution requires code changes

Required-column checks fail safely, but new useful fields are dropped unless
added to the canonical schema and SQL tables.

Improvement: add contract-version detection, schema-drift alerts, and explicit
migrations.

## 9. Limited validation rules

Current checks cover obvious missing, negative, and timestamp-order errors.
They do not validate TLC zone ranges, plausible trip duration/speed, currency
bounds, duplicates within Silver, or cross-field business rules.

Improvement: add versioned quality rules and publish quality metrics by batch.

## 10. Rejected rows are stored as JSON text

This is flexible but inefficient for large-scale analysis, and the SQL column
is `TEXT` rather than PostgreSQL `JSONB`.

Improvement: use `JSONB`, index commonly queried properties, and define
retention rules.

## 11. Download reliability is basic

Downloads use timeouts and temporary files but lack retry/backoff, checksum
comparison against an upstream manifest, and explicit Parquet integrity checks
before database work.

Improvement: add bounded HTTP retries, content-type checks, Parquet metadata
validation, and source publication/completeness checks.

## 12. No concurrency guard

Two processes can ingest the same taxi type and month simultaneously.

Improvement: use a PostgreSQL advisory lock or a uniqueness rule for active
batches.

## 13. SQL files are initialization scripts, not migrations

Docker runs `/docker-entrypoint-initdb.d` only for a new volume. Changing SQL
files does not upgrade an existing database.

Improvement: adopt Alembic, Flyway, Liquibase, or another migration system.

## 14. Local-only orchestration

The CLI performs sequential backfills. There is no scheduler, dependency
graph, alerting service, SLA, or automatic catch-up policy.

Improvement: schedule the container with an orchestrator such as Airflow,
Prefect, Dagster, Kubernetes CronJob, or a managed cloud service.

## 15. Observability is incomplete

Logs are readable but not structured JSON, metrics are not exported, and no
alerts fire for stalled or failed batches.

Improvement: emit structured logs, durations, throughput, rejection rates,
heartbeats, and Prometheus/OpenTelemetry metrics.

## 16. Tests do not cover PostgreSQL end to end

Unit tests validate core transformations, but there is no automated integration
test proving schema initialization, transactional rollback, promotion, and
idempotency against a disposable PostgreSQL instance.

Improvement: add Docker-backed integration tests and CI.

## 17. Secrets and access controls are development-grade

Credentials are environment variables and PostgreSQL is published on the host.
There is no secrets manager, TLS, role separation, or network policy.

Improvement: use secret injection, least-privilege roles, private networking,
TLS, backups, and credential rotation before non-local deployment.

## 18. Local Bronze storage is not durable infrastructure

Raw files live on one workstation filesystem. They are not replicated,
versioned independently, lifecycle-managed, or protected by object-store
durability.

Improvement: place Bronze data in S3, Azure Blob Storage, GCS, or equivalent
object storage.

## Prioritized roadmap

1. Replace chunk INSERTs with durable staging plus PostgreSQL `COPY`.
2. Add advisory locking and integration tests.
3. Introduce database migrations.
4. Add HTTP retries and Parquet integrity validation.
5. Make progress/checkpoints durable and resumable.
6. Incrementally maintain the reporting aggregate.
7. Add scheduling, metrics, alerts, and production secret management.
