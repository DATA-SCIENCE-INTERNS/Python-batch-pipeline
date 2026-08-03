/*
NYC Taxi Pipeline Showcase 02: Data quality and rejected records
All queries are read-only.
*/

-- 1. Acceptance and rejection rate for every successful monthly batch.
WITH latest_success AS (
    SELECT DISTINCT ON (taxi_type, source_year, source_month)
           *
    FROM pipeline.batch_runs
    WHERE status = 'success'
    ORDER BY taxi_type, source_year, source_month, run_id DESC
)
SELECT run_id,
       taxi_type,
       source_year,
       source_month,
       extracted_rows,
       loaded_rows,
       rejected_rows,
       ROUND(
           100.0 * loaded_rows / NULLIF(extracted_rows, 0),
           4
       ) AS accepted_pct,
       ROUND(
           100.0 * rejected_rows / NULLIF(extracted_rows, 0),
           4
       ) AS rejected_pct
FROM latest_success
ORDER BY source_year, source_month, taxi_type;


-- 2. Most common validation failures.
WITH latest_success AS (
    SELECT DISTINCT ON (taxi_type, source_year, source_month)
           run_id
    FROM pipeline.batch_runs
    WHERE status = 'success'
    ORDER BY taxi_type, source_year, source_month, run_id DESC
)
SELECT reject_reason,
       COUNT(*) AS rejected_records,
       COUNT(DISTINCT run_id) AS affected_runs
FROM pipeline.rejected_records
WHERE run_id IN (SELECT run_id FROM latest_success)
GROUP BY reject_reason
ORDER BY rejected_records DESC, reject_reason;


-- 3. Rejections by taxi type and month.
WITH latest_success AS (
    SELECT DISTINCT ON (taxi_type, source_year, source_month)
           run_id
    FROM pipeline.batch_runs
    WHERE status = 'success'
    ORDER BY taxi_type, source_year, source_month, run_id DESC
)
SELECT b.taxi_type,
       b.source_year,
       b.source_month,
       COUNT(r.reject_id) AS stored_rejections
FROM pipeline.batch_runs AS b
JOIN pipeline.rejected_records AS r
  ON r.run_id = b.run_id
JOIN latest_success AS l
  ON l.run_id = b.run_id
GROUP BY b.taxi_type, b.source_year, b.source_month
ORDER BY b.source_year, b.source_month, b.taxi_type;


-- 4. Inspect a small sample without printing the full JSON record.
WITH latest_success AS (
    SELECT DISTINCT ON (taxi_type, source_year, source_month)
           run_id
    FROM pipeline.batch_runs
    WHERE status = 'success'
    ORDER BY taxi_type, source_year, source_month, run_id DESC
)
SELECT r.reject_id,
       r.run_id,
       b.taxi_type,
       b.source_year,
       b.source_month,
       r.trip_key,
       r.reject_reason,
       LEFT(r.record, 250) AS record_preview,
       r.rejected_at
FROM pipeline.rejected_records AS r
JOIN pipeline.batch_runs AS b
  ON b.run_id = r.run_id
JOIN latest_success AS l
  ON l.run_id = b.run_id
ORDER BY r.reject_id DESC
LIMIT 20;


-- 5. Reconcile extraction: every source row must be accepted or rejected.
-- Expected reconciliation_difference: zero for every successful run.
WITH latest_success AS (
    SELECT DISTINCT ON (taxi_type, source_year, source_month)
           *
    FROM pipeline.batch_runs
    WHERE status = 'success'
    ORDER BY taxi_type, source_year, source_month, run_id DESC
)
SELECT run_id,
       taxi_type,
       source_year,
       source_month,
       extracted_rows,
       loaded_rows + rejected_rows AS accounted_for_rows,
       extracted_rows - loaded_rows - rejected_rows
           AS reconciliation_difference
FROM latest_success
ORDER BY ABS(extracted_rows - loaded_rows - rejected_rows) DESC,
         run_id DESC;
