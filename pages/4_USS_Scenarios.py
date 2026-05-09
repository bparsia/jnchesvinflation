"""USS Pension Indexation Scenarios.

Model what happens to £1,000/month pension in payment under different
indexation rules, using historical CPI data.
"""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from utils import CPI, RPI

st.title("USS Pension: Indexation Scenarios")
st.markdown(
    "Model the effect of different indexation rules on a **£1,000/month pension in payment**. "
    "Real values are expressed in the retirement year's prices — so £1,000 means purchasing "
    "power has been fully maintained."
)

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
st.sidebar.header("Model parameters")

common_years = sorted(set(CPI) & set(RPI))
# Need prior year to compute annual rate; exclude the last year as a start (nothing to project to)
start_options = [y for y in common_years if y - 1 in CPI and y - 1 in RPI and y < max(common_years)]

start_year = st.sidebar.selectbox(
    "Retirement year",
    options=start_options,
    index=start_options.index(2009) if 2009 in start_options else 0,
    help="The year the pension comes into payment at £1,000/month.",
)

st.sidebar.divider()
st.sidebar.subheader("CI scenario parameters")

initial_fr = st.sidebar.slider(
    "Initial funding ratio (%)",
    min_value=70, max_value=130, value=100, step=5,
    help="Funding ratio at retirement year. Evolves each year based on real asset return.",
)

real_return = st.sidebar.slider(
    "Real asset return (% p.a.)",
    min_value=-2.0, max_value=8.0, value=2.0, step=0.5,
    help=(
        "Annual return on assets above CPI. "
        "FR improves when positive (assets outpace liabilities), "
        "deteriorates when negative. CPI effects roughly cancel between "
        "asset returns and liability growth."
    ),
)

hybrid_floor = st.sidebar.slider(
    "Hybrid CI — guaranteed floor (%)",
    min_value=0.0, max_value=5.0, value=2.5, step=0.5,
    help="Indexation paid regardless of funding level under Hybrid CI.",
)

# ---------------------------------------------------------------------------
# Indexation rules
# ---------------------------------------------------------------------------

def soft_cap_rate(cpi_pct: float) -> float:
    """Full CPI ≤ 5%; 5% + 50% of (CPI − 5%) for CPI 5–15%; max 10%."""
    if cpi_pct <= 5.0:
        return cpi_pct
    elif cpi_pct <= 15.0:
        return 5.0 + 0.5 * (cpi_pct - 5.0)
    else:
        return 10.0  # CPI > 15% still caps at 10%


def full_ci_rate(cpi_pct: float, fr: float) -> float:
    """Full CPI when funded (≥ 100%); 0% when underfunded."""
    return cpi_pct if fr >= 100.0 else 0.0


def hybrid_ci_rate(cpi_pct: float, fr: float, floor_pct: float) -> float:
    """Guaranteed floor always paid; remainder of CPI conditional on funding."""
    guaranteed = min(cpi_pct, floor_pct)
    conditional = max(0.0, cpi_pct - floor_pct) if fr >= 100.0 else 0.0
    return guaranteed + conditional


def graded_ci_rate(cpi_pct: float, fr: float) -> float:
    """Indexation scales linearly with funding ratio (capped at 100% → full CPI)."""
    return cpi_pct * min(1.0, fr / 100.0)


def annual_cpi_rate(year: int) -> float:
    if year - 1 not in CPI:
        return 0.0
    return (CPI[year] - CPI[year - 1]) / CPI[year - 1] * 100.0


# ---------------------------------------------------------------------------
# Scenario registry
# ---------------------------------------------------------------------------
hybrid_label = f"Hybrid CI (≥{hybrid_floor:.1f}% guaranteed)"

NOINDEX_COLOUR = "#888888"

# ---------------------------------------------------------------------------
# Dynamic funding ratio
# ---------------------------------------------------------------------------
projection_years = [y for y in common_years if y >= start_year]

# FR evolves as: FR_t = FR_0 × (1 + real_return)^t
# Rationale: nominal asset return ≈ real_return + CPI; liabilities grow at CPI;
# so CPI largely cancels and FR change is driven by the real return alone.
funding_ratios = {
    year: initial_fr * ((1 + real_return / 100) ** i)
    for i, year in enumerate(projection_years)
}

# Scenarios: rules now take (cpi_rate, year) so they can look up the year's FR
SCENARIOS = [
    # (label,         rule_fn(cpi_rate, year),                                      colour,    dash)
    ("Soft cap",      lambda r, y: soft_cap_rate(r),                                "#636EFA", "solid"),
    ("Full CI",       lambda r, y: full_ci_rate(r, funding_ratios[y]),              "#EF553B", "solid"),
    (hybrid_label,    lambda r, y: hybrid_ci_rate(r, funding_ratios[y], hybrid_floor), "#00CC96", "solid"),
    ("Graded CI",     lambda r, y: graded_ci_rate(r, funding_ratios[y]),            "#AB63FA", "solid"),
]

