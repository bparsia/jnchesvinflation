"""USS Pension Indexation Scenarios — stochastic fund model.

Upside modes when the fund is well-funded:
  CPI only  — maintains purchasing power, no real gain
  RPI       — slight real uplift (RPI historically ~0.5–1pp above CPI)
  Returns   — CPI + sharing_fraction × max(0, real portfolio return)
              i.e. DC-like benefit enhancement when the fund does well

Investment returns: log-normal equity (Davies, Grant & Shapland 2021) + deterministic bonds.
Historical CPI/RPI rates drive all indexation calculations.
"""
import numpy as np
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

from utils import CPI, RPI

st.title("USS Pension: Indexation Scenarios")
st.markdown(
    "Model what happens to a **£1,000/month pension in payment** under different indexation rules, "
    "using actual historical CPI/RPI and stochastic investment returns. "
    "CI scenarios produce a **distribution** of outcomes depending on whether the fund "
    "outperforms or underperforms each year."
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
)

st.sidebar.divider()
st.sidebar.subheader("Investment returns")
st.sidebar.caption("Parameters from Davies, Grant & Shapland (2021). Equity returns are log-normal.")

equity_share = st.sidebar.slider("Equity allocation (%)", 0, 100, 67, 5)
equity_mean  = st.sidebar.slider("Equity real return — mean (% p.a.)", 0.0, 10.0, 4.5, 0.5)
equity_vol   = st.sidebar.slider("Equity return — volatility (% std dev)", 5.0, 30.0, 17.5, 0.5)
bond_return  = st.sidebar.slider("Bond real return (% p.a.)", -3.0, 5.0, 0.0, 0.5)

st.sidebar.divider()
st.sidebar.subheader("CI parameters")

hybrid_floor = st.sidebar.slider(
    "Hybrid CI — guaranteed floor (%)", 0.0, 5.0, 2.5, 0.5,
    help="Always paid regardless of funding level.",
)

upside_mode = st.sidebar.selectbox(
    "Upside when funded",
    ["CPI only", "RPI", "Return sharing"],
    help=(
        "What CI pays when the fund is sufficiently funded.\n\n"
        "**CPI only** — maintains real value, no enhancement.\n"
        "**RPI** — slight real uplift (RPI ≈ CPI + 0.5–1 pp historically).\n"
        "**Return sharing** — CPI + fraction of the fund's real return, "
        "DC-like benefit enhancement in good years."
    ),
)

sharing_fraction = 1.0
if upside_mode == "Return sharing":
    sharing_fraction = st.sidebar.slider(
        "Return sharing fraction (%)", 10, 100, 100, 10,
        help="What fraction of the fund's real return (above zero) is passed on.",
    ) / 100

N_SIMS = 2000

# ---------------------------------------------------------------------------
# Pure functions
# ---------------------------------------------------------------------------
def soft_cap_rate(cpi_pct: float) -> float:
    if cpi_pct <= 5.0:   return cpi_pct
    elif cpi_pct <= 15.0: return 5.0 + 0.5 * (cpi_pct - 5.0)
    else:                 return 10.0

def yr_rate(index: dict, year: int) -> float:
    if year - 1 not in index: return 0.0
    return (index[year] - index[year - 1]) / index[year - 1] * 100.0

def hex_rgba(col: str, a: float) -> str:
    h = col.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{a})"

# ---------------------------------------------------------------------------
# Data preparation
# ---------------------------------------------------------------------------
projection_years = [y for y in common_years if y >= start_year]
n_steps = len(projection_years) - 1

cpi_steps = np.array([yr_rate(CPI, projection_years[i + 1]) for i in range(n_steps)])
rpi_steps = np.array([yr_rate(RPI, projection_years[i + 1]) for i in range(n_steps)])
sc_steps  = np.array([soft_cap_rate(r) for r in cpi_steps])

