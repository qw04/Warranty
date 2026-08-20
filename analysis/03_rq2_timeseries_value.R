# RQ2 - Do rolling time-series SMART features (mean/std/slope over 7/30 days)
# improve 30-day failure prediction versus snapshot-only features?
# Re-fits the RQ1 elastic-net logistic model with the rolling features added,
# on the same pre-built train/test split, and compares AUC / PR-AUC uplift.
source("analysis/00_setup.R")
suppressMessages({ library(glmnet); library(pROC); library(PRROC) })

set.seed(1)

train_raw <- load_train_sample()
test_raw <- load_test_sample()

snapshot_cols <- grep("^smart_\\d+_(raw|normalized)$", names(train_raw), value = TRUE)
ts_cols <- grep("_(roll7|roll30)_(mean|std)$|_slope30$", names(train_raw), value = TRUE)
cat(sprintf("Snapshot features: %d | Time-series features: %d\n", length(snapshot_cols), length(ts_cols)))

all_cols <- c(snapshot_cols, ts_cols)
train <- train_raw %>% select(all_of(c("fail_within_30d", all_cols))) %>% na.omit()
test <- test_raw %>% select(all_of(c("fail_within_30d", all_cols))) %>% na.omit()
cat(sprintf("Train: %d rows (%d pos) | Test: %d rows (%d pos)\n",
            nrow(train), sum(train$fail_within_30d), nrow(test), sum(test$fail_within_30d)))

fit_eval <- function(cols, label) {
  x_train <- as.matrix(train[, cols]); y_train <- train$fail_within_30d
  x_test <- as.matrix(test[, cols])
  cv_fit <- cv.glmnet(x_train, y_train, family = "binomial", alpha = 0.5, nfolds = 5)
  pred <- as.numeric(predict(cv_fit, newx = x_test, s = "lambda.min", type = "response"))
  roc_obj <- roc(test$fail_within_30d, pred, quiet = TRUE)
  pr_obj <- pr.curve(scores.class0 = pred[test$fail_within_30d == 1],
                      scores.class1 = pred[test$fail_within_30d == 0], curve = FALSE)
  cat(sprintf("%-30s AUC = %.4f | PR-AUC = %.4f\n", label, auc(roc_obj), pr_obj$auc.integral))
  list(fit = cv_fit, roc = roc_obj, pr = pr_obj, pred = pred)
}

cat("\n=== RQ2 results: snapshot-only vs snapshot+time-series ===\n")
res_snapshot <- fit_eval(snapshot_cols, "Snapshot-only")
res_full <- fit_eval(all_cols, "Snapshot + time-series")

png(file.path(RESULTS_DIR, "rq2_roc_comparison.png"), width = 700, height = 600)
plot(res_snapshot$roc, col = "steelblue", main = "RQ2: value of time-series features")
lines(res_full$roc, col = "darkorange")
legend("bottomright", legend = c("Snapshot-only", "Snapshot + time-series"),
       col = c("steelblue", "darkorange"), lwd = 2)
dev.off()

saveRDS(list(snapshot = res_snapshot, full = res_full, snapshot_cols = snapshot_cols, ts_cols = ts_cols),
        file.path(RESULTS_DIR, "rq2_models.rds"))
cat("\nSaved: results/rq2_models.rds, results/rq2_roc_comparison.png\n")
