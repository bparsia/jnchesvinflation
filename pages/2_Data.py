"""Raw data table with filters."""
import streamlit as st
import pandas as pd

from utils import get_data, BASE_YEAR

st.title("Raw Data")

with st.sidebar:
    st.header("Filters")
    measure = st.radio("Inflation measure", ["CPI", "RPI"], horizontal=True)
    st.divider()

try:
    df = get_data(measure=measure)
except FileNotFoundError:
    st.warning("No data found. Run the fetch and extract scripts first.")
    st.stop()

all_points = sorted(df["spine_point"].dropna().unique().astype(int))
all_years = sorted(df["year"].unique())

with st.sidebar:
    selected_points = st.multiselect("Spine points", all_points, default=all_points)
    selected_years = st.multiselect("Settlement year", all_years, default=all_years)

filtered = df[
    df["spine_point"].isin(selected_points) & df["year"].isin(selected_years)
].sort_values(["date", "spine_point"])

display = filtered[[
    "year", "effective_date", "spine_point", "salary", "real_salary"
]].copy()
display.columns = [
    "Settlement year", "Effective date", "Spine point",
    "Nominal salary (£)", f"Real salary (£, {BASE_YEAR} {measure} prices)"
]

st.dataframe(display, use_container_width=True, hide_index=True)
st.caption(f"{len(display):,} rows")

csv = display.to_csv(index=False)
st.download_button("Download CSV", csv, "jnches_spine_points.csv", "text/csv")
