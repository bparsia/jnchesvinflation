"""
Fill in spine point values for years where the settlement PDF contains only
percentage increases rather than a full salary table.

Covered years:
  2013-14  1 Aug 2013  1% on all points
  2014-15  1 Aug 2014  2% on all points + £60 extra on SP1
  2017-18  1 Aug 2017  1.7% on SP1, SP17-51; specific %s on SP2-16
  2018-19  1 Aug 2018  2% on SP1, SP16-51; +£425 on SP2-15 (override extracted)

Reads data/processed/spine_points.csv (must already exist from extract.py).
Appends derived rows and rewrites the file, adding a 'source' column.
"""
import csv
from pathlib import Path

OUT = Path("data/processed/spine_points.csv")
FIELDNAMES = ["year", "effective_date", "spine_point", "salary", "source"]

# Percentage increases for 2017-18 SP2-16; all others get 1.7%
PCTS_2017_18 = {
    2: 2.43, 3: 2.37, 4: 2.33, 5: 2.29, 6: 2.24,
    7: 2.19, 8: 2.15, 9: 2.10, 10: 2.04, 11: 1.98,
    12: 1.93, 13: 1.87, 14: 1.82, 15: 1.77, 16: 1.72,
}

# Flat £ uplift for 2018-19 SP2-15; all others get 2%
FLAT_2018_19 = {sp: 425 for sp in range(2, 16)}


def apply_pct(salary: int, pct: float) -> int:
    return round(salary * (1 + pct / 100))


def apply_flat(salary: int, uplift: int) -> int:
    return salary + uplift


def load_csv() -> list[dict]:
    with OUT.open() as f:
        return list(csv.DictReader(f))


def as_spine_map(rows: list[dict], effective_date: str) -> dict[int, int]:
    """Return {spine_point: salary} for a given effective_date."""
    return {
        int(r["spine_point"]): int(r["salary"])
        for r in rows
        if r["effective_date"] == effective_date
    }


def make_rows(year: str, effective_date: str, spine_map: dict[int, int],
              source: str = "derived") -> list[dict]:
    return [
        {
            "year": year,
            "effective_date": effective_date,
            "spine_point": sp,
            "salary": sal,
            "source": source,
        }
        for sp, sal in sorted(spine_map.items())
    ]


def main():
    rows = load_csv()

    # Tag existing rows with source=extracted if no source column
    for r in rows:
        r.setdefault("source", "extracted")

    # Build lookup by effective_date
    def get_map(effective_date: str) -> dict[int, int]:
        return as_spine_map(rows, effective_date)

    new_rows: list[dict] = []
    present_dates = {r["effective_date"] for r in rows}

    # -----------------------------------------------------------------------
    # 2013-14: 1% on all 51 points from Aug 2012
    # -----------------------------------------------------------------------
    if "1 August 2013" not in present_dates:
        base = get_map("1 August 2012")
        if not base:
            print("[warn] 2013-14: no Aug 2012 values found, skipping")
        else:
            spine_2013 = {sp: apply_pct(sal, 1.0) for sp, sal in base.items()}
            new_rows.extend(make_rows("2013-14", "1 August 2013", spine_2013))
            print(f"[derive] 2013-14: {len(spine_2013)} points")

    # -----------------------------------------------------------------------
    # 2014-15: 2% on all points + £60 extra on SP1 from Aug 2013
    # -----------------------------------------------------------------------
    if "1 August 2014" not in present_dates:
        # Use freshly derived Aug 2013 if available
        base = as_spine_map(new_rows, "1 August 2013") or get_map("1 August 2013")
        if not base:
            print("[warn] 2014-15: no Aug 2013 values found, skipping")
        else:
            spine_2014 = {}
            for sp, sal in base.items():
                v = apply_pct(sal, 2.0)
                if sp == 1:
                    v += 60
                spine_2014[sp] = v
            new_rows.extend(make_rows("2014-15", "1 August 2014", spine_2014))
            print(f"[derive] 2014-15: {len(spine_2014)} points")

    # -----------------------------------------------------------------------
    # 2017-18: 1.7% base, specific %s for SP2-16 from Aug 2016
    # -----------------------------------------------------------------------
    if "1 August 2017" not in present_dates:
        base = get_map("1 August 2016")
        if not base:
            print("[warn] 2017-18: no Aug 2016 values found, skipping")
        else:
            spine_2017 = {}
            for sp, sal in base.items():
                pct = PCTS_2017_18.get(sp, 1.7)
                spine_2017[sp] = apply_pct(sal, pct)
            new_rows.extend(make_rows("2017-18", "1 August 2017", spine_2017))
            print(f"[derive] 2017-18: {len(spine_2017)} points")

    # -----------------------------------------------------------------------
    # 2018-19: 2% base, +£425 for SP2-15 from Aug 2017.
    # The extract step already captured SP2-15 from the PDF; override with
    # derived SP1 + SP16-51 (2% on 2017 values) and keep PDF values for SP2-15.
    # -----------------------------------------------------------------------
    base_2017 = as_spine_map(new_rows, "1 August 2017") or get_map("1 August 2017")
    existing_2018 = get_map("1 August 2018")

    if base_2017:
        spine_2018 = {}
        for sp, sal in base_2017.items():
            if sp in FLAT_2018_19:
                spine_2018[sp] = apply_flat(sal, FLAT_2018_19[sp])
            else:
                spine_2018[sp] = apply_pct(sal, 2.0)
        # Override with PDF-extracted values where available
        spine_2018.update(existing_2018)
        # Remove old 2018-19 extracted rows and replace with complete set
        rows = [r for r in rows if r["effective_date"] != "1 August 2018"]
        new_rows.extend(make_rows("2018-19", "1 August 2018", spine_2018))
        print(f"[derive] 2018-19: {len(spine_2018)} points (merged extracted+derived)")
    else:
        print("[warn] 2018-19: no Aug 2017 values found, keeping partial extracted data")

    all_rows = rows + new_rows

    # Sort by effective_date then spine_point
    from datetime import datetime
    def sort_key(r: dict) -> tuple:
        try:
            d = datetime.strptime(r["effective_date"], "%d %B %Y")
        except ValueError:
            d = datetime.min
        return (d, int(r["spine_point"]))

    all_rows.sort(key=sort_key)

    with OUT.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"\nWrote {len(all_rows)} total records to {OUT}")


if __name__ == "__main__":
    main()
