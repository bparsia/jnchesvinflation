"""Overview page: real-terms salary trends across all spine points."""
import streamlit as st
import plotly.express as px
import pandas as pd

from utils import get_data, BASE_YEAR

st.title("JNCHES Pay Spine vs Inflation")

# Sidebar controls
st.sidebar.header("Display options")
measure = st.sidebar.radio("Inflation measure", ["CPI", "RPI"], horizontal=True)

st.caption(
    f"HE national pay spine salary values, inflation-adjusted to "
    f"{BASE_YEAR} prices using ONS {measure}."
)

try:
    df = get_data(measure=measure)
except FileNotFoundError:
    st.warning(
        "No data found. Run `uv run python fetch.py` then `uv run python extract.py` "
        "to download and extract the PDF data."
    )
    st.stop()

all_points = sorted(df["spine_point"].dropna().unique().astype(int))
default_points = [1, 10, 20, 30, 40, 51]
default_points = [p for p in default_points if p in all_points]

st.sidebar.divider()
selected = st.sidebar.multiselect(
    "Spine points to highlight",
    options=all_points,
    default=default_points,
)

show_nominal = st.sidebar.checkbox("Show nominal (not inflation-adjusted) salaries", value=False)

salary_col = "salary" if show_nominal else "real_salary"
salary_label = "Nominal salary (£)" if show_nominal else f"Real salary (£, {BASE_YEAR} prices)"

# Filter to selected points
if selected:
    plot_df = df[df["spine_point"].isin(selected)].copy()
else:
    plot_df = df.copy()

plot_df = plot_df.sort_values("date")
plot_df["spine_point_str"] = "SP " + plot_df["spine_point"].astype(int).astype(str)

# Main chart
fig = px.line(
    plot_df,
    x="date",
    y=salary_col,
    color="spine_point_str",
    labels={"date": "Effective date", salary_col: salary_label, "spine_point_str": "Spine point"},
    title="HE Pay Spine: real-terms salary over time",
    markers=True,
)
fig.update_layout(
    xaxis_title="Effective date",
    yaxis_title=salary_label,
    legend_title="Spine point",
    hovermode="x unified",
)
st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
# Summary stats with configurable baseline
# ---------------------------------------------------------------------------
st.subheader("Change from baseline")

# Build available dates sorted chronologically
all_dates_sorted = (
    df[["effective_date", "date"]]
    .drop_duplicates()
    .sort_values("date")
)
date_labels = {
    row["effective_date"]: row["date"].strftime("%b %Y")
    for _, row in all_dates_sorted.iterrows()
}

latest_date = all_dates_sorted["date"].max()

# Presets: find the closest available effective_date to each target
def closest_date(target_str: str) -> str:
    target = pd.Timestamp(target_str)
    idx = (all_dates_sorted["date"] - target).abs().idxmin()
    return all_dates_sorted.loc[idx, "effective_date"]

PRESETS = {
    "Since 2009": closest_date("2009-08-01"),
    "Since 2015": closest_date("2015-08-01"),
    "Pre-COVID (2019)": closest_date("2019-08-01"),
    "Since COVID (2020)": closest_date("2020-08-01"),
    "~5 years ago": closest_date(str(latest_date - pd.DateOffset(years=5))),
    "~10 years ago": closest_date(str(latest_date - pd.DateOffset(years=10))),
    "Custom…": None,
}

preset_choice = st.radio(
    "Baseline",
    list(PRESETS.keys()),
    index=0,
    horizontal=True,
)

if preset_choice == "Custom…":
    baseline_date = st.selectbox(
        "Choose baseline date",
        options=list(date_labels.keys())[:-1],   # exclude the latest
        format_func=lambda d: date_labels[d],
    )
else:
    baseline_date = PRESETS[preset_choice]

baseline_label = date_labels[baseline_date]
latest_label = date_labels[all_dates_sorted["effective_date"].iloc[-1]]

summary_rows = []
for sp in (selected if selected else all_points):
    base_rows = df[(df["spine_point"] == sp) & (df["effective_date"] == baseline_date)]
    last_rows = df[(df["spine_point"] == sp) & (df["date"] == latest_date)]
    if base_rows.empty or last_rows.empty:
        continue
    first = base_rows.iloc[0]
    last = last_rows.iloc[0]
    nominal_change = (last["salary"] - first["salary"]) / first["salary"] * 100
    real_change = (last["real_salary"] - first["real_salary"]) / first["real_salary"] * 100
    summary_rows.append({
        "Spine point": int(sp),
        f"Salary {baseline_label} (£)": f"{int(first['salary']):,}",
        f"Salary {latest_label} (£)": f"{int(last['salary']):,}",
        "Nominal change": f"{nominal_change:+.1f}%",
        f"Real change ({measure})": f"{real_change:+.1f}%",
    })

if summary_rows:
    st.dataframe(
        pd.DataFrame(summary_rows).set_index("Spine point"),
        use_container_width=True,
    )
else:
    st.info("No data available for the selected spine points at this baseline date.")
