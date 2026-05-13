import streamlit as st
from branding.branding import BLURB

st.title("About")

st.markdown("""
This app visualises the **JNCHES (Joint Negotiating Committee for Higher Education Staff)**
national pay spine for UK Higher Education, comparing salary values over time adjusted for inflation.

### Data sources

- Pay settlement documents: [UCEA Previous Pay Settlements](https://www.ucea.ac.uk/our-work/collective-pay-negotiations-landing/Previous-Pay-Settlements/)
- Inflation adjustment (CPI): ONS CPIH annual averages (series D7BT), base year 2015=100
- Inflation adjustment (RPI): ONS RPI All Items annual averages (series CHAW), base year 2015=100

### Coverage and missing years

The app currently covers **August 2005 to February 2024** across 22 effective dates.
The table below explains every settlement year's status:

| Year | Effective date(s) | Status | Notes |
|------|-------------------|--------|-------|
| 2006–09 | Aug 2005, Aug 2006, Feb 2007, Aug 2007, May 2008, Oct 2008 | Included | Six-column spine table extracted from PDF |
| 2009–10 | Aug 2009 | Included | Full spine table extracted from PDF |
| 2010–11 | Aug 2010 | Included | Full spine table extracted from PDF |
| 2011–12 | Aug 2011 | Included | Full spine table extracted from PDF |
| 2012–13 | Aug 2012 | Included | Full spine table extracted from PDF |
| 2013–14 | Aug 2013 | Included (derived) | PDF contains no spine table; 1% uplift applied to Aug 2012 values |
| 2014–15 | Aug 2014 | Included (derived) | PDF contains no spine table; 2% uplift applied to Aug 2013 + £60 on SP1 |
| 2015–16 | Aug 2015 | Included | Full spine table extracted from PDF |
| 2016–17 | Aug 2016 | Included | Full spine table extracted from PDF |
| 2017–18 | Aug 2017 | Included (derived) | PDF contains only % increases; applied per-point rates to Aug 2016 values |
| 2018–19 | Aug 2018 | Included (derived) | SP2–15 extracted from PDF; SP1 and SP16–51 derived at 2% on Aug 2017 values |
| 2019–20 | Aug 2019 | Included (partial derived) | SP2–20 extracted from PDF; SP21–51 derived at flat 1.8% on Aug 2018 values |
| 2020–21 | Aug 2020 | Included | Extracted from the 2021–22 PDF (which includes Aug 2020 as base column) |
| 2021–22 | Aug 2021 | Included | Full spine table extracted from PDF |
| 2022–23 | Aug 2022 | Included (partial derived) | SP3–20 extracted from PDF; SP21–51 derived at flat 3% on Aug 2021 values |
| 2023–24 | Aug 2023, Feb 2024 | Included (derived) | PDF contains only % uplifts by range; two-phase derivation applied |
| 2024–25 | Aug 2024, Mar 2025 | **Missing** | Offer letter only — no full spine table available in downloaded PDF |

The spine point numbering also changed over time: SP1 was removed after the 2016–17 settlement,
and SP2 was removed by 2020–21. From Aug 2020 onwards the spine runs SP3–51.

### How to update

```
uv run python fetch.py     # downloads publicly accessible PDFs; copies manual ones
uv run python extract.py   # extracts spine tables from PDFs
uv run python derive.py    # fills gaps using published % increases
uv run streamlit run app.py
```

Manually downloaded PDFs should be placed in `data/raw/manual/` with their original filenames,
then registered in `sources/pdf_urls.csv`.

### Notes on derived values

Where a settlement PDF contained only percentage increases (rather than a full salary table),
values are derived by applying the published rates to the previous year's spine. These
match published tables to within rounding (nearest £1) where cross-checks are possible.
Derived rows are flagged as `source = derived` in the raw data download.

---

*Data: [UCEA](https://www.ucea.ac.uk)*
""")
st.markdown(BLURB)
