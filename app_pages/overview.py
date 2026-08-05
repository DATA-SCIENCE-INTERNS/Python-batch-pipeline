"""Pipeline overview page."""
import pandas as pd
import streamlit as st

from dashboard.database import DatabaseUnavailable, show_database_error
from dashboard.queries import (
    load_dashboard_status,
    load_latest_batch_metrics,
    load_monthly_summary,
)


st.caption("A current view of curated data, coverage, revenue and pipeline health.")


@st.fragment(run_every="30s")
def operational_status():
    try:
        status = load_dashboard_status()
    except DatabaseUnavailable as error:
        show_database_error(error)
        return
    if status.empty:
        st.badge("No pipeline runs recorded", icon=":material/info:", color="gray")
        return
    row = status.iloc[0]
    with st.container(
        horizontal=True,
        horizontal_alignment="distribute",
        vertical_alignment="center",
        border=True,
    ):
        if int(row["active_pipeline_sessions"]) > 0:
            st.badge(
                f"{int(row['active_pipeline_sessions'])} active pipeline session(s)",
                icon=":material/pending:",
                color="orange",
            )
        elif int(row["stale_running_records"]) > 0:
            st.badge(
                f"{int(row['stale_running_records'])} stale running record(s)",
                icon=":material/warning:",
                color="orange",
                help="No active pipeline database session was found.",
            )
        else:
            st.badge(
                "Pipeline idle",
                icon=":material/check_circle:",
                color="green",
            )
        st.caption(
            f"Latest attempt: run {int(row['run_id'])} · "
            f"{row['taxi_type']} {int(row['source_year'])}-"
            f"{int(row['source_month']):02d} · {row['status']}"
        )
        checked = pd.to_datetime(row["checked_at"])
        st.caption(f"Status checked {checked:%Y-%m-%d %H:%M:%S %Z}")


operational_status()

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

taxi_options = sorted(monthly["taxi_type"].unique().tolist())
with st.sidebar:
    st.subheader("Overview filters")
    selected_taxis = st.pills(
        "Taxi type",
        taxi_options,
        selection_mode="multi",
        default=taxi_options,
    )
    st.caption("Operational status refreshes every 30 seconds.")

if not selected_taxis:
    st.info("Select at least one taxi type to display the overview.")
    st.stop()

monthly = monthly[monthly["taxi_type"].isin(selected_taxis)].copy()
metrics = metrics[metrics["taxi_type"].isin(selected_taxis)].copy()

total_trips = int(monthly["trips"].sum())
total_revenue = float(monthly["total_revenue"].sum())
completed_months = int(metrics["completed_months"].sum())
rejected_rows = int(metrics["rejected_rows"].sum())

trip_trend = monthly.groupby("period")["trips"].sum().sort_index().tolist()
revenue_trend = (
    monthly.groupby("period")["total_revenue"].sum().sort_index().tolist()
)


def latest_delta(values):
    if len(values) < 2 or values[-2] == 0:
        return None
    return f"{100 * (values[-1] - values[-2]) / values[-2]:+.1f}% last period"

with st.container(horizontal=True):
    st.metric(
        "Gold trips",
        f"{total_trips:,.0f}",
        latest_delta(trip_trend),
        border=True,
        chart_data=trip_trend,
        chart_type="line",
    )
    st.metric(
        "Total revenue",
        f"${total_revenue:,.2f}",
        latest_delta(revenue_trend),
        border=True,
        chart_data=revenue_trend,
        chart_type="line",
    )
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
