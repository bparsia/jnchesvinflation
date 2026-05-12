"""USS Pension Indexation Scenarios — stochastic fund model.

Upside modes when the fund is well-funded:
  CPI only  — maintains purchasing power, no real gain
  RPI       — slight real uplift (RPI historically ~0.5–1pp above CPI)
  Returns   — CPI + sharing_fraction × max(0, real portfolio return)
              i.e. DC-like benefit enhancement when the fund does well

Investment returns: log-normal equity (Davies, Grant & Shapland 2021) + deterministic bonds.
Historical CPI/RPI rates drive all indexation calculations.

Soft cap+ proposal: Otsuka (2024)
  https://mikeotsuka.medium.com/the-conditional-indexation-of-uss-benefits-is-the-most-promising-route-to-their-improvement-538c415b41bf
"""
import numpy as np
import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from utils import CPI, RPI
import re

st.markdown("""
<style>
.bjp-note {
    font-family: Georgia, 'Times New Roman', serif;
    font-style: italic;
    background-color: #fdf8f0;
    border-left: 4px solid #c9953a;
    padding: 1rem 1.25rem;
    margin: 1rem 0 1rem 0;
    border-radius: 0 6px 6px 0;
    color: #3d2e10;
    line-height: 1.75;
}
.bjp-note h3 {
    font-style: italic;
    font-weight: bold;
    font-size: 1.15em;
    margin: 0 0 0.5em 0;
    color: #6b4c10;
}
.bjp-note a { color: #8b6914; }
.bjp-note p { margin: 0.5em 0; }
</style>
""", unsafe_allow_html=True)


def bjp(text: str) -> None:
    """Render user editorial text in a distinctive italic serif callout block."""
    t = text.strip()
    t = re.sub(r'^#{1,3} (.+)$', r'<h3>\1</h3>', t, flags=re.MULTILINE)
    t = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', t)
    t = re.sub(r'\*(.+?)\*', r'<em>\1</em>', t)
    t = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2">\1</a>', t)
    paras = re.split(r'\n\s*\n', t)
    html = "".join(
        p.strip() if p.strip().startswith("<h") else f"<p>{p.strip()}</p>"
        for p in paras if p.strip()
    )
    st.markdown(f'<div class="bjp-note">{html}</div>', unsafe_allow_html=True)


st.title("USS Pension: Indexation Scenarios")

bjp("""# WARNING WARNING
This is an experiment with some *very preliminary*, *totally unvetted* modeling. It is not predictive or retrodictive. It is not a financial planning tool. It is intended for education and for expert consideration in negotiations.

"All models are false; some are useful." This, while true, does not mean useful models are useful to everyone.

Probably the most useful aspect is to help get you used to thinking about the riks involved in various indexation schemes and to start thinking about conditional indexation as a *family* of things, not a single thing.

Probably the best place to start is with the [final year outcome head to head](https://jnchesvinflation.streamlit.app/USS_Scenarios#final-year-2025-outcome-distribution) plot. It's the best way to start thinking about different schemes with uncertainty around investment returns.
""")

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
    index=2,
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
    if cpi_pct <= 5.0:    return cpi_pct
    elif cpi_pct <= 15.0: return 5.0 + 0.5 * (cpi_pct - 5.0)
    else:                  return 10.0

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
eq_gross   = np.exp(lmew + lsigma * rng.standard_normal((n_steps, N_SIMS)))
port_gross = eq_sh * eq_gross + (1 - eq_sh) * (1 + b_r)

# Funding ratio paths
FR = np.empty((n_steps + 1, N_SIMS))
FR[0] = initial_fr
FR[1:] = initial_fr * np.cumprod(port_gross, axis=0)

# ---------------------------------------------------------------------------
# Upside rate — what gets paid when sufficiently funded
# Shape: (n_steps, N_SIMS)
# ---------------------------------------------------------------------------
if upside_mode == "CPI only":
    upside = np.broadcast_to(cpi_steps[:, None], (n_steps, N_SIMS)).copy()
elif upside_mode == "RPI":
    upside = np.broadcast_to(rpi_steps[:, None], (n_steps, N_SIMS)).copy()
