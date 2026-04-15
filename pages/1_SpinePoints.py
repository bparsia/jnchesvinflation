"""Spine Points page: compare individual spine points side-by-side."""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from utils import get_data, BASE_YEAR

st.title("Spine Point Comparison")

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
st.sidebar.header("Display options")
measure = st.sidebar.radio("Inflation measure", ["CPI", "RPI"], horizontal=True)
st.caption(f"Compare up to 5 individual spine points across years. Real values in {BASE_YEAR} {measure} prices.")

try:
    df = get_data(measure=measure)
except FileNotFoundError:
    st.warning("No data found. Run the fetch and extract scripts first.")
    st.stop()

all_points = sorted(df["spine_point"].dropna().unique().astype(int))
options = [None] + all_points

st.sidebar.divider()
cols = st.columns(5)
selected = []
defaults = [1, 10, 20, None, None]
for i, col in enumerate(cols):
    default = defaults[i] if defaults[i] in all_points else (all_points[0] if defaults[i] is not None else None)
    sp = col.selectbox(
        f"Point {i+1}",
        options=options,
        index=options.index(default),
        format_func=lambda x: "None" if x is None else str(x),
        key=f"sp_{i}",
    )
    if sp is not None:
        selected.append(sp)

show_nominal = st.sidebar.checkbox("Show nominal salaries", value=False)
show_inflation_only = st.sidebar.checkbox(
    "Show inflation-only line", value=False,
    help="Adds a dashed line showing what each salary would be if it had only "
         "tracked inflation from the baseline date, with no real pay rises or cuts."
)

# ---------------------------------------------------------------------------
# Baseline selector
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
fig = go.Figure()
colours = px.colors.qualitative.Plotly

for idx, sp in enumerate(selected):
    sub = df[df["spine_point"] == sp].sort_values("date")
    colour = colours[idx % len(colours)]

    fig.add_trace(go.Scatter(
        x=sub["date"],
        y=sub["real_salary"],
        mode="lines+markers",
        name=f"SP {sp} (real)",
        line=dict(color=colour, width=2),
        hovertemplate=f"SP {sp}<br>%{{x|%b %Y}}<br>Real: £%{{y:,.0f}}<extra></extra>",
    ))

    if show_nominal:
        fig.add_trace(go.Scatter(
            x=sub["date"],
            y=sub["salary"],
            mode="lines+markers",
            name=f"SP {sp} (nominal)",
            line=dict(color=colour, width=1, dash="dot"),
            hovertemplate=f"SP {sp}<br>%{{x|%b %Y}}<br>Nominal: £%{{y:,.0f}}<extra></extra>",
        ))

    if show_inflation_only:
        base_row = sub[sub["effective_date"] == baseline_date]
        if base_row.empty:
            continue
        base_real    = base_row.iloc[0]["real_salary"]
        base_salary  = base_row.iloc[0]["salary"]
        base_idx_val = base_row.iloc[0]["index_val"]

        # Real chart: flat line at baseline real salary
        fig.add_trace(go.Scatter(
            x=sub["date"],
            y=[base_real] * len(sub),
            mode="lines",
            name=f"SP {sp} ({measure}-only from {baseline_label})",
            line=dict(color=colour, width=1.5, dash="dash"),
            hovertemplate=f"SP {sp} — Needed to keep up with inflation<br>%{{x|%b %Y}}<br>£%{{y:,.0f}}<extra></extra>",
        ))

        if show_nominal:
            infl_nominal = base_salary * sub["index_val"] / base_idx_val
            fig.add_trace(go.Scatter(
                x=sub["date"],
                y=infl_nominal,
                mode="lines",
                name=f"SP {sp} ({measure}-only nominal from {baseline_label})",
                line=dict(color=colour, width=1, dash="dashdot"),
                hovertemplate=f"SP {sp} — Inflation-compensated (nominal)<br>%{{x|%b %Y}}<br>£%{{y:,.0f}}<extra></extra>",
            ))

fig.update_layout(
    title=f"Spine point salaries over time ({BASE_YEAR} {measure} prices)",
    xaxis_title="Effective date",
    yaxis_title="Salary (£)",
    hovermode="x unified",
    legend_title="Spine point",
)
st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
# Summary table
# ---------------------------------------------------------------------------
st.subheader(f"Change from {baseline_label} to {latest_label}")

summary_rows = []
for sp in selected:
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

# ---------------------------------------------------------------------------
# Salary table
# ---------------------------------------------------------------------------
st.subheader("Full salary table")
if selected:
    pivot = (
        df[df["spine_point"].isin(selected)]
        .sort_values("date")
        .pivot_table(index="effective_date", columns="spine_point", values="salary", aggfunc="first")
        .sort_index(key=lambda idx: pd.to_datetime(idx, format="%d %B %Y", errors="coerce"))
    )
    pivot.index.name = "Effective date"
    pivot.columns = [f"SP {c}" for c in pivot.columns]
    st.dataframe(pivot.style.format("£{:,.0f}"), use_container_width=True)
