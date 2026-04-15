"""Overview page: real-terms salary trends across all spine points."""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from utils import get_data, BASE_YEAR

st.title("JNCHES Pay Spine vs Inflation")

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
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
show_nominal = st.sidebar.checkbox("Show nominal salaries", value=False)
show_inflation_only = st.sidebar.checkbox(
    "Show inflation-only line", value=False,
    help="Adds a dashed line showing what each salary would be if it had only "
         "tracked inflation from the baseline date, with no real pay rises or cuts."
)

# ---------------------------------------------------------------------------
# Baseline selector (used by both chart overlay and summary table)
# ---------------------------------------------------------------------------
all_dates_sorted = (
    df[["effective_date", "date"]]
    .drop_duplicates()
    .sort_values("date")
    .reset_index(drop=True)
)
date_labels = {
    row["effective_date"]: row["date"].strftime("%b %Y")
    for _, row in all_dates_sorted.iterrows()
}
latest_date = all_dates_sorted["date"].max()

def closest_date(target_str: str) -> str:
    target = pd.Timestamp(target_str)
    idx = (all_dates_sorted["date"] - target).abs().idxmin()
    return all_dates_sorted.loc[idx, "effective_date"]

PRESETS = {
    "Start of data": all_dates_sorted["effective_date"].iloc[0],
    "Since 2009":    closest_date("2009-08-01"),
    "Since 2015":    closest_date("2015-08-01"),
    "Since COVID (2020)": closest_date("2020-08-01"),
    "~5 years ago":  closest_date(str(latest_date - pd.DateOffset(years=5))),
    "~10 years ago": closest_date(str(latest_date - pd.DateOffset(years=10))),
    "Custom…": None,
}

st.subheader("Baseline for comparison")
preset_choice = st.radio("", list(PRESETS.keys()), index=1, horizontal=True,
                         label_visibility="collapsed")

if preset_choice == "Custom…":
    baseline_date = st.selectbox(
        "Choose baseline date",
        options=list(date_labels.keys())[:-1],
        format_func=lambda d: date_labels[d],
    )
else:
    baseline_date = PRESETS[preset_choice]

baseline_label = date_labels[baseline_date]
latest_label   = date_labels[all_dates_sorted["effective_date"].iloc[-1]]

# ---------------------------------------------------------------------------
# Chart
# ---------------------------------------------------------------------------
salary_col   = "salary" if show_nominal else "real_salary"
salary_label = "Nominal salary (£)" if show_nominal else f"Real salary (£, {BASE_YEAR} prices)"

plot_points = selected if selected else all_points
colours = px.colors.qualitative.Plotly

fig = go.Figure()

for idx, sp in enumerate(plot_points):
    sub = df[df["spine_point"] == sp].sort_values("date")
    colour = colours[idx % len(colours)]

    fig.add_trace(go.Scatter(
        x=sub["date"], y=sub[salary_col],
        mode="lines+markers",
        name=f"SP {sp}",
        line=dict(color=colour, width=2),
        hovertemplate=f"SP {sp}<br>%{{x|%b %Y}}<br>£%{{y:,.0f}}<extra></extra>",
    ))

    if show_inflation_only:
        base_row = sub[sub["effective_date"] == baseline_date]
        if base_row.empty:
            continue
        base_salary   = base_row.iloc[0]["salary"]
        base_idx_val  = base_row.iloc[0]["index_val"]

        # Nominal salary needed at each date to maintain baseline purchasing power
        infl_nominal = base_salary * sub["index_val"] / base_idx_val
        # In real terms this is a flat line at the baseline real salary
        if show_nominal:
            y_infl = infl_nominal
            hover_label = "Inflation-compensated"
        else:
            # real = infl_nominal × base_CPI / index_val = base_salary × base_CPI / base_idx_val (constant)
            base_real = base_row.iloc[0]["real_salary"]
            y_infl = [base_real] * len(sub)
            hover_label = "Needed to keep up with inflation"

        fig.add_trace(go.Scatter(
            x=sub["date"], y=y_infl,
            mode="lines",
            name=f"SP {sp} ({measure}-only from {baseline_label})",
            line=dict(color=colour, width=1.5, dash="dash"),
            hovertemplate=f"SP {sp} — {hover_label}<br>%{{x|%b %Y}}<br>£%{{y:,.0f}}<extra></extra>",
        ))

fig.update_layout(
    title=f"HE Pay Spine: {salary_label.lower()} over time",
    xaxis_title="Effective date",
    yaxis_title=salary_label,
    legend_title="Spine point",
    hovermode="x unified",
)
st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
# Summary table
# ---------------------------------------------------------------------------
st.subheader(f"Change from {baseline_label} to {latest_label}")

summary_rows = []
for sp in (selected if selected else all_points):
    base_rows = df[(df["spine_point"] == sp) & (df["effective_date"] == baseline_date)]
    last_rows = df[(df["spine_point"] == sp) & (df["date"] == latest_date)]
    if base_rows.empty or last_rows.empty:
        continue
    first = base_rows.iloc[0]
    last  = last_rows.iloc[0]
    nominal_change = (last["salary"] - first["salary"]) / first["salary"] * 100
    real_change    = (last["real_salary"] - first["real_salary"]) / first["real_salary"] * 100
    summary_rows.append({
        "Spine point": int(sp),
        f"Salary {baseline_label} (£)": f"{int(first['salary']):,}",
        f"Salary {latest_label} (£)":   f"{int(last['salary']):,}",
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
