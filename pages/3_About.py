import streamlit as st

st.title("About")

st.markdown("""
This app visualises the **JNCHES (Joint Negotiating Committee for Higher Education Staff)**
national pay spine for UK Higher Education, comparing salary values over time adjusted for inflation.

### Data sources

- Pay settlement documents: [UCEA Previous Pay Settlements](https://www.ucea.ac.uk/our-work/collective-pay-negotiations-landing/Previous-Pay-Settlements/)
- Inflation adjustment: ONS CPI annual averages (series D7BT / CPIH), base year 2015=100

### Coverage

Data covers pay settlements from 2009 to the most recent available year.
Some earlier (2006–09) and more recent (2019–present) settlement PDFs are hosted on
private UCEA storage and may require manual download.

### How to update

1. Run `uv run python fetch.py` to download new PDFs
2. Manually save any private PDFs to `data/raw/<year>.pdf`
3. Run `uv run python extract.py` to regenerate `data/processed/spine_points.csv`
4. The app will automatically pick up the new data

### Notes

- Inflation adjustment uses ONS CPIH annual averages. The {BASE_YEAR} figure is an estimate.
- Where a settlement introduced different % increases for lower spine points, the
  actual salary values (as published in the spine table) are used — not derived from percentages.
- The 51-point spine was introduced in 2004 following the Framework Agreement.

---

*Built with [Streamlit](https://streamlit.io) · Data: UCEA · Code: [GitHub](https://github.com)*
""")
