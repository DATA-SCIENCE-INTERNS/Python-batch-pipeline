-- Create pipeline tables for taxi data ingestion

CREATE TABLE IF NOT EXISTS pipeline.batch_runs (
    run_id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    taxi_type       TEXT        NOT NULL CHECK (taxi_type IN ('yellow','green')),
    source_year     INT         NOT NULL,
    source_month    INT         NOT NULL CHECK (source_month BETWEEN 1 AND 12),
    source          TEXT        NOT NULL,
    status          TEXT        NOT NULL DEFAULT 'running'
                    CHECK (status IN ('running','success','failed')),
    started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at     TIMESTAMPTZ,
    extracted_rows  BIGINT      NOT NULL DEFAULT 0,
    loaded_rows     BIGINT      NOT NULL DEFAULT 0,
    rejected_rows   BIGINT      NOT NULL DEFAULT 0,
    error_message   TEXT
);

CREATE INDEX IF NOT EXISTS ix_batch_runs_batch
    ON pipeline.batch_runs (taxi_type, source_year, source_month);

CREATE TABLE IF NOT EXISTS pipeline.file_ingestions (
    file_id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_id          BIGINT      NOT NULL REFERENCES pipeline.batch_runs(run_id),
    taxi_type       TEXT        NOT NULL,
    source_year     INT         NOT NULL,
    source_month    INT         NOT NULL,
    file_path       TEXT        NOT NULL,
    checksum_sha256 TEXT        NOT NULL,
    status          TEXT        NOT NULL,
    row_count       BIGINT,
    ingested_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    error_message   TEXT
);

CREATE TABLE IF NOT EXISTS pipeline.rejected_records (
    reject_id     BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_id        BIGINT      NOT NULL REFERENCES pipeline.batch_runs(run_id),
    trip_key      TEXT,
    reject_reason TEXT        NOT NULL,
    record        TEXT,
    rejected_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
