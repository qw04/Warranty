# Supporting survival analysis: Kaplan-Meier + Cox PH.
# Used to (a) justify the 30-day RQ1 horizon and class imbalance, (b) provide a
# baseline hazard view, and (c) validate the RQ3 clusters and RQ4 loss curves.
source("analysis/00_setup.R")

events <- load_events()
cat(sprintf("Loaded %d drives (%d models), %d failures\n",
            nrow(events), n_distinct(events$model), sum(events$event)))

## --- Kaplan-Meier: overall, and by model ------------------------------
surv_obj <- Surv(time = events$age_start_days, time2 = events$age_stop_days, event = events$event)

km_overall <- survfit(surv_obj ~ 1, data = events)
p_overall <- ggsurvplot(km_overall, data = events, conf.int = TRUE,
                         xlab = "Drive age (days, power-on hours / 24)",
                         ylab = "Survival probability",
                         title = "Overall Kaplan-Meier survival curve")
ggsave(file.path(RESULTS_DIR, "km_overall.png"), p_overall$plot, width = 8, height = 5)

km_by_model <- survfit(surv_obj ~ model, data = events)
p_model <- ggsurvplot(km_by_model, data = events, conf.int = FALSE,
                       xlab = "Drive age (days)", ylab = "Survival probability",
                       title = "Kaplan-Meier survival by model", legend = "right")
ggsave(file.path(RESULTS_DIR, "km_by_model.png"), p_model$plot, width = 10, height = 6)

## What survival probability is left at the 30-day RQ1 horizon, on average?
s30 <- summary(km_overall, times = FAILURE_HORIZON_DAYS)
cat(sprintf("\nP(survive past age %d days | already reached that age band) ~ %.5f\n",
            FAILURE_HORIZON_DAYS, s30$surv))
cat("(Motivates why a 30-day *forward* window rather than lifetime failure is used for RQ1/RQ2 -\n",
    " baseline hazard is low and roughly flat, so most signal has to come from SMART trend, not raw age.)\n")

## --- Cox proportional hazards ------------------------------------------
## capacity_bytes is dropped: in this dataset it's (near-)deterministic given
## model (each model ships at one fixed capacity), so including both causes
## separation/non-convergence. `model` already captures that variation.
cox_simple <- coxph(surv_obj ~ model, data = events)
print(summary(cox_simple))
saveRDS(cox_simple, file.path(RESULTS_DIR, "cox_simple.rds"))

cat("\nCox PH assumption check (Schoenfeld residuals):\n")
print(cox.zph(cox_simple))

cat("\nSaved: results/km_overall.png, results/km_by_model.png, results/cox_simple.rds\n")
