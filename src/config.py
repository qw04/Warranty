from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw data"
PROCESSED_DIR = ROOT / "data" / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

# Reduced sample window (see fetch_data.py)
YEARS = [2021, 2022]
QUARTERS = [1, 2, 3, 4]

QUARTER_FOLDERS = [f"data_Q{q}_{y}" for y in YEARS for q in QUARTERS]

# 30-day short horizon used throughout the RQs (RQ1)
FAILURE_HORIZON_DAYS = 30

# Canonical SMART attributes reported broadly across Seagate / WDC / HGST / Toshiba,
# and repeatedly identified as failure-relevant in Backblaze-based literature.
# Both *_normalized and *_raw are pulled for each; coverage is re-checked empirically
# in scripts/inspect_models.py before features are finalised. Used as snapshot
# features (RQ1) and for the panel's column set.
CANDIDATE_SMART_IDS = [1, 5, 7, 9, 10, 12, 187, 188, 192, 193, 194, 197, 198, 199]

# Narrower subset used for ROLLING time-series feature engineering (RQ2): the
# attributes most consistently identified as failure-predictive in Backblaze-
# based reliability literature (reallocated/pending/uncorrectable sectors,
# command timeouts, and power-on hours for age). Rolling stats multiply the
# column count fast (attrs x windows x stats), so this stays small to keep
# pipeline/02_feature_engineering.py within a laptop's memory budget.
ROLLING_SMART_IDS = [5, 9, 187, 188, 197, 198]
ROLL_WINDOWS = [7, 30]

BASE_COLUMNS = ["date", "serial_number", "model", "capacity_bytes", "failure"]
