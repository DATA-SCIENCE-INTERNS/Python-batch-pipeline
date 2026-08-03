"""Pipeline overview page."""
import pandas as pd
import streamlit as st

from dashboard.database import DatabaseUnavailable, show_database_error
from dashboard.queries import load_latest_batch_metrics, load_monthly_summary


st.caption("A current view of curated data, coverage, revenue and pipeline health.")

try:
    monthly = load_monthly_summary()
    metrics = load_latest_batch_metrics()
except DatabaseUnavailable as error:
    show_database_error(error)
    st.stop()

if monthly.empty:
    st.info("No successful Gold batches are available yet.")
    st.stop()

monthly["period"] = pd.to_datetime(
    dict(year=monthly["source_year"], month=monthly["source_month"], day=1)
)

total_trips = int(monthly["trips"].sum())
total_revenue = float(monthly["total_revenue"].sum())
completed_months = int(metrics["completed_months"].sum())
rejected_rows = int(metrics["rejected_rows"].sum())

with st.container(horizontal=True):
    st.metric("Gold trips", f"{total_trips:,.0f}", border=True)
    st.metric("Total revenue", f"${total_revenue:,.2f}", border=True)
    st.metric("Completed taxi-months", f"{completed_months:,}", border=True)
    st.metric("Rejected source rows", f"{rejected_rows:,}", border=True)

left, right = st.columns(2)
with left:
    with st.container(border=True):
        st.subheader("Monthly trips")
        st.line_chart(monthly, x="period", y="trips", color="taxi_type")
with right:
    with st.container(border=True):
        st.subheader("Monthly revenue")
        st.bar_chart(
            monthly,
            x="period",
            y="total_revenue",
            color="taxi_type",
            stack=False,
        )

with st.container(border=True):
    st.subheader("Loaded coverage")
    st.dataframe(
        monthly,
        column_order=[
            "taxi_type", "source_year", "source_month", "trips",
            "avg_distance", "total_revenue",
        ],
        column_config={
            "taxi_type": st.column_config.TextColumn("Taxi type"),
            "source_year": st.column_config.NumberColumn("Year", format="%d"),
            "source_month": st.column_config.NumberColumn("Month", format="%d"),
            "trips": st.column_config.NumberColumn("Trips", format=",%d"),
            "avg_distance": st.column_config.NumberColumn(
                "Average distance", format="%.2f"
            ),
            "total_revenue": st.column_config.NumberColumn(
                "Total revenue", format="$%,.2f"
            ),
        },
        hide_index=True,
    )
