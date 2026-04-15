"""
Extract spine point salary data from downloaded UCEA pay settlement PDFs.
Outputs data/processed/spine_points.csv with columns:
  year, effective_date, spine_point, salary, source

Handles:
  - Bordered tables (pdfplumber extract_tables)
  - Text-based tables ("SINGLE PAY SPINE" heading, whitespace-delimited)
  - Multi-year text tables (2006-09 format with 6 date columns)
  - "Month YYYY" date headers (no day number) → normalised to "1 Month YYYY"
  - Sub-header rows containing only £/% symbols (skipped)
  - Spine point values with suffixes like "2*"
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

MONTHS = {
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december",
}

# Matches "Salary from [1 ]August 2020", "Annual salary value from 1 August 2018", etc.
DATE_HEADER_CELL_RE = re.compile(
    r"(?:salary|annual\s+salary)[^\w]*from\s+(?:\d{1,2}\s+)?(\w+\s+\d{4})",
    re.IGNORECASE | re.DOTALL,
)
VALUE_FROM_RE = re.compile(
    r"(?:value\s+)?from\s+(?:\d{1,2}\s+)?(\w+\s+\d{4})",
    re.IGNORECASE | re.DOTALL,
)

SPINE_HEADING_RE = re.compile(r"SINGLE PAY SPINE", re.IGNORECASE)


def normalise_date(s: str) -> str:
    """Collapse whitespace, strip trailing annotations, add day '1' if absent."""
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"\s*\(.*\)$", "", s).strip()   # strip "(£)" etc.
    # Check the first token is a month name → no day present
    first = s.split()[0].lower() if s else ""
    if first in MONTHS:
        s = "1 " + s
    return s


def parse_salary(s: str) -> int | None:
    s = re.sub(r"[£,\s]", "", str(s))
    try:
        v = int(s)
        return v if 5_000 < v < 300_000 else None
    except ValueError:
        return None


def parse_spine_point(s: str) -> int | None:
    """Parse spine point, tolerating suffixes like '*'."""
    m = re.match(r"^(\d+)", str(s).strip())
    if not m:
        return None
    v = int(m.group(1))
    return v if 1 <= v <= 60 else None


def is_subheader_row(row: list) -> bool:
    """True if every non-empty cell contains only £, %, or whitespace."""
    non_empty = [str(c).strip() for c in row if c and str(c).strip()]
    return bool(non_empty) and all(re.match(r"^[£%\s]+$", c) for c in non_empty)


def find_dates_in_cell(cell: str) -> list[str]:
    dates = []
    for pattern in (DATE_HEADER_CELL_RE, VALUE_FROM_RE):
        m = pattern.search(cell)
        if m:
            d = normalise_date(m.group(1))
            # Validate: second token should be a 4-digit year
            parts = d.split()
            if len(parts) >= 2 and re.match(r"^\d{4}$", parts[-1]):
                dates.append(d)
    return dates


# ---------------------------------------------------------------------------
# Method 1: pdfplumber bordered table extraction
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
                    if not row:
                        continue
                    if is_subheader_row(row):
                        continue
                    if row[0] is None:
                        continue
                    spine = parse_spine_point(row[0])
                    if spine is None:
                        continue
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
# Method 2a: standard text-table parser (one or two date columns)
# ---------------------------------------------------------------------------

DATA_ROW_RE = re.compile(
    r"^(\d{1,2})\*?\s+"      # spine point (optionally starred)
    r"([\d,]+)\s*"            # first salary
    r"([\d,]+)?$"             # optional second salary
)


def extract_via_text(pdf_path: Path) -> list[dict]:
    records = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text or not SPINE_HEADING_RE.search(text):
                continue

            lines = text.splitlines()
            dates: list[str] = []
            in_table = False

            for line in lines:
                stripped = line.strip()

                if not in_table and re.search(
                    r"salary\s+from|value\s+from", stripped, re.IGNORECASE
                ):
                    dates = re.findall(
                        r"(?:\d{1,2}\s+)?\b(?:January|February|March|April|May|June|"
                        r"July|August|September|October|November|December)\b\s+\d{4}",
                        stripped, re.IGNORECASE,
                    )
                    dates = [normalise_date(d) for d in dates]
                    if dates:
                        in_table = True
                    continue

                if not in_table:
                    continue

                m = DATA_ROW_RE.match(stripped)
                if not m:
                    if stripped == "":
                        continue
                    if not re.match(r"^\d", stripped):
                        in_table = False
                    continue

                spine = parse_spine_point(m.group(1))
                if spine is None:
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
# Method 2b: multi-year text-table parser (2006-09 format)
# ---------------------------------------------------------------------------

def parse_month_year_header(salary_line: str, months_line: str, years_line: str) -> list[str]:
    """
    Combine month names and years from the split 2006-09 header:
      'Salary from Salary from ...'
      'Spine August August February August May October'
      'Point 2005 2006 2007 2007 2008 2008 *'
    """
    month_words = [w for w in months_line.split() if w.lower() in MONTHS]
    year_words = [w.strip("*") for w in years_line.split() if re.match(r"^\d{4}[\*]?$", w)]
    return [f"1 {m} {y}" for m, y in zip(month_words, year_words)]


MULTI_SALARY_FROM_RE = re.compile(r"(salary\s+from\s*){2,}", re.IGNORECASE)
# A multi-salary data row: spine_point followed by 3+ salary values
MULTI_DATA_ROW_RE = re.compile(r"^(\d{1,2})\s+((?:[\d,]+\s*){2,})$")


def extract_via_text_multiyear(pdf_path: Path) -> list[dict]:
    records = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text or not SPINE_HEADING_RE.search(text):
                continue

            lines = [l.strip() for l in text.splitlines()]
            dates: list[str] = []
            in_table = False

            i = 0
            while i < len(lines):
                line = lines[i]

                # Detect repeated "Salary from" → multi-year header starts
                if not in_table and MULTI_SALARY_FROM_RE.search(line):
                    # Next two lines should be months and years
                    if i + 2 < len(lines):
                        months_line = lines[i + 1]
                        years_line = lines[i + 2]
                        dates = parse_month_year_header(line, months_line, years_line)
                        if len(dates) >= 2:
                            in_table = True
                            i += 3
                            continue

                if not in_table:
                    i += 1
                    continue

                m = MULTI_DATA_ROW_RE.match(line)
                if not m:
                    if line == "":
                        i += 1
                        continue
                    if not re.match(r"^\d", line):
                        in_table = False
                    i += 1
                    continue

                spine = parse_spine_point(m.group(1))
                if spine is None:
                    i += 1
                    continue

                sal_strings = m.group(2).split()
                for j, sal_str in enumerate(sal_strings):
                    salary = parse_salary(sal_str)
                    if salary is None:
                        continue
                    date_str = dates[j] if j < len(dates) else dates[-1]
                    records.append({
                        "effective_date": date_str,
                        "spine_point": spine,
                        "salary": salary,
                    })
                i += 1

    return records


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

def extract_spine_tables(pdf_path: Path) -> list[dict]:
    records = extract_via_tables(pdf_path)
    if not records:
        records = extract_via_text_multiyear(pdf_path)
    if not records:
        records = extract_via_text(pdf_path)
    return records


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

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

    # Deduplicate by (year, effective_date, spine_point)
    seen = set()
    deduped = []
    for r in all_records:
        key = (r["year"], r["effective_date"], r["spine_point"])
        if key not in seen:
            seen.add(key)
            deduped.append(r)

    fieldnames = ["year", "effective_date", "spine_point", "salary", "source"]
    for r in deduped:
        r.setdefault("source", "extracted")

    with OUT.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(deduped)

    print(f"\nWrote {len(deduped)} records to {OUT}")


if __name__ == "__main__":
    main()
