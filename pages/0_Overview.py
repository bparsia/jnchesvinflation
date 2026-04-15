"""Overview page: real-terms salary trends across all spine points."""
import streamlit as st
import plotly.express as px
import pandas as pd

from utils import get_data, BASE_YEAR

st.title("JNCHES Pay Spine vs Inflation")
st.caption(
    "HE national pay spine salary values, inflation-adjusted to "
    f"{BASE_YEAR} prices using ONS CPI data."
)

try:
    df = get_data()
except FileNotFoundError:
    st.warning(
        "No data found. Run `uv run python fetch.py` then `uv run python extract.py` "
        "to download and extract the PDF data."
    )
    st.stop()

# Sidebar controls
st.sidebar.header("Display options")

all_points = sorted(df["spine_point"].dropna().unique().astype(int))
default_points = [1, 10, 20, 30, 40, 51]
default_points = [p for p in default_points if p in all_points]

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

# Summary stats
st.subheader("Change since earliest record")
summary_rows = []
for sp in (selected if selected else all_points):
    sub = df[df["spine_point"] == sp].sort_values("date")
    if len(sub) < 2:
        continue
    first = sub.iloc[0]
    last = sub.iloc[-1]
    nominal_change = (last["salary"] - first["salary"]) / first["salary"] * 100
    real_change = (last["real_salary"] - first["real_salary"]) / first["real_salary"] * 100
    summary_rows.append({
        "Spine point": int(sp),
        "Earliest salary (£)": f"{first['salary']:,}",
        "Latest salary (£)": f"{last['salary']:,}",
        "Nominal change (%)": f"{nominal_change:+.1f}%",
        f"Real change (%, {BASE_YEAR} prices)": f"{real_change:+.1f}%",
        "Earliest date": first["date"].strftime("%b %Y"),
        "Latest date": last["date"].strftime("%b %Y"),
    })

if summary_rows:
    st.dataframe(
        pd.DataFrame(summary_rows).set_index("Spine point"),
        use_container_width=True,
    )
