#!/usr/bin/env Rscript
# Independent R implementation of RQ1 paired contrast verification.
# Uses ONLY previously archived R1 Held Out evaluation units.
# Executes in the canonical pinned T3 container; no model refitting.
a <- commandArgs(trailingOnly=TRUE)
if(length(a)!=3L)stop("Usage: FAMILY SOURCE_R1_ROOT OUTPUT_DIR")
family <- a[[1L]]
prior <- a[[2L]]
out <- a[[3L]]
families <- c("normal","lognormal","weibull","invgauss","exgaussian","exwald")
methods <- c("ga","nsga2","de","dirichlet")
if(!family %in% families)stop("Unknown family")
reference <- read.csv("R1/runs/44307352615/all_pairwise_global_holm.csv")
sensitivity <- read.csv(file.path(prior,"synthesis","reviewer_exact_signflip_loo_global_holm.csv"))
if(nrow(reference)!=216L||nrow(sensitivity)!=216L)stop("Original R1 evidence is incomplete")
pair_names <- combn(methods,2L,simplify=FALSE)
flip_signs <- as.matrix(expand.grid(rep(list(c(-1,1)),10L)))
if(!identical(dim(flip_signs),c(1024L,10L)))stop("Sign-flip enumeration failed")
tol <- function(actual,ref,label) {
 if(!is.finite(actual)||!is.finite(ref)||abs(actual-ref)>1e-9*max(1,abs(ref)))
   stop("Independent R check disagrees on ",label,": ",actual," vs ",ref)
}
rows <- list()
for(n in c(200L,1000L,3000L)) {
 file <- file.path(prior,"heldout",paste0(family,"-n",n),"candidate_by_eval.csv")
 if(!file.exists(file))stop("Missing immutable original R1 candidates: ",file)
 d <- read.csv(file)
 req <- c("training_seed","eval_seed","method","mse","q95")
 if(!all(req%in%names(d)))stop("Missing candidate evaluation fields")
 if(nrow(d)!=400L||anyDuplicated(d[c("training_seed","eval_seed","method")])||
    !setequal(d$training_seed,0:9)||!setequal(d$eval_seed,10:19)||
    !setequal(d$method,methods)||any(!is.finite(d$mse))||any(!is.finite(d$q95)))
    stop("Invalid original individual-frozen-candidate by evaluation-seed grid")
 # Reconstruct 10 independent evaluation-seed units after averaging the
 # correlated training-seed candidates within each independent seed.
 p <- aggregate(d[c("mse","q95")],d[c("eval_seed","method")],mean)
 if(nrow(p)!=40L)stop("Missing independent pairs")
 for(pair in pair_names) for(metric in c("mse","q95")) {
  aa <- p[p$method==pair[[1L]],c("eval_seed",metric)]
  bb <- p[p$method==pair[[2L]],c("eval_seed",metric)]
  names(aa)[2L] <- "x";names(bb)[2L] <- "y"
  m <- merge(aa,bb,by="eval_seed")
  if(nrow(m)!=10L||!setequal(m$eval_seed,10:19))stop("Broken evaluation-seed matching")
  delta <- m$x-m$y
  avg <- mean(delta);sdv <- sd(delta)
  ste <- sdv/sqrt(10)
  crit <- qt(.975,9L)
  lower <- avg-crit*ste;upper <- avg+crit*ste
  pval <- if(sdv>0) 2*pt(-abs(avg/ste),9) else if(avg==0) 1 else 0
  keys <- reference$family==family&reference$sample_n==n&
      reference$method_a==pair[[1L]]&reference$method_b==pair[[2L]]&
      reference$metric==metric
  r <- reference[keys,,drop=FALSE]
  if(nrow(r)!=1L)stop("Missing original inference panel key")
  tol(avg,r$difference,"mean loss contrast")
  tol(lower,r$ci_low,"lower 95% CI")
  tol(upper,r$ci_high,"upper 95% CI")
  tol(pval,r$p,"two-sided paired t p")
  flips <- abs(drop(flip_signs%*%delta)/10)
  observed <- abs(avg)
  exact_p <- mean(flips>=observed-1e-12*max(1,observed))
  rs <- sensitivity[keys,,drop=FALSE]
  if(nrow(rs)!=1L)stop("Missing original reviewer contrast")
  tol(exact_p,rs$p_signflip_exact_two_sided,"exact sign flip sensitivity")
  leave_one <- vapply(seq_along(delta),function(i)mean(delta[-i]),numeric(1))
  tol(min(leave_one),rs$leave_one_out_min_mean,"leave-one-seed-out minimum")
  tol(max(leave_one),rs$leave_one_out_max_mean,"leave-one-seed-out maximum")
  rows[[length(rows)+1L]] <- data.frame(
    family=family,sample_n=n,method_a=pair[[1L]],method_b=pair[[2L]],metric=metric,
    difference=avg,ci_lower=lower,ci_upper=upper,
    p_paired_t=pval,p_signflip_exact=exact_p,paired_effect_size_dz=if(sdv>0)avg/sdv else NA_real_,
    fraction_independent_seeds_favor_a=mean(delta<0),
    leave_one_out_sign_stable=(all(leave_one<0)||all(leave_one>0)),
    original_holm_global=r$holm_p_global,
    reviewer_holm_global=rs$holm_signflip_global,
    replication_of_original=TRUE,
    stringsAsFactors=FALSE)
 }
}
z <- do.call(rbind,rows)
if(nrow(z)!=36L||anyDuplicated(z[c("family","sample_n","method_a","method_b","metric")]))
 stop("Invalid reviewer independent crosscheck coverage")
dir.create(out,recursive=TRUE,showWarnings=FALSE)
write.csv(z,file.path(out,"independent_r_paired_reaudit.csv"),row.names=FALSE)
writeLines(c(
 "Independent base-R recalculation of 36 original method x metric x size contrasts.",
 "Independent unit: heldout evaluation seed (10), with correlated frozen candidates averaged within each seed.",
 "Original parametric p, CI, mean and exact sign-flip sensitivity were independently reproduced.",
 "All sign-flip tests are supplementary sensitivity checks, not a selection-aware error calibration.",
 "Preserves original R1 evidence; no resimulation, retuning, retraining or weight modification.",
 "The GHCR digest is frozen in config/T3_DEFAULT_ANALYSIS_RUNTIME.env."),
 file.path(out,"AUDIT_SCOPE.txt"))
cat("R1_PINNED_CONTAINER_REAUDIT_PASS",family,nrow(z),"\n")
