# Common paths + package loads for all r/*.R scripts.
# Run scripts from the project root, e.g.:
#   "C:/Program Files/R/R-4.6.1/bin/Rscript.exe" r/01_survival_km_cox.R

suppressMessages({
  library(arrow)
  library(dplyr)
  library(survival)
  library(survminer)
  library(ggplot2)
})

# Run from the project root (warranty/) so relative paths below resolve.
PROCESSED_DIR <- file.path(getwd(), "data", "processed")
FEATURES_DIR <- file.path(PROCESSED_DIR, "features")  # one parquet file per model
EVENTS_PATH <- file.path(PROCESSED_DIR, "event_table.parquet")
RESULTS_DIR <- file.path(getwd(), "results")
dir.create(RESULTS_DIR, showWarnings = FALSE, recursive = TRUE)

FAILURE_HORIZON_DAYS <- 30

load_events <- function() {
  ev <- arrow::read_parquet(EVENTS_PATH)
  # capacity_bytes comes through as bit64::integer64 (arrow's int64 mapping),
  # which survival::coxph silently mishandles (manifests as "infinite
  # predictor"). Cast to double, and drop Backblaze's -1 sentinel for
  # unknown/missing capacity.
  ev$capacity_bytes <- as.numeric(ev$capacity_bytes)

  # Left-truncated, right-censored time axis in DAYS of drive age, using
  # power-on hours as the true age covariate (robust to drives that already
  # had service life before entering the 2021-2022 observation window).
  ev <- ev %>%
    mutate(
      age_start_days = power_on_hours_first / 24,
      age_stop_days  = power_on_hours_last / 24,
      event = as.integer(failed)
    ) %>%
    filter(
      age_stop_days > age_start_days, !is.na(age_start_days), !is.na(age_stop_days),
      capacity_bytes > 0
    )
  ev
}

## The per-model feature files under FEATURES_DIR total ~130M rows - far more
## than R can safely collect() into memory. pipeline/03_prepare_r_inputs.py
## pre-builds small, already-downsampled/aggregated parquet files for exactly
## this purpose; load those instead of touching FEATURES_DIR directly from R.
load_train_sample <- function() arrow::read_parquet(file.path(PROCESSED_DIR, "train_sample.parquet"))
load_test_sample <- function() arrow::read_parquet(file.path(PROCESSED_DIR, "test_sample.parquet"))
load_last_observation <- function() arrow::read_parquet(file.path(PROCESSED_DIR, "last_observation.parquet"))
load_label_summary <- function() read.csv(file.path(PROCESSED_DIR, "label_summary.csv"))
