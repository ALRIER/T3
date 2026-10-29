# Audit context is set only during V3 Monte Carlo matrix construction.
t2_numeric_audit_start <- function(path, context=list()) {
 options(t2.audit.path=path,t2.audit.context=context)
 invisible(TRUE)
}
t2_numeric_audit_stop <- function() {
 options(t2.audit.path=NULL,t2.audit.context=NULL)
 invisible(TRUE)
}
t2_numeric_audit_log <- function(name, reason, iterations=NA_integer_, converged=FALSE) {
 path<-getOption("t2.audit.path")
 if(is.null(path))return(invisible(NULL))
 dir.create(dirname(path),recursive=TRUE,showWarnings=FALSE)
 ctx<-getOption("t2.audit.context",list())
 vals<-c(list(estimator=name,reason=reason,iterations=iterations,converged=converged),ctx)
 row<-as.data.frame(lapply(vals,function(x)if(length(x))as.character(x) else ""),stringsAsFactors=FALSE)
 # Append CSV rows using an identical fixed field order across events.
 row<-row[,c("estimator","reason","iterations","converged","stage","family","seed","n","scenario","replicate"),drop=FALSE]
 utils::write.table(row,path,sep=",",row.names=FALSE,col.names=!file.exists(path),
                    append=file.exists(path),qmethod="double")
 invisible(NULL)
}
t2_rlm_audited <- function(x,psi,k=NULL,label) {
 warnings<-character()
 fit<-tryCatch(withCallingHandlers({
   args<-list(formula=x~1,psi=psi,scale.est="MAD",maxit=100L,na.action=na.omit)
   if(!is.null(k))args$k<-k
   do.call(MASS::rlm,args)
 },warning=function(w) {
   warnings<<-c(warnings,conditionMessage(w))
   invokeRestart("muffleWarning")
 }),error=function(e)e)
 if(inherits(fit,"error")) {
  t2_numeric_audit_log(label,paste0("error: ",conditionMessage(fit)))
  return(stats::median(x,na.rm=TRUE))
 }
 val<-as.numeric(stats::coef(fit)[1L])
 converged<-isTRUE(fit$converged)
 if(!converged||length(warnings)||!is.finite(val))
  t2_numeric_audit_log(label,
    if(length(warnings))paste(warnings,collapse=" | ") else
      if(!converged)"maxit_no_convergence" else "nonfinite_coefficient",
    iterations=length(fit$conv),converged=converged)
 if(!is.finite(val))stats::median(x,na.rm=TRUE) else val
}

# Source registry: historical NEST26. These functions remain scientifically unchanged.
.qs3 <- function(x) {
  stats::quantile(x, probs = c(0.25, 0.50, 0.75), names = FALSE, type = 8, na.rm = TRUE)
}

harmonic_mean_safe <- function(x) {
  x <- as.numeric(x); if (!length(x)) return(NA_real_)
  xp <- x[is.finite(x) & x > 0]
  if (!length(xp)) return(stats::median(x, na.rm = TRUE))
  length(xp) / sum(1 / xp)
}

geometric_mean_safe <- function(x) {
  x <- as.numeric(x); if (!length(x)) return(NA_real_)
  xp <- x[is.finite(x) & x > 0]
  if (!length(xp)) return(stats::median(x, na.rm = TRUE))
  exp(base::mean(log(xp)))
}

mode_hsm_safe <- function(x) {
  x <- as.numeric(x)
  out <- tryCatch(modeest::hsm(x), error = function(e) NA_real_)
  if (!is.finite(out)) stats::median(x, na.rm = TRUE) else out
}

mode_parzen_safe <- function(x) {
  x <- as.numeric(x)
  out <- tryCatch(as.numeric(modeest::mlv(x, method = "parzen")),
                  error = function(e) NA_real_)
  if (!is.finite(out)) stats::median(x, na.rm = TRUE) else out
}