# ---------------------------------------------------------------------------
# Run projection
# ---------------------------------------------------------------------------
running = {label: 1000.0 for label, *_ in SCENARIOS}

nominal_series  = {label: [] for label, *_ in SCENARIOS}
real_cpi_series = {label: [] for label, *_ in SCENARIOS}
real_rpi_series = {label: [] for label, *_ in SCENARIOS}
increase_series = {label: [] for label, *_ in SCENARIOS}
cpi_rate_series = []
noindex_real_cpi = []
noindex_real_rpi = []

for i, year in enumerate(projection_years):
    cpi_rate = annual_cpi_rate(year) if i > 0 else 0.0
    rcpi = CPI[start_year] / CPI[year]
    rrpi = RPI[start_year] / RPI[year]
    cpi_rate_series.append(cpi_rate)

    for label, rule, colour, dash in SCENARIOS:
        inc = rule(cpi_rate, year) if i > 0 else 0.0
        if i > 0:
            running[label] *= (1 + inc / 100)
        nominal_series[label].append(running[label])
        real_cpi_series[label].append(running[label] * rcpi)
        real_rpi_series[label].append(running[label] * rrpi)
        increase_series[label].append(inc)

    noindex_real_cpi.append(1000.0 * rcpi)
    noindex_real_rpi.append(1000.0 * rrpi)

# ---------------------------------------------------------------------------
# Chart 1: Nominal monthly pension
# ---------------------------------------------------------------------------
st.subheader("Nominal monthly pension (£)")
st.caption("What you actually receive each month — not adjusted for inflation.")

fig_nom = go.Figure()

# No indexation: flat at £1,000
fig_nom.add_trace(go.Scatter(
    x=projection_years, y=[1000.0] * len(projection_years),
    mode="lines", name="No indexation",
    line=dict(color=NOINDEX_COLOUR, width=2, dash="dot"),
    hovertemplate="No indexation<br>%{x}<br>£1,000/month<extra></extra>",
))

for label, rule, colour, dash in SCENARIOS:
    fig_nom.add_trace(go.Scatter(
        x=projection_years, y=nominal_series[label],
        mode="lines+markers", name=label,
        line=dict(color=colour, width=2, dash=dash),
        hovertemplate=f"{label}<br>%{{x}}<br>£%{{y:,.0f}}/month<extra></extra>",
    ))

fig_nom.update_layout(
    xaxis_title="Year",
    yaxis_title="Monthly pension (£)",
    hovermode="x unified",
    legend_title="Scenario",
    yaxis=dict(rangemode="tozero"),
)
st.plotly_chart(fig_nom, use_container_width=True)

# ---------------------------------------------------------------------------
# Chart 1b: Funding ratio trajectory
# ---------------------------------------------------------------------------
st.subheader("Funding ratio over time")
st.caption(
    f"Starting at {initial_fr}%, evolving at {real_return:+.1f}% real return p.a. "
    "The 100% line is the CI trigger for Full CI and Hybrid CI."
)

fig_fr = go.Figure()
fig_fr.add_hline(y=100, line_dash="dash", line_color="lightgray", line_width=1,
                 annotation_text="100% (fully funded)", annotation_position="top left")
fig_fr.add_trace(go.Scatter(
    x=projection_years,
    y=[funding_ratios[y] for y in projection_years],
    mode="lines+markers",
    name="Funding ratio",
    line=dict(color="#FFA15A", width=2),
    hovertemplate="%{x}<br>FR: %{y:.1f}%<extra></extra>",
))
fig_fr.update_layout(
    xaxis_title="Year",
    yaxis_title="Funding ratio (%)",
    showlegend=False,
    yaxis=dict(ticksuffix="%"),
)
st.plotly_chart(fig_fr, use_container_width=True)

# ---------------------------------------------------------------------------
# Chart 2: Real monthly pension (purchasing power)
# ---------------------------------------------------------------------------
st.subheader(f"Real monthly pension (£, {start_year} prices)")
st.caption(
    f"Purchasing power expressed in {start_year} prices. "
    "The £1,000 reference line means full inflation protection."
)

fig_real = go.Figure()

# Reference line
fig_real.add_hline(
    y=1000, line_dash="dash", line_color="lightgray", line_width=1,
    annotation_text="Full purchasing power (£1,000)",
    annotation_position="top left",
)

# No indexation — CPI eroded
fig_real.add_trace(go.Scatter(
    x=projection_years, y=noindex_real_cpi,
    mode="lines", name="No indexation (CPI eroded)",
    line=dict(color=NOINDEX_COLOUR, width=2, dash="solid"),
    hovertemplate="No indexation (CPI)<br>%{x}<br>£%{y:,.0f}<extra></extra>",
))

