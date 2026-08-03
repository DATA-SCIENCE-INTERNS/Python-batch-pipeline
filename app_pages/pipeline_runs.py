"""Pipeline execution history page."""
import streamlit as st

from dashboard.database import DatabaseUnavailable, show_database_error
from dashboard.queries import load_recent_runs


st.caption("Audit history for ingestion attempts, failures and row counts.")

try:
    runs = load_recent_runs()
except DatabaseUnavailable as error:
    show_database_error(error)
    st.stop()

if runs.empty:
    st.info("No pipeline runs have been recorded.")
    st.stop()

status_options = sorted(runs["status"].dropna().unique().tolist())
taxi_options = sorted(runs["taxi_type"].dropna().unique().tolist())

with st.sidebar:
    st.subheader("Filters")
    selected_statuses = st.multiselect(
        "Status", status_options, default=status_options
    )
    selected_taxis = st.multiselect(
        "Taxi type", taxi_options, default=taxi_options
    )

filtered = runs[
    runs["status"].isin(selected_statuses)
    & runs["taxi_type"].isin(selected_taxis)
].copy()

with st.container(horizontal=True):
    st.metric("Shown attempts", f"{len(filtered):,}", border=True)
    st.metric(
        "Successful", f"{int((filtered['status'] == 'success').sum()):,}", border=True
    )
    st.metric(
        "Failed", f"{int((filtered['status'] == 'failed').sum()):,}", border=True
    )
    st.metric(
        "Running", f"{int((filtered['status'] == 'running').sum()):,}", border=True
    )

with st.container(border=True):
    st.subheader("Run attempts")
    st.dataframe(
        filtered,
        column_config={
            "run_id": st.column_config.NumberColumn("Run ID", format="%d", pinned=True),
            "source_year": st.column_config.NumberColumn("Year", format="%d"),
            "source_month": st.column_config.NumberColumn("Month", format="%d"),
            "started_at": st.column_config.DatetimeColumn(
                "Started", format="YYYY-MM-DD HH:mm:ss"
            ),
            "finished_at": st.column_config.DatetimeColumn(
                "Finished", format="YYYY-MM-DD HH:mm:ss"
            ),
            "extracted_rows": st.column_config.NumberColumn(
                "Extracted", format=",%d"
            ),
            "loaded_rows": st.column_config.NumberColumn("Loaded", format=",%d"),
            "rejected_rows": st.column_config.NumberColumn(
                "Rejected", format=",%d"
            ),
        },
        hide_index=True,
    )
