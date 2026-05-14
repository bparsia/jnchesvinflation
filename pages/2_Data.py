"""Raw data table with filters."""
import streamlit as st
import pandas as pd

from utils import get_data, BASE_YEAR

st.title("Raw Data")

with st.expander("Data coverage and sources"):
    st.markdown("""
### Data sources

- Pay settlement documents: [UCEA Previous Pay Settlements](https://www.ucea.ac.uk/our-work/collective-pay-negotiations-landing/Previous-Pay-Settlements/)
- Inflation adjustment (CPI): ONS CPIH annual averages (series D7BT), base year 2015=100
- Inflation adjustment (RPI): ONS RPI All Items annual averages (series CHAW), base year 2015=100

### Coverage

The dataset covers **August 2005 to February 2024** across 22 effective dates.

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

The spine point numbering changed over time: SP1 was removed after 2016–17, SP2 after 2020–21.
From Aug 2020 onwards the spine runs SP3–51.

### Derived values

Where a settlement PDF contained only percentage increases, values are derived by applying
the published rates to the previous year's spine. These match published tables to within
rounding (nearest £1) where cross-checks are possible. Derived rows are flagged as
`source = derived` in the download.

### How to update

```
uv run python fetch.py     # downloads publicly accessible PDFs; copies manual ones
uv run python extract.py   # extracts spine tables from PDFs
uv run python derive.py    # fills gaps using published % increases
```

Manually downloaded PDFs should be placed in `data/raw/manual/` and registered in `sources/pdf_urls.csv`.
""")

with st.sidebar:
    st.header("Filters")
    measure = st.radio("Inflation measure", ["CPI", "RPI"], horizontal=True)
    st.divider()

try:
    df = get_data(measure=measure)
except FileNotFoundError:
    st.warning("No data found. Run the fetch and extract scripts first.")
    st.stop()

all_points = sorted(df["spine_point"].dropna().unique().astype(int))
all_years = sorted(df["year"].unique())

with st.sidebar:
    selected_points = st.multiselect("Spine points", all_points, default=all_points)
    selected_years = st.multiselect("Settlement year", all_years, default=all_years)

filtered = df[
    df["spine_point"].isin(selected_points) & df["year"].isin(selected_years)
].sort_values(["date", "spine_point"])

display = filtered[[
    "year", "effective_date", "spine_point", "salary", "real_salary"
]].copy()
display.columns = [
    "Settlement year", "Effective date", "Spine point",
    "Nominal salary (£)", f"Real salary (£, {BASE_YEAR} {measure} prices)"
]

st.dataframe(display, width="stretch", hide_index=True)
st.caption(f"{len(display):,} rows")

csv = display.to_csv(index=False)
st.download_button("Download CSV", csv, "jnches_spine_points.csv", "text/csv")
