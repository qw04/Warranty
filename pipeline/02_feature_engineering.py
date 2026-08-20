"""
Third pass: turn the drive-day panel (data/processed/panel/*.parquet) into a
model-ready feature table.

For every drive-day row this builds:
  - snapshot features: the raw SMART attributes themselves (+ power_on_hours as
    a true age covariate, robust to left-truncation since drives already in
    service before 2021-01-01 still carry their real age in smart_9_raw)
  - time-series features: rolling mean / std / slope over the preceding
    7/30 days, for a narrow high-signal SMART subset (src.config.ROLLING_SMART_IDS)
  - fail_within_30d: forward-looking label for RQ1/RQ2 (1 if the serial's
    failure date falls in (date, date+30d])
  - a `label_valid` flag: False for negative rows within 30 days of the end of
    the observation window, where we can't rule out an unobserved failure
    (right-censoring at the data boundary) - RQ1/RQ2 modelling should filter
    to label_valid == True
  - a per-serial event/censoring table (data/processed/event_table.parquet)
    for the survival analysis (RQ3/RQ4/supporting KM+Cox) in R

The panel is ~130M rows across 15 models - holding it all in memory at once
(even just for a global sort) exceeds a 16GB laptop's RAM. Instead this
processes ONE MODEL AT A TIME: for each model it re-reads only that model's
rows out of each quarter parquet file (pyarrow predicate pushdown), builds
that model's event rows + label + rolling features, writes its own output
parquet, and frees the memory before moving to the next model. This rereads
the quarter files once per model (more disk I/O) in exchange for bounded
peak memory (roughly the largest single model's row count).

Output:
    data/processed/features/<model>.parquet   (one file per model)
    data/processed/event_table.parquet
"""
from __future__ import annotations

import gc
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import PROCESSED_DIR, ROLLING_SMART_IDS, ROLL_WINDOWS, FAILURE_HORIZON_DAYS

PANEL_DIR = PROCESSED_DIR / "panel"
FEATURES_DIR = PROCESSED_DIR / "features"


def safe_name(model: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", model)


def list_quarter_files() -> list[Path]:
    files = sorted(PANEL_DIR.glob("*.parquet"))
    if not files:
        raise SystemExit(f"No panel parquet files found in {PANEL_DIR} - run pipeline/01_build_panel.py first")
    return files


def list_models(files: list[Path]) -> list[str]:
    models = set()
    for f in files:
        col = pd.read_parquet(f, columns=["model"])
        models.update(col["model"].unique().tolist())
    return sorted(models)


def get_max_date(files: list[Path]) -> pd.Timestamp:
    max_date = None
    for f in files:
        col = pd.read_parquet(f, columns=["date"])
        d = pd.to_datetime(col["date"]).max()
        max_date = d if max_date is None else max(max_date, d)
    return max_date


def load_model_frame(files: list[Path], model: str) -> pd.DataFrame:
    frames = []
    for f in files:
        part = pd.read_parquet(f, filters=[("model", "==", model)])
        if not part.empty:
            frames.append(part)
    df = pd.concat(frames, ignore_index=True)
    del frames
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["serial_number", "date"]).reset_index(drop=True)
    df["serial_number"] = df["serial_number"].astype("category")
    return df


def build_event_rows(model_df: pd.DataFrame, max_date: pd.Timestamp) -> pd.DataFrame:
    grp = model_df.groupby("serial_number", observed=True)
    first_seen = grp["date"].min()
    last_seen = grp["date"].max()
    capacity_bytes = grp["capacity_bytes"].first()
    failed = grp["failure"].max().astype(bool)

    age_col = "smart_9_raw"
    power_on_at_first = grp[age_col].first() if age_col in model_df.columns else pd.Series(np.nan, index=first_seen.index)
    power_on_at_last = grp[age_col].last() if age_col in model_df.columns else pd.Series(np.nan, index=first_seen.index)

    events = pd.DataFrame({
        "serial_number": first_seen.index.astype(str),
        "model": model_df["model"].iloc[0],
        "capacity_bytes": capacity_bytes.values,
        "first_seen": first_seen.values,
        "last_seen": last_seen.values,
        "failed": failed.values,
        "power_on_hours_first": power_on_at_first.values,
        "power_on_hours_last": power_on_at_last.values,
    })
    events["observed_days"] = (events["last_seen"] - events["first_seen"]).dt.days + 1
    events["censored"] = ~events["failed"]
    events["censored_at_boundary"] = events["censored"] & (events["last_seen"] >= max_date - pd.Timedelta(days=1))
    return events


