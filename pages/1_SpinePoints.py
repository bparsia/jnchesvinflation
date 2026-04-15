"""Spine Points page: compare individual spine points side-by-side."""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from utils import get_data, BASE_YEAR

st.title("Spine Point Comparison")
st.caption("Compare up to 5 individual spine points across years.")

try:
    df = get_data()
except FileNotFoundError:
    st.warning("No data found. Run the fetch and extract scripts first.")
    st.stop()

all_points = sorted(df["spine_point"].dropna().unique().astype(int))

cols = st.columns(5)
selected = []
for i, col in enumerate(cols):
    default = [1, 10, 20, 30, 51][i] if [1, 10, 20, 30, 51][i] in all_points else all_points[i]
    sp = col.selectbox(f"Point {i+1}", options=all_points, index=all_points.index(default), key=f"sp_{i}")
    selected.append(sp)

show_nominal = st.checkbox("Show nominal salaries alongside real", value=True)

fig = go.Figure()
colours = px_colours = ["#636EFA", "#EF553B", "#00CC96", "#AB63FA", "#FFA15A"]

import plotly.express as px
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

fig.update_layout(
    title=f"Spine point salaries over time ({BASE_YEAR} prices)",
    xaxis_title="Effective date",
    yaxis_title=f"Salary (£)",
    hovermode="x unified",
    legend_title="Spine point",
)
st.plotly_chart(fig, use_container_width=True)

# Table: one row per settlement date, columns = selected spine points
st.subheader("Salary table")
pivot = (
    df[df["spine_point"].isin(selected)]
    .sort_values("date")
    .assign(label=lambda d: d["date"].dt.strftime("%b %Y") + " — SP " + d["spine_point"].astype(int).astype(str))
    .pivot_table(index="effective_date", columns="spine_point", values="salary", aggfunc="first")
    .sort_index(key=lambda idx: pd.to_datetime(idx, format="%d %B %Y", errors="coerce"))
)
pivot.index.name = "Effective date"
pivot.columns = [f"SP {c}" for c in pivot.columns]
st.dataframe(pivot.style.format("£{:,.0f}"), use_container_width=True)
