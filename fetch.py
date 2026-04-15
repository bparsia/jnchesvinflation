"""
Download UCEA pay settlement PDFs listed in sources/pdf_urls.csv.
  - 'auto' rows: downloaded directly from uceastorage
  - 'manual' rows: copied from data/raw/manual/<manual_filename>
"""
import csv
import shutil
import sys
from pathlib import Path

import requests

SOURCES = Path("sources/pdf_urls.csv")
RAW = Path("data/raw")
MANUAL = RAW / "manual"

RAW.mkdir(parents=True, exist_ok=True)

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; research-scraper/1.0)"}


def dest_path(year: str) -> Path:
    return RAW / f"{year}.pdf"


def main():
    with SOURCES.open() as f:
        rows = list(csv.DictReader(f))

    for row in rows:
        year = row["year"]
        dest = dest_path(year)
        accessible = row["accessible"]
        manual_filename = row.get("manual_filename", "").strip()

        if accessible == "manual":
            if not manual_filename:
                print(f"[skip] {year} — no manual_filename recorded")
                continue
            src = MANUAL / manual_filename
            if not src.exists():
                print(f"[missing] {year} — expected: {src}")
                continue
            if dest.exists():
                print(f"[skip] {year} already copied")
                continue
            shutil.copy2(src, dest)
            print(f"[copy] {year} ← {src.name}")

        elif accessible == "auto":
            if dest.exists():
                print(f"[skip] {year} already downloaded")
                continue
            url = row["url"]
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
