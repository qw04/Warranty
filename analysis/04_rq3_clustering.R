# RQ3 - Are there distinct clusters of drives with similar degradation
# patterns, and do they carry different failure risk (validated via
# per-cluster Kaplan-Meier curves)?
source("analysis/00_setup.R")
suppressMessages({ library(factoextra); library(cluster) })

set.seed(1)

## pipeline/03_prepare_r_inputs.py already reduces this to one row per drive -
## its most recent observed degradation snapshot (closest to failure, for
## failed drives; closest to end-of-window, for censored ones).
last_obs_raw <- load_last_observation()
ts_cols <- grep("_(roll7|roll30)_(mean|std)$|_slope30$", names(last_obs_raw), value = TRUE)

last_obs <- last_obs_raw %>%
  select(serial_number, model, all_of(ts_cols)) %>%
  na.omit()

cat(sprintf("Clustering on %d drives x %d degradation features\n", nrow(last_obs), length(ts_cols)))

X <- scale(as.matrix(last_obs[, ts_cols]))

## Choose k via silhouette score over a small candidate range. silhouette()
## needs a full pairwise distance matrix, which is infeasible at ~190k drives
## (190000^2 entries ~ 144GB) - kmeans itself is fit on the FULL data (cheap,
## O(n*k*iter)), but silhouette is evaluated on a fixed random subsample.
sil_sample <- sample(nrow(X), min(5000, nrow(X)))
sil_scores <- sapply(2:6, function(k) {
  km <- kmeans(X, centers = k, nstart = 10, iter.max = 50)
  mean(silhouette(km$cluster[sil_sample], dist(X[sil_sample, ]))[, 3])
})
best_k <- (2:6)[which.max(sil_scores)]
cat(sprintf("Silhouette by k: %s -> chosen k = %d\n",
            paste(sprintf("k=%d:%.3f", 2:6, sil_scores), collapse = ", "), best_k))

km_final <- kmeans(X, centers = best_k, nstart = 25, iter.max = 100)
last_obs$cluster <- factor(km_final$cluster)

p_clusters <- fviz_cluster(km_final, data = X, geom = "point", ellipse.type = "norm",
                            main = "RQ3: degradation-pattern clusters")
ggsave(file.path(RESULTS_DIR, "rq3_clusters.png"), p_clusters, width = 8, height = 6)

## --- Validation: per-cluster failure rate + Kaplan-Meier ------------------
events <- load_events() %>% left_join(last_obs %>% select(serial_number, cluster), by = "serial_number")

cluster_summary <- events %>%
  filter(!is.na(cluster)) %>%
  group_by(cluster) %>%
  summarise(n_drives = n(), failure_rate = mean(failed), .groups = "drop")
cat("\nPer-cluster failure rate:\n")
print(cluster_summary)

surv_obj <- Surv(time = events$age_start_days, time2 = events$age_stop_days, event = events$event)
km_cluster <- survfit(surv_obj ~ cluster, data = events)
p_km <- ggsurvplot(km_cluster, data = events, conf.int = TRUE,
                    xlab = "Drive age (days)", ylab = "Survival probability",
                    title = "RQ3: Kaplan-Meier survival by degradation cluster",
                    legend = "right")
ggsave(file.path(RESULTS_DIR, "rq3_km_by_cluster.png"), p_km$plot, width = 9, height = 6)

## survdiff() (the usual log-rank test) doesn't support the left-truncated
## counting-process Surv(start, stop, event) form used here. A single-covariate
## Cox model's score test is asymptotically equivalent to the log-rank test and
## does support this form, so it's used as the significance test instead.
cox_cluster <- coxph(surv_obj ~ cluster, data = events)
cat("\nCox score (log-rank-equivalent) test for difference in survival across clusters:\n")
print(summary(cox_cluster)$sctest)

saveRDS(list(kmeans = km_final, last_obs = last_obs, cluster_summary = cluster_summary),
        file.path(RESULTS_DIR, "rq3_clustering.rds"))
cat("\nSaved: results/rq3_clusters.png, results/rq3_km_by_cluster.png, results/rq3_clustering.rds\n")
