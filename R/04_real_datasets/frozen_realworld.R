realworld_frozen_comparison <- function(sample_matrix,weights,reference_mean,eligible=rep(TRUE,26L)) {
  # sample_matrix is the 26-component matrix computed on resamples of ONE dataset.
  # Full-data mean is a PROXY for the unknown true population mean.
  evaluate_weights(sample_matrix,weights,reference_mean,eligible)
}
realworld_fdr <- function(predeclared_p_values,alpha=.05) {
  q<-p.adjust(predeclared_p_values,method='BH')
  data.frame(p=predeclared_p_values,q=q,pass=q<=alpha)
}


# Real-world reference is a full-dataset proxy; confidence intervals quantify
# resampling variability conditional on that proxy, not population-mean uncertainty.
realworld_frozen_with_q95_ci <- function(sample_matrix,weights,reference_mean,B=500L,seed=1L) {
 W<-normalize_weights(as.matrix(weights))
 list(point=realworld_frozen_comparison(sample_matrix,W,reference_mean),
      q95_uncertainty=t2_q95_audit_weights(sample_matrix,W,reference_mean,B=B,seed=seed),
      target_type="full_dataset_mean_proxy")
}
