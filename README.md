# Warranty

## Data-Driven Risk Modelling of Hard Drive Failures for Insurance Pricing

This project uses the Backblaze hard drive dataset to model short-horizon and
lifetime hard drive failure risk, to inform third-party hard drive insurance
pricing. It applies classification, time-series feature engineering,
clustering and regression (the module's core methods) to the risk problem,
with Kaplan-Meier and Cox survival analysis used as supporting tools to
handle censoring and validate the core-method results.

## Research Questions

- **RQ1 (Classification)** - Can early-life SMART attributes and recent SMART
  trends predict whether a drive will fail within the next 30 days?
- **RQ2 (Time series)** - Do rolling time-series SMART features (mean/slope/
  volatility) improve short-horizon prediction over snapshot-only features?
- **RQ3 (Clustering)** - Are there distinct degradation-pattern clusters, and
  do they carry different failure risk (validated via per-cluster KM curves)?
- **RQ4 (Regression)** - How does predicted failure risk translate into
  expected insurance losses across models and coverage durations?
- **Supporting** - Kaplan-Meier and Cox PH analysis, to justify the 30-day
  horizon, handle censoring/left-truncation properly, and cross-check RQ1/3/4.

## Data

Sourced from Backblaze's public hard drive failure data
([webpage](https://www.backblaze.com/cloud-storage/resources/hard-drive-test-data)).
This project uses a **reduced sample: 2021-2022** (8 quarters, ~7.5GB
compressed) rather than the full 2016-2022 range, restricted to the
**top ~15 drive models by population** (with a minimum observed-failure
count) - see `data/processed/model_summary.csv` after running the pipeline.
Full raw data and all processed outputs are gitignored; regenerate with the
pipeline below.

### Known limitations / assumptions

- Enterprise-only, observational population (not consumer usage patterns).
- SMART attribute availability differs by manufacturer; only attributes with
  broad coverage across the selected models are used (see
  `src/config.py:CANDIDATE_SMART_IDS`).
- Drives already in service before 2021-01-01 are left-truncated in calendar
  time; `power_on_hours` (SMART 9) is used as the true age axis instead,
  handled via `Surv(start, stop, event)` in the Cox model.
- RQ4's replacement cost is a simple $/TB proxy (`COST_PER_TB_USD` in
  `analysis/05_rq4_expected_loss.R`), not real manufacturer/retail pricing - swap in
  real figures if available.
- No causal claims: SMART/degradation associations with failure are
  correlational.

## Pipeline

```
1. python fetch_data.py                       # download raw zips -> data/raw_data
2. python scripts/unzip_clean.py               # unzip/flatten/clean -> "data/raw data"
3. python scripts/inspect_models.py             # -> data/processed/model_summary.csv
4. python pipeline/01_build_panel.py            # top-N models -> data/processed/panel/*.parquet
5. python pipeline/02_feature_engineering.py    # -> data/processed/features/*.parquet + event_table.parquet
6. python pipeline/03_prepare_r_inputs.py       # downsampled train/test + last_observation + label_summary (R-safe sizes)
7. Rscript analysis/01_survival_km_cox.R               # supporting KM + Cox
8. Rscript analysis/02_rq1_classification.R            # RQ1
9. Rscript analysis/03_rq2_timeseries_value.R          # RQ2
10. Rscript analysis/04_rq3_clustering.R               # RQ3
11. Rscript analysis/05_rq4_expected_loss.R            # RQ4 (needs cox_simple.rds from step 7)
12. rmarkdown::render("analysis/report.Rmd")           # final report -> analysis/report.html
```

Python dependencies: `pip install -r requirements.txt` (a `.venv` is used -
see `.venv/Scripts/python.exe`). R packages: `survival`, `survminer`,
`dplyr`, `ggplot2`, `arrow`, `cluster`, `factoextra`, `glmnet`, `pROC`,
`PRROC`, `rmarkdown`, `knitr`.

## Tools Used

- Python : data download, cleaning, panel construction, feature engineering
- R : classification, clustering, regression, survival modelling
- RMarkdown : final report
- GitHub : version control and project management
