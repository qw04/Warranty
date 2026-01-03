from __future__ import annotations

import re
from pathlib import Path
from datetime import date, timedelta
from collections import defaultdict

# ======================================================
# BASE PATH (script lives in warranty/)
# ======================================================
ROOT = Path(__file__).resolve().parent
BASE_DIR = ROOT / "data" / "raw data"

# Optional enforcement of expected years
ENFORCE_YEAR_RANGE = False
YEAR_MIN = 2016
YEAR_MAX = 2025
# ======================================================

FOLDER_RE = re.compile(r"^data_Q([1-4])_(20\d{2})$")
CSV_RE = re.compile(r"^(20\d{2})-(\d{2})-(\d{2})\.csv$", re.IGNORECASE)

def quarter_date_range(y: int, q: int):
    if q == 1:
        return date(y, 1, 1), date(y, 3, 31)
    if q == 2:
        return date(y, 4, 1), date(y, 6, 30)
    if q == 3:
        return date(y, 7, 1), date(y, 9, 30)
    if q == 4:
        return date(y, 10, 1), date(y, 12, 31)
    raise ValueError("Quarter must be 1..4")

def daterange(d0: date, d1: date):
    d = d0
    while d <= d1:
        yield d
        d += timedelta(days=1)

def main():
    if not BASE_DIR.exists():
        raise SystemExit(f"BASE_DIR not found: {BASE_DIR}")

    present_quarters = set()                       # (year, quarter)
    present_dates = defaultdict(set)               # (year, quarter) -> dates
    weird_folders = []
    weird_files = []

    years_found = set()

    for folder in BASE_DIR.iterdir():
        if not folder.is_dir():
            continue

        m = FOLDER_RE.match(folder.name)
        if not m:
            weird_folders.append(folder.name)
            continue

        q = int(m.group(1))
        y = int(m.group(2))
        years_found.add(y)
        present_quarters.add((y, q))

        for f in folder.iterdir():
            if not f.is_file():
                continue

            m2 = CSV_RE.match(f.name)
            if not m2:
                weird_files.append((folder.name, f.name))
                continue

            fy, mm, dd = int(m2.group(1)), int(m2.group(2)), int(m2.group(3))
            try:
                d = date(fy, mm, dd)
            except ValueError:
                weird_files.append((folder.name, f.name))
                continue

            if fy != y:
                weird_files.append((folder.name, f.name))
                continue

            start, end = quarter_date_range(y, q)
            if start <= d <= end:
                present_dates[(y, q)].add(d)
            else:
                weird_files.append((folder.name, f.name))

    if ENFORCE_YEAR_RANGE:
        years_to_check = range(YEAR_MIN, YEAR_MAX + 1)
    else:
        years_to_check = range(min(years_found), max(years_found) + 1)

    print("\n=== Missing quarters ===")
    missing_quarters = [
        (y, q)
        for y in years_to_check
        for q in range(1, 5)
        if (y, q) not in present_quarters and (y, q) != (2025, 4)
    ]
    if not missing_quarters:
        print("None ✅")
    else:
        for y, q in missing_quarters:
            print(f"- data_Q{q}_{y}")

    print("\n=== Missing dates ===")
    any_missing = False
    for y in years_to_check:
        for q in range(1, 5):
            if (y, q) not in present_quarters:
                continue
            start, end = quarter_date_range(y, q)
            expected = set(daterange(start, end))
            got = present_dates.get((y, q), set())
            missing = sorted(expected - got)
            if missing:
                any_missing = True
                print(f"\n[data_Q{q}_{y}] missing {len(missing)} day(s):")
                for d in missing[:20]:
                    print(f"  - {d.isoformat()} ({d.strftime('%d/%m/%Y')})")
                if len(missing) > 20:
                    print(f"  ... and {len(missing) - 20} more")
    if not any_missing:
        print("None ✅")

    print("\n=== Unexpected folder names ===")
    print("\n".join(f"- {x}" for x in weird_folders) if weird_folders else "None ✅")

    print("\n=== Unexpected / invalid files ===")
    if weird_files:
        for folder, file in weird_files[:40]:
            print(f"- {folder}\\{file}")
        if len(weird_files) > 40:
            print(f"... and {len(weird_files)-40} more")
    else:
        print("None ✅")

if __name__ == "__main__":
    main()