else:  # Return sharing
    real_ret_pct = (port_gross - 1) * 100
    upside = cpi_steps[:, None] + sharing_fraction * np.maximum(0, real_ret_pct)

funded = FR[:-1] >= 100   # boolean mask (n_steps, N_SIMS)

# ---------------------------------------------------------------------------
# Pension paths
# ---------------------------------------------------------------------------
def cum_pension(step_pct: np.ndarray) -> np.ndarray:
    p = np.empty((n_steps + 1,) if step_pct.ndim == 1 else (n_steps + 1, N_SIMS))
    p[0] = 1000.0
    p[1:] = 1000.0 * np.cumprod(1 + step_pct / 100, axis=0)
    return p

# No indexation
pension_no_idx = np.full(n_steps + 1, 1000.0)

# Soft cap — deterministic, current USS DB promise
pension_sc = cum_pension(sc_steps)

# Soft cap+ (Otsuka 2024): soft cap is the guaranteed floor; CI adds upside when funded.
# Members can never be worse off than current DB. Only upside risk relative to status quo.
sc_plus_steps = np.where(funded, np.maximum(sc_steps[:, None], upside), sc_steps[:, None])
pension_scplus = cum_pension(sc_plus_steps)

# Binary CI: 0% when underfunded; full upside when funded. Hard cliff edge.
bci_steps = np.where(funded, upside, 0.0)
pension_bci = cum_pension(bci_steps)

# Hybrid CI: guaranteed floor always; remainder of upside conditional on funding
guaranteed  = np.minimum(cpi_steps[:, None], hybrid_floor)
conditional = np.where(funded, np.maximum(0.0, upside - guaranteed), 0.0)
pension_hci = cum_pension(guaranteed + conditional)

# Graded CI: proportional 0→CPI below 100% FR; proportional CPI→upside above 100% FR.
# No binary trigger — smooth, no cliff edge.
below = cpi_steps[:, None] * FR[:-1] / 100
above = cpi_steps[:, None] + (upside - cpi_steps[:, None]) * (FR[:-1] - 100) / 100
gci_steps = np.maximum(0.0, np.where(FR[:-1] < 100, below, above))
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

fr_p      = pcts(FR)
scplus_p  = pcts(pension_scplus)
bci_p     = pcts(pension_bci)
hci_p     = pcts(pension_hci)
gci_p     = pcts(pension_gci)

scplus_rp = pcts(pension_scplus * cpi_defl[:, None])
bci_rp    = pcts(pension_bci   * cpi_defl[:, None])
hci_rp    = pcts(pension_hci   * cpi_defl[:, None])
gci_rp    = pcts(pension_gci   * cpi_defl[:, None])

pct_ci_paid = np.mean(funded, axis=1) * 100

COLOURS = {
    "Soft cap":   "#636EFA",
    "Soft cap+":  "#FF6692",
    "Binary CI":  "#EF553B",
    "Hybrid CI":  "#00CC96",
    "Graded CI":  "#AB63FA",
}
GREY = "#888888"
hybrid_label  = f"Hybrid CI (≥{hybrid_floor:.1f}% floor)"

# ---------------------------------------------------------------------------
# Plot helpers
# ---------------------------------------------------------------------------
def add_fan(fig, years, p: dict, colour: str, name: str) -> None:
    fig.add_trace(go.Scatter(x=years, y=p[95], mode="lines", line=dict(width=0),
                             showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=years, y=p[5], mode="lines", line=dict(width=0),
                             fill="tonexty", fillcolor=hex_rgba(colour, 0.10),
                             showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=years, y=p[75], mode="lines", line=dict(width=0),
                             showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=years, y=p[25], mode="lines", line=dict(width=0),
                             fill="tonexty", fillcolor=hex_rgba(colour, 0.22),
                             showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=years, y=p[50], mode="lines+markers", name=name,
                             line=dict(color=colour, width=2),
                             hovertemplate=f"{name}<br>%{{x}}<br>Median: £%{{y:,.0f}}<extra></extra>"))

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------
tab_overview, tab_hh = st.tabs(["Overview", "Head-to-head"])

