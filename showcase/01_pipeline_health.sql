/*
NYC Taxi Pipeline Showcase 01: Pipeline health and lineage
All queries are read-only.
*/

-- 1. Latest batch attempt for every taxi type and month.
-- Demonstrates orchestration, audit status, and row-level counters.
WITH latest AS (
    SELECT DISTINCT ON (taxi_type, source_year, source_month)
           run_id,
           taxi_type,
           source_year,
           source_month,
           status,
           started_at,
           finished_at,
           extracted_rows,
           loaded_rows,
           rejected_rows,
           error_message
    FROM pipeline.batch_runs
    ORDER BY taxi_type, source_year, source_month, run_id DESC
)
SELECT *
FROM latest
ORDER BY source_year, source_month, taxi_type;


-- 2. Successful monthly coverage.
-- A presentation-friendly matrix: one row per taxi type and one column/month.
WITH successful AS (
    SELECT taxi_type, source_month, MAX(run_id) AS latest_successful_run
    FROM pipeline.batch_runs
    WHERE source_year = 2025
      AND status = 'success'
    GROUP BY taxi_type, source_month
)
SELECT taxi_type,
       COUNT(*) AS completed_months,
       STRING_AGG(
           TO_CHAR(MAKE_DATE(2025, source_month, 1), 'Mon'),
           ', ' ORDER BY source_month
       ) AS completed_month_list
FROM successful
GROUP BY taxi_type
ORDER BY taxi_type;


-- 3. Overall processing totals for successful runs.
WITH latest_success AS (
    SELECT DISTINCT ON (taxi_type, source_year, source_month)
           taxi_type,
           extracted_rows,
           loaded_rows,
           rejected_rows
    FROM pipeline.batch_runs
    WHERE status = 'success'
    ORDER BY taxi_type, source_year, source_month, run_id DESC
)
SELECT taxi_type,
       COUNT(*) AS completed_batches,
       SUM(extracted_rows) AS extracted_rows,
       SUM(loaded_rows) AS accepted_rows,
       SUM(rejected_rows) AS rejected_rows,
       ROUND(
           100.0 * SUM(loaded_rows)
           / NULLIF(SUM(extracted_rows), 0),
           4
       ) AS acceptance_rate_pct
FROM latest_success
GROUP BY taxi_type
ORDER BY taxi_type;


-- 4. File-level lineage and reproducibility evidence.
-- SHA-256 identifies the exact Bronze artifact used by each successful run.
WITH latest_successful_file AS (
    SELECT DISTINCT ON (taxi_type, source_year, source_month)
           *
    FROM pipeline.file_ingestions
    WHERE status = 'success'
    ORDER BY taxi_type, source_year, source_month, run_id DESC
)
SELECT f.file_id,
       f.run_id,
       f.taxi_type,
       f.source_year,
       f.source_month,
       f.file_path,
       f.row_count,
       f.checksum_sha256,
       f.status,
       f.ingested_at
FROM latest_successful_file AS f
ORDER BY f.source_year DESC, f.source_month DESC, f.taxi_type;


-- 5. Failures remain auditable instead of disappearing.
SELECT run_id,
       taxi_type,
       source_year,
       source_month,
       started_at,
       finished_at,
       error_message
FROM pipeline.batch_runs
WHERE status = 'failed'
ORDER BY run_id DESC;
