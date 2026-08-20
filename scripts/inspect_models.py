"""
Lightweight first pass over the raw daily CSVs (base columns only) to work out,
per drive model, how many drives were observed and how many failures occurred
across the 2021-2022 window. Used to pick a manageable top-N model subset before
loading the full SMART columns in pipeline/01_build_panel.py.

Writes data/processed/model_summary.csv.
"""
from __future__ import annotations

import sys
from pathlib import Path
from collections import defaultdict

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import RAW_DIR, PROCESSED_DIR, QUARTER_FOLDERS, BASE_COLUMNS


def main():
    row_counts = defaultdict(int)
    failure_counts = defaultdict(int)
    serials = defaultdict(set)
    days_seen = defaultdict(set)

    n_files = 0
    for qf in QUARTER_FOLDERS:
        folder = RAW_DIR / qf
        if not folder.exists():
            print(f"[SKIP] missing folder: {qf}")
            continue
        csvs = sorted(folder.glob("*.csv"))
        print(f"[{qf}] {len(csvs)} files")
        for f in csvs:
            n_files += 1
            df = pd.read_csv(f, usecols=BASE_COLUMNS)
            for model, g in df.groupby("model"):
                row_counts[model] += len(g)
                failure_counts[model] += int(g["failure"].sum())
                serials[model].update(g["serial_number"].unique())
                days_seen[model].add(g["date"].iloc[0])
            if n_files % 50 == 0:
                print(f"  ...processed {n_files} files so far")

    rows = []
    for model in row_counts:
        rows.append({
            "model": model,
            "total_drive_days": row_counts[model],
            "distinct_serials": len(serials[model]),
            "days_observed": len(days_seen[model]),
            "avg_daily_population": row_counts[model] / max(len(days_seen[model]), 1),
            "total_failures": failure_counts[model],
        })

    summary = pd.DataFrame(rows).sort_values("avg_daily_population", ascending=False)
    out = PROCESSED_DIR / "model_summary.csv"
    summary.to_csv(out, index=False)
    print(f"\nWrote {out} ({len(summary)} models, {n_files} files processed)")
    print(summary.head(25).to_string(index=False))


if __name__ == "__main__":
    main()