# ============================================================
# TAB 1: Overview
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
    add_fan(fig_nom, projection_years, scplus_p, COLOURS["Soft cap+"], "Soft cap+")
    add_fan(fig_nom, projection_years, bci_p,    COLOURS["Binary CI"], "Binary CI")
    add_fan(fig_nom, projection_years, hci_p,    COLOURS["Hybrid CI"], hybrid_label)
    add_fan(fig_nom, projection_years, gci_p,    COLOURS["Graded CI"], "Graded CI")
    fig_nom.update_layout(xaxis_title="Year", yaxis_title="Monthly pension (£)",
                          hovermode="x unified", legend_title="Scenario")
    st.plotly_chart(fig_nom, use_container_width=True)

    # --- Funding ratio ---
    st.subheader("Funding ratio over time")
    st.caption(
        f"Starts at {initial_fr}%. {equity_share}% equities, "
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
    st.caption("Fraction of simulations with FR ≥ 100% (right axis: historical CPI).")
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
        hovermode="x unified", legend=dict(x=0.01, y=0.99),
    )
    st.plotly_chart(fig_prob, use_container_width=True)

    # --- Real pension ---
    st.subheader(f"Real monthly pension (£, {start_year} prices)")
    st.caption(
        f"CPI-deflated purchasing power. £1,000 = full protection maintained. "
        f"Values above £1,000 indicate real enhancement "
        f"({'possible' if upside_mode != 'CPI only' else 'not possible'} with upside mode: {upside_mode}). "
        "Soft cap+ floor means it can never fall below the Soft cap line."
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
    add_fan(fig_real, projection_years, scplus_rp, COLOURS["Soft cap+"], "Soft cap+")
    add_fan(fig_real, projection_years, bci_rp,    COLOURS["Binary CI"], "Binary CI")
    add_fan(fig_real, projection_years, hci_rp,    COLOURS["Hybrid CI"], hybrid_label)
    add_fan(fig_real, projection_years, gci_rp,    COLOURS["Graded CI"], "Graded CI")
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
        "Compare scenarios at the **same percentile** — e.g. at the unlucky p25, "
        "which CI type performs best? And see the full spread at the final year."
    )

    # ---- Percentile trajectories ----
    st.subheader("Real pension trajectories at selected percentile")
    pct_options = {
        "5th — worst 5%":        5,
        "25th — lower quartile": 25,
        "50th — median":         50,
        "75th — upper quartile": 75,
        "95th — best 5%":        95,
    }
    pct_label = st.radio(
        "Percentile:", list(pct_options.keys()), index=2, horizontal=True,
        label_visibility="collapsed",
    )
    pct_val = pct_options[pct_label]

    fig_hh = go.Figure()
    fig_hh.add_hline(y=1000, line_dash="dash", line_color="lightgray", line_width=1,
                     annotation_text="Full purchasing power", annotation_position="top left")
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
    for label, rp, colour in [
        ("Soft cap+",  scplus_rp, COLOURS["Soft cap+"]),
        ("Binary CI",  bci_rp,   COLOURS["Binary CI"]),
        (hybrid_label, hci_rp,   COLOURS["Hybrid CI"]),
        ("Graded CI",  gci_rp,   COLOURS["Graded CI"]),
    ]:
        fig_hh.add_trace(go.Scatter(
            x=projection_years, y=rp[pct_val], mode="lines+markers",
            name=label, line=dict(color=colour, width=2),
            hovertemplate=f"{label}<br>%{{x}}<br>£%{{y:,.0f}}<extra></extra>",
        ))
    fig_hh.update_layout(
        title=f"Real pension — {pct_label}",
        xaxis_title="Year",
        yaxis_title=f"Monthly pension (£, {start_year} prices)",
        hovermode="x unified", legend_title="Scenario",
    )
    st.plotly_chart(fig_hh, use_container_width=True)

# ---------------------------------------------------------------------------
# Final year outcome distribution — top-level so anchor links work
# ---------------------------------------------------------------------------
end_year     = projection_years[-1]
end_cpi_defl = cpi_defl[-1]
end_rpi_defl = rpi_defl[-1]

st.subheader(f"Final year ({end_year}) outcome distribution")

