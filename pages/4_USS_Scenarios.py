"""USS Pension Indexation Scenarios — stochastic fund model.

Investment returns are modelled as a mix of:
  - Equities: log-normal real returns (Davies, Grant & Shapland 2021 parameters)
  - Bonds/gilts: deterministic real return

Historical CPI drives indexation rules. CI scenarios produce a distribution
of outcomes depending on whether the funding ratio exceeds the trigger each year.
"""
import numpy as np
import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from utils import CPI, RPI

st.title("USS Pension: Indexation Scenarios")
st.markdown(
    "Model the effect of different indexation rules on a **£1,000/month pension in payment**, "
    "using actual historical CPI and stochastic investment returns. "
    "CI scenarios show a distribution of outcomes across simulated market histories."
)

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
st.sidebar.header("Model parameters")

common_years = sorted(set(CPI) & set(RPI))
start_options = [y for y in common_years if y - 1 in CPI and y - 1 in RPI and y < max(common_years)]

start_year = st.sidebar.selectbox(
    "Retirement year",
    options=start_options,
    index=start_options.index(2009) if 2009 in start_options else 0,
)

st.sidebar.divider()
st.sidebar.subheader("Scheme funding")

initial_fr = st.sidebar.slider(
    "Initial funding ratio (%)", min_value=70, max_value=130, value=100, step=5,
    help="Funding ratio at the retirement year.",
)

st.sidebar.divider()
st.sidebar.subheader("Investment returns")
st.sidebar.caption(
    "Equity parameters from Davies, Grant & Shapland (2021) 'The USS Trustees' risky strategy'. "
    "Equity returns are log-normally distributed; bonds are deterministic."
)

equity_share = st.sidebar.slider(
    "Equity allocation (%)", min_value=0, max_value=100, value=67, step=5,
    help="Share of fund in equities. Remainder in bonds/gilts.",
)
equity_mean = st.sidebar.slider(
    "Equity real return — mean (% p.a.)", min_value=0.0, max_value=10.0, value=4.5, step=0.5,
    help="Expected real arithmetic return on equities. Paper baseline: 4.5%.",
)
equity_vol = st.sidebar.slider(
    "Equity return — volatility (% std dev)", min_value=5.0, max_value=30.0, value=17.5, step=0.5,
    help="Std dev of annual log equity returns. Paper baseline: 17.5%.",
)
bond_return = st.sidebar.slider(
    "Bond real return (% p.a.)", min_value=-3.0, max_value=5.0, value=0.0, step=0.5,
    help="Deterministic real return on bonds/gilts.",
)

st.sidebar.divider()
st.sidebar.subheader("CI parameters")

hybrid_floor = st.sidebar.slider(
    "Hybrid CI — guaranteed floor (%)", min_value=0.0, max_value=5.0, value=2.5, step=0.5,
    help="Indexation always paid under Hybrid CI regardless of funding.",
)

N_SIMS = 2000  # number of Monte Carlo paths

# ---------------------------------------------------------------------------
# Indexation rules
# ---------------------------------------------------------------------------
def soft_cap_rate(cpi_pct: float) -> float:
    """Full CPI ≤ 5%; 5% + 50% × (CPI − 5%) for CPI 5–15%; max 10%."""
    if cpi_pct <= 5.0:
        return cpi_pct
    elif cpi_pct <= 15.0:
        return 5.0 + 0.5 * (cpi_pct - 5.0)
    else:
        return 10.0

def annual_cpi_rate(year: int) -> float:
    if year - 1 not in CPI:
        return 0.0
    return (CPI[year] - CPI[year - 1]) / CPI[year - 1] * 100.0

# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------
projection_years = [y for y in common_years if y >= start_year]
n_steps = len(projection_years) - 1   # transitions (year-to-year steps)

# Historical CPI rate at each step (index i = transition from year[i] to year[i+1])
cpi_steps = np.array([annual_cpi_rate(projection_years[i + 1]) for i in range(n_steps)])
sc_steps  = np.array([soft_cap_rate(r) for r in cpi_steps])