# Log-normal equity parameters (real returns, above CPI)
eq_m  = equity_mean / 100
eq_v  = equity_vol  / 100
eq_sh = equity_share / 100
b_r   = bond_return / 100
lmew   = np.log((1 + eq_m)**2 / np.sqrt(eq_v**2 + (1 + eq_m)**2))
lsigma = np.sqrt(np.log(1 + eq_v**2 / (1 + eq_m)**2))

rng = np.random.default_rng(42)
eq_gross   = np.exp(lmew + lsigma * rng.standard_normal((n_steps, N_SIMS)))  # (steps, sims)
port_gross = eq_sh * eq_gross + (1 - eq_sh) * (1 + b_r)                      # real gross return

# Funding ratio paths: FR[t+1] = FR[t] × real_portfolio_return
# (CPI cancels: nominal asset return / CPI liability growth ≈ real return)
FR = np.empty((n_steps + 1, N_SIMS))
FR[0] = initial_fr
FR[1:] = initial_fr * np.cumprod(port_gross, axis=0)

# ---------------------------------------------------------------------------
# Upside rate — what gets paid when fund is sufficiently funded
# Shape: (n_steps, N_SIMS)
# ---------------------------------------------------------------------------
if upside_mode == "CPI only":
    upside = np.broadcast_to(cpi_steps[:, None], (n_steps, N_SIMS)).copy()
elif upside_mode == "RPI":
    upside = np.broadcast_to(rpi_steps[:, None], (n_steps, N_SIMS)).copy()
else:  # Return sharing
    real_ret_pct = (port_gross - 1) * 100                          # real portfolio return %
    upside = cpi_steps[:, None] + sharing_fraction * np.maximum(0, real_ret_pct)

# ---------------------------------------------------------------------------
# Pension paths
# ---------------------------------------------------------------------------
def cum_pension(step_pct: np.ndarray) -> np.ndarray:
    """step_pct: (n_steps,) or (n_steps, N_SIMS) → (n_steps+1, ...) starting at 1000."""
    p = np.empty((n_steps + 1,) if step_pct.ndim == 1 else (n_steps + 1, N_SIMS))
    p[0] = 1000.0
    p[1:] = 1000.0 * np.cumprod(1 + step_pct / 100, axis=0)
    return p

pension_no_idx = np.full(n_steps + 1, 1000.0)
pension_sc     = cum_pension(sc_steps)

# Full CI: 0% when underfunded; upside when funded
fci_steps = np.where(FR[:-1] >= 100, upside, 0.0)
pension_fci = cum_pension(fci_steps)

# Hybrid CI: guaranteed floor always; remainder of upside conditional on funding
guaranteed  = np.minimum(cpi_steps[:, None], hybrid_floor)
conditional = np.where(FR[:-1] >= 100, np.maximum(0.0, upside - guaranteed), 0.0)
pension_hci = cum_pension(guaranteed + conditional)

# Graded CI: proportional 0→CPI below 100% FR; proportional CPI→upside above 100% FR.
# Smooth, no binary trigger. Naturally shares returns when FR is high.
below = cpi_steps[:, None] * FR[:-1] / 100
above = cpi_steps[:, None] + (upside - cpi_steps[:, None]) * (FR[:-1] - 100) / 100
gci_steps = np.where(FR[:-1] < 100, below, above)
gci_steps = np.maximum(0.0, gci_steps)           # no negative indexation
pension_gci = cum_pension(gci_steps)

# Deflation (deterministic historical CPI/RPI)
cpi_defl = np.array([CPI[start_year] / CPI[y] for y in projection_years])
rpi_defl = np.array([RPI[start_year] / RPI[y] for y in projection_years])

# ---------------------------------------------------------------------------
# Percentiles
# ---------------------------------------------------------------------------
PERCS = [5, 25, 50, 75, 95]

def pcts(arr: np.ndarray) -> dict:
    return {p: np.percentile(arr, p, axis=1) for p in PERCS}

fr_p   = pcts(FR)
fci_p  = pcts(pension_fci)
hci_p  = pcts(pension_hci)
gci_p  = pcts(pension_gci)

