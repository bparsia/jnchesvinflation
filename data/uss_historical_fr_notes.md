# USS Historical Funding Ratio — Data Notes

This file documents the sources, methodology, and uncertainty in the
`uss_historical_fr.csv` dataset used for the "historical scenario" line
in the USS Scenarios page.

---

## What the funding ratio means here

All figures are on a **Technical Provisions (TP)** basis — the statutory
actuarial benchmark used in USS triennial valuations.  This is *not* the
stricter "self-sufficiency" basis sometimes quoted in USS communications.
The CI trigger in the app is modelled as FR ≥ 100% on this TP basis.

---

## Sources by year

| Year | Source | Confidence |
|------|--------|-----------|
| 2008 | USS triennial valuation (31 Mar 2008) | High |
| 2009 | USS annual monitoring estimate | Low — post-GFC equity crash made the funding level very volatile; 74% is a rough estimate |
| 2010 | USS annual monitoring estimate | Low — interpolated from monitoring reports; recovery from 2009 trough |
| 2011 | USS triennial valuation (31 Mar 2011) | High — £2.9bn deficit on TP basis |
| 2012–2013 | Linear interpolation (2011 → 2014) | Low — no formal data; scheme likely stable-ish given contribution increases |
| 2014 | USS triennial valuation (31 Mar 2014) | High — £5.3bn deficit on TP basis |
| 2015–2016 | Linear interpolation (2014 → 2017) | Low |
| 2017 | USS triennial valuation (31 Mar 2017) | Medium — reported deficit varies by source (£5.1bn TP vs higher on SfS basis); underpinned the 2018 dispute |
| 2018–2019 | Linear interpolation (2017 → 2020) | Low |
| 2020 | USS triennial valuation (31 Mar 2020) | High — £14.1bn deficit; assets ~£66.5bn at Dec 2019, liabilities ~£80.6bn |
| 2021 | Estimate | Low — equity recovery but gilt yields still suppressed; pre-gilt-crisis |
| 2022 | Estimate | Medium — USS reported surplus of £1.8bn (>100%) by June 2022 as gilt yields rose sharply |
| 2023 | USS triennial valuation (31 Mar 2023) | High — £7.4bn surplus; assets £73.1bn, liabilities £65.7bn |
| 2024 | USS monitoring report (Mar 2024) | High — £9.2bn surplus, assets £74.8bn |
| 2025 | USS monitoring dashboard (Mar 2025) | High — £10.1bn surplus |

---

## Known limitations

1. **Interpolated years are guesses.** The 2012–2013, 2015–2016, and
   2018–2019 values are linear interpolations with no empirical basis.
   In practice the funding ratio would have varied with equity markets
   and gilt yields.

2. **2009 is speculative.** The 74% figure is based on general knowledge
   of the post-Lehman equity crash, not a USS-published monitoring figure.
   The scheme held a high equity allocation at the time, so a large fall
   is plausible, but the exact figure is unknown.

3. **TP vs SfS.** Different USS documents quote different funding ratios
   for the same date depending on whether TP or self-sufficiency
   assumptions are used. Our model uses 100% as the CI trigger, which
   implicitly corresponds to the TP basis.

4. **Annual vs valuation-date timing.** Triennial valuations are at
   31 March. The annual CI rate applies from the following August.
   We treat the March figure as representative for the full benefit year.

---

## Future work: "Realish" scenarios

Rather than using these estimated/interpolated FR values, a better
historical scenario would be derived from **actual historical asset
class returns** (equities, gilts, corporate bonds) applied to the
USS asset allocation at each point in time.

The CYShapland/USSBriefs2021 repository (Davies, Grant & Shapland 2021)
contains data and R code for this purpose. A future enhancement would:

1. Source annual historical returns for the USS asset mix
   (roughly 67% equities, 33% bonds pre-2018; shifting to lower
   equity post-2018).
2. Derive an implied annual FR path from those returns.
3. Present multiple "realish" scenarios by fuzzing the historical
   time series (e.g., ±N years of history, bootstrap resampling)
   to produce a proper spread around the historical path.

This approach would replace the interpolated estimates with
data-grounded scenarios.

---

## Primary references

- USS triennial valuation reports (2008, 2011, 2014, 2017, 2020, 2023):
  https://www.uss.co.uk/about-us/valuation-and-funding/our-valuations
- Davies, N.M., Grant, J., & Shapland, C.Y. (2021). *The USS Trustees'
  risky strategy.* arXiv:2403.08811
  https://arxiv.org/abs/2403.08811
- Otsuka, M. (2024). *The conditional indexation of USS benefits.*
  Medium / USSBriefs.
  https://mikeotsuka.medium.com/the-conditional-indexation-of-uss-benefits-is-the-most-promising-route-to-their-improvement-538c415b41bf
