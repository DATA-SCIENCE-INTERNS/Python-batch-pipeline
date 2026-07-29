#Creating silver tables for taxi data ingestion

CREATE TABLE IF NOT EXISTS silver.trips (
    trip_key              TEXT        NOT NULL,
    taxi_type             TEXT        NOT NULL CHECK (taxi_type IN ('yellow','green')),
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
    airport_fee           NUMERIC(10,2),   #yellow 
    trip_type             INT,             #green 
    source_file           TEXT        NOT NULL,
    source_year           INT         NOT NULL,
    source_month          INT         NOT NULL,
    ingested_at           TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_silver_trips_batch
    ON silver.trips (taxi_type, source_year, source_month);
