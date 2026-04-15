import streamlit as st

st.title("About")

st.markdown("""
This app visualises the **JNCHES (Joint Negotiating Committee for Higher Education Staff)**
national pay spine for UK Higher Education, comparing salary values over time adjusted for inflation.

### Data sources

- Pay settlement documents: [UCEA Previous Pay Settlements](https://www.ucea.ac.uk/our-work/collective-pay-negotiations-landing/Previous-Pay-Settlements/)
- Inflation adjustment: ONS CPI annual averages (series D7BT / CPIH), base year 2015=100

### Coverage and missing years

The app currently covers **October 2008 to August 2018**. The table below explains every year's status:

| Year | Effective date | Status | Notes |
|------|---------------|--------|-------|
| 2006–09 | Aug 2006, Aug 2007, Aug 2008 | **Missing** | PDF hosted on private UCEA storage; requires manual download |
| 2009–10 | Oct 2008, Aug 2009 | Included | Full spine table extracted from PDF |
| 2010–11 | Aug 2010 | Included | Full spine table extracted from PDF |
| 2011–12 | Aug 2011 | Included | Full spine table extracted from PDF |
| 2012–13 | Aug 2012 | Included | Full spine table extracted from PDF |
| 2013–14 | Aug 2013 | Included (derived) | PDF contains no spine table; values calculated as 1% uplift on Aug 2012 |
| 2014–15 | Aug 2014 | Included (derived) | PDF contains no spine table; values calculated as 2% uplift on Aug 2013 + £60 on SP1 |
| 2015–16 | Aug 2015 | Included | Full spine table extracted from PDF |
| 2016–17 | Aug 2016 | Included | Full spine table extracted from PDF |
| 2017–18 | Aug 2017 | Included (derived) | PDF contains only % increases; values derived from Aug 2016 using published rates |
| 2018–19 | Aug 2018 | Included (derived) | PDF only lists SP2–15; SP1 and SP16–51 derived as 2% on Aug 2017 values |
| 2019–20 | Aug 2019 | **Missing** | PDF hosted on private UCEA storage; requires manual download |
| 2020–21 | Aug 2020 | **Missing** | PDF hosted on private UCEA storage; requires manual download |
| 2021–22 | Aug 2021 | **Missing** | PDF hosted on private UCEA storage; requires manual download |
| 2022–23 | Aug 2022 | **Missing** | PDF hosted on private UCEA storage; requires manual download |
| 2023–24 | Feb & Aug 2023 | **Missing** | PDF hosted on private UCEA storage; requires manual download |
| 2024–25 | Aug 2024, Mar 2025 | **Missing** | PDF hosted on private UCEA storage; requires manual download |

Missing years can be added by downloading the relevant PDFs from the UCEA website
(login may be required), saving them to `data/raw/<year>.pdf`, and re-running the pipeline.

### How to update

```
uv run python fetch.py     # downloads publicly accessible PDFs
uv run python extract.py   # extracts spine tables from PDFs
uv run python derive.py    # fills gaps using published % increases
uv run streamlit run app.py
```

### Notes on derived values

Where a settlement PDF contained only percentage increases (rather than a full salary table),
values are derived by applying the published rates to the previous year's spine. These
match the published tables to within rounding (nearest £1) where cross-checks are possible.
Derived rows are flagged as `source = derived` in the raw data download.

---

*Built with [Streamlit](https://streamlit.io) · Data: [UCEA](https://www.ucea.ac.uk)*
""")