fci_rp = pcts(pension_fci * cpi_defl[:, None])
hci_rp = pcts(pension_hci * cpi_defl[:, None])
gci_rp = pcts(pension_gci * cpi_defl[:, None])

pct_ci_paid = np.mean(FR[:-1] >= 100, axis=1) * 100  # P(trigger fires) each step

COLOURS = {
    "Soft cap":  "#636EFA",
    "Full CI":   "#EF553B",
    "Hybrid CI": "#00CC96",
    "Graded CI": "#AB63FA",
}
GREY = "#888888"
hybrid_label = f"Hybrid CI (≥{hybrid_floor:.1f}% floor)"

# ---------------------------------------------------------------------------
# Plot helpers
# ---------------------------------------------------------------------------
def add_fan(fig, years, p: dict, colour: str, name: str, row=None, col=None) -> None:
    kw = dict(row=row, col=col) if row else {}
    fig.add_trace(go.Scatter(x=years, y=p[95], mode="lines", line=dict(width=0),
                             showlegend=False, hoverinfo="skip"), **kw)
    fig.add_trace(go.Scatter(x=years, y=p[5], mode="lines", line=dict(width=0),
                             fill="tonexty", fillcolor=hex_rgba(colour, 0.10),
                             showlegend=False, hoverinfo="skip"), **kw)
    fig.add_trace(go.Scatter(x=years, y=p[75], mode="lines", line=dict(width=0),
                             showlegend=False, hoverinfo="skip"), **kw)
    fig.add_trace(go.Scatter(x=years, y=p[25], mode="lines", line=dict(width=0),
                             fill="tonexty", fillcolor=hex_rgba(colour, 0.22),
                             showlegend=False, hoverinfo="skip"), **kw)
    fig.add_trace(go.Scatter(x=years, y=p[50], mode="lines+markers", name=name,
                             line=dict(color=colour, width=2),
                             hovertemplate=f"{name}<br>%{{x}}<br>Median: £%{{y:,.0f}}<extra></extra>"),
                  **kw)

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------
tab_overview, tab_hh = st.tabs(["Overview", "Head-to-head"])

