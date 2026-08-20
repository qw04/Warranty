# RQ4 - Translate survival-model failure risk into expected insurance losses
# across models and coverage durations, and characterise how expected loss
# scales with coverage length (linear/multilinear regression).
source("r/00_setup.R")

## No public replacement-cost data exists for this dataset, so a simple cost
## proxy is used and clearly flagged as an assumption: $X per TB of capacity.
## Swap this for real manufacturer/retail pricing if available.
COST_PER_TB_USD <- 25

events <- load_events()
cox_simple <- readRDS(file.path(RESULTS_DIR, "cox_simple.rds"))

COVERAGE_DAYS <- c(30, 90, 180, 365, 545, 730)  # 1mo .. 2yr contracts
models_present <- levels(factor(events$model))

## Model-specific capacity (each model ships at essentially one fixed
## capacity - see r/01_survival_km_cox.R), so replacement cost is tied to the
## actual drive rather than a single dataset-wide median.
capacity_by_model <- events %>%
  group_by(model) %>%
  summarise(capacity_bytes = median(capacity_bytes, na.rm = TRUE), .groups = "drop")

newdata <- data.frame(model = models_present)

## Predicted survival curve per model, starting a fresh (age-0) warranty clock
sf <- survfit(cox_simple, newdata = newdata)

loss_table <- expand.grid(model = models_present, coverage_days = COVERAGE_DAYS, stringsAsFactors = FALSE)
loss_table <- loss_table %>% left_join(capacity_by_model, by = "model")
loss_table$capacity_tb <- loss_table$capacity_bytes / 1e12
loss_table$replacement_cost_usd <- loss_table$capacity_tb * COST_PER_TB_USD

## step-function survival probability at each requested coverage length, per model column
loss_table$p_fail_within_coverage <- mapply(function(m, d) {
  col <- which(models_present == m)
  row_idx <- findInterval(d, sf$time)
  if (row_idx < 1) return(0)
  1 - sf$surv[row_idx, col]
}, loss_table$model, loss_table$coverage_days)

loss_table$expected_loss_usd <- loss_table$p_fail_within_coverage * loss_table$replacement_cost_usd

cat("Expected loss table (head):\n")
print(head(loss_table, 12))

## --- Regression: how does expected loss scale with coverage length? -------
loss_reg <- lm(expected_loss_usd ~ coverage_days + I(coverage_days^2) + model, data = loss_table)
cat("\n=== RQ4 regression: expected loss ~ coverage length + model ===\n")
print(summary(loss_reg))

p_loss <- ggplot(loss_table, aes(x = coverage_days, y = expected_loss_usd, color = model)) +
  geom_line() + geom_point() +
  labs(title = "RQ4: expected warranty loss vs. coverage length",
       x = "Coverage length (days)", y = "Expected loss (USD, cost-proxy)") +
  theme_minimal()
ggsave(file.path(RESULTS_DIR, "rq4_loss_curves.png"), p_loss, width = 9, height = 6)

write.csv(loss_table, file.path(RESULTS_DIR, "rq4_loss_table.csv"), row.names = FALSE)
saveRDS(loss_reg, file.path(RESULTS_DIR, "rq4_loss_regression.rds"))
cat("\nSaved: results/rq4_loss_curves.png, results/rq4_loss_table.csv, results/rq4_loss_regression.rds\n")
