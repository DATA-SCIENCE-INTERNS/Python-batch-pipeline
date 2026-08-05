"""Cached, read-only dashboard query functions."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard.database import query_dataframe


@st.cache_data(ttl="15s", max_entries=5, show_spinner=False)
def load_dashboard_status() -> pd.DataFrame:
    return query_dataframe(
        """
        WITH latest AS (
            SELECT run_id, taxi_type, source_year, source_month, status,
                   started_at, finished_at
            FROM pipeline.batch_runs
            ORDER BY run_id DESC
            LIMIT 1
        )
        SELECT latest.*,
               (SELECT COUNT(*) FROM pipeline.batch_runs
                WHERE status = 'running')::INT AS running_records,
               (SELECT COUNT(*) FROM pipeline.batch_runs
                WHERE status = 'running'
                  AND started_at < CLOCK_TIMESTAMP() - INTERVAL '6 hours')::INT
                   AS stale_running_records,
               (SELECT COUNT(*) FROM pg_stat_activity
                WHERE application_name = 'nyc_taxi_batch_pipeline')::INT
                   AS active_pipeline_sessions,
               (SELECT COUNT(*) FROM pipeline.batch_runs
                WHERE status = 'failed')::INT AS failed_runs,
               CLOCK_TIMESTAMP() AS checked_at
        FROM latest
        """
    )


@st.cache_data(ttl="2m", max_entries=10, show_spinner=False)
def load_monthly_summary() -> pd.DataFrame:
    return query_dataframe(
        """
        SELECT taxi_type, source_year, source_month, trips,
               avg_distance::FLOAT AS avg_distance,
               total_revenue::FLOAT AS total_revenue
        FROM gold.monthly_summary
        ORDER BY source_year, source_month, taxi_type
        """
    )


@st.cache_data(ttl="1m", max_entries=10, show_spinner=False)
def load_latest_batch_metrics() -> pd.DataFrame:
    return query_dataframe(
        """
        WITH latest_success AS (
            SELECT DISTINCT ON (taxi_type, source_year, source_month)
                   taxi_type, source_year, source_month,
                   extracted_rows, loaded_rows, rejected_rows
            FROM pipeline.batch_runs
            WHERE status = 'success'
            ORDER BY taxi_type, source_year, source_month, run_id DESC
        )
        SELECT taxi_type,
               COUNT(*)::BIGINT AS completed_months,
               SUM(extracted_rows)::BIGINT AS extracted_rows,
               SUM(loaded_rows)::BIGINT AS loaded_rows,
               SUM(rejected_rows)::BIGINT AS rejected_rows
        FROM latest_success
        GROUP BY taxi_type
        ORDER BY taxi_type
        """
    )


@st.cache_data(ttl="30s", max_entries=10, show_spinner=False)
def load_recent_runs(limit: int = 250) -> pd.DataFrame:
    return query_dataframe(
        """
        SELECT run_id, taxi_type, source_year, source_month, status,
               started_at, finished_at, extracted_rows, loaded_rows,
               rejected_rows, error_message
        FROM pipeline.batch_runs
        ORDER BY run_id DESC
        LIMIT %s
        """,
        (limit,),
    )


@st.cache_data(ttl="2m", max_entries=10, show_spinner=False)
def load_quality_by_month() -> pd.DataFrame:
    return query_dataframe(
        """
        WITH latest_success AS (
            SELECT DISTINCT ON (taxi_type, source_year, source_month)
                   run_id, taxi_type, source_year, source_month,
                   extracted_rows, loaded_rows, rejected_rows
            FROM pipeline.batch_runs
            WHERE status = 'success'
            ORDER BY taxi_type, source_year, source_month, run_id DESC
        )
        SELECT *,
               100.0 * loaded_rows / NULLIF(extracted_rows, 0)
                   AS accepted_pct,
               100.0 * rejected_rows / NULLIF(extracted_rows, 0)
                   AS rejected_pct
        FROM latest_success
        ORDER BY source_year, source_month, taxi_type
        """
    )


@st.cache_data(ttl="2m", max_entries=10, show_spinner=False)
def load_rejection_reasons() -> pd.DataFrame:
    return query_dataframe(
        """
        WITH latest_success AS (
            SELECT DISTINCT ON (taxi_type, source_year, source_month)
                   run_id, taxi_type, source_year, source_month
            FROM pipeline.batch_runs
            WHERE status = 'success'
            ORDER BY taxi_type, source_year, source_month, run_id DESC
        )
        SELECT l.taxi_type, l.source_year, l.source_month,
               r.reject_reason, COUNT(*)::BIGINT AS rejected_records
        FROM latest_success AS l
        JOIN pipeline.rejected_records AS r ON r.run_id = l.run_id
        GROUP BY l.taxi_type, l.source_year, l.source_month, r.reject_reason
        ORDER BY l.source_year, l.source_month, l.taxi_type, rejected_records DESC
        """
    )


@st.cache_data(ttl="2m", max_entries=10, show_spinner=False)
def load_rejection_samples(limit: int = 100) -> pd.DataFrame:
    return query_dataframe(
        """
        WITH latest_success AS (
            SELECT DISTINCT ON (taxi_type, source_year, source_month)
                   run_id, taxi_type, source_year, source_month
            FROM pipeline.batch_runs
            WHERE status = 'success'
            ORDER BY taxi_type, source_year, source_month, run_id DESC
        )
        SELECT r.reject_id, l.taxi_type, l.source_year, l.source_month,
               r.reject_reason, r.trip_key, LEFT(r.record, 300) AS record_preview,
               r.rejected_at
        FROM latest_success AS l
        JOIN pipeline.rejected_records AS r ON r.run_id = l.run_id
        ORDER BY r.reject_id DESC
        LIMIT %s
        """,
        (limit,),
    )


@st.cache_data(ttl="5m", max_entries=20, show_spinner=False)
def load_hourly_trips(taxi_type: str, year: int, month: int) -> pd.DataFrame:
    table = "yellow_trips" if taxi_type == "yellow" else "green_trips"
    return query_dataframe(
        f"""
        SELECT EXTRACT(HOUR FROM pickup_datetime)::INT AS pickup_hour,
               COUNT(*)::BIGINT AS trips,
               AVG(total_amount)::FLOAT AS avg_total_amount,
               AVG(trip_distance)::FLOAT AS avg_distance
        FROM gold.{table}
        WHERE source_year = %s AND source_month = %s
        GROUP BY pickup_hour
        ORDER BY pickup_hour
        """,
        (year, month),
    )


@st.cache_data(ttl="5m", max_entries=20, show_spinner=False)
def load_top_routes(taxi_type: str, year: int, month: int) -> pd.DataFrame:
    table = "yellow_trips" if taxi_type == "yellow" else "green_trips"
    return query_dataframe(
        f"""
        SELECT pu_location_id, do_location_id, COUNT(*)::BIGINT AS trips,
               AVG(trip_distance)::FLOAT AS avg_distance,
               AVG(total_amount)::FLOAT AS avg_total_amount
        FROM gold.{table}
        WHERE source_year = %s AND source_month = %s
        GROUP BY pu_location_id, do_location_id
        ORDER BY trips DESC
        LIMIT 20
        """,
        (year, month),
    )


@st.cache_data(ttl="2m", max_entries=10, show_spinner=False)
def load_file_lineage() -> pd.DataFrame:
    return query_dataframe(
        """
        SELECT f.file_id, f.run_id, f.taxi_type, f.source_year,
               f.source_month, f.file_path, f.checksum_sha256,
               f.status, f.row_count, f.ingested_at
        FROM pipeline.file_ingestions AS f
        ORDER BY f.file_id DESC
        LIMIT 500
        """
    )
