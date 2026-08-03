"""Read-only PostgreSQL access for the dashboard."""
from __future__ import annotations

import os
from collections.abc import Sequence

import pandas as pd
import psycopg2
import streamlit as st


class DatabaseUnavailable(RuntimeError):
    """Raised when the dashboard cannot query PostgreSQL."""


def _dsn() -> str:
    required = [
        "POSTGRES_HOST",
        "POSTGRES_PORT",
        "POSTGRES_DB",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
    ]
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        raise DatabaseUnavailable(
            "Missing database configuration: " + ", ".join(missing)
        )
    return (
        f"host={os.environ['POSTGRES_HOST']} "
        f"port={os.environ['POSTGRES_PORT']} "
        f"dbname={os.environ['POSTGRES_DB']} "
        f"user={os.environ['POSTGRES_USER']} "
        f"password={os.environ['POSTGRES_PASSWORD']} "
        "connect_timeout=5 application_name=nyc_taxi_streamlit"
    )


def query_dataframe(sql: str, params: Sequence | None = None) -> pd.DataFrame:
    """Execute a parameterized read query and return a DataFrame."""
    try:
        with psycopg2.connect(_dsn()) as connection:
            connection.set_session(readonly=True, autocommit=False)
            with connection.cursor() as cursor:
                cursor.execute(sql, params)
                rows = cursor.fetchall()
                columns = [item.name for item in cursor.description]
        return pd.DataFrame(rows, columns=columns)
    except (psycopg2.Error, OSError) as error:
        raise DatabaseUnavailable(str(error)) from error


def show_database_error(error: Exception) -> None:
    """Render a useful connection error without exposing credentials."""
    st.error(
        "The dashboard cannot reach PostgreSQL. Start Docker Desktop and the "
        "postgres service, then refresh this page.",
        icon=":material/database_off:",
    )
    with st.expander("Connection details"):
        st.code(
            f"Host: {os.getenv('POSTGRES_HOST', '<missing>')}\n"
            f"Port: {os.getenv('POSTGRES_PORT', '<missing>')}\n"
            f"Database: {os.getenv('POSTGRES_DB', '<missing>')}\n"
            f"Error: {error}"
        )
