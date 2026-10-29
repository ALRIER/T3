# All engines use identical resamples, component estimates, and benchmark comparisons.
# Resampling reference is the full-dataset sample mean (a PROXY, not population truth).
realworld_prepare <- function(x,sample_sizes=c(200L,1000L,3000L),R=500L,
                              seed=101L,replace=TRUE) {
  x<-as.numeric(x);x<-x[is.finite(x)]
  if(length(x)<20L) stop('Insufficient finite observations')
  stopifnot(R>2L)
  set.seed(seed)
  theta<-mean(x)
  out<-list()
  for(n in sample_sizes){
    # With replacement for datasets shorter than n. Output records resampling scheme.
    # `sample()` does not accept `simplify`; simplification belongs to
    # `replicate()`. Keep the generated matrix stable across R versions.
    draws<-replicate(R,sample(x,n,replace=(replace||n>length(x))))
    samples<-lapply(seq_len(R),function(i)draws[,i])
    out[[as.character(n)]]<-list(T=component_matrix(samples),target=theta,
        dataset_n=length(x),sample_n=n,replace=replace||n>length(x),seed=seed)
  }
  out
}
realworld_compare_models <- function(prepared,models,dataset_id='dataset') {
  do.call(rbind,lapply(names(prepared),function(n){
    a<-prepared[[n]]; y<-score_model_set(a$T,models,a$target)
    y$dataset_id<-dataset_id;y$sample_n<-a$sample_n;
    y$empirical_target_proxy<-a$target;y
  }))
}
# External dataset acquisition and dataset-specific transforms are supplied
# as a separate, reviewed legacy source module under R/04_real_datasets/legacy_sources.