trimean_safe <- function(x) {
  x <- as.numeric(x); q <- .qs3(x); (q[1] + 2*q[2] + q[3]) / 4
}

huber_mean_safe <- function(x) t2_rlm_audited(as.numeric(x),MASS::psi.huber,label="huber")
biweight_mean_safe <- function(x) t2_rlm_audited(as.numeric(x),MASS::psi.bisquare,label="biweight")

finite_numeric <- function(x) {
  x <- as.numeric(x)
  x[is.finite(x)]
}

winsorized_mean_safe <- function(x, p = 0.10) {
  x <- finite_numeric(x)
  if (!length(x)) return(NA_real_)
  qs <- stats::quantile(x, probs = c(p, 1 - p), na.rm = TRUE, names = FALSE, type = 8)
  mean(pmin(pmax(x, qs[1]), qs[2]))
}

median_of_means_safe <- function(x, k = 10L) {
  x <- finite_numeric(x)
  n <- length(x)
  if (n == 0L) return(NA_real_)
  k <- max(1L, min(as.integer(k), n))
  idx <- split(seq_len(n), cut(seq_len(n), breaks = k, labels = FALSE))
  stats::median(vapply(idx, function(ii) mean(x[ii]), numeric(1)), na.rm = TRUE)
}

catoni_psi_safe <- function(u) {
  sign(u) * log1p(abs(u) + 0.5 * u^2)
}

catoni_mean_safe <- function(x, alpha = 0.20, maxit = 100L, tol = 1e-08) {
  x <- finite_numeric(x)
  if (!length(x)) return(NA_real_)
  if (length(unique(x)) == 1L) return(x[1])
  alpha <- as.numeric(alpha)
  if (!is.finite(alpha) || alpha <= 0) alpha <- 0.20
  f <- function(theta) sum(catoni_psi_safe(alpha * (x - theta)))
  sdx <- stats::sd(x)
  if (!is.finite(sdx)) sdx <- 0
  lo <- min(x) - sdx - 1
  hi <- max(x) + sdx + 1
  out <- tryCatch(stats::uniroot(f, interval = c(lo, hi), tol = tol, maxiter = maxit)$root,
                  error = function(e) NA_real_)
  if (!is.finite(out)) stats::median(x) else out
}

huber_tuned_mean_safe <- function(x,k=1.345)
 t2_rlm_audited(finite_numeric(x),MASS::psi.huber,k=k,label=paste0("huber_k",k))

ESTIMATOR_REGISTRY <- list(
  mean        = function(x) base::mean(x, na.rm = TRUE),
  median      = function(x) stats::median(x, na.rm = TRUE),
  trimmed20   = function(x) base::mean(x, trim = 0.20, na.rm = TRUE),
  trimmed10   = function(x) base::mean(x, trim = 0.10, na.rm = TRUE),
  winsorized_0.15 = function(x) winsorized_mean_safe(x, p = 0.15),
  mode_hsm    = mode_hsm_safe,
  mode_parzen = mode_parzen_safe,
  trimean     = trimean_safe,
  huber       = huber_mean_safe,
  biweight    = biweight_mean_safe,
  winsorized_0.05 = function(x) winsorized_mean_safe(x, p = 0.05),
  winsorized_0.1  = function(x) winsorized_mean_safe(x, p = 0.10),
  winsorized_0.2  = function(x) winsorized_mean_safe(x, p = 0.20),
  mom_k5      = function(x) median_of_means_safe(x, k = 5L),
  mom_k10     = function(x) median_of_means_safe(x, k = 10L),
  mom_k20     = function(x) median_of_means_safe(x, k = 20L),
  catoni_a0.05 = function(x) catoni_mean_safe(x, alpha = 0.05),
  catoni_a0.1  = function(x) catoni_mean_safe(x, alpha = 0.10),
  catoni_a0.2  = function(x) catoni_mean_safe(x, alpha = 0.20),
  catoni_a0.35 = function(x) catoni_mean_safe(x, alpha = 0.35),
  catoni_a0.5  = function(x) catoni_mean_safe(x, alpha = 0.50),
  huber_k0.75  = function(x) huber_tuned_mean_safe(x, k = 0.75),
  huber_k1     = function(x) huber_tuned_mean_safe(x, k = 1.00),
  huber_k1.345 = function(x) huber_tuned_mean_safe(x, k = 1.345),
  huber_k1.75  = function(x) huber_tuned_mean_safe(x, k = 1.75),
  huber_k2     = function(x) huber_tuned_mean_safe(x, k = 2.00)
)

