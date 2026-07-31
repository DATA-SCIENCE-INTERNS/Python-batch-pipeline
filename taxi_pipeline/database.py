from contextlib import contextmanager
import logging
import time
from typing import Iterable

import psycopg2
from psycopg2.extras import execute_values

from .config import Settings

log = logging.getLogger(__name__)

SILVER_COLUMNS = [
    "trip_key", "taxi_type", "vendor_id", "pickup_datetime",
    "dropoff_datetime", "passenger_count", "trip_distance", "ratecode_id",
    "store_and_fwd_flag", "pu_location_id", "do_location_id",
    "payment_type", "fare_amount", "extra", "mta_tax", "tip_amount",
    "tolls_amount", "improvement_surcharge", "total_amount",
    "congestion_surcharge", "airport_fee", "trip_type", "source_file",
    "source_year", "source_month", "ingested_at",
]


def get_connection(settings: Settings, attempts: int = 24,
                   delay_seconds: int = 5):
    """Connect to PostgreSQL, waiting through a temporary restart."""
    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            conn = psycopg2.connect(
                settings.dsn,
                connect_timeout=5,
                application_name="nyc_taxi_batch_pipeline",
            )
            conn.autocommit = False
            return conn
        except psycopg2.OperationalError as error:
            last_error = error
            if attempt == attempts:
                break
            log.warning(
                "PostgreSQL unavailable; retrying connection in %ss "
                "(attempt %s/%s)",
                delay_seconds, attempt, attempts,
            )
            time.sleep(delay_seconds)
    raise last_error


@contextmanager
def transaction(conn):
    """Run a block atomically: commit on success, rollback on any error."""
    try:
        with conn.cursor() as cur:
            yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def create_batch_run(conn, taxi_type: str, year: int, month: int,
                     source: str) -> int:
    with transaction(conn) as cur:
        cur.execute(
            """
            INSERT INTO pipeline.batch_runs
                (taxi_type, source_year, source_month, source)
            VALUES (%s, %s, %s, %s)
            RETURNING run_id
            """,
            (taxi_type, year, month, source),
        )
        return cur.fetchone()[0]


def create_file_ingestion(conn, run_id: int, taxi_type: str, year: int,
                          month: int, path: str, checksum: str) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO pipeline.file_ingestions
                (run_id, taxi_type, source_year, source_month, file_path,
                 checksum_sha256, status)
            VALUES (%s, %s, %s, %s, %s, %s, 'running')
            RETURNING file_id
            """,
            (run_id, taxi_type, year, month, path, checksum),
        )
        return cur.fetchone()[0]


def replace_silver_batch(cur, taxi_type: str, year: int, month: int) -> None:
    cur.execute(
        """
        DELETE FROM silver.trips
        WHERE taxi_type = %s AND source_year = %s AND source_month = %s
        """,
        (taxi_type, year, month),
    )


def _db_value(value):
    # Avoid importing numpy types into psycopg2's adaptation layer.
    if value is None:
        return None
    try:
        import pandas as pd
        if pd.isna(value):
            return None
        if isinstance(value, pd.Timestamp):
            return value.to_pydatetime()
    except (TypeError, ValueError):
        pass
    return value.item() if hasattr(value, "item") else value


def insert_silver_rows(cur, rows: Iterable) -> int:
    prepared = [
        tuple(_db_value(row[column]) for column in SILVER_COLUMNS)
        for _, row in rows.iterrows()
    ]
    if not prepared:
        return 0
    execute_values(
        cur,
        f"INSERT INTO silver.trips ({', '.join(SILVER_COLUMNS)}) VALUES %s",
        prepared,
        page_size=2_000,
    )
    return len(prepared)


def insert_rejected_rows(cur, run_id: int, rows: Iterable) -> int:
    prepared = [
        (run_id, row["trip_key"], row["reject_reason"], row["record"])
        for _, row in rows.iterrows()
    ]
    if not prepared:
        return 0
    execute_values(
        cur,
        """
        INSERT INTO pipeline.rejected_records
            (run_id, trip_key, reject_reason, record)
        VALUES %s
        """,
        prepared,
        page_size=2_000,
    )
    return len(prepared)


def promote_to_gold(cur, taxi_type: str, year: int, month: int) -> int:
    table = "yellow_trips" if taxi_type == "yellow" else "green_trips"
    gold_columns = [column for column in SILVER_COLUMNS if column != "taxi_type"]
    columns = ", ".join(gold_columns)
    cur.execute(
        f"""
        INSERT INTO gold.{table} ({columns})
        SELECT {columns}
        FROM silver.trips
        WHERE taxi_type = %s AND source_year = %s AND source_month = %s
        ON CONFLICT (trip_key) DO NOTHING
        """,
        (taxi_type, year, month),
    )
    return cur.rowcount


def finish_batch(cur, run_id: int, file_id: int, status: str,
                 extracted: int, loaded: int, rejected: int,
                 error: str | None = None) -> None:
    cur.execute(
        """
        UPDATE pipeline.file_ingestions
        SET status = %s, row_count = %s, error_message = %s
        WHERE file_id = %s
        """,
        (status, extracted, error, file_id),
    )
    cur.execute(
        """
        UPDATE pipeline.batch_runs
        SET status = %s, finished_at = now(), extracted_rows = %s,
            loaded_rows = %s, rejected_rows = %s, error_message = %s
        WHERE run_id = %s
        """,
        (status, extracted, loaded, rejected, error, run_id),
    )
