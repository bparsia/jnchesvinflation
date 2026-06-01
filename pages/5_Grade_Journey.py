"""Grade Journey: simulate a career path through a grade in real terms."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils import INDICES, ROOT, get_data

st.title("Grade Journey")
st.caption(
    "Simulate a career starting at the bottom of a grade, auto-incrementing one "
    "spine point per year until the grade ceiling, then stuck. Real values use "
    "the start year as base."
)

# ---------------------------------------------------------------------------
# Load grade mappings
# ---------------------------------------------------------------------------
GRADE_FILES = {
    "UoM": ROOT / "data" / "uom_grade_spine.csv",
    "MMU": ROOT / "data" / "mmu_grade_spine.csv",
}

# ---------------------------------------------------------------------------
# Sidebar controls
# ---------------------------------------------------------------------------
st.sidebar.header("Options")
institution = st.sidebar.radio("Institution", list(GRADE_FILES.keys()))
measure = st.sidebar.radio("Inflation measure", ["CPI", "RPI"], horizontal=True)

grade_df = pd.read_csv(GRADE_FILES[institution])
available_grades = sorted(grade_df["grade"].unique())
grade = st.sidebar.selectbox("Grade", available_grades, index=len(available_grades) // 2)

show_nominal = st.sidebar.checkbox("Show nominal salary", value=True)
show_band = st.sidebar.checkbox("Show full grade band", value=True)

# ---------------------------------------------------------------------------
# Load salary data — one row per year per spine point (latest date in year)
# ---------------------------------------------------------------------------
try:
    raw = get_data(measure=measure)
except FileNotFoundError:
    st.warning("No salary data found.")
    st.stop()

# Keep latest pay date per year
annual = (
    raw.sort_values("date")
    .groupby(["date_year", "spine_point"], as_index=False)
    .last()
)

# ---------------------------------------------------------------------------
# Grade spine points
# ---------------------------------------------------------------------------
grade_rows = grade_df[grade_df["grade"] == grade]
auto_sps = sorted(grade_rows[grade_rows["type"] == "auto"]["spine_point"])
all_sps = sorted(grade_rows["spine_point"])

if not auto_sps:
    st.error("No auto increment points found for this grade.")
    st.stop()

start_sp = auto_sps[0]
ceiling_sp = auto_sps[-1]

# ---------------------------------------------------------------------------
# Build journey
# ---------------------------------------------------------------------------
years = sorted(annual["date_year"].unique())
start_year = years[0]
index = INDICES[measure]
base_index = index[start_year]

journey = []
for yr in years:
    offset = yr - start_year
    sp = min(start_sp + offset, ceiling_sp)
    row = annual[(annual["date_year"] == yr) & (annual["spine_point"] == sp)]
    if row.empty:
        continue
    nominal = float(row["salary"].iloc[0])
    real = round(nominal * base_index / index[yr])
    journey.append({"year": yr, "spine_point": sp, "nominal": nominal, "real": real})

if not journey:
    st.error("No salary data found for this grade's spine points.")
    st.stop()

jdf = pd.DataFrame(journey)

# ---------------------------------------------------------------------------
# Grade band (min and max auto SP at each year)
# ---------------------------------------------------------------------------
band_data = []
if show_band:
    for yr in years:
        yr_index = index.get(yr)
        if yr_index is None:
            continue
        lo_row = annual[(annual["date_year"] == yr) & (annual["spine_point"] == start_sp)]
        hi_row = annual[(annual["date_year"] == yr) & (annual["spine_point"] == ceiling_sp)]
        if lo_row.empty or hi_row.empty:
            continue
        lo_real = round(float(lo_row["salary"].iloc[0]) * base_index / yr_index)
        hi_real = round(float(hi_row["salary"].iloc[0]) * base_index / yr_index)
        band_data.append({"year": yr, "lo": lo_real, "hi": hi_real})
    band_df = pd.DataFrame(band_data)

# ---------------------------------------------------------------------------
# Plot
# ---------------------------------------------------------------------------
fig = go.Figure()

# Grade band
if show_band and band_data:
    fig.add_trace(go.Scatter(
        x=band_df["year"].tolist() + band_df["year"].tolist()[::-1],
        y=band_df["hi"].tolist() + band_df["lo"].tolist()[::-1],
        fill="toself",
        fillcolor="rgba(100,150,255,0.12)",
        line=dict(color="rgba(0,0,0,0)"),
        hoverinfo="skip",
        name=f"Grade {grade} auto range",
        showlegend=True,
    ))

# Nominal salary
if show_nominal:
    fig.add_trace(go.Scatter(
        x=jdf["year"], y=jdf["nominal"],
        mode="lines+markers",
        line=dict(dash="dot", color="grey", width=1),
        marker=dict(size=5),
        name="Nominal salary",
        hovertemplate="%{x}: £%{y:,.0f}<extra>Nominal</extra>",
    ))

# Real salary journey
fig.add_trace(go.Scatter(
    x=jdf["year"], y=jdf["real"],
    mode="lines+markers",
    line=dict(color="#1f77b4", width=2),
    marker=dict(
        size=8,
        color=jdf["spine_point"],
        colorscale="Blues",
        showscale=True,
        colorbar=dict(title="Spine point", thickness=12),
    ),
    name=f"Real salary ({measure}, {start_year}=100)",
    hovertemplate=(
        "%{x}: £%{y:,.0f}<br>Spine point %{customdata}<extra>Real</extra>"
    ),
    customdata=jdf["spine_point"],
))

# Annotate when stuck at ceiling
stuck_year = start_year + (ceiling_sp - start_sp)
if stuck_year <= years[-1]:
    fig.add_vline(
        x=stuck_year, line_dash="dash", line_color="red", line_width=1,
        annotation_text=f"Ceiling (SP {ceiling_sp})",
        annotation_position="top right",
        annotation_font_size=11,
    )

fig.update_layout(
    xaxis_title="Year",
    yaxis_title=f"Salary (£, {start_year} {measure} prices)",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    hovermode="x unified",
    height=500,
    margin=dict(t=60),
)

st.plotly_chart(fig, width="stretch")

# ---------------------------------------------------------------------------
# Summary table
# ---------------------------------------------------------------------------
with st.expander("Journey data"):
    st.dataframe(
        jdf.rename(columns={
            "year": "Year", "spine_point": "Spine point",
            "nominal": "Nominal (£)", "real": f"Real (£, {start_year}={measure})",
        }),
        use_container_width=True,
        hide_index=True,
    )