# Log-normal equity return parameters (real, above CPI)
# Using the Fisher / method-of-moments conversion from Davies et al.
eq_m  = equity_mean / 100
eq_v  = equity_vol  / 100
eq_sh = equity_share / 100
b_r   = bond_return / 100

lmew   = np.log((1 + eq_m)**2 / np.sqrt(eq_v**2 + (1 + eq_m)**2))
lsigma = np.sqrt(np.log(1 + eq_v**2 / (1 + eq_m)**2))

rng = np.random.default_rng(42)
# Equity gross real returns: shape (n_steps, N_SIMS)
eq_gross = np.exp(lmew + lsigma * rng.standard_normal((n_steps, N_SIMS)))
# Portfolio gross real return: shape (n_steps, N_SIMS)
port_gross = eq_sh * eq_gross + (1 - eq_sh) * (1 + b_r)

# Funding ratio paths (real terms: CPI cancels between nominal asset return and CPI liability growth)
# FR_t+1 = FR_t × portfolio_real_gross_t
# Shape: (n_steps+1, N_SIMS)
FR = np.empty((n_steps + 1, N_SIMS))
FR[0] = initial_fr
FR[1:] = initial_fr * np.cumprod(port_gross, axis=0)

# ---------------------------------------------------------------------------
# Pension paths
# ---------------------------------------------------------------------------
# For each scenario: step_growth_pct[i] = % increase applied at step i
# pension[t] = 1000 × ∏_{i<t}(1 + step_growth[i]/100)

def pension_paths(step_pct):
    """
    step_pct: (n_steps,) or (n_steps, N_SIMS) — percentage increases at each step.
    Returns: (n_steps+1,) or (n_steps+1, N_SIMS) pension values starting at £1,000.
    """
    is_1d = step_pct.ndim == 1
    p = np.empty((n_steps + 1,) if is_1d else (n_steps + 1, N_SIMS))
    p[0] = 1000.0
    p[1:] = 1000.0 * np.cumprod(1 + step_pct / 100, axis=0)
    return p

pension_no_idx = np.full(n_steps + 1, 1000.0)
pension_sc     = pension_paths(sc_steps)

# CI scenarios use FR[:-1] (FR at start of each step) as the trigger
fci_steps = np.where(FR[:-1] >= 100, cpi_steps[:, None], 0.0)
pension_fci = pension_paths(fci_steps)

guaranteed = np.minimum(cpi_steps[:, None], hybrid_floor)
conditional = np.where(FR[:-1] >= 100, np.maximum(0, cpi_steps[:, None] - hybrid_floor), 0.0)
pension_hci = pension_paths(guaranteed + conditional)

gci_steps = cpi_steps[:, None] * np.minimum(1.0, FR[:-1] / 100)
pension_gci = pension_paths(gci_steps)

# Deflation factors (deterministic)
cpi_defl = np.array([CPI[start_year] / CPI[y] for y in projection_years])
rpi_defl = np.array([RPI[start_year] / RPI[y] for y in projection_years])

# ---------------------------------------------------------------------------
# Percentile helper
# ---------------------------------------------------------------------------
PERCS = [5, 25, 50, 75, 95]

def pcts(arr):
    """arr: (n_steps+1, N_SIMS) → dict {pct: array (n_steps+1,)}"""
    return {p: np.percentile(arr, p, axis=1) for p in PERCS}

fr_p    = pcts(FR)
fci_p   = pcts(pension_fci)
hci_p   = pcts(pension_hci)
gci_p   = pcts(pension_gci)
fci_rp  = pcts(pension_fci * cpi_defl[:, None])
hci_rp  = pcts(pension_hci * cpi_defl[:, None])
gci_rp  = pcts(pension_gci * cpi_defl[:, None])

# % of simulations where CI trigger fires each year
pct_ci_paid = np.mean(FR[:-1] >= 100, axis=1) * 100   # (n_steps,)

# ---------------------------------------------------------------------------
# Plot helpers
# ---------------------------------------------------------------------------
def hex_to_rgba(hex_col: str, alpha: float) -> str:
    h = hex_col.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"

