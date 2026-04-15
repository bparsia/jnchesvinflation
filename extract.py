"""
Extract spine point salary data from downloaded UCEA pay settlement PDFs.
Outputs data/processed/spine_points.csv with columns:
  year, effective_date, spine_point, salary

Strategy:
  1. Try pdfplumber table extraction (works when PDF has bordered tables).
  2. Fall back to text parsing: find the "SINGLE PAY SPINE" heading, then
     parse the header line for dates and data lines for salaries.
"""
import csv
import re
import sys
from pathlib import Path

import pdfplumber

SOURCES = Path("sources/pdf_urls.csv")
RAW = Path("data/raw")
PROCESSED = Path("data/processed")
OUT = PROCESSED / "spine_points.csv"

PROCESSED.mkdir(parents=True, exist_ok=True)

# Match date phrases like "1 August 2009", "1 October 2008"
DATE_RE = re.compile(r"\d{1,2}\s+\w+\s+\d{4}")

# Match a salary column header cell containing a date
DATE_HEADER_CELL_RE = re.compile(
    r"(?:salary|annual\s+salary)[^\d]*from[^\d]*(\d{1,2}\s+\w+\s+\d{4})",
    re.IGNORECASE | re.DOTALL,
)

# Also match simpler header forms: "value from 1 August 2018"
VALUE_FROM_RE = re.compile(
    r"(?:value\s+)?from\s+(\d{1,2}\s+\w+\s+\d{4})",
    re.IGNORECASE | re.DOTALL,
)


def parse_salary(s: str) -> int | None:
    s = re.sub(r"[£,\s]", "", s)
    try:
        v = int(s)
        return v if 5000 < v < 200000 else None
    except ValueError:
        return None


def normalise_date(s: str) -> str:
    """Collapse whitespace/newlines in a date string."""
    return re.sub(r"\s+", " ", s).strip()


def find_dates_in_cell(cell: str) -> list[str]:
    """Extract date strings from a table header cell."""
    dates = []
    for pattern in (DATE_HEADER_CELL_RE, VALUE_FROM_RE):
        m = pattern.search(cell)
        if m:
            dates.append(normalise_date(m.group(1)))
    return dates


# ---------------------------------------------------------------------------
# Method 1: pdfplumber table extraction
# ---------------------------------------------------------------------------

def extract_via_tables(pdf_path: Path) -> list[dict]:
    records = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            for table in (page.extract_tables() or []):
                if not table or len(table) < 2:
                    continue
                header = table[0]
                date_cols: list[tuple[int, str]] = []
                for col_i, cell in enumerate(header):
                    if cell is None:
                        continue
                    for date_str in find_dates_in_cell(cell):
                        date_cols.append((col_i, date_str))

                if not date_cols:
                    continue

                for row in table[1:]:
                    if not row or row[0] is None:
                        continue
                    sp_str = str(row[0]).strip()
                    if not re.match(r"^\d+$", sp_str):
                        continue
                    spine = int(sp_str)
                    for col_i, date_str in date_cols:
                        if col_i >= len(row) or row[col_i] is None:
                            continue
                        salary = parse_salary(row[col_i])
                        if salary is None:
                            continue
                        records.append({
                            "effective_date": date_str,
                            "spine_point": spine,
                            "salary": salary,
                        })
    return records


# ---------------------------------------------------------------------------
# Method 2: text-based parsing
# ---------------------------------------------------------------------------

SPINE_HEADING_RE = re.compile(r"SINGLE PAY SPINE", re.IGNORECASE)
# A data row: integer, then one or two salary-like numbers (5–6 digits, may
# be comma-formatted like 13,085 or plain like 13085)
DATA_ROW_RE = re.compile(
    r"^(\d{1,2})\s+"           # spine point (1 or 2 digits)
    r"([\d,]+)\s*"             # first salary
    r"([\d,]+)?$"              # optional second salary
)


def extract_via_text(pdf_path: Path) -> list[dict]:
    records = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue
            if not SPINE_HEADING_RE.search(text):
                continue

            lines = text.splitlines()
            dates: list[str] = []
            in_table = False

            for line in lines:
                stripped = line.strip()

                # Header line: contains "Salary from" or similar with a date
                if not in_table and re.search(r"salary\s+from|value\s+from", stripped, re.IGNORECASE):
                    dates = DATE_RE.findall(stripped)
                    if dates:
                        in_table = True
                    continue

                if not in_table:
                    continue

                m = DATA_ROW_RE.match(stripped)
                if not m:
                    # Stop on blank or non-data line (allow continuation)
                    if stripped == "":
                        continue
                    # Any non-numeric first token ends the table
                    if not re.match(r"^\d", stripped):
                        in_table = False
                    continue

                spine = int(m.group(1))
                if spine < 1 or spine > 60:
                    continue

                salaries = [m.group(2)]
                if m.group(3):
                    salaries.append(m.group(3))

                for i, sal_str in enumerate(salaries):
                    salary = parse_salary(sal_str)
                    if salary is None:
                        continue
                    date_str = dates[i] if i < len(dates) else dates[-1]
                    records.append({
                        "effective_date": date_str,
                        "spine_point": spine,
                        "salary": salary,
                    })

    return records


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def extract_spine_tables(pdf_path: Path) -> list[dict]:
    records = extract_via_tables(pdf_path)
    if not records:
        records = extract_via_text(pdf_path)
    return records


def load_years() -> dict[str, str]:
    years = {}
    with SOURCES.open() as f:
        for row in csv.DictReader(f):
            years[row["year"]] = row["year"] + ".pdf"
    return years


def main():
    years = load_years()
    all_records = []

    for year, filename in sorted(years.items()):
        pdf_path = RAW / filename
        if not pdf_path.exists():
            print(f"[skip] {year} — not downloaded")
            continue
        print(f"[extract] {year} ...", end=" ", flush=True)
        try:
            records = extract_spine_tables(pdf_path)
            for r in records:
                r["year"] = year
            all_records.extend(records)
            print(f"{len(records)} rows")
        except Exception as e:
            print(f"FAILED: {e}", file=sys.stderr)

    if not all_records:
        print("No records extracted.", file=sys.stderr)
        sys.exit(1)

    # Deduplicate
    seen = set()
    deduped = []
    for r in all_records:
        key = (r["year"], r["effective_date"], r["spine_point"])
        if key not in seen:
            seen.add(key)
            deduped.append(r)

    fieldnames = ["year", "effective_date", "spine_point", "salary"]
    with OUT.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(deduped)

    print(f"\nWrote {len(deduped)} records to {OUT}")


if __name__ == "__main__":
    main()
