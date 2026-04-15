"""
Fill in spine point values for years where the settlement PDF contains only
percentage increases rather than a full salary table, or where only a partial
table (lower spine points) appears in the PDF.

Covered gaps:
  2013-14   1 Aug 2013  1% on all points (no spine table in PDF)
  2014-15   1 Aug 2014  2% on all points + £60 on SP1 (no spine table in PDF)
  2017-18   1 Aug 2017  1.7% base, specific %s for SP2-16 (no spine table in PDF)
  2018-19   1 Aug 2018  2% base / +£425 for SP2-15 (merges partial extracted)
  2019-20   1 Aug 2019  SP21-51 at 1.8% (PDF only tables SP2-20)
  2022-23   1 Aug 2022  SP21-51 at 3% (PDF only tables SP3-20)
  2023-24a  1 Aug 2023  % by range (SP3-5=8%, SP6-14=7%, SP15-25=6%, SP26+=5%)
  2023-24b  1 Feb 2024  SP3-41 +£1,000; SP42+ +2% on Aug 2023 values

Not derived:
  2024-25   No full spine table or complete uplift schedule in available PDF.

Reads data/processed/spine_points.csv (must exist from extract.py).
Appends/merges derived rows and rewrites the file.
"""
import csv
from datetime import datetime
from pathlib import Path

OUT = Path("data/processed/spine_points.csv")
FIELDNAMES = ["year", "effective_date", "spine_point", "salary", "source"]

# 2017-18: per-point % for SP2-16; all others 1.7%
PCTS_2017_18 = {
    2: 2.43, 3: 2.37, 4: 2.33, 5: 2.29, 6: 2.24,
    7: 2.19, 8: 2.15, 9: 2.10, 10: 2.04, 11: 1.98,
    12: 1.93, 13: 1.87, 14: 1.82, 15: 1.77, 16: 1.72,
}

# 2018-19: £425 flat for SP2-15; all others 2%
FLAT_2018_19 = {sp: 425 for sp in range(2, 16)}


def pct_2023_24a(sp: int) -> float:
    if sp <= 5:   return 8.0
    if sp <= 14:  return 7.0
    if sp <= 25:  return 6.0
    return 5.0


def apply_pct(salary: int, pct: float) -> int:
    return round(salary * (1 + pct / 100))


def apply_flat(salary: int, uplift: int) -> int:
    return salary + uplift


def load_csv() -> list[dict]:
    with OUT.open() as f:
        return list(csv.DictReader(f))


def as_spine_map(rows: list[dict], effective_date: str) -> dict[int, int]:
    return {
        int(r["spine_point"]): int(r["salary"])
        for r in rows
        if r["effective_date"] == effective_date
    }


def make_rows(year: str, date: str, spine_map: dict[int, int],
              source: str = "derived") -> list[dict]:
    return [
        {"year": year, "effective_date": date,
         "spine_point": sp, "salary": sal, "source": source}
        for sp, sal in sorted(spine_map.items())
    ]


def sort_key(r: dict) -> tuple:
    try:
        d = datetime.strptime(r["effective_date"], "%d %B %Y")
    except ValueError:
        d = datetime.min
    return (d, int(r["spine_point"]))


def present_sps(rows: list[dict], date: str) -> set[int]:
    return {int(r["spine_point"]) for r in rows if r["effective_date"] == date}