def add_fan(fig: go.Figure, years, p: dict, colour: str, name: str) -> None:
    """Add 5–95 band, 25–75 band, and median line."""
    fig.add_trace(go.Scatter(
        x=years, y=p[95], mode="lines", line=dict(width=0),
        showlegend=False, hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=years, y=p[5], mode="lines", line=dict(width=0),
        fill="tonexty", fillcolor=hex_to_rgba(colour, 0.12),
        showlegend=False, hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=years, y=p[75], mode="lines", line=dict(width=0),
        showlegend=False, hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=years, y=p[25], mode="lines", line=dict(width=0),
        fill="tonexty", fillcolor=hex_to_rgba(colour, 0.22),
        showlegend=False, hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=years, y=p[50], mode="lines+markers", name=name,
        line=dict(color=colour, width=2),
        hovertemplate=f"{name}<br>%{{x}}<br>Median: £%{{y:,.0f}}<extra></extra>",
    ))

COLOURS = {
    "Soft cap":   "#636EFA",
    "Full CI":    "#EF553B",
    "Hybrid CI":  "#00CC96",
    "Graded CI":  "#AB63FA",
}
GREY = "#888888"
hybrid_label = f"Hybrid CI (≥{hybrid_floor:.1f}% floor)"

# ---------------------------------------------------------------------------
# Chart 1: Nominal pension
# ---------------------------------------------------------------------------
st.subheader("Nominal monthly pension (£)")
st.caption(
    "What you actually receive each month. "
    "Bands show 5th–95th and 25th–75th percentile across simulated market histories."
)

fig_nom = go.Figure()
fig_nom.add_trace(go.Scatter(
    x=projection_years, y=pension_no_idx,
    mode="lines", name="No indexation",
    line=dict(color=GREY, width=2, dash="dot"),
    hovertemplate="No indexation<br>%{x}<br>£1,000/month<extra></extra>",
))
fig_nom.add_trace(go.Scatter(
    x=projection_years, y=pension_sc,
    mode="lines+markers", name="Soft cap",
    line=dict(color=COLOURS["Soft cap"], width=2),
    hovertemplate="Soft cap<br>%{x}<br>£%{y:,.0f}<extra></extra>",
))
add_fan(fig_nom, projection_years, fci_p, COLOURS["Full CI"], "Full CI")
add_fan(fig_nom, projection_years, hci_p, COLOURS["Hybrid CI"], hybrid_label)
add_fan(fig_nom, projection_years, gci_p, COLOURS["Graded CI"], "Graded CI")
fig_nom.update_layout(
    xaxis_title="Year", yaxis_title="Monthly pension (£)",
    hovermode="x unified", legend_title="Scenario",
    yaxis=dict(rangemode="tozero"),
)
st.plotly_chart(fig_nom, use_container_width=True)

# ---------------------------------------------------------------------------
# Chart 2: Funding ratio fan
# ---------------------------------------------------------------------------
st.subheader("Funding ratio over time")
st.caption(
    f"Starts at {initial_fr}%. Evolves via stochastic portfolio returns "
    f"({equity_share}% equities, mean real return {equity_mean:.1f}%, vol {equity_vol:.1f}%). "
    "The 100% line is the CI trigger for Full CI and Hybrid CI."
)

fig_fr = go.Figure()
fig_fr.add_hline(
    y=100, line_dash="dash", line_color="lightgray", line_width=1,
    annotation_text="100% trigger", annotation_position="top left",
)
add_fan(fig_fr, projection_years, fr_p, "#FFA15A", "Funding ratio")
fig_fr.update_layout(
    xaxis_title="Year", yaxis_title="Funding ratio (%)",
    showlegend=False, yaxis=dict(ticksuffix="%"),
)
st.plotly_chart(fig_fr, use_container_width=True)

# ---------------------------------------------------------------------------
# Chart 3: P(CI paid) by year
# ---------------------------------------------------------------------------
st.subheader("Probability CI trigger fires (funding ratio ≥ 100%)")
st.caption(
    f"Across {N_SIMS:,} simulated market histories. "
    "Years where CPI is high but equity returns are poor show the sharpest drops."
)

