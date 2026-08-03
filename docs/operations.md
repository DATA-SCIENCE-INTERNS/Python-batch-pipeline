# Operations runbook

## Start the database

Run commands from the directory containing `docker-compose.yml`:

```powershell
docker compose up -d postgres
docker compose ps
```

The database should report `healthy` before a pipeline job starts.

The project publishes PostgreSQL on host port `5433` because this workstation
also has a native PostgreSQL server on port `5432`. Containers still connect to
the `postgres` service on its internal port `5432`.

For pgAdmin running directly on Windows, use:

```text
Host: 127.0.0.1
Port: 5433
Maintenance database: nyc_taxi
Username: taxi_user
```

## Run and monitor a backfill

Start a foreground job:

```powershell
docker compose run --rm pipeline backfill `
  --taxi-type green --start 2025-02 --end 2025-12
```

For a detached job with a predictable name:

```powershell
docker compose run -d --name green_backfill_2025 pipeline backfill `
  --taxi-type green --start 2025-02 --end 2025-12
```

Follow its logs:

```powershell
docker logs -f green_backfill_2025
```

`Ctrl+C` stops following logs; it does not stop the detached job.

## Determine whether a quiet job is stuck

The Python log is quiet during Gold promotion and materialized-view refresh.
Check PostgreSQL before stopping anything:

```powershell
docker exec nyc_taxi_postgres psql -U taxi_user -d nyc_taxi `
  -c "SELECT pid,state,wait_event_type,wait_event,now()-query_start AS age,left(query,120) AS query FROM pg_stat_activity WHERE datname='nyc_taxi' AND state <> 'idle';"
```

Interpretation:

- `active` plus `WALWrite`, `DataFileWrite`, or another I/O event means work
  is progressing.
- An active `INSERT INTO gold...` after the final chunk log is expected.
- A materialized-view refresh can also be quiet for a long period.
- Investigate an unchanged query only after checking disk space, PostgreSQL
  logs, and locks.

View database logs:

```powershell
docker logs --tail 100 nyc_taxi_postgres
```

## Inspect tables

Open an interactive console:

```powershell
docker exec -it nyc_taxi_postgres psql -U taxi_user -d nyc_taxi
```

Then:

```sql
\dt pipeline.*
\dt silver.*
\dt gold.*
SELECT * FROM gold.monthly_summary ORDER BY source_year,source_month,taxi_type;
\q
```

## Recover from interruption

If Docker or PostgreSQL restarts during a month:

1. Wait until PostgreSQL is healthy.
2. Check the run status and server logs.
3. Mark a genuinely abandoned `running` record as `failed`.
4. Rerun the same month.

Example audit correction:

```sql
UPDATE pipeline.batch_runs
SET status = 'failed',
    finished_at = now(),
    error_message = 'Interrupted by database restart'
WHERE run_id = 123 AND status = 'running';
```

Rerunning is safe for Gold because promotion ignores existing `trip_key`
values. Silver replacement occurs transactionally.

Do not mark an active run failed based only on quiet Python logs. First check
`pg_stat_activity`.

## Common errors

### `no configuration file provided: not found`

Docker Compose cannot find `docker-compose.yml`. Change to the project
directory or pass `-f` and `--project-directory`.

### `could not translate host name "postgres"`

The pipeline container temporarily cannot resolve the Compose database service,
often because the Compose network or database is restarting.

### `connection refused` or `database system is starting up`

PostgreSQL is stopped or recovering. The pipeline now retries connections, but
an already-open monthly transaction will roll back if its connection is
terminated.

### `connection already closed`

The server disappeared during an active transaction. Inspect PostgreSQL logs
for shutdown, crash, or resource events, then rerun the month.

### Quiet after the last `Processed batch` line

Usually Gold insertion or summary refresh. Query `pg_stat_activity`; do not
restart Docker while database work is active.

## Safe shutdown

Avoid stopping PostgreSQL during a batch. If interruption is necessary, expect
the current month to roll back:

```powershell
docker stop --time 30 <pipeline-container>
```

After all jobs finish:

```powershell
docker compose stop
```

Do not use `docker compose down -v` unless you explicitly intend to delete the
PostgreSQL data volume.
