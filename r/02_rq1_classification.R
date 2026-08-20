# RQ1 - Can early-life SMART attributes predict failure within the next 30 days?
# Baseline: logistic regression on SNAPSHOT SMART features only (no rolling
# time-series features - those are added in 03_rq2_timeseries_value.R so the
# uplift from time-series info can be isolated).
#
# Train/test come from pipeline/03_prepare_r_inputs.py: split by drive
# (serial_number hash, no leakage), all positives kept, negatives downsampled
# NEG_TO_POS_RATIO:1 within each split. AUC on the downsampled test set is
# still an unbiased estimate of the population AUC (rank statistic); PR-AUC is
# NOT invariant to class prior, so it's reported alongside the true prevalence
# from label_summary.csv for context.
source("r/00_setup.R")
suppressMessages({ library(glmnet); library(pROC); library(PRROC) })

set.seed(1)

train <- load_train_sample()
test <- load_test_sample()
label_summary <- load_label_summary()
true_prevalence <- sum(label_summary$positive_rows) / sum(label_summary$valid_rows)

snapshot_cols <- grep("^smart_\\d+_(raw|normalized)$", names(train), value = TRUE)
cat("Snapshot features:", paste(snapshot_cols, collapse = ", "), "\n")
cat(sprintf("True population positive rate: %.5f%% | train: %d rows (%d pos) | test: %d rows (%d pos)\n",
            100 * true_prevalence, nrow(train), sum(train$fail_within_30d),
            nrow(test), sum(test$fail_within_30d)))

train <- train %>% select(all_of(c("fail_within_30d", snapshot_cols))) %>% na.omit()
test <- test %>% select(all_of(c("fail_within_30d", snapshot_cols))) %>% na.omit()

## --- Baseline: logistic regression ---------------------------------------
## Fitting on the full snapshot set (raw + normalized) fails badly: several
## SMART attributes are constant (0 variance) for a given manufacturer, and
## raw/normalized pairs are near-collinear encodings of the same signal - with
## a rare event this produces quasi-complete separation (glm.fit does not
## converge, coefficients blow up to ~1e13, AUC collapses to ~0.60, worse than
## chance-adjacent). The unpenalized MLE baseline is given a cleaner, less
## collinear predictor set (raw attributes only, zero-variance ones dropped)
## so it's a fair comparison point; the elastic-net model below still uses the
## full snapshot set since its penalty handles the collinearity directly.
raw_cols <- grep("_raw$", snapshot_cols, value = TRUE)
nzv <- sapply(train[, raw_cols], function(x) var(x, na.rm = TRUE) > 0)
glm_cols <- raw_cols[nzv]
cat(sprintf("\nBaseline glm predictors (raw, non-constant): %s\n", paste(glm_cols, collapse = ", ")))

## model = FALSE, y = FALSE: glm() otherwise retains the full model frame /
## response vector inside the fitted object, which on a 1.4M-row training set
## made a naive saveRDS() balloon to 300+MB (and got committed to git once
## before results/ was gitignored - see .gitignore).
glm_fit <- glm(reformulate(glm_cols, "fail_within_30d"), data = train, family = binomial(),
               model = FALSE, y = FALSE)
print(summary(glm_fit))

pred_glm <- predict(glm_fit, newdata = test, type = "response")
roc_glm <- roc(test$fail_within_30d, pred_glm, quiet = TRUE)
pr_glm <- pr.curve(scores.class0 = pred_glm[test$fail_within_30d == 1],
                    scores.class1 = pred_glm[test$fail_within_30d == 0], curve = FALSE)
cat(sprintf("Logistic regression PR-AUC (on downsampled test set, not true prevalence): %.4f\n",
            pr_glm$auc.integral))

## --- Comparison classifier: regularized logistic regression (elastic net) -
x_train <- as.matrix(train[, snapshot_cols])
y_train <- train$fail_within_30d
x_test <- as.matrix(test[, snapshot_cols])

cv_fit <- cv.glmnet(x_train, y_train, family = "binomial", alpha = 0.5, nfolds = 5)
pred_glmnet <- as.numeric(predict(cv_fit, newx = x_test, s = "lambda.min", type = "response"))
roc_glmnet <- roc(test$fail_within_30d, pred_glmnet, quiet = TRUE)

cat(sprintf("\n=== RQ1 results (snapshot-only) ===\n"))
cat(sprintf("Logistic regression   : AUC = %.4f\n", auc(roc_glm)))
cat(sprintf("Elastic-net logistic  : AUC = %.4f\n", auc(roc_glmnet)))

saveRDS(list(glm = glm_fit, glmnet = cv_fit, snapshot_cols = snapshot_cols,
             roc_glm = roc_glm, roc_glmnet = roc_glmnet, true_prevalence = true_prevalence),
        file.path(RESULTS_DIR, "rq1_models.rds"))

png(file.path(RESULTS_DIR, "rq1_roc.png"), width = 700, height = 600)
plot(roc_glm, col = "steelblue", main = "RQ1: 30-day failure prediction (snapshot features)")
lines(roc_glmnet, col = "firebrick")
legend("bottomright", legend = c("Logistic regression", "Elastic-net logistic"),
       col = c("steelblue", "firebrick"), lwd = 2)
dev.off()

cat("\nSaved: results/rq1_models.rds, results/rq1_roc.png\n")