fig_prob = go.Figure()
fig_prob.add_trace(go.Bar(
    x=projection_years[1:],
    y=pct_ci_paid,
    marker_color="#FFA15A",
    hovertemplate="%{x}<br>P(CI paid): %{y:.1f}%<extra></extra>",
))
# Overlay CPI rate as a line on secondary axis
fig_prob.add_trace(go.Scatter(
    x=projection_years[1:], y=cpi_steps,
    mode="lines+markers", name="CPI rate",
    line=dict(color=GREY, width=1.5, dash="dot"),
    yaxis="y2",
    hovertemplate="%{x}<br>CPI: %{y:.1f}%<extra></extra>",
))
fig_prob.update_layout(
    xaxis_title="Year",
    yaxis=dict(title="P(CI trigger fires, %)", range=[0, 100], ticksuffix="%"),
    yaxis2=dict(title="CPI (%)", overlaying="y", side="right", range=[0, max(cpi_steps) * 2]),
    hovermode="x unified",
    legend=dict(x=0.01, y=0.99),
    barmode="overlay",
)
st.plotly_chart(fig_prob, use_container_width=True)

# ---------------------------------------------------------------------------
# Chart 4: Real pension (purchasing power)
# ---------------------------------------------------------------------------
st.subheader(f"Real monthly pension (£, {start_year} prices)")
st.caption(
    f"Purchasing power in {start_year} prices using historical CPI deflation. "
    "£1,000 reference = full purchasing power maintained."
)

fig_real = go.Figure()
fig_real.add_hline(
    y=1000, line_dash="dash", line_color="lightgray", line_width=1,
    annotation_text="Full purchasing power (£1,000)",
    annotation_position="top left",
)
fig_real.add_trace(go.Scatter(
    x=projection_years, y=1000.0 * cpi_defl,
    mode="lines", name="No indexation (CPI eroded)",
    line=dict(color=GREY, width=2, dash="solid"),
    hovertemplate="No indexation (CPI)<br>%{x}<br>£%{y:,.0f}<extra></extra>",
))
fig_real.add_trace(go.Scatter(
    x=projection_years, y=1000.0 * rpi_defl,
    mode="lines", name="No indexation (RPI eroded)",
    line=dict(color=GREY, width=2, dash="dot"),
    hovertemplate="No indexation (RPI)<br>%{x}<br>£%{y:,.0f}<extra></extra>",
))
fig_real.add_trace(go.Scatter(
    x=projection_years, y=pension_sc * cpi_defl,
    mode="lines+markers", name="Soft cap",
    line=dict(color=COLOURS["Soft cap"], width=2),
    hovertemplate="Soft cap<br>%{x}<br>£%{y:,.0f}<extra></extra>",
))
add_fan(fig_real, projection_years, fci_rp, COLOURS["Full CI"], "Full CI")
add_fan(fig_real, projection_years, hci_rp, COLOURS["Hybrid CI"], hybrid_label)
add_fan(fig_real, projection_years, gci_rp, COLOURS["Graded CI"], "Graded CI")
fig_real.update_layout(
    xaxis_title="Year",
    yaxis_title=f"Monthly pension (£, {start_year} prices)",
    hovermode="x unified",
    legend_title="Scenario",
)
st.plotly_chart(fig_real, use_container_width=True)

# ---------------------------------------------------------------------------
# Summary table: median outcomes
# ---------------------------------------------------------------------------
end_year = projection_years[-1]
st.subheader(f"Median outcomes: {start_year} → {end_year}")

def pct_change(final, initial=1000.0):
    return f"{(final / initial - 1) * 100:+.1f}%"

