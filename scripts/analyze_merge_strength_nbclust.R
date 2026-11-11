#!/usr/bin/env Rscript

# Run the actual NbClust package against the three point-level merge-strength
# features. The package library is isolated under .artifacts/nbclust-r/library.

script_arg <- grep("^--file=", commandArgs(trailingOnly = FALSE), value = TRUE)
script_path <- normalizePath(sub("^--file=", "", script_arg[[1]]))
project_root <- normalizePath(file.path(dirname(script_path), ".."))
library_path <- file.path(project_root, ".artifacts", "nbclust-r", "library")
.libPaths(c(library_path, .libPaths()))

if (!requireNamespace("NbClust", quietly = TRUE)) {
  stop("NbClust is missing. Run: Rscript scripts/setup_nbclust_r_env.R")
}
suppressPackageStartupMessages(library(NbClust))

merge_dir <- file.path(project_root, "data_clean", "merge_analysis")
input_path <- file.path(merge_dir, "point_merge_strength_clusters.csv")
point_output <- file.path(merge_dir, "point_merge_strength_nbclust_r.csv")
votes_output <- file.path(merge_dir, "nbclust_r_index_votes.csv")
report_output <- file.path(merge_dir, "nbclust_r_report.md")
console_output <- file.path(merge_dir, "nbclust_r_console.txt")

feature_cols <- c("avg_S0_S1", "avg_S1_S2", "avg_S2_S3")
min_clusters <- 2L
max_clusters <- 6L
seed <- 20261111L

data <- read.csv(input_path, check.names = FALSE, stringsAsFactors = FALSE,
                 fileEncoding = "UTF-8-BOM")
if (!all(c("point_id", "point_name", "nbclust_cluster", feature_cols) %in% names(data))) {
  stop("Input table is missing point IDs, existing clusters, or merge-strength features.")
}
data <- data[complete.cases(data[, feature_cols]), , drop = FALSE]
if (nrow(data) < max_clusters + 1L) stop("Too few complete points for the requested k range.")

# Use the same z-score feature space as the current comparison, then run the
# package's majority-rule index selection separately for Ward.D2 and k-means.
x <- scale(as.matrix(data[, feature_cols]))
if (any(!is.finite(x))) stop("Standardized features contain non-finite values.")

run_nbclust <- function(method) {
  set.seed(seed)
  warnings <- character()
  diagnostic_pdf <- tempfile(fileext = ".pdf")
  grDevices::pdf(diagnostic_pdf)
  on.exit({
    grDevices::dev.off()
    unlink(diagnostic_pdf)
  }, add = TRUE)
  printed <- capture.output({
    result <- withCallingHandlers(
      NbClust::NbClust(
        data = x,
        distance = "euclidean",
        min.nc = min_clusters,
        max.nc = max_clusters,
        method = method,
        index = "all"
      ),
      warning = function(w) {
        warnings <<- c(warnings, conditionMessage(w))
        invokeRestart("muffleWarning")
      }
    )
  })
  list(result = result, printed = printed, warnings = unique(warnings))
}

methods <- c("ward.D2", "kmeans")
results <- setNames(lapply(methods, run_nbclust), methods)
writeLines(unlist(lapply(names(results), function(method) {
  c(paste0("===== ", method, " ====="), results[[method]]$printed,
    paste0("Warnings: ", if (length(results[[method]]$warnings))
      paste(results[[method]]$warnings, collapse = " | ") else "none"), "")
})), console_output, useBytes = TRUE)

cluster_vote_rows <- list()
for (method in methods) {
  result <- results[[method]]$result
  best_nc <- result$Best.nc
  proposed <- as.numeric(best_nc["Number_clusters", ])
  names(proposed) <- colnames(best_nc)
  for (index_name in names(proposed)) {
    k <- proposed[[index_name]]
    cluster_vote_rows[[length(cluster_vote_rows) + 1L]] <- data.frame(
      method = method,
      index = index_name,
      proposed_k = k,
      value_index = as.numeric(best_nc["Value_Index", index_name]),
      valid_vote = is.finite(k) && k >= min_clusters && k <= max_clusters,
      stringsAsFactors = FALSE
    )
  }
}
votes <- do.call(rbind, cluster_vote_rows)

display_clusters <- function(raw_labels, frame) {
  centers <- aggregate(frame[, feature_cols, drop = FALSE],
                       by = list(raw_cluster = raw_labels), FUN = mean)
  rownames(centers) <- as.character(centers$raw_cluster)
  raw_ids <- as.character(centers$raw_cluster)
  center_matrix <- as.matrix(centers[, feature_cols, drop = FALSE])
  rownames(center_matrix) <- raw_ids

  low_id <- raw_ids[which.min(rowMeans(center_matrix))]
  remaining <- setdiff(raw_ids, low_id)
  if (length(remaining) >= 2L) {
    stage_score <- center_matrix[remaining, "avg_S2_S3"] -
      center_matrix[remaining, "avg_S1_S2"]
    s2s3_id <- remaining[which.max(stage_score)]
    s1s2_id <- setdiff(remaining, s2s3_id)[[1]]
    name_map <- c(setNames("C1 低强度型", low_id),
                  setNames("C2 歌模合并主导型", s2s3_id),
                  setNames("C3 歌麻合并主导型", s1s2_id))
  } else {
    remaining_id <- setdiff(raw_ids, low_id)[[1]]
    name_map <- c(setNames("C1 低强度型", low_id),
                  setNames("C2 强合并型", remaining_id))
  }
  list(labels = unname(name_map[as.character(raw_labels)]),
       centers = centers, name_map = name_map)
}