# No indexation — RPI eroded
fig_real.add_trace(go.Scatter(
    x=projection_years, y=noindex_real_rpi,
    mode="lines", name="No indexation (RPI eroded)",
    line=dict(color=NOINDEX_COLOUR, width=2, dash="dot"),
    hovertemplate="No indexation (RPI)<br>%{x}<br>£%{y:,.0f}<extra></extra>",
))

for label, rule, colour, dash in SCENARIOS:
    fig_real.add_trace(go.Scatter(
        x=projection_years, y=real_cpi_series[label],
        mode="lines+markers", name=label,
        line=dict(color=colour, width=2, dash=dash),
        hovertemplate=f"{label}<br>%{{x}}<br>£%{{y:,.0f}} ({start_year} prices)<extra></extra>",
    ))

fig_real.update_layout(
    xaxis_title="Year",
    yaxis_title=f"Monthly pension (£, {start_year} prices)",
    hovermode="x unified",
    legend_title="Scenario",
)
st.plotly_chart(fig_real, use_container_width=True)

# ---------------------------------------------------------------------------
# Summary table
# ---------------------------------------------------------------------------
end_year = projection_years[-1]
st.subheader(f"Summary: {start_year} → {end_year}")

summary_rows = []

# No indexation
summary_rows.append({
    "Scenario": "No indexation",
    "Final nominal (£/month)": "£1,000",
    f"Final real, CPI (£, {start_year} prices)": f"£{noindex_real_cpi[-1]:,.0f}",
    f"Final real, RPI (£, {start_year} prices)": f"£{noindex_real_rpi[-1]:,.0f}",
    "Real CPI change": f"{(noindex_real_cpi[-1] / 1000 - 1) * 100:+.1f}%",
    "Real RPI change": f"{(noindex_real_rpi[-1] / 1000 - 1) * 100:+.1f}%",
})

for label, rule, colour, dash in SCENARIOS:
    final_nom = nominal_series[label][-1]
    final_rcpi = real_cpi_series[label][-1]
    final_rrpi = real_rpi_series[label][-1]
    summary_rows.append({
        "Scenario": label,
        "Final nominal (£/month)": f"£{final_nom:,.0f}",
        f"Final real, CPI (£, {start_year} prices)": f"£{final_rcpi:,.0f}",
        f"Final real, RPI (£, {start_year} prices)": f"£{final_rrpi:,.0f}",
        "Real CPI change": f"{(final_rcpi / 1000 - 1) * 100:+.1f}%",
        "Real RPI change": f"{(final_rrpi / 1000 - 1) * 100:+.1f}%",
    })

st.dataframe(pd.DataFrame(summary_rows).set_index("Scenario"), use_container_width=True)

# ---------------------------------------------------------------------------
# Year-by-year detail table
# ---------------------------------------------------------------------------
with st.expander("Year-by-year detail"):
    detail_rows = []
    for i, year in enumerate(projection_years):
        row = {
            "Year": year,
            "CPI rate (%)": f"{cpi_rate_series[i]:.1f}%",
            "Funding ratio (%)": f"{funding_ratios[year]:.1f}%",
        }
        for label, rule, colour, dash in SCENARIOS:
            row[f"{label} — increase"] = f"{increase_series[label][i]:.1f}%"
            row[f"{label} — nominal (£)"] = f"£{nominal_series[label][i]:,.0f}"
            row[f"{label} — real (£)"] = f"£{real_cpi_series[label][i]:,.0f}"
        row["No index real CPI (£)"] = f"£{noindex_real_cpi[i]:,.0f}"
        row["No index real RPI (£)"] = f"£{noindex_real_rpi[i]:,.0f}"
        detail_rows.append(row)
    st.dataframe(pd.DataFrame(detail_rows).set_index("Year"), use_container_width=True)

# ---------------------------------------------------------------------------
# Soft cap explainer
# ---------------------------------------------------------------------------
with st.expander("How the soft cap is calculated"):
    st.markdown(f"""
| CPI rate | Soft cap indexation |
|----------|-------------------|
| ≤ 5% | Full CPI |
| 5% – 15% | 5% + 50% × (CPI − 5%) |
| > 15% | 10% (maximum) |

**Example**: CPI = {cpi_rate_series[-1]:.1f}% → soft cap gives {soft_cap_rate(cpi_rate_series[-1]):.1f}%

**CI scenarios** start at **{initial_fr}%** funding ratio, evolving at **{real_return:+.1f}%** real return p.a.
- **Full CI**: pays full CPI if ≥ 100% funded; 0% otherwise
- **Hybrid CI**: always pays up to {hybrid_floor:.1f}%; pays remainder (up to CPI) only if ≥ 100% funded
- **Graded CI**: pays CPI × funding_ratio/100 (proportional; no binary trigger)
""")
