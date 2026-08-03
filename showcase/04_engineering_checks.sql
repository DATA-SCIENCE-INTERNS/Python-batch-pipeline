/*
NYC Taxi Pipeline Showcase 04: Engineering and integrity checks
All queries are read-only.
*/

-- 1. Gold primary-key integrity.
-- The database constraint prevents duplicate trip_key values without needing
-- an expensive full-table COUNT(DISTINCT ...) scan during a presentation.
SELECT n.nspname AS schema_name,
       c.relname AS table_name,
       con.conname AS constraint_name,
       PG_GET_CONSTRAINTDEF(con.oid) AS enforced_rule
FROM pg_constraint AS con
JOIN pg_class AS c
  ON c.oid = con.conrelid
JOIN pg_namespace AS n
  ON n.oid = c.relnamespace
WHERE n.nspname = 'gold'
  AND c.relname IN ('yellow_trips', 'green_trips')
  AND con.contype = 'p'
ORDER BY c.relname;


-- 2. Silver-to-Gold reconciliation by month.
-- A lower Gold count can be valid if source rows share the inferred trip key.
WITH silver_counts AS (
    SELECT taxi_type, source_year, source_month, COUNT(*) AS silver_rows
    FROM silver.trips
    GROUP BY taxi_type, source_year, source_month
),
gold_counts AS (
    SELECT 'yellow'::TEXT AS taxi_type,
           source_year,
           source_month,
           COUNT(*) AS gold_rows
    FROM gold.yellow_trips
    GROUP BY source_year, source_month
    UNION ALL
    SELECT 'green',
           source_year,
           source_month,
           COUNT(*)
    FROM gold.green_trips
    GROUP BY source_year, source_month
)
SELECT s.taxi_type,
       s.source_year,
       s.source_month,
       s.silver_rows,
       COALESCE(g.gold_rows, 0) AS gold_rows,
       s.silver_rows - COALESCE(g.gold_rows, 0) AS difference
FROM silver_counts AS s
LEFT JOIN gold_counts AS g
  USING (taxi_type, source_year, source_month)
ORDER BY s.source_year, s.source_month, s.taxi_type;


-- 3. Confirm lineage completeness in curated data.
SELECT 'yellow' AS taxi_type,
       COUNT(*) FILTER (WHERE source_file IS NULL) AS missing_source_file,
       COUNT(*) FILTER (WHERE source_year IS NULL) AS missing_source_year,
       COUNT(*) FILTER (WHERE source_month IS NULL) AS missing_source_month,
       COUNT(*) FILTER (WHERE ingested_at IS NULL) AS missing_ingested_at
FROM gold.yellow_trips
UNION ALL
SELECT 'green',
       COUNT(*) FILTER (WHERE source_file IS NULL),
       COUNT(*) FILTER (WHERE source_year IS NULL),
       COUNT(*) FILTER (WHERE source_month IS NULL),
       COUNT(*) FILTER (WHERE ingested_at IS NULL)
FROM gold.green_trips;


-- 4. Confirm that every successful file record has a valid SHA-256 shape.
-- SHA-256 is represented by exactly 64 hexadecimal characters.
SELECT COUNT(*) AS invalid_successful_checksums
FROM pipeline.file_ingestions
WHERE status = 'success'
  AND checksum_sha256 !~ '^[0-9a-f]{64}$';


-- 5. Check for stale running metadata.
-- Review any row returned; do not automatically mark it failed without
-- checking pg_stat_activity and container logs.
SELECT run_id,
       taxi_type,
       source_year,
       source_month,
       started_at,
       NOW() - started_at AS apparent_age
FROM pipeline.batch_runs
WHERE status = 'running'
ORDER BY started_at;


-- 6. Show the indexes supporting batch lookup and Gold idempotency.
SELECT schemaname,
       tablename,
       indexname,
       indexdef
FROM pg_indexes
WHERE schemaname IN ('pipeline', 'silver', 'gold')
ORDER BY schemaname, tablename, indexname;
