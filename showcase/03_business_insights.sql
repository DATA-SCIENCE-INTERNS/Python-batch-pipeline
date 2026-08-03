/*
NYC Taxi Pipeline Showcase 03: Business and operational insights
All queries are read-only.
*/

-- 1. Executive monthly summary produced by the Gold reporting layer.
SELECT taxi_type,
       source_year,
       source_month,
       trips,
       avg_distance,
       total_revenue,
       ROUND(total_revenue / NULLIF(trips, 0), 2)
           AS revenue_per_trip
FROM gold.monthly_summary
ORDER BY source_year, source_month, taxi_type;


-- 2. Compare Yellow and Green monthly demand and revenue.
WITH monthly AS (
    SELECT taxi_type,
           source_year,
           source_month,
           trips,
           total_revenue
    FROM gold.monthly_summary
)
SELECT source_year,
       source_month,
       MAX(trips) FILTER (WHERE taxi_type = 'yellow') AS yellow_trips,
       MAX(trips) FILTER (WHERE taxi_type = 'green') AS green_trips,
       MAX(total_revenue) FILTER (WHERE taxi_type = 'yellow')
           AS yellow_revenue,
       MAX(total_revenue) FILTER (WHERE taxi_type = 'green')
           AS green_revenue
FROM monthly
GROUP BY source_year, source_month
ORDER BY source_year, source_month;


-- 3. Busiest pickup hours for one completed Yellow month.
SELECT EXTRACT(HOUR FROM pickup_datetime)::INT AS pickup_hour,
       COUNT(*) AS trips,
       ROUND(AVG(total_amount), 2) AS avg_total_amount,
       ROUND(AVG(trip_distance), 2) AS avg_distance
FROM gold.yellow_trips
WHERE source_year = 2025
  AND source_month = 3
GROUP BY pickup_hour
ORDER BY trips DESC;


-- 4. Most common pickup-to-drop-off zone pairs for Green trips.
-- TLC zone IDs can later be joined to the official Taxi Zone lookup table.
SELECT pu_location_id,
       do_location_id,
       COUNT(*) AS trips,
       ROUND(AVG(trip_distance), 2) AS avg_distance,
       ROUND(AVG(total_amount), 2) AS avg_total_amount
FROM gold.green_trips
WHERE source_year = 2025
GROUP BY pu_location_id, do_location_id
ORDER BY trips DESC
LIMIT 15;


-- 5. Yellow payment mix and tipping for one month.
-- NYC TLC payment_type 1 represents credit card in the source dictionary.
SELECT payment_type,
       COUNT(*) AS trips,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2)
           AS trip_share_pct,
       ROUND(AVG(total_amount), 2) AS avg_total_amount,
       ROUND(AVG(tip_amount), 2) AS avg_tip_amount
FROM gold.yellow_trips
WHERE source_year = 2025
  AND source_month = 3
GROUP BY payment_type
ORDER BY trips DESC;


-- 6. Trip-distance bands for Green data.
SELECT CASE
           WHEN trip_distance = 0 THEN '0 miles'
           WHEN trip_distance <= 2 THEN '0-2 miles'
           WHEN trip_distance <= 5 THEN '2-5 miles'
           WHEN trip_distance <= 10 THEN '5-10 miles'
           ELSE '10+ miles'
       END AS distance_band,
       COUNT(*) AS trips,
       ROUND(AVG(total_amount), 2) AS avg_total_amount
FROM gold.green_trips
WHERE source_year = 2025
GROUP BY distance_band
ORDER BY MIN(trip_distance);


-- 7. Daily trend for a selected month.
SELECT pickup_datetime::DATE AS pickup_date,
       COUNT(*) AS trips,
       ROUND(SUM(total_amount), 2) AS total_revenue,
       ROUND(AVG(trip_distance), 2) AS avg_distance
FROM gold.green_trips
WHERE source_year = 2025
  AND source_month = 12
  AND pickup_datetime >= DATE '2025-12-01'
  AND pickup_datetime < DATE '2026-01-01'
GROUP BY pickup_date
ORDER BY pickup_date;
