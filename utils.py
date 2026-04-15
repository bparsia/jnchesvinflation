"""Shared data loading and helpers."""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parent
PROCESSED = ROOT / "data" / "processed"
SPINE_CSV = PROCESSED / "spine_points.csv"

# All indices normalised to 2015=100. Annual averages.
# Source: ONS. https://www.ons.gov.uk/economy/inflationandpriceindices

# CPI (CPIH, series D7BT)
CPI = {
    2005: 74.9,
    2006: 76.8,
    2007: 79.0,
    2008: 82.7,
    2009: 83.5,
    2010: 86.4,
    2011: 90.4,
    2012: 93.5,
    2013: 96.1,
    2014: 97.9,
    2015: 100.0,
    2016: 101.0,
    2017: 103.6,
    2018: 106.0,
    2019: 108.0,
    2020: 108.7,
    2021: 111.5,
    2022: 121.3,
    2023: 131.4,
    2024: 135.3,
    2025: 138.0,  # estimate
}

# RPI (All Items, series CHAW), normalised to 2015=100
RPI = {
    2005: 74.3,
    2006: 76.6,
    2007: 79.9,
    2008: 83.1,
    2009: 82.7,
    2010: 86.5,
    2011: 91.0,
    2012: 93.9,
    2013: 96.7,
    2014: 98.9,
    2015: 100.0,
    2016: 101.8,
    2017: 105.1,
    2018: 108.3,
    2019: 111.4,
    2020: 113.2,
    2021: 120.2,
    2022: 136.8,
    2023: 146.3,
    2024: 152.0,
    2025: 156.7,  # estimate
}

INDICES = {"CPI": CPI, "RPI": RPI}

BASE_YEAR = 2024


def _mtime() -> float:
    if SPINE_CSV.exists():
        return SPINE_CSV.stat().st_mtime
    return 0.0


def load_spine_data(mtime: float, measure: str = "CPI") -> pd.DataFrame:  # noqa: ARG001
    df = pd.read_csv(SPINE_CSV)
    df["salary"] = pd.to_numeric(df["salary"], errors="coerce")
    df["spine_point"] = pd.to_numeric(df["spine_point"], errors="coerce")

    # Normalise date strings (strip stray whitespace/newlines from PDF extraction)
    df["effective_date"] = df["effective_date"].str.replace(r"\s+", " ", regex=True).str.strip()

    # Deduplicate: same effective_date + spine_point may appear in multiple PDFs.
    # Values are consistent across PDFs; prefer extracted over derived.
    source_order = {"extracted": 0, "derived": 1}
    if "source" in df.columns:
        df["_sort"] = df["source"].map(source_order).fillna(99)
        df = df.sort_values("_sort").drop_duplicates(
            subset=["effective_date", "spine_point"], keep="first"
        ).drop(columns=["_sort"])
    else:
        df = df.drop_duplicates(subset=["effective_date", "spine_point"], keep="first")

    # Parse effective_date → datetime and extract year
    df["date"] = pd.to_datetime(df["effective_date"], format="%d %B %Y", errors="coerce")
    df["date_year"] = df["date"].dt.year

    # Inflation-adjust to BASE_YEAR using selected index
    index = INDICES[measure]
    base_val = index[BASE_YEAR]
    df["index_val"] = df["date_year"].map(index)
    df["real_salary"] = (df["salary"] * base_val / df["index_val"]).round(0)

    return df.dropna(subset=["salary", "spine_point", "date"])


def get_data(measure: str = "CPI") -> pd.DataFrame:
    return load_spine_data(_mtime(), measure=measure)
