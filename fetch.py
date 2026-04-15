"""
Download UCEA pay settlement PDFs listed in sources/pdf_urls.csv.
Only fetches rows where accessible == 'auto'; skips 'manual' rows with instructions.
"""
import csv
import sys
from pathlib import Path

import requests

SOURCES = Path("sources/pdf_urls.csv")
RAW = Path("data/raw")

RAW.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; research-scraper/1.0)"
}


def filename_for(year: str) -> str:
    return f"{year}.pdf"


def main():
    with SOURCES.open() as f:
        rows = list(csv.DictReader(f))

    auto = [r for r in rows if r["accessible"] == "auto"]
    manual = [r for r in rows if r["accessible"] == "manual"]

    if manual:
        print("The following PDFs require manual download (private storage):")
        for r in manual:
            dest = RAW / filename_for(r["year"])
            print(f"  {r['year']}: {r['url']}")
            print(f"    → save as: {dest}")
        print()

    for row in auto:
        year = row["year"]
        url = row["url"]
        dest = RAW / filename_for(year)
        if dest.exists():
            print(f"[skip] {year} already downloaded")
            continue
        print(f"[fetch] {year} ...", end=" ", flush=True)
        try:
            resp = requests.get(url, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            dest.write_bytes(resp.content)
            print(f"OK ({len(resp.content) // 1024} KB)")
        except Exception as e:
            print(f"FAILED: {e}", file=sys.stderr)

    print("\nDone.")


if __name__ == "__main__":
    main()