bjp("""The first thing to notice is that (if you start in 2009) *all* the deterministic outcomes: No indexation against CPI or RPI or the current "soft cap" (up to 10% of CPI) show loss against historical inflation but that the soft cap *really* mitigates. Without any indexation you lose nearly half your purchacing power. With the soft cap you retain ≈97%. *That's not bad!*

The soft-cap+ option (current soft-cap + CI on returns above inflation) *strictly domainates* the soft cap, as one might expect. It cannot do worse and half the scenarios result in real purchasing power of over twice your initial £1000. I.e., the median sceanrio is £2000 and the high is £4000.

Note that this *only* analyses CI. Indexation is not the only way your benefits could improve. We could augment benefits directly via negotiation. However, when we negotiation benefit increases, *many* uses of that money are on the table including contribution reductions.

The worst for members scheme is "binary CI" wherein basically we look for a funding ratio trigger and either give 0% indexation or full indexation. The downside is essentially no indexation and that's a possible scenario. If we are unlucky, we'd do worse than the soft cap. But we do *better* than the soft cap in ≈78% of the simulations.

The other two forms of CI try to hedge against the extreme downside risk and push the worst case scenario (in our simulations) to pretty close to the soft cap. That gives us some negotiating wiggle room. Soft cap+ is a pure win for us, but offers less to the employers. Hybrid CI, which trades a *lot* of the cap away, is about £100 per £1000 worse in extremis but has similar upsides.

Now members might be extremely risk sensitive so it's soft-cap+ or bust. (And we need to validate the simulations and quantify the uncertainty introduced there.) But if we assume the simulations are pretty good, then we can discuss our risk/reward profile.

Please note that while  this has an *element* of defined contribution (DC) (we, the members, take on some risk) there are a lot of differences with DC. In particularly, unlike a stocks and shares ISA, members are less screwed by market timing. E.g., you never dip into your capital here. You have some insulation from market fluctuations and unwise decision making. OTOH, the fact that you can't lose your retirement fund on a risky investment means you can't double your retirment fund on a risky investment.
""")
st.caption(
    "Each scenario on its own row. Box: 25th–75th percentile; whiskers: 5th–95th. "
    "Deterministic scenarios show as a single line."
)

def box_trace(name, p5, p25, med, p75, p95, colour):
    return go.Box(
        name=name, y=[name], orientation="h",
        q1=[p25], median=[med], q3=[p75],
        lowerfence=[p5], upperfence=[p95],
        marker_color=colour, line_color=colour,
        fillcolor=hex_rgba(colour, 0.3),
        boxpoints=False,
        hovertemplate=(
            f"{name}<br>p5: £%{{lowerfence:,.0f}}<br>Q1: £%{{q1:,.0f}}<br>"
            f"Median: £%{{median:,.0f}}<br>Q3: £%{{q3:,.0f}}<br>"
            f"p95: £%{{upperfence:,.0f}}<extra></extra>"
        ),
    )

def det_box(name, val, colour):
    return box_trace(name, val, val, val, val, val, colour)

fig_box = go.Figure([
    box_trace("Graded CI",
              gci_rp[5][-1], gci_rp[25][-1], gci_rp[50][-1],
              gci_rp[75][-1], gci_rp[95][-1], COLOURS["Graded CI"]),
    box_trace(hybrid_label,
              hci_rp[5][-1], hci_rp[25][-1], hci_rp[50][-1],
              hci_rp[75][-1], hci_rp[95][-1], COLOURS["Hybrid CI"]),
    box_trace("Binary CI",
              bci_rp[5][-1], bci_rp[25][-1], bci_rp[50][-1],
              bci_rp[75][-1], bci_rp[95][-1], COLOURS["Binary CI"]),
    box_trace("Soft cap+",
              scplus_rp[5][-1], scplus_rp[25][-1], scplus_rp[50][-1],
              scplus_rp[75][-1], scplus_rp[95][-1], COLOURS["Soft cap+"]),
    det_box("Soft cap",       pension_sc[-1] * end_cpi_defl, COLOURS["Soft cap"]),
    det_box("No index (RPI)", 1000 * end_rpi_defl,           GREY),
    det_box("No index (CPI)", 1000 * end_cpi_defl,           GREY),
])
fig_box.add_vline(x=1000, line_dash="dash", line_color="lightgray", line_width=1,
                  annotation_text="£1,000", annotation_position="top right")