# ============================================================
# TAB 1: Overview — fan charts
# ============================================================
with tab_overview:
    # --- Nominal ---
    st.subheader("Nominal monthly pension (£)")
    st.caption("Bands: 5th–95th and 25th–75th percentile across simulated market histories.")

    fig_nom = go.Figure()
    fig_nom.add_trace(go.Scatter(
        x=projection_years, y=pension_no_idx, mode="lines", name="No indexation",
        line=dict(color=GREY, width=2, dash="dot"),
        hovertemplate="No indexation<br>%{x}<br>£1,000/month<extra></extra>",
    ))
    fig_nom.add_trace(go.Scatter(
        x=projection_years, y=pension_sc, mode="lines+markers", name="Soft cap",
        line=dict(color=COLOURS["Soft cap"], width=2),
        hovertemplate="Soft cap<br>%{x}<br>£%{y:,.0f}<extra></extra>",
    ))
    add_fan(fig_nom, projection_years, fci_p, COLOURS["Full CI"], "Full CI")
    add_fan(fig_nom, projection_years, hci_p, COLOURS["Hybrid CI"], hybrid_label)
    add_fan(fig_nom, projection_years, gci_p, COLOURS["Graded CI"], "Graded CI")
    fig_nom.update_layout(xaxis_title="Year", yaxis_title="Monthly pension (£)",
                          hovermode="x unified", legend_title="Scenario")
    st.plotly_chart(fig_nom, use_container_width=True)

    # --- Funding ratio ---
    st.subheader("Funding ratio over time")
    st.caption(
        f"Starts at {initial_fr}%. Stochastic: {equity_share}% equities, "
        f"mean real return {equity_mean:.1f}%, vol {equity_vol:.1f}%. "
        "CI trigger fires when FR ≥ 100%."
    )
    fig_fr = go.Figure()
    fig_fr.add_hline(y=100, line_dash="dash", line_color="lightgray", line_width=1,
                     annotation_text="100% trigger", annotation_position="top left")
    add_fan(fig_fr, projection_years, fr_p, "#FFA15A", "Funding ratio")
    fig_fr.update_layout(xaxis_title="Year", yaxis_title="Funding ratio (%)",
                         showlegend=False, yaxis=dict(ticksuffix="%"))
    st.plotly_chart(fig_fr, use_container_width=True)

    # --- P(CI fires) ---
    st.subheader("P(CI trigger fires) by year")
    st.caption("Bar: fraction of simulations where FR ≥ 100%. Line: historical CPI rate (right axis).")
    fig_prob = go.Figure()
    fig_prob.add_trace(go.Bar(
        x=projection_years[1:], y=pct_ci_paid, marker_color="#FFA15A",
        hovertemplate="%{x}<br>P(CI): %{y:.1f}%<extra></extra>",
    ))
    fig_prob.add_trace(go.Scatter(
        x=projection_years[1:], y=cpi_steps, mode="lines+markers",
        name="CPI rate", line=dict(color=GREY, width=1.5, dash="dot"),
        yaxis="y2", hovertemplate="%{x}<br>CPI: %{y:.1f}%<extra></extra>",
    ))
    fig_prob.update_layout(
        xaxis_title="Year",
        yaxis=dict(title="P(trigger, %)", range=[0, 100], ticksuffix="%"),
        yaxis2=dict(title="CPI (%)", overlaying="y", side="right",
                    range=[0, max(cpi_steps) * 2.2]),
        hovermode="x unified",
        legend=dict(x=0.01, y=0.99),
    )
    st.plotly_chart(fig_prob, use_container_width=True)

    # --- Real pension ---
    st.subheader(f"Real monthly pension (£, {start_year} prices)")
    st.caption(
        f"CPI-deflated purchasing power. £1,000 = full protection. "
        f"Values **above** £1,000 indicate real enhancement "
        f"({'possible' if upside_mode != 'CPI only' else 'not possible'} with current upside mode: {upside_mode})."
    )
    fig_real = go.Figure()
    fig_real.add_hline(y=1000, line_dash="dash", line_color="lightgray", line_width=1,
                       annotation_text="Full purchasing power", annotation_position="top left")
    fig_real.add_trace(go.Scatter(
        x=projection_years, y=1000 * cpi_defl, mode="lines", name="No index (CPI eroded)",
        line=dict(color=GREY, width=2, dash="solid"),
        hovertemplate="No index (CPI)<br>%{x}<br>£%{y:,.0f}<extra></extra>",
    ))
    fig_real.add_trace(go.Scatter(
        x=projection_years, y=1000 * rpi_defl, mode="lines", name="No index (RPI eroded)",
        line=dict(color=GREY, width=2, dash="dot"),
        hovertemplate="No index (RPI)<br>%{x}<br>£%{y:,.0f}<extra></extra>",
    ))
    fig_real.add_trace(go.Scatter(
        x=projection_years, y=pension_sc * cpi_defl, mode="lines+markers", name="Soft cap",
        line=dict(color=COLOURS["Soft cap"], width=2),
        hovertemplate="Soft cap<br>%{x}<br>£%{y:,.0f}<extra></extra>",
    ))
    add_fan(fig_real, projection_years, fci_rp, COLOURS["Full CI"], "Full CI")
    add_fan(fig_real, projection_years, hci_rp, COLOURS["Hybrid CI"], hybrid_label)
    add_fan(fig_real, projection_years, gci_rp, COLOURS["Graded CI"], "Graded CI")
    fig_real.update_layout(
        xaxis_title="Year",
        yaxis_title=f"Monthly pension (£, {start_year} prices)",
        hovermode="x unified", legend_title="Scenario",
    )
    st.plotly_chart(fig_real, use_container_width=True)

