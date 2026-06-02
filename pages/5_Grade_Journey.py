"""Grade Journey: simulate a career path through a grade in real terms."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils import INDICES, ROOT, get_data
from styles import inject_bjp_css, bjp

inject_bjp_css()

st.title("Grade Journey")
st.caption(
    "Fan shows the full auto-increment range of each grade in real terms. "
    "Journey line tracks someone starting at the grade floor, incrementing one "
    "spine point per year until the ceiling. Real values use the start year as base."
)
bjp('''# EXPERIMENTAL PAGE!
I've just started with a couple of sets of grades and already it's clear that one needs some role
mapping to get a coherent cross instituion picture. E.g., it's not just that the University of Manchester's
grade 5 is a *little* different from Manchester Metropolitan's, but that they are completely different and are 
almost certainly associated with different roles. I don't know that pairwise comparison is what we centrally want here
...it's useful but I think we want a map of roles to spine points, ultimately.

But, the worker's pay journey is nice. Assuming you start at the bottome of a grade, it shows the increase due to within grade 
spine point incrementing, then the pure devaluation due to inflation that happens there after.
''')
# ---------------------------------------------------------------------------
# Load grade mappings
# ---------------------------------------------------------------------------
GRADE_FILES = {
    "UoM": ROOT / "data" / "uom_grade_spine.csv",
    "MMU": ROOT / "data" / "mmu_grade_spine.csv",
}
SERIES_COLOURS      = ["#1f77b4",               "#e05a00"]
SERIES_COLOURS_FILL = ["rgba(31,119,180,0.15)", "rgba(224,90,0,0.15)"]

grade_dfs = {inst: pd.read_csv(path) for inst, path in GRADE_FILES.items()}

# ---------------------------------------------------------------------------
# Sidebar controls
# ---------------------------------------------------------------------------
st.sidebar.header("Options")
measure = st.sidebar.radio("Inflation measure", ["CPI", "RPI"], horizontal=True)
show_journey = st.sidebar.checkbox("Show journey lines", value=True)

st.sidebar.divider()
selections = {}
defaults = [("UoM", None), ("MMU", None)]
for i, (default_inst, _) in enumerate(defaults):
    label = f"Series {i + 1}"
    st.sidebar.markdown(f"**{label}**")
    inst = st.sidebar.selectbox("Institution", list(GRADE_FILES.keys()),
                                index=list(GRADE_FILES.keys()).index(default_inst),
                                key=f"inst_{i}")
    gdf = grade_dfs[inst]
    grades = sorted(gdf["grade"].unique())
    grade = st.sidebar.selectbox("Grade", grades, index=len(grades) // 2, key=f"grade_{i}")
    selections[i] = (inst, grade)

# ---------------------------------------------------------------------------
# Load salary data — latest pay date per year per spine point
# ---------------------------------------------------------------------------
try:
    raw = get_data(measure=measure)
except FileNotFoundError:
    st.warning("No salary data found.")
    st.stop()

annual = (
    raw.sort_values("date")
    .groupby(["date_year", "spine_point"], as_index=False)
    .last()
)

years = sorted(annual["date_year"].unique())
start_year = years[0]
index = INDICES[measure]
base_index = index[start_year]

# ---------------------------------------------------------------------------
# Build fan + journey per institution
# ---------------------------------------------------------------------------
def build_fan_and_journey(inst: str, grade: int):
    gdf = grade_dfs[inst]
    grade_rows = gdf[gdf["grade"] == grade]
    auto_sps = sorted(grade_rows[grade_rows["type"] == "auto"]["spine_point"])
    if not auto_sps:
        return None, None

    start_sp = auto_sps[0]
    ceiling_sp = auto_sps[-1]

    fan, journey = [], []
    for yr in years:
        yr_idx = index.get(yr)
        if yr_idx is None:
            continue
        lo_row = annual[(annual["date_year"] == yr) & (annual["spine_point"] == start_sp)]
        hi_row = annual[(annual["date_year"] == yr) & (annual["spine_point"] == ceiling_sp)]
        if lo_row.empty or hi_row.empty:
            continue
        lo_real = round(float(lo_row["salary"].iloc[0]) * base_index / yr_idx)
        hi_real = round(float(hi_row["salary"].iloc[0]) * base_index / yr_idx)
        fan.append({"year": yr, "lo": lo_real, "hi": hi_real})

        offset = yr - start_year
        sp = min(start_sp + offset, ceiling_sp)
        sp_row = annual[(annual["date_year"] == yr) & (annual["spine_point"] == sp)]
        if not sp_row.empty:
            real = round(float(sp_row["salary"].iloc[0]) * base_index / yr_idx)
            journey.append({"year": yr, "spine_point": sp, "real": real})

    return pd.DataFrame(fan), pd.DataFrame(journey)

# ---------------------------------------------------------------------------
# Plot
# ---------------------------------------------------------------------------
fig = go.Figure()

for i, (inst, grade) in selections.items():
    colour = SERIES_COLOURS[i]
    fill   = SERIES_COLOURS_FILL[i]
    fan_df, journey_df = build_fan_and_journey(inst, grade)

    if fan_df is None or fan_df.empty:
        st.warning(f"No data for {inst} Grade {grade}.")
        continue

    # Fan
    fig.add_trace(go.Scatter(
        x=fan_df["year"].tolist() + fan_df["year"].tolist()[::-1],
        y=fan_df["hi"].tolist() + fan_df["lo"].tolist()[::-1],
        fill="toself",
        fillcolor=fill,
        line=dict(color="rgba(0,0,0,0)"),
        hoverinfo="skip",
        name=f"{inst} G{grade} range",
        showlegend=True,
    ))

    # Fan boundary lines
    for edge, label in [(fan_df["hi"], "ceiling"), (fan_df["lo"], "floor")]:
        fig.add_trace(go.Scatter(
            x=fan_df["year"], y=edge,
            mode="lines",
            line=dict(color=colour, width=1, dash="dot"),
            hovertemplate=f"{inst} G{grade} {label}: £%{{y:,.0f}}<extra></extra>",
            showlegend=False,
        ))

    # Journey line
    if show_journey and journey_df is not None and not journey_df.empty:
        ceiling_sp = grade_dfs[inst][
            (grade_dfs[inst]["grade"] == grade) & (grade_dfs[inst]["type"] == "auto")
        ]["spine_point"].max()
        stuck_year = start_year + (ceiling_sp - grade_dfs[inst][
            (grade_dfs[inst]["grade"] == grade) & (grade_dfs[inst]["type"] == "auto")
        ]["spine_point"].min())

        fig.add_trace(go.Scatter(
            x=journey_df["year"], y=journey_df["real"],
            mode="lines+markers+text",
            line=dict(color=colour, width=2),
            marker=dict(size=6),
            text=journey_df["spine_point"],
            textposition="top center",
            textfont=dict(size=9, color=colour),
            name=f"{inst} G{grade} journey",
            hovertemplate=(
                f"{inst} G{{grade}} %{{x}}: £%{{y:,.0f}}<br>"
                "SP %{customdata}<extra></extra>"
            ),
            customdata=journey_df["spine_point"],
        ))

        if stuck_year <= years[-1]:
            fig.add_vline(
                x=stuck_year,
                line_dash="dash", line_color=colour, line_width=1, opacity=0.5,
                annotation_text=f"{inst} G{grade} ceiling",
                annotation_position="top left" if i == 1 else "top right",
                annotation_font_size=10, annotation_font_color=colour,
            )

fig.update_layout(
    xaxis_title="Year",
    yaxis_title=f"Salary (£, {start_year} {measure} prices)",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    hovermode="x unified",
    height=520,
    margin=dict(t=80),
)

st.plotly_chart(fig, width="stretch")

# ---------------------------------------------------------------------------
# Grade definition tables
# ---------------------------------------------------------------------------
st.subheader("Grade definitions")
cols = st.columns(len(selections))
for col, (i, (inst, grade)) in zip(cols, selections.items()):
    gdf = grade_dfs[inst]
    rows = []
    for g in sorted(gdf["grade"].unique()):
        g_rows = gdf[gdf["grade"] == g]
        auto_sps = sorted(g_rows[g_rows["type"] == "auto"]["spine_point"])
        exc_sps  = sorted(g_rows[g_rows["type"] == "exceptional"]["spine_point"])
        rows.append({
            "Grade": g,
            "Auto SPs": f"{auto_sps[0]}–{auto_sps[-1]}" if auto_sps else "—",
            "Exceptional SPs": ", ".join(str(s) for s in exc_sps) if exc_sps else "—",
        })
    tdf = pd.DataFrame(rows)
    col.markdown(f"**{inst}**")
    col.dataframe(
        tdf.style.apply(
            lambda row: ["background-color: #e8f0fb; font-weight: bold" if row["Grade"] == grade
                         else "" for _ in row],
            axis=1,
        ),
        hide_index=True,
        use_container_width=True,
    )