fig_box.update_layout(
    xaxis_title=f"Monthly pension (£, {start_year} prices)",
    yaxis_title="", showlegend=False, height=460,
)
st.plotly_chart(fig_box, use_container_width=True)

# ---- Quartile summary ----
st.subheader("Quartile summary")
rows = [
    ("No index (CPI)",  {p: 1000 * end_cpi_defl          for p in PERCS}),
    ("No index (RPI)",  {p: 1000 * end_rpi_defl          for p in PERCS}),
    ("Soft cap",        {p: pension_sc[-1] * end_cpi_defl for p in PERCS}),
    ("Soft cap+",       {p: scplus_rp[p][-1]              for p in PERCS}),
    ("Binary CI",       {p: bci_rp[p][-1]                 for p in PERCS}),
    (hybrid_label,      {p: hci_rp[p][-1]                 for p in PERCS}),
    ("Graded CI",       {p: gci_rp[p][-1]                 for p in PERCS}),
]
st.dataframe(
    pd.DataFrame([
        {"Scenario": label,
         "5th %ile": f"£{q[5]:,.0f}", "25th %ile": f"£{q[25]:,.0f}",
         "Median": f"£{q[50]:,.0f}",  "75th %ile": f"£{q[75]:,.0f}",
         "95th %ile": f"£{q[95]:,.0f}"}
        for label, q in rows
    ]).set_index("Scenario"),
    use_container_width=True,
)

# ---------------------------------------------------------------------------
# Expander: model notes
# ---------------------------------------------------------------------------
with st.expander("Model notes & citations"):
    st.markdown(f"""
**Soft cap rule** (current USS DB): full CPI ≤ 5%; 5% + 50%×(CPI−5%) for CPI 5–15%; maximum 10%.

**Soft cap+** — proposed by Michael Otsuka (2024).
The soft cap remains a **guaranteed floor**: indexation can never fall below the current DB soft cap.
When the fund is sufficiently funded, CI adds upside above the soft cap, up to full CPI (or the
selected upside rate). Members face no downside risk relative to current DB provision — only
the prospect of gains.
> Otsuka, M. (2024). *The conditional indexation of USS benefits is the most promising route to
> their improvement.* Medium / USSBriefs.
> [Link](https://mikeotsuka.medium.com/the-conditional-indexation-of-uss-benefits-is-the-most-promising-route-to-their-improvement-538c415b41bf)

**Binary CI**: pays full upside when funded (FR ≥ 100%); 0% when underfunded. Hard cliff edge.

**Hybrid CI**: always pays the guaranteed floor ({hybrid_floor:.1f}%); pays upside (up to selected rate)
when funded. Floor is an arbitrary fixed value rather than the principled soft cap guarantee.

**Graded CI**: proportional — 0% at FR=0%, CPI at FR=100%, upside at FR=200%. No binary trigger.

**Upside mode: {upside_mode}**{"" if upside_mode == "CPI only" else
" — RPI typically ~0.5–1 pp above CPI historically." if upside_mode == "RPI" else
f" — CPI + {sharing_fraction*100:.0f}% of fund's real return. Floor: 0% (no pension cuts)."}

**Funding ratio** evolves as FR_{{t+1}} = FR_t × real portfolio return_t (CPI cancels).
Equity returns are log-normal; parameters from Davies, Grant & Shapland (2021).
> Davies, N.M., Grant, J., & Shapland, C.Y. (2021). *The USS Trustees' risky strategy.*
> [arXiv:2403.08811](https://arxiv.org/abs/2403.08811) / USSBriefs.

USS CI interim modelling report (May 2025):
> USS (2025). *Conditional Indexation — interim report.*
> [uss.co.uk](https://www.uss.co.uk/-/media/project/ussmainsite/files/news-and-views/briefings-and-analysis/interim-conditional-indexation-report-2025.pdf)

{N_SIMS:,} Monte Carlo paths, seed = 42.
""")
