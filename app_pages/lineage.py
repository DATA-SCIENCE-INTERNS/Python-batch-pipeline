"""File lineage and reproducibility page."""
import streamlit as st

from dashboard.database import DatabaseUnavailable, show_database_error
from dashboard.queries import load_file_lineage


st.caption("Bronze source paths, checksums and their associated batch attempts.")

try:
    lineage = load_file_lineage()
except DatabaseUnavailable as error:
    show_database_error(error)
    st.stop()

if lineage.empty:
    st.info("No file-ingestion metadata has been recorded.")
    st.stop()

status_options = sorted(lineage["status"].dropna().unique().tolist())
taxi_options = sorted(lineage["taxi_type"].dropna().unique().tolist())
with st.sidebar:
    st.subheader("Filters")
    selected_statuses = st.multiselect(
        "Status", status_options, default=status_options
    )
    selected_taxis = st.multiselect(
        "Taxi type", taxi_options, default=taxi_options
    )

filtered = lineage[
    lineage["status"].isin(selected_statuses)
    & lineage["taxi_type"].isin(selected_taxis)
]

with st.container(horizontal=True):
    st.metric("File records", f"{len(filtered):,}", border=True)
    st.metric(
        "Successful files",
        f"{int((filtered['status'] == 'success').sum()):,}",
        border=True,
    )
    st.metric(
        "Unique checksums", f"{filtered['checksum_sha256'].nunique():,}", border=True
    )

with st.container(border=True):
    st.subheader("File ingestion history")
    st.dataframe(
        filtered,
        column_config={
            "file_id": st.column_config.NumberColumn("File ID", format="%d"),
            "run_id": st.column_config.NumberColumn("Run ID", format="%d"),
            "source_year": st.column_config.NumberColumn("Year", format="%d"),
            "source_month": st.column_config.NumberColumn("Month", format="%d"),
            "row_count": st.column_config.NumberColumn("Source rows", format=",%d"),
            "ingested_at": st.column_config.DatetimeColumn(
                "Ingested at", format="YYYY-MM-DD HH:mm:ss"
            ),
        },
        hide_index=True,
    )