# Convenience metadata used throughout the project: estimator names define column labels, and N_EST is
# the dimensionality of the GA weight vector. Many parts of the pipeline (simplex normalization, warm-start
# matrices, perturbation tests) assume length(weights) == N_EST, so this central definition is critical.
ESTIMATOR_NAMES <- names(ESTIMATOR_REGISTRY)
N_EST <- length(ESTIMATOR_NAMES)



family_support_class <- function(distribution = NULL) {
  # Returns a coarse support label used only for estimator admissibility.
  # Unknown families are treated permissively to avoid breaking exploratory runs.
  if (is.null(distribution) || length(distribution) == 0L || is.na(distribution[1])) {
    return("unknown")
  }
  d <- tolower(as.character(distribution[1]))
  d <- gsub("[^a-z0-9_]+", "", d)
  if (d %in% c("normal", "gaussian", "exgaussian", "ex_gaussian")) {
    return("can_be_nonpositive")
  }
  if (d %in% c("lognormal", "weibull", "invgauss", "inversegaussian",
               "inverse_gaussian", "exwald", "ex_wald")) {
    return("strictly_positive")
  }
  "unknown"
}

family_allows_nonpositive <- function(distribution = NULL) {
  identical(family_support_class(distribution), "can_be_nonpositive")
}

admissible_estimator_mask <- function(distribution = NULL,
                                      target = "arithmetic_mean",
                                      strict_support = TRUE) {
  # A named TRUE/FALSE vector aligned with ESTIMATOR_NAMES.
  # Revised T2 core registry consists entirely of real-support location estimators.
  # Historical harmonic/geometric restrictions no longer apply to core weights.
  mask <- rep(TRUE, N_EST)
  names(mask) <- ESTIMATOR_NAMES

  # Every registered core component is defined for mixed-sign finite samples.

  mask
}

apply_estimator_admissibility <- function(weights,
                                          distribution = NULL,
                                          target = "arithmetic_mean",
                                          strict_support = TRUE) {
  stopifnot(length(weights) == N_EST)
  w <- .normalize_simplex(as.numeric(weights))
  mask <- admissible_estimator_mask(distribution = distribution,
                                    target = target,
                                    strict_support = strict_support)
  w[!mask] <- 0
  if (!any(is.finite(w)) || sum(w, na.rm = TRUE) <= 0) {
    # Defensive fallback: if all weight was on blocked estimators, redistribute
    # uniformly over allowed estimators. If the family is unknown and everything
    # is somehow blocked, fall back to the full simplex.
    allowed <- which(mask)
    if (!length(allowed)) allowed <- seq_len(N_EST)
    w <- numeric(N_EST)
    w[allowed] <- 1 / length(allowed)
  } else {
    w <- .normalize_simplex(w)
  }
  names(w) <- ESTIMATOR_NAMES
  as.numeric(w)
}

compute_components_vector <- function(x) {
  # defensive: remove non-finite values if they appear
  x <- as.numeric(x); x <- x[is.finite(x)]
  if (!length(x)) return(rep(NA_real_, N_EST))
  # Use the registry to preserve consistent mapping: estimator names <-> component functions
  comps <- vapply(ESTIMATOR_REGISTRY, function(f) {
    out <- tryCatch(f(x), error = function(e) NA_real_)
    if (!is.finite(out)) stats::median(x, na.rm = TRUE) else out
  }, numeric(1))
  as.numeric(comps)
}