def add_forward_label(model_df: pd.DataFrame, max_date: pd.Timestamp) -> pd.DataFrame:
    failure_dates = (
        model_df.loc[model_df["failure"] == 1, ["serial_number", "date"]]
        .rename(columns={"date": "failure_date"})
        .drop_duplicates("serial_number")
    )
    model_df = model_df.merge(failure_dates, on="serial_number", how="left")

    horizon = pd.Timedelta(days=FAILURE_HORIZON_DAYS)
    model_df["fail_within_30d"] = (
        model_df["failure_date"].notna()
        & (model_df["date"] < model_df["failure_date"])
        & (model_df["failure_date"] - model_df["date"] <= horizon)
    ).astype("int8")

    model_df["label_valid"] = (model_df["fail_within_30d"] == 1) | (model_df["date"] <= max_date - horizon)
    model_df = model_df.drop(columns=["failure_date"])
    return model_df


def add_rolling_features(model_df: pd.DataFrame) -> pd.DataFrame:
    raw_cols = [f"smart_{i}_raw" for i in ROLLING_SMART_IDS if f"smart_{i}_raw" in model_df.columns]
    g = model_df.groupby("serial_number", sort=False, observed=True)

    for col in raw_cols:
        for w in ROLL_WINDOWS:
            model_df[f"{col}_roll{w}_mean"] = g[col].transform(
                lambda s: s.rolling(w, min_periods=1).mean()
            ).astype("float32")
            model_df[f"{col}_roll{w}_std"] = g[col].transform(
                lambda s: s.rolling(w, min_periods=2).std()
            ).astype("float32")
        shifted = g[col].shift(ROLL_WINDOWS[-1])
        model_df[f"{col}_slope{ROLL_WINDOWS[-1]}"] = (
            (model_df[col] - shifted) / ROLL_WINDOWS[-1]
        ).astype("float32")

    return model_df


def main():
    files = list_quarter_files()
    print("Scanning for max date and model list (cheap, single-column reads)...")
    max_date = get_max_date(files)
    models = list_models(files)
    print(f"  max_date={max_date.date()}, {len(models)} models")

    FEATURES_DIR.mkdir(parents=True, exist_ok=True)
    events_path = PROCESSED_DIR / "event_table.parquet"
    event_cols = ["serial_number", "model", "capacity_bytes", "date", "failure", "smart_9_raw"]
    event_rows = []

    for i, model in enumerate(models, 1):
        out_path = FEATURES_DIR / f"{safe_name(model)}.parquet"
        if out_path.exists():
            print(f"[{i}/{len(models)}] [SKIP existing features] {model}")
            if not events_path.exists():
                model_df = pd.read_parquet(out_path, columns=event_cols)
                model_df["date"] = pd.to_datetime(model_df["date"])
                event_rows.append(build_event_rows(model_df, max_date))
                del model_df
        else:
            print(f"[{i}/{len(models)}] {model}: loading...")
            model_df = load_model_frame(files, model)
            print(f"    {len(model_df):,} rows, {model_df['serial_number'].nunique():,} serials")

            model_df = add_forward_label(model_df, max_date)
            model_df = add_rolling_features(model_df)
            model_df.to_parquet(out_path, index=False)
            print(f"    wrote {out_path.name}")

            if not events_path.exists():
                event_rows.append(build_event_rows(model_df, max_date))
            del model_df
            gc.collect()

    if events_path.exists():
        print(f"\n[SKIP existing] {events_path}")
    else:
        events = pd.concat(event_rows, ignore_index=True)
        events.to_parquet(events_path, index=False)
        print(f"\nwrote {events_path} ({len(events):,} drives, {events['failed'].sum():,} failures)")

    print(f"\nDone. Feature parquet files in {FEATURES_DIR}")


if __name__ == "__main__":
    main()
