"""Data quality page."""
import pandas as pd
import streamlit as st

from dashboard.database import DatabaseUnavailable, show_database_error
from dashboard.queries import (
    load_quality_by_month,
    load_rejection_reasons,
    load_rejection_samples,
)


st.caption("Acceptance, rejection and record-level quarantine evidence.")

try:
    quality = load_quality_by_month()
    reasons = load_rejection_reasons()
    samples = load_rejection_samples()
except DatabaseUnavailable as error:
    show_database_error(error)
    st.stop()

if quality.empty:
    st.info("No completed batches are available for quality analysis.")
    st.stop()

quality["period"] = pd.to_datetime(
    dict(year=quality["source_year"], month=quality["source_month"], day=1)
)
total_extracted = int(quality["extracted_rows"].sum())
total_loaded = int(quality["loaded_rows"].sum())
total_rejected = int(quality["rejected_rows"].sum())
acceptance = 100 * total_loaded / total_extracted if total_extracted else 0

with st.container(horizontal=True):
    st.metric("Extracted", f"{total_extracted:,.0f}", border=True)
    st.metric("Accepted", f"{total_loaded:,.0f}", border=True)
    st.metric("Rejected", f"{total_rejected:,.0f}", border=True)
    st.metric("Acceptance rate", f"{acceptance:.3f}%", border=True)

left, right = st.columns(2)
with left:
    with st.container(border=True):
        st.subheader("Rejected rows by month")
        st.bar_chart(
            quality,
            x="period",
            y="rejected_rows",
            color="taxi_type",
            stack=False,
        )
with right:
    with st.container(border=True):
        st.subheader("Rejection reasons")
        if reasons.empty:
            st.info("No rejected records in the latest successful batches.")
        else:
            grouped = (
                reasons.groupby("reject_reason", as_index=False)["rejected_records"]
                .sum()
                .sort_values("rejected_records", ascending=False)
            )
            st.bar_chart(grouped, x="reject_reason", y="rejected_records")

with st.container(border=True):
    st.subheader("Latest rejected-record samples")
    st.dataframe(
        samples,
        column_config={
            "reject_id": st.column_config.NumberColumn("Reject ID", format="%d"),
            "source_year": st.column_config.NumberColumn("Year", format="%d"),
            "source_month": st.column_config.NumberColumn("Month", format="%d"),
            "rejected_at": st.column_config.DatetimeColumn(
                "Rejected at", format="YYYY-MM-DD HH:mm:ss"
            ),
        },
        hide_index=True,
    )
