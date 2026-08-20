"""
Fourth pass: turn data/processed/features/*.parquet (~130M rows total) into
small, R-safe inputs. R (via arrow::collect()) materialises everything into
plain in-memory vectors - collecting the full feature table would need far
more RAM than this machine has, so the downsampling has to happen here.

Reads each model's feature parquet ONE AT A TIME (same bounded-memory pattern
as pipeline/02_feature_engineering.py), and produces:

  - data/processed/train_sample.parquet / test_sample.parquet
      For RQ1/RQ2. Drives are split 70/30 by a stable hash of serial_number
      (not a row-level split) so a drive's history never leaks across the
      split. Within each split, ALL positive (fail_within_30d==1) rows are
      kept and negatives are uniformly downsampled at NEG_TO_POS_RATIO:1 -
      standard practice for severe class imbalance. AUC on the downsampled
      test set is still an unbiased estimator of the population AUC (rank
      statistic, invariant to uniform negative subsampling); PR-AUC is NOT
      invariant to class prior, so label_summary.csv's true prevalence should
      be quoted alongside any PR-AUC figure.

  - data/processed/last_observation.parquet
      One row per drive (its most recent observation) for RQ3 clustering -
      no downsampling needed, this is already small (~1 row/drive).

  - data/processed/label_summary.csv
      True (non-downsampled) row/positive counts per model, for reporting
      real-world prevalence alongside metrics computed on the sample.
"""
from __future__ import annotations

import gc
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import PROCESSED_DIR

FEATURES_DIR = PROCESSED_DIR / "features"
NEG_TO_POS_RATIO = 15
TRAIN_FRACTION = 0.7
RANDOM_SEED = 1


def downsample(df: pd.DataFrame) -> pd.DataFrame:
    pos = df[df["fail_within_30d"] == 1]
    neg = df[df["fail_within_30d"] == 0]
    n_neg = min(len(neg), max(len(pos) * NEG_TO_POS_RATIO, 1000))
    neg_sample = neg.sample(n=n_neg, random_state=RANDOM_SEED) if len(neg) > 0 else neg
    return pd.concat([pos, neg_sample], ignore_index=True)


def main():
    files = sorted(FEATURES_DIR.glob("*.parquet"))
    if not files:
        raise SystemExit(f"No feature files in {FEATURES_DIR} - run pipeline/02_feature_engineering.py first")

    train_parts, test_parts, last_obs_parts, summary_rows = [], [], [], []

    for i, f in enumerate(files, 1):
        model = f.stem
        print(f"[{i}/{len(files)}] {model}")
        df = pd.read_parquet(f)

        summary_rows.append({
            "model": model,
            "total_rows": len(df),
            "valid_rows": int(df["label_valid"].sum()),
            "positive_rows": int(df["fail_within_30d"].sum()),
        })

        # --- last observation per drive, for RQ3 clustering ---
        last_obs = df.sort_values("date").groupby("serial_number", as_index=False).tail(1)
        last_obs_parts.append(last_obs.drop(columns=["date", "failure", "fail_within_30d", "label_valid"]))

        # --- train/test split by serial hash, then downsample negatives ---
        valid = df[df["label_valid"] == True].copy()
        h = pd.util.hash_pandas_object(valid["serial_number"].astype(str), index=False)
        is_train = (h % 10) < int(TRAIN_FRACTION * 10)

        train_parts.append(downsample(valid[is_train]))
        test_parts.append(downsample(valid[~is_train]))

        del df, valid, last_obs
        gc.collect()

    print("\nWriting outputs...")
    pd.concat(train_parts, ignore_index=True).to_parquet(PROCESSED_DIR / "train_sample.parquet", index=False)
    pd.concat(test_parts, ignore_index=True).to_parquet(PROCESSED_DIR / "test_sample.parquet", index=False)
    pd.concat(last_obs_parts, ignore_index=True).to_parquet(PROCESSED_DIR / "last_observation.parquet", index=False)
    pd.DataFrame(summary_rows).to_csv(PROCESSED_DIR / "label_summary.csv", index=False)

    summary = pd.DataFrame(summary_rows)
    print(f"\nTrue population: {summary['valid_rows'].sum():,} valid rows, "
          f"{summary['positive_rows'].sum():,} positives "
          f"({100*summary['positive_rows'].sum()/summary['valid_rows'].sum():.5f}%)")
    print("Wrote: train_sample.parquet, test_sample.parquet, last_observation.parquet, label_summary.csv")


if __name__ == "__main__":
    main()
