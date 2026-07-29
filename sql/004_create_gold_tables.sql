#Creating gold tables for taxi data ingestion
CREATE TABLE IF NOT EXISTS gold.yellow_trips (
    trip_key              TEXT        PRIMARY KEY,
    vendor_id             INT,
    pickup_datetime       TIMESTAMP,
    dropoff_datetime      TIMESTAMP,
    passenger_count       INT,
    trip_distance         NUMERIC(10,3),
    ratecode_id           INT,
    store_and_fwd_flag    TEXT,
    pu_location_id        INT,
    do_location_id        INT,
    payment_type          INT,
    fare_amount           NUMERIC(10,2),
    extra                 NUMERIC(10,2),
    mta_tax               NUMERIC(10,2),
    tip_amount            NUMERIC(10,2),
    tolls_amount          NUMERIC(10,2),
    improvement_surcharge NUMERIC(10,2),
    total_amount          NUMERIC(10,2),
    congestion_surcharge  NUMERIC(10,2),
    airport_fee           NUMERIC(10,2),
    trip_type             INT,
    source_file           TEXT        NOT NULL,
    source_year           INT         NOT NULL,
    source_month          INT         NOT NULL,
    ingested_at           TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_gold_yellow_pickup
    ON gold.yellow_trips (pickup_datetime);
CREATE INDEX IF NOT EXISTS ix_gold_yellow_batch
    ON gold.yellow_trips (source_year, source_month);

CREATE TABLE IF NOT EXISTS gold.green_trips (
    LIKE gold.yellow_trips INCLUDING ALL
);

#reporting layer on top of gold: monthly revenue summary.
CREATE MATERIALIZED VIEW IF NOT EXISTS gold.monthly_summary AS
SELECT 'yellow' AS taxi_type, source_year, source_month,
       COUNT(*) AS trips,
       ROUND(AVG(trip_distance), 2) AS avg_distance,
       ROUND(SUM(total_amount), 2) AS total_revenue
FROM gold.yellow_trips
GROUP BY source_year, source_month
UNION ALL
SELECT 'green', source_year, source_month,
       COUNT(*), ROUND(AVG(trip_distance), 2),
       ROUND(SUM(total_amount), 2)
FROM gold.green_trips
GROUP BY source_year, source_month;