for (method in methods) {
  result <- results[[method]]$result
  raw_labels <- as.integer(result$Best.partition)
  if (length(raw_labels) != nrow(data)) stop(paste(method, "returned a misaligned partition."))
  display <- display_clusters(raw_labels, data)
  prefix <- if (method == "ward.D2") "r_wardd2" else "r_kmeans"
  data[[paste0(prefix, "_raw_cluster")]] <- raw_labels
  data[[paste0(prefix, "_cluster_label")]] <- display$labels

  valid_votes <- votes[votes$method == method & votes$valid_vote, , drop = FALSE]
  vote_counts <- table(factor(valid_votes$proposed_k,
                              levels = min_clusters:max_clusters))
  selected_k <- as.integer(names(which.max(vote_counts)))
  if (length(unique(raw_labels)) != selected_k) {
    stop(paste(method, "package partition does not match majority-rule k."))
  }
  message(sprintf("%s: NbClust majority k=%d; sizes=%s", method, selected_k,
                  paste(as.integer(table(raw_labels)), collapse = ",")))
}

write.csv(data, point_output, row.names = FALSE, fileEncoding = "UTF-8")
write.csv(votes, votes_output, row.names = FALSE, fileEncoding = "UTF-8")

ari <- function(a, b) {
  tab <- table(a, b)
  choose2 <- function(v) v * (v - 1) / 2
  n <- sum(tab)
  expected <- sum(choose2(rowSums(tab))) * sum(choose2(colSums(tab))) / choose2(n)
  maximum <- (sum(choose2(rowSums(tab))) + sum(choose2(colSums(tab)))) / 2
  (sum(choose2(tab)) - expected) / (maximum - expected)
}

vote_summary <- do.call(rbind, lapply(methods, function(method) {
  valid <- votes[votes$method == method & votes$valid_vote, , drop = FALSE]
  counts <- table(factor(valid$proposed_k, levels = min_clusters:max_clusters))
  data.frame(method = method,
             selected_k = as.integer(names(which.max(counts))),
             winning_votes = max(counts),
             total_votes = sum(counts),
             vote_breakdown = paste(paste0(names(counts), ":", as.integer(counts)), collapse = ", "),
             stringsAsFactors = FALSE)
}))

ward_raw <- data$r_wardd2_raw_cluster
kmeans_raw <- data$r_kmeans_raw_cluster
current_raw <- as.integer(data$nbclust_cluster)
current_display <- c("1" = "C1 低强度型", "3" = "C2 歌模合并主导型",
                     "2" = "C3 歌麻合并主导型")[as.character(current_raw)]
comparison <- table(current_kmeans_k3 = current_display,
                    r_ward_d2 = data$r_wardd2_cluster_label)
disagreements <- data[current_display != data$r_wardd2_cluster_label,
                      c("point_id", "point_name")]

report <- c(
  "# Actual R/NbClust merge-strength clustering",
  "",
  sprintf("- Points: %d (SJ02 is excluded by the current formal input set).", nrow(data)),
  sprintf("- Features: %s; z-score standardized; Euclidean distance; candidate k=%d..%d.",
          paste(feature_cols, collapse = ", "), min_clusters, max_clusters),
  sprintf("- R: %s; NbClust: %s; seed: %d.", getRversion(),
          as.character(packageVersion("NbClust")), seed),
  "- The map uses Ward.D2 labels selected by NbClust majority rule; k-means is included as a method sensitivity check.",
  "",
  "## Majority votes",
  "",
  "| Method | Selected k | Votes for selected k | Valid index votes | Vote breakdown (k:votes) |",
  "|---|---:|---:|---:|---|",
  vapply(seq_len(nrow(vote_summary)), function(i) {
    row <- vote_summary[i, ]
    sprintf("| %s | %d | %d | %d | %s |", row$method, row$selected_k,
            row$winning_votes, row$total_votes, row$vote_breakdown)
  }, character(1)),
  "",
  "## Ward.D2 cluster centers",
  "",
  "| Display cluster | Points | Mean S0-S1 | Mean S1-S2 | Mean S2-S3 |",
  "|---|---:|---:|---:|---:|"
)
ward_display <- data$r_wardd2_cluster_label
ward_centers <- aggregate(data[, feature_cols, drop = FALSE],
                          by = list(display = ward_display), FUN = mean)
ward_sizes <- table(ward_display)
for (i in seq_len(nrow(ward_centers))) {
  row <- ward_centers[i, ]
  report <- c(report, sprintf("| %s | %d | %.3f | %.3f | %.3f |",
                              row$display, ward_sizes[[row$display]],
                              row$avg_S0_S1, row$avg_S1_S2, row$avg_S2_S3))
}
report <- c(report,
  "",
  "## Comparison with the current Python-selected k-means k=3",
  "",
  sprintf("- Adjusted Rand index (R Ward.D2 vs current): %.3f.", ari(current_raw, ward_raw)),
  sprintf("- Adjusted Rand index (R k-means vs current): %.3f.", ari(current_raw, kmeans_raw)),
  "- Ward.D2 vs current cluster cross-tab after aligning semantic labels:",
  "",
  "```text",
  capture.output(print(comparison)),
  "```",
  "",
  sprintf("- Points whose Ward.D2 partition differs from current: %d / %d.",
          nrow(disagreements), nrow(data)),
  if (nrow(disagreements)) paste0("- Points moved to a different group: ",
       paste(disagreements$point_name, collapse = "、")) else "- The partitions are identical.",
  "",
  "Full point assignments, index votes, and NbClust console output are saved alongside this report."
)
writeLines(report, report_output, useBytes = TRUE)

cat("Point assignments:", point_output, "\n")
cat("Index votes:", votes_output, "\n")
cat("Report:", report_output, "\n")
cat("NbClust output:", console_output, "\n")
