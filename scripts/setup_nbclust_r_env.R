#!/usr/bin/env Rscript

# Create an isolated user library for the real NbClust analysis without
# modifying the system R library.
script_arg <- grep("^--file=", commandArgs(trailingOnly = FALSE), value = TRUE)
script_path <- normalizePath(sub("^--file=", "", script_arg[[1]]))
project_root <- normalizePath(file.path(dirname(script_path), ".."))
library_path <- file.path(project_root, ".artifacts", "nbclust-r", "library")
dir.create(library_path, recursive = TRUE, showWarnings = FALSE)
.libPaths(c(library_path, .libPaths()))

if (!requireNamespace("NbClust", quietly = TRUE)) {
  install.packages("NbClust", lib = library_path, repos = "https://cloud.r-project.org")
}
if (!requireNamespace("NbClust", quietly = TRUE)) {
  stop("NbClust installation failed. Check CRAN network access and try again.")
}

cat("R:", getRversion(), "\n")
cat("NbClust:", as.character(packageVersion("NbClust")), "\n")
cat("Isolated library:", library_path, "\n")
