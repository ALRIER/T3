#!/usr/bin/env Rscript
# Independent pinned-container R audit of original Q2 paired loss records.
args <- commandArgs(trailingOnly=TRUE)
stopifnot(length(args)==1L, file.exists(args[[1L]]))
stopifnot(as.character(packageVersion("statmod"))=="1.5.2")
df <- read.csv(gzfile(args[[1L]]), stringsAsFactors=FALSE)
required <- c("family","sample_n","scenario_id","method","training_seed",
              "evaluation_seed","benchmark_role","mse_candidate","q95_candidate",
              "mse_reference","q95_reference","mse_difference","q95_difference",
              "mse_gain_pct","q95_gain_pct")
stopifnot(all(required %in% names(df)))
stopifnot(nrow(df)==10L*10L*4L*241L*2L)
stopifnot(length(unique(df$scenario_id))==241L)
stopifnot(length(unique(df$training_seed))==10L)
stopifnot(identical(sort(unique(df$evaluation_seed)),10:19))
stopifnot(identical(sort(unique(df$method)),
                    sort(c("ga","nsga2","de","dirichlet"))))
stopifnot(identical(sort(unique(df$benchmark_role)),c("mean","own")))
stopifnot(all(is.finite(as.matrix(df[,c("mse_difference","q95_difference",
                                    "mse_gain_pct","q95_gain_pct")]))))
stopifnot(max(abs(df$mse_candidate-df$mse_reference-df$mse_difference))<1e-7)
stopifnot(max(abs(df$q95_candidate-df$q95_reference-df$q95_difference))<1e-7)
check <- function(metric) {
  diff <- df[[paste0(metric,"_difference")]]
  gain <- df[[paste0(metric,"_gain_pct")]]
  original <- df[[paste0(metric,"_reference")]]
  calc <- -100*diff/pmax(abs(original),1e-14)
  scale <- pmax(1,abs(calc),abs(gain))
  stopifnot(max(abs(calc-gain)/scale)<1e-7)
}
check("mse");check("q95")
key <- paste(df$scenario_id,df$method,df$training_seed,
             df$evaluation_seed,df$benchmark_role,sep="|")
stopifnot(!anyDuplicated(key))
cat("Q2_PINNED_R_AUDIT_PASS",nrow(df),"rows, 10x10 independent seeds, exact paired losses\n")
