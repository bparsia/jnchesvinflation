"""Shared data loading and helpers."""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parent
PROCESSED = ROOT / "data" / "processed"
SPINE_CSV = PROCESSED / "spine_points.csv"

# UK CPI annual averages (2015=100 base, extended to 2025).
# Source: ONS series D7BT / CPIH. Values are annual averages.
# https://www.ons.gov.uk/economy/inflationandpriceindices
CPI = {
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

BASE_YEAR = 2024


def _mtime() -> float:
    if SPINE_CSV.exists():
        return SPINE_CSV.stat().st_mtime
    return 0.0


def load_spine_data(mtime: float) -> pd.DataFrame:  # noqa: ARG001 (mtime used as cache key)
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

    # Inflation-adjust to BASE_YEAR
    base_cpi = CPI[BASE_YEAR]
    df["cpi"] = df["date_year"].map(CPI)
    df["real_salary"] = (df["salary"] * base_cpi / df["cpi"]).round(0).astype("Int64")

    return df.dropna(subset=["salary", "spine_point", "date"])


def get_data() -> pd.DataFrame:
    return load_spine_data(_mtime())