# ============================================================
# TAB 2: Head-to-head
# ============================================================
with tab_hh:
    st.markdown(
        "Compare scenarios directly at the **same percentile** — e.g. how does Full CI compare "
        "to Graded CI for the unlucky 25%? And see the full outcome distribution at retirement end."
    )

    # ---- Percentile trajectory ----
    st.subheader("Real pension trajectories at selected percentile")

    pct_options = {
        "5th — worst 5% of outcomes":      5,
        "25th — lower quartile":           25,
        "50th — median":                   50,
        "75th — upper quartile":           75,
        "95th — best 5% of outcomes":      95,
    }
    pct_label = st.radio(
        "Percentile to compare across scenarios:",
        list(pct_options.keys()), index=2, horizontal=True,
        label_visibility="collapsed",
    )
    pct_val = pct_options[pct_label]

    fig_hh = go.Figure()
    fig_hh.add_hline(y=1000, line_dash="dash", line_color="lightgray", line_width=1,
                     annotation_text="Full purchasing power", annotation_position="top left")

    # Deterministic scenarios (same regardless of percentile)
    fig_hh.add_trace(go.Scatter(
        x=projection_years, y=1000 * cpi_defl, mode="lines",
        name="No index (CPI)", line=dict(color=GREY, width=2, dash="solid"),
        hovertemplate="No index (CPI)<br>%{x}<br>£%{y:,.0f}<extra></extra>",
    ))
    fig_hh.add_trace(go.Scatter(
        x=projection_years, y=1000 * rpi_defl, mode="lines",
        name="No index (RPI)", line=dict(color=GREY, width=2, dash="dot"),
        hovertemplate="No index (RPI)<br>%{x}<br>£%{y:,.0f}<extra></extra>",
    ))
    fig_hh.add_trace(go.Scatter(
        x=projection_years, y=pension_sc * cpi_defl, mode="lines+markers",
        name="Soft cap", line=dict(color=COLOURS["Soft cap"], width=2),
        hovertemplate="Soft cap<br>%{x}<br>£%{y:,.0f}<extra></extra>",
    ))

    # Stochastic scenarios at selected percentile
    for label, rp, colour in [
        ("Full CI",     fci_rp, COLOURS["Full CI"]),
        (hybrid_label,  hci_rp, COLOURS["Hybrid CI"]),
        ("Graded CI",   gci_rp, COLOURS["Graded CI"]),
    ]:
        fig_hh.add_trace(go.Scatter(
            x=projection_years, y=rp[pct_val], mode="lines+markers",
            name=label, line=dict(color=colour, width=2),
            hovertemplate=f"{label} ({pct_label[:3]}th)<br>%{{x}}<br>£%{{y:,.0f}}<extra></extra>",
        ))

    fig_hh.update_layout(
        title=f"Real pension — {pct_label}",
        xaxis_title="Year",
        yaxis_title=f"Monthly pension (£, {start_year} prices)",
        hovermode="x unified", legend_title="Scenario",
    )
    st.plotly_chart(fig_hh, use_container_width=True)

    # ---- Final year distribution ----
    st.subheader(f"Final year ({projection_years[-1]}) outcome distribution")
    st.caption(
        "Horizontal box plots show the spread of real pension outcomes. "
        "Whiskers = 5th–95th percentile. Soft cap and no-indexation are single values."
    )

    end_cpi_defl = cpi_defl[-1]
    end_rpi_defl = rpi_defl[-1]

    fig_box = go.Figure()

    # Stochastic scenarios — raw simulation data → Plotly computes quartiles
    for label, pension_arr, colour in [
        ("Graded CI",   pension_gci, COLOURS["Graded CI"]),
        (hybrid_label,  pension_hci, COLOURS["Hybrid CI"]),
        ("Full CI",     pension_fci, COLOURS["Full CI"]),
    ]:
        real_vals = pension_arr[-1] * end_cpi_defl
        fig_box.add_trace(go.Box(
            x=real_vals,
            name=label,
            orientation="h",
            marker_color=colour,
            boxpoints=False,
            q1=[np.percentile(real_vals, 25)],
            median=[np.percentile(real_vals, 50)],
            q3=[np.percentile(real_vals, 75)],
            lowerfence=[np.percentile(real_vals, 5)],
            upperfence=[np.percentile(real_vals, 95)],
        ))

    # Deterministic scenarios — single vertical line markers
    for label, val in [
        ("Soft cap",          pension_sc[-1] * end_cpi_defl),
        ("No index (RPI)",    1000 * end_rpi_defl),
        ("No index (CPI)",    1000 * end_cpi_defl),
    ]:
        colour = COLOURS.get("Soft cap") if "Soft" in label else GREY
        fig_box.add_trace(go.Scatter(
            x=[val], y=[label], mode="markers",
            marker=dict(color=colour, size=14, symbol="diamond"),
            name=label, showlegend=False,
            hovertemplate=f"{label}<br>£%{{x:,.0f}}<extra></extra>",
        ))

    fig_box.add_vline(x=1000, line_dash="dash", line_color="lightgray", line_width=1,
                      annotation_text="£1,000", annotation_position="top")
    fig_box.update_layout(
        xaxis_title=f"Monthly pension (£, {start_year} prices)",
        yaxis_title="",
        showlegend=False,
        height=350,
    )
    st.plotly_chart(fig_box, use_container_width=True)

    # ---- Quartile summary table ----
    st.subheader("Quartile summary")
    end_year = projection_years[-1]
    rows = []
    for label, rp in [
        ("No index (CPI)",  {p: 1000 * end_cpi_defl for p in PERCS}),
        ("No index (RPI)",  {p: 1000 * end_rpi_defl for p in PERCS}),
        ("Soft cap",        {p: pension_sc[-1] * end_cpi_defl for p in PERCS}),
        ("Full CI",         {p: fci_rp[p][-1] for p in PERCS}),
        (hybrid_label,      {p: hci_rp[p][-1] for p in PERCS}),
        ("Graded CI",       {p: gci_rp[p][-1] for p in PERCS}),
    ]:
        rows.append({
            "Scenario": label,
            "5th %ile": f"£{rp[5]:,.0f}",
            "25th %ile": f"£{rp[25]:,.0f}",
            "Median": f"£{rp[50]:,.0f}",
            "75th %ile": f"£{rp[75]:,.0f}",
            "95th %ile": f"£{rp[95]:,.0f}",
        })
    st.dataframe(pd.DataFrame(rows).set_index("Scenario"), use_container_width=True)

