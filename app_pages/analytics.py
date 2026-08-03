"""Month-filtered Gold trip analytics page."""
import streamlit as st

from dashboard.database import DatabaseUnavailable, show_database_error
from dashboard.queries import (
    load_hourly_trips,
    load_monthly_summary,
    load_top_routes,
)


st.caption("Detailed Gold analysis is restricted to one loaded month for responsive queries.")

try:
    monthly = load_monthly_summary()
except DatabaseUnavailable as error:
    show_database_error(error)
    st.stop()

if monthly.empty:
    st.info("No Gold data is available.")
    st.stop()

taxi_types = sorted(monthly["taxi_type"].unique().tolist())
with st.sidebar:
    st.subheader("Analysis filters")
    taxi_type = st.selectbox("Taxi type", taxi_types)
    available = monthly[monthly["taxi_type"] == taxi_type]
    periods = [
        (int(row.source_year), int(row.source_month))
        for row in available.itertuples()
    ]
    year, month = st.selectbox(
        "Loaded month",
        periods,
        format_func=lambda value: f"{value[0]}-{value[1]:02d}",
    )

selected = available[
    (available["source_year"] == year) & (available["source_month"] == month)
].iloc[0]

with st.container(horizontal=True):
    st.metric("Trips", f"{int(selected['trips']):,.0f}", border=True)
    st.metric(
        "Total revenue", f"${float(selected['total_revenue']):,.2f}", border=True
    )
    st.metric(
        "Average distance", f"{float(selected['avg_distance']):,.2f} miles", border=True
    )
    st.metric(
        "Revenue per trip",
        f"${float(selected['total_revenue']) / int(selected['trips']):,.2f}",
        border=True,
    )

hour_slot = st.container()
route_slot = st.container()

try:
    with hour_slot, st.skeleton(height=320):
        hourly = load_hourly_trips(taxi_type, year, month)
        st.subheader("Trips by pickup hour")
        st.bar_chart(hourly, x="pickup_hour", y="trips")
    with route_slot, st.skeleton(height=380):
        routes = load_top_routes(taxi_type, year, month)
        st.subheader("Top pickup-to-drop-off zone pairs")
        st.dataframe(
            routes,
            column_config={
                "pu_location_id": st.column_config.NumberColumn(
                    "Pickup zone", format="%d"
                ),
                "do_location_id": st.column_config.NumberColumn(
                    "Drop-off zone", format="%d"
                ),
                "trips": st.column_config.NumberColumn("Trips", format=",%d"),
                "avg_distance": st.column_config.NumberColumn(
                    "Average distance", format="%.2f"
                ),
                "avg_total_amount": st.column_config.NumberColumn(
                    "Average amount", format="$%.2f"
                ),
            },
            hide_index=True,
        )
except DatabaseUnavailable as error:
    show_database_error(error)
