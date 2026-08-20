"""
Second pass: build the consolidated drive-day panel for a chosen top-N set of
models (see data/processed/model_summary.csv from scripts/inspect_models.py),
pulling base columns + candidate SMART attributes only, and write one parquet
file per quarter to data/processed/panel/.

Usage:
    python pipeline/01_build_panel.py --top-n 15 --min-failures 15
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import (
    RAW_DIR, PROCESSED_DIR, QUARTER_FOLDERS, BASE_COLUMNS, CANDIDATE_SMART_IDS,
)

PANEL_DIR = PROCESSED_DIR / "panel"


def select_models(top_n: int, min_failures: int) -> list[str]:
    summary_path = PROCESSED_DIR / "model_summary.csv"
    if not summary_path.exists():
        raise SystemExit(f"Run scripts/inspect_models.py first: {summary_path} not found")
    summary = pd.read_csv(summary_path)
    eligible = summary[summary["total_failures"] >= min_failures]
    chosen = eligible.sort_values("avg_daily_population", ascending=False).head(top_n)
    print("Selected models:")
    print(chosen[["model", "avg_daily_population", "distinct_serials", "total_failures"]].to_string(index=False))
    return chosen["model"].tolist()


def smart_columns() -> list[str]:
    cols = []
    for i in CANDIDATE_SMART_IDS:
        cols.append(f"smart_{i}_normalized")
        cols.append(f"smart_{i}_raw")
    return cols


def downcast(df: pd.DataFrame) -> pd.DataFrame:
    for col in df.columns:
        if col in ("date", "serial_number", "model"):
            continue
        if col == "failure":
            df[col] = df[col].astype("int8")
        elif col == "capacity_bytes":
            df[col] = pd.to_numeric(df[col], downcast="integer")
        else:
            df[col] = pd.to_numeric(df[col], downcast="float")
    return df


def build_quarter(qf: str, models: set[str], want_cols: list[str]) -> pd.DataFrame | None:
    folder = RAW_DIR / qf
    if not folder.exists():
        print(f"[SKIP] missing folder: {qf}")
        return None

    frames = []
    csvs = sorted(folder.glob("*.csv"))
    for i, f in enumerate(csvs, 1):
        header = pd.read_csv(f, nrows=0).columns
        usecols = [c for c in want_cols if c in header]
        df = pd.read_csv(f, usecols=usecols)
        df = df[df["model"].isin(models)]
        if df.empty:
            continue
        frames.append(downcast(df))
        if i % 30 == 0:
            print(f"  [{qf}] {i}/{len(csvs)} files")

    if not frames:
        return None
    out = pd.concat(frames, ignore_index=True)
    out["date"] = pd.to_datetime(out["date"])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top-n", type=int, default=15)
    ap.add_argument("--min-failures", type=int, default=15)
    args = ap.parse_args()

    models = set(select_models(args.top_n, args.min_failures))
    want_cols = BASE_COLUMNS + smart_columns()

    PANEL_DIR.mkdir(parents=True, exist_ok=True)
    for qf in QUARTER_FOLDERS:
        out_path = PANEL_DIR / f"{qf}.parquet"
        if out_path.exists():
            print(f"[SKIP existing] {out_path.name}")
            continue
        print(f"\n=== {qf} ===")
        df = build_quarter(qf, models, want_cols)
        if df is None:
            continue
        df.to_parquet(out_path, index=False)
        print(f"  wrote {out_path} ({len(df):,} rows)")

    print("\nDone. Panel parquet files in", PANEL_DIR)


if __name__ == "__main__":
    main()