summary_rows = [
    {
        "Scenario": "No indexation",
        "Final nominal (£/month)": "£1,000",
        f"Final real, CPI (£, {start_year})": f"£{1000 * cpi_defl[-1]:,.0f}",
        f"Final real, RPI (£, {start_year})": f"£{1000 * rpi_defl[-1]:,.0f}",
        "Real CPI change": pct_change(1000 * cpi_defl[-1]),
        "Real RPI change": pct_change(1000 * rpi_defl[-1]),
    },
    {
        "Scenario": "Soft cap",
        "Final nominal (£/month)": f"£{pension_sc[-1]:,.0f}",
        f"Final real, CPI (£, {start_year})": f"£{pension_sc[-1] * cpi_defl[-1]:,.0f}",
        f"Final real, RPI (£, {start_year})": f"£{pension_sc[-1] * rpi_defl[-1]:,.0f}",
        "Real CPI change": pct_change(pension_sc[-1] * cpi_defl[-1]),
        "Real RPI change": pct_change(pension_sc[-1] * rpi_defl[-1]),
    },
]
for label, p, rp in [
    ("Full CI",     fci_p,  fci_rp),
    (hybrid_label,  hci_p,  hci_rp),
    ("Graded CI",   gci_p,  gci_rp),
]:
    summary_rows.append({
        "Scenario": label,
        "Final nominal (£/month)": f"£{p[50][-1]:,.0f}  (median)",
        f"Final real, CPI (£, {start_year})": f"£{rp[50][-1]:,.0f}  (median)",
        f"Final real, RPI (£, {start_year})": f"£{p[50][-1] * rpi_defl[-1]:,.0f}  (median)",
        "Real CPI change": pct_change(rp[50][-1]),
        "Real RPI change": pct_change(p[50][-1] * rpi_defl[-1]),
    })

st.dataframe(pd.DataFrame(summary_rows).set_index("Scenario"), use_container_width=True)

# ---------------------------------------------------------------------------
# Year-by-year detail
# ---------------------------------------------------------------------------
with st.expander("Year-by-year detail"):
    detail = []
    for i, year in enumerate(projection_years):
        row = {
            "Year": year,
            "CPI (%)": f"{(cpi_steps[i-1] if i > 0 else 0):.1f}%",
            "Soft cap (%)": f"{(sc_steps[i-1] if i > 0 else 0):.1f}%",
            "P(CI fires)": f"{(pct_ci_paid[i-1] if i > 0 else 100):.0f}%",
            "Soft cap pension": f"£{pension_sc[i]:,.0f}",
            "Full CI median": f"£{fci_p[50][i]:,.0f}",
            f"Hybrid CI median": f"£{hci_p[50][i]:,.0f}",
            "Graded CI median": f"£{gci_p[50][i]:,.0f}",
            "FR median (%)": f"{fr_p[50][i]:.0f}%",
        }
        detail.append(row)
    st.dataframe(pd.DataFrame(detail).set_index("Year"), use_container_width=True)

# ---------------------------------------------------------------------------
# Model notes
# ---------------------------------------------------------------------------
with st.expander("Model notes"):
    st.markdown(f"""
**Soft cap rule**

| CPI | Indexation |
|-----|-----------|
| ≤ 5% | Full CPI |
| 5% – 15% | 5% + 50% × (CPI − 5%) |
| > 15% | 10% (maximum) |

**CI scenarios** use the funding ratio at the *start* of each year as the trigger.

**Funding ratio evolution**

The scheme FR is modelled in real terms. In each year:

$$FR_{{t+1}} = FR_t \\times \\text{{portfolio real gross return}}_t$$

where portfolio real gross return = equity share × log-normal equity return + bond share × (1 + bond real return),
and log-normal parameters are computed via method-of-moments from the mean/vol inputs.

CPI terms cancel: nominal asset return = real return × (1 + CPI); nominal liability growth = CPI indexation.
When full CPI is paid, (1 + CPI) cancels and FR depends only on the real return.
When less than CPI is paid (e.g., Full CI unfunded = 0%), the FR actually *improves* relative to the
full-CPI case — capturing the self-stabilising property of conditional indexation.

The FR model treats the fund as representative of the whole scheme, not affected by a single pensioner's indexation.

**Parameters from** Davies, Grant & Shapland (2021) *'The USS Trustees' risky strategy'*, [arXiv:2403.08811](https://arxiv.org/abs/2403.08811):
equity mean real return = **4.5%**, equity vol = **17.5%** (base case).

Simulations: {N_SIMS:,} Monte Carlo paths, seed = 42.
""")
