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

## Run the Streamlit dashboard

The dashboard is a read-only reporting layer. It queries PostgreSQL but does
not start, stop, or modify ingestion jobs.

Start PostgreSQL and the dashboard from the project directory:

```powershell
cd "C:\Users\ekica\Documents\python pipeline\Python-batch-pipeline"
docker compose up -d --build dashboard
```

Compose waits for PostgreSQL to become healthy before starting Streamlit.
Open the dashboard at:

```text
http://localhost:8502
```

Check service state:

```powershell
docker compose ps
```

Expected port mappings:

```text
nyc_taxi_dashboard   0.0.0.0:8502->8501/tcp
nyc_taxi_postgres    0.0.0.0:5433->5432/tcp
```

Follow dashboard logs:

```powershell
docker compose logs -f dashboard
```

`Ctrl+C` stops following logs; it does not stop the dashboard.

Check Streamlit's health endpoint:

```powershell
(Invoke-WebRequest -UseBasicParsing `
  -Uri "http://127.0.0.1:8502/_stcore/health").Content
```

Expected response:

```text
ok
```

Restart or stop only the dashboard:

```powershell
docker compose restart dashboard
docker compose stop dashboard
```

### Dashboard database addresses

The correct address depends on where Streamlit runs:

| Streamlit location | PostgreSQL host | PostgreSQL port |
| --- | --- | --- |
| Docker Compose dashboard | `postgres` | `5432` |
| Windows host process | `127.0.0.1` | `5433` |

The Docker dashboard receives its settings from `docker-compose.yml`. Do not
change its host to `localhost`; inside the dashboard container, `localhost`
means the dashboard container itself.

### Dashboard port conflict

The project publishes Streamlit on host port `8502` because another Python
process on this workstation uses `8501`. If `8502` is later occupied, choose a
free host port in `.env`:

```dotenv
STREAMLIT_PORT=8503
```

Then recreate the dashboard and open the new port:

```powershell
docker compose up -d --force-recreate dashboard
```

### Dashboard cannot reach PostgreSQL

Inspect both services and their logs:

```powershell
docker compose ps
docker compose logs --tail 100 dashboard postgres
```

Confirm the dashboard can query the database from inside its container:

```powershell
docker exec nyc_taxi_dashboard python -c `
  "from dashboard.database import query_dataframe; print(query_dataframe('SELECT current_database()').to_dict('records'))"
```

Expected database name: `nyc_taxi`.

The Overview page distinguishes active pipeline database sessions from stale
`running` metadata. A stale badge means the audit table contains a running row
older than six hours but PostgreSQL has no corresponding pipeline session.
Investigate container and database logs before changing that audit record.

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