# ---------------------------------------------------------------------------
# Expanders (outside tabs)
# ---------------------------------------------------------------------------
with st.expander("Model notes"):
    st.markdown(f"""
**Soft cap rule**: full CPI ≤ 5%; 5% + 50%×(CPI−5%) for CPI 5–15%; maximum 10%.

**Upside mode: {upside_mode}**
{"CPI only — real value maintained at £1,000 when funded, no enhancement." if upside_mode == "CPI only" else
 "RPI — slight real uplift when funded, as RPI historically runs ~0.5–1 pp above CPI." if upside_mode == "RPI" else
 f"Return sharing ({sharing_fraction*100:.0f}%) — when funded, pensioner receives CPI + {sharing_fraction*100:.0f}% of the fund's real return. In a year with 5% real portfolio return and 3% CPI, indexation = 3% + {sharing_fraction*100:.0f}%×5% = {3 + sharing_fraction*5:.1f}%. The floor is 0% — poor returns suppress CI but don't cut the pension."}

**Graded CI** scales linearly from 0% (FR=0%) through CPI (FR=100%) to the upside rate (FR=200%).
No binary trigger — the CI payment grows smoothly with funding health and naturally shares
upside returns without a separate threshold.

**Funding ratio** evolves in real terms: FR_{{t+1}} = FR_t × real portfolio return_t.
CPI cancels between nominal asset returns and CPI liability growth.
All {N_SIMS:,} Monte Carlo paths use seed 42.

**Parameters** from Davies, Grant & Shapland (2021), [arXiv:2403.08811](https://arxiv.org/abs/2403.08811).
""")