def main():
    rows = load_csv()
    for r in rows:
        r.setdefault("source", "extracted")

    new_rows: list[dict] = []

    def get_map(date: str) -> dict[int, int]:
        return as_spine_map(rows + new_rows, date)

    def present_dates() -> set[str]:
        return {r["effective_date"] for r in rows + new_rows}

    # -----------------------------------------------------------------------
    # 2013-14: 1% on all points from Aug 2012
    # -----------------------------------------------------------------------
    if "1 August 2013" not in present_dates():
        base = get_map("1 August 2012")
        if base:
            s = {sp: apply_pct(sal, 1.0) for sp, sal in base.items()}
            new_rows.extend(make_rows("2013-14", "1 August 2013", s))
            print(f"[derive] 2013-14 (Aug 2013): {len(s)} points")
        else:
            print("[warn] 2013-14: no Aug 2012 base")

    # -----------------------------------------------------------------------
    # 2014-15: 2% + £60 on SP1 from Aug 2013
    # -----------------------------------------------------------------------
    if "1 August 2014" not in present_dates():
        base = get_map("1 August 2013")
        if base:
            s = {sp: apply_pct(sal, 2.0) + (60 if sp == 1 else 0)
                 for sp, sal in base.items()}
            new_rows.extend(make_rows("2014-15", "1 August 2014", s))
            print(f"[derive] 2014-15 (Aug 2014): {len(s)} points")
        else:
            print("[warn] 2014-15: no Aug 2013 base")

    # -----------------------------------------------------------------------
    # 2017-18: per-point %s from Aug 2016
    # -----------------------------------------------------------------------
    if "1 August 2017" not in present_dates():
        base = get_map("1 August 2016")
        if base:
            s = {sp: apply_pct(sal, PCTS_2017_18.get(sp, 1.7))
                 for sp, sal in base.items()}
            new_rows.extend(make_rows("2017-18", "1 August 2017", s))
            print(f"[derive] 2017-18 (Aug 2017): {len(s)} points")
        else:
            print("[warn] 2017-18: no Aug 2016 base")

    # -----------------------------------------------------------------------
    # 2018-19: 2% base / +£425 for SP2-15, merge with PDF-extracted SP2-15
    # -----------------------------------------------------------------------
    base_2017 = get_map("1 August 2017")
    extracted_2018 = as_spine_map(rows, "1 August 2018")
    if base_2017:
        s = {sp: (apply_flat(sal, FLAT_2018_19[sp]) if sp in FLAT_2018_19
                  else apply_pct(sal, 2.0))
             for sp, sal in base_2017.items()}
        s.update(extracted_2018)   # prefer PDF-extracted values
        rows = [r for r in rows if r["effective_date"] != "1 August 2018"]
        new_rows.extend(make_rows("2018-19", "1 August 2018", s))
        print(f"[derive] 2018-19 (Aug 2018): {len(s)} points (merged extracted+derived)")
    else:
        print("[warn] 2018-19: no Aug 2017 base")

    # -----------------------------------------------------------------------
    # 2019-20: complete SP21-51 at 1.8% on Aug 2018 values
    # (PDF tables only SP2-20 explicitly)
    # -----------------------------------------------------------------------
    have_2019 = present_sps(rows + new_rows, "1 August 2019")
    base_2018 = get_map("1 August 2018")
    if base_2018 and have_2019:
        missing_sps = {sp for sp in base_2018 if sp not in have_2019 and sp >= 2}
        if missing_sps:
            s = {sp: apply_pct(base_2018[sp], 1.8) for sp in missing_sps}
            new_rows.extend(make_rows("2019-20", "1 August 2019", s))
            print(f"[derive] 2019-20 (Aug 2019): +{len(s)} points (SP21-51 at 1.8%)")

    # -----------------------------------------------------------------------
    # 2022-23: complete SP21-51 at 3% on Aug 2021 values
    # (PDF tables only SP3-20 explicitly)
    # -----------------------------------------------------------------------
    have_2022 = present_sps(rows + new_rows, "1 August 2022")
    base_2021 = get_map("1 August 2021")
    if base_2021 and have_2022:
        missing_sps = {sp for sp in base_2021 if sp not in have_2022 and sp >= 3}
        if missing_sps:
            s = {sp: apply_pct(base_2021[sp], 3.0) for sp in missing_sps}
            new_rows.extend(make_rows("2022-23", "1 August 2022", s))
            print(f"[derive] 2022-23 (Aug 2022): +{len(s)} points (SP21-51 at 3%)")

    # -----------------------------------------------------------------------
    # 2023-24 phase 1: % by range from Aug 2022
    # -----------------------------------------------------------------------
    if "1 August 2023" not in present_dates():
        base = get_map("1 August 2022")
        if base:
            s = {sp: apply_pct(sal, pct_2023_24a(sp)) for sp, sal in base.items()}
            new_rows.extend(make_rows("2023-24", "1 August 2023", s))
            print(f"[derive] 2023-24 (Aug 2023): {len(s)} points")
        else:
            print("[warn] 2023-24 phase 1: no Aug 2022 base")

    # -----------------------------------------------------------------------
    # 2023-24 phase 2: SP3-41 +£1,000; SP42+ +2% from Aug 2023
    # -----------------------------------------------------------------------
    if "1 February 2024" not in present_dates():
        base = get_map("1 August 2023")
        if base:
            s = {sp: (apply_flat(sal, 1000) if sp <= 41 else apply_pct(sal, 2.0))
                 for sp, sal in base.items()}
            new_rows.extend(make_rows("2023-24", "1 February 2024", s))
            print(f"[derive] 2023-24 (Feb 2024): {len(s)} points")
        else:
            print("[warn] 2023-24 phase 2: no Aug 2023 base")

    # -----------------------------------------------------------------------
    # 2024-25: no full spine table — skipped
    # -----------------------------------------------------------------------
    print("[skip] 2024-25 — no full spine table in available PDF")

    all_rows = rows + new_rows
    all_rows.sort(key=sort_key)

    with OUT.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"\nWrote {len(all_rows)} total records to {OUT}")


if __name__ == "__main__":
    main()
