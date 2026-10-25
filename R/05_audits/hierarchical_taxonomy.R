# Shared prespecified reporting taxonomy (not used for optimizer fitness).
# Each row is a comparison on an INDEPENDENT inference unit; aggregate before calling.
t2_taxonomy <- function(x, alpha=.05, family_cols=c("stage","level","benchmark_id"),
                        strict_ci=TRUE) {
  required<-c("stage","level","benchmark_id","model_id","mse_difference",
              "q95_difference","mse_p_value","q95_p_value")
  if(!all(required%in%names(x)))stop("Taxonomy input missing columns: ",
                               paste(setdiff(required,names(x)),collapse=","))
  if(!all(family_cols%in%names(x)))stop("Invalid BH family")
  if(anyNA(x[,required,drop=FALSE]))stop("Incomplete taxonomy hypotheses")
  if(any(!is.finite(x$mse_p_value)|!is.finite(x$q95_p_value)) ||
     any(x$mse_p_value<0|x$mse_p_value>1|x$q95_p_value<0|x$q95_p_value>1))
    stop("Invalid p values")
  # One family of tests per metric and declared level/reference, NOT one BH per model.
  x$mse_q_value<-NA_real_;x$q95_q_value<-NA_real_
  groups<-interaction(x[,family_cols,drop=FALSE],drop=TRUE,lex.order=TRUE)
  for(ii in split(seq_len(nrow(x)),groups)) {
    x$mse_q_value[ii]<-p.adjust(x$mse_p_value[ii],method="BH")
    x$q95_q_value[ii]<-p.adjust(x$q95_p_value[ii],method="BH")
  }
  c1<-if(strict_ci){if(!"mse_ci_high"%in%names(x))stop("Missing mse CI")
                  is.finite(x$mse_ci_high)&x$mse_ci_high<0} else rep(TRUE,nrow(x))
  c2<-if(strict_ci){if(!"q95_ci_high"%in%names(x))stop("Missing q95 CI")
                  is.finite(x$q95_ci_high)&x$q95_ci_high<0} else rep(TRUE,nrow(x))
  x$mse_supported<-x$mse_difference<0 & c1 & x$mse_q_value<=alpha
  x$q95_supported<-x$q95_difference<0 & c2 & x$q95_q_value<=alpha
  x$taxonomy<-ifelse(x$mse_supported & x$q95_supported,"both_mse_q95_bh_fdr",
                 ifelse(x$mse_supported,"mse_only_bh_fdr",
                   ifelse(x$q95_supported,"q95_only_bh_fdr","no_supported_gain")))
  x
}
t2_taxonomy_levels <- function()c("scenario","neighborhood","intrafamily","global")
t2_taxonomy_absolute <- function(x, required_stages=c("heldout","stress","realworld"),
                                 levels=c("global"), benchmark_id="mean") {
  # Strict intersection at a fixed level/reference. Never infer an absent win.
  stopifnot(all(c("stage","level","benchmark_id","model_id","mse_supported",
                  "q95_supported")%in%names(x)))
  z<-x[x$level%in%levels & x$benchmark_id==benchmark_id,,drop=FALSE]
  if(!nrow(z))return(data.frame())
  ids<-unique(z$model_id)
  do.call(rbind,lapply(ids,function(id){
    rows<-z[z$model_id==id,,drop=FALSE]
    complete<-all(required_stages%in%unique(rows$stage)) &&
              all(table(rows$stage[rows$stage%in%required_stages])==1L)
    rows<-rows[rows$stage%in%required_stages,,drop=FALSE]
    data.frame(model_id=id,benchmark_id=benchmark_id,level=paste(levels,collapse="+"),
      complete=complete,absolute_mse=complete&&all(rows$mse_supported),
      absolute_q95=complete&&all(rows$q95_supported),
      absolute_both=complete&&all(rows$mse_supported & rows$q95_supported),
      stringsAsFactors=FALSE)
  }))
}

# Shared contract attached to every stage result. A version mismatch is fatal.
t2_taxonomy_contract <- function() list(
  schema="t2_taxonomy_v1",
  levels=t2_taxonomy_levels(),
  classifications=c("both_mse_q95_bh_fdr","mse_only_bh_fdr",
                    "q95_only_bh_fdr","no_supported_gain"),
  primary_benchmark="mean",
  secondary_benchmarks=c("median","trimmed20","huber"),
  alpha=.05,
  metrics=c("mse","q95"),
  adjustment="BH_by_stage_level_benchmark_separately_per_metric",
  candidate_basis="frozen_weights",
  discovery_evidence="development_only",
  absolute_stages=c("heldout","stress","realworld"),
  component_names=ESTIMATOR_NAMES
)
t2_verify_taxonomy_contract <- function(x) {
  expected<-t2_taxonomy_contract()
  if(!identical(x,expected)) stop("Taxonomy contract mismatch: refusing incompatible stage result")
  invisible(TRUE)
}
t2_save_taxonomy_contract <- function(path) {
  dir.create(dirname(path),recursive=TRUE,showWarnings=FALSE)
  saveRDS(t2_taxonomy_contract(),path)
  invisible(path)
}
