# Frozen-model stress tests, with NO training or weight update.
# The original validation suite is archived in legacy_sources for auditability.
stress_run_models <- function(data_generator,models,conditions,
                              R=200L,n=c(200L,1000L,3000L),seed=501L,bootstrap_B=500L) {
  stopifnot(is.function(data_generator),length(models)>0L)
  rows<-list();k<-0L
  for(s in seq_len(nrow(conditions))) for(nn in n){
    # CRN: all competing models see same samples in this setting.
    set.seed(seed + s*1000L + nn)
    samples<-lapply(seq_len(R),function(r)data_generator(conditions[s,,drop=FALSE],nn))
    T<-component_matrix(samples)
    target<-attr(conditions,'true_mean')
    if(is.null(target) && 'true_mean' %in% names(conditions)) target<-conditions$true_mean[s]
    if(is.null(target)||length(target)!=1L||!is.finite(target))
      stop('Generator must supply known true mean via condition metadata')
    y<-score_model_set(T,models,target)
    if(R>=30L) {
      ci<-stress_frozen_q95_ci(T,models,target,B=bootstrap_B,seed=seed+s*1000L+nn)
      ix<-match(y$model,ci$model)
      for(k in setdiff(names(ci),'model'))y[[k]]<-ci[[k]][ix]
    }
    y$scenario_id<-if('scenario_id'%in%names(conditions)) conditions$scenario_id[s] else s
    y$sample_n<-nn;k<-k+1L;rows[[k]]<-y
  }
  do.call(rbind,rows)
}
stress_diagnostics <- function(results) {
  aggregate(cbind(mse,q95)~model+sample_n,data=results,FUN=function(v)c(mean=mean(v),max=max(v)))
}


# Evaluate frozen stress samples with paired replicate-level q95 uncertainty.
stress_frozen_q95_ci <- function(T,models,target,B=500L,seed=1L) {
 stopifnot(length(models)>0L)
 base<-(T[,match("mean",colnames(T))]-target)^2
 do.call(rbind,lapply(seq_along(models),function(i) {
  e<-(model_predict(T,models[[i]])-target)^2
  ci<-t2_q95_ci_v3(e,base,B=B,seed=seed+i)
  data.frame(model=models[[i]]$id,q95=ci$q95,
    q95_lower=ci$q95_lower,q95_upper=ci$q95_upper,
    q95_delta=ci$delta,q95_delta_lower=ci$delta_lower,
    q95_delta_upper=ci$delta_upper,bootstrap_B=B)
 }))
}
