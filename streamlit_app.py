"""NYC Taxi Pipeline dashboard entry point."""
import streamlit as st


st.set_page_config(
    page_title="NYC Taxi Pipeline",
    page_icon=":material/local_taxi:",
    layout="wide",
)

pages = [
    st.Page(
        "app_pages/overview.py",
        title="Overview",
        icon=":material/monitoring:",
        default=True,
    ),
    st.Page(
        "app_pages/pipeline_runs.py",
        title="Pipeline runs",
        icon=":material/account_tree:",
    ),
    st.Page(
        "app_pages/data_quality.py",
        title="Data quality",
        icon=":material/fact_check:",
    ),
    st.Page(
        "app_pages/analytics.py",
        title="Trip analytics",
        icon=":material/query_stats:",
    ),
    st.Page(
        "app_pages/lineage.py",
        title="Lineage",
        icon=":material/lan:",
    ),
]

page = st.navigation(pages, position="top")

with st.container(
    horizontal=True,
    horizontal_alignment="distribute",
    vertical_alignment="center",
):
    st.title(f"{page.icon} {page.title}")
    if st.button(":material/refresh: Refresh data", type="tertiary"):
        st.cache_data.clear()
        st.rerun()

page.run()
