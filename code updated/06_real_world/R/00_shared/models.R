# Common interface: all engines receive the SAME prepared R x 26 component matrix.
# Mean / median / trimmed20 / Huber are the initial four baseline controls;
# additional learned competitors can register a frozen weight vector with a name.
reference_models <- function() c('mean','median','trimmed20','huber')
assert_model_registry <- function() {
  stopifnot(exists('ESTIMATOR_REGISTRY'), length(ESTIMATOR_REGISTRY)==26L,
            all(reference_models() %in% names(ESTIMATOR_REGISTRY)))
  invisible(TRUE)
}
new_frozen_model <- function(id, weights=NULL, component=NULL, family=NULL) {
  stopifnot(is.character(id),length(id)==1L, nzchar(id))
  if(!is.null(weights)) { stopifnot(length(weights)==26L,all(is.finite(weights)),all(weights>=0),sum(weights)>0);weights<-weights/sum(weights) }
  if(is.null(weights) && is.null(component)) stop('Model requires weights or component')
  list(id=id,weights=weights,component=component,family=family)
}
reference_model_set <- function() lapply(reference_models(),function(nm)new_frozen_model(nm,component=nm))
model_predict <- function(T,model,eligible=rep(TRUE,26L)) {
  stopifnot(is.matrix(T),ncol(T)==26L,all(is.finite(T)))
  if(!is.null(model$weights)) return(drop(T%*%normalize_weights(matrix(model$weights,26L),eligible)))
  ix<-match(model$component,colnames(T))
  if(is.na(ix)) ix<-match(model$component,ESTIMATOR_NAMES)
  if(is.na(ix)||!eligible[ix]) stop(paste('Blocked/missing component',model$component))
  T[,ix]
}
score_model_set <- function(T,models,target,eligible=rep(TRUE,26L)) {
  stopifnot(is.finite(target),length(target)==1L)
  do.call(rbind,lapply(models,function(model){
    e<-(model_predict(T,model,eligible)-target)^2
    data.frame(model=model$id,mse=mean(e),q95=unname(quantile(e,.95,type=8)),
               n_rep=length(e),stringsAsFactors=FALSE)
  }))
}
# Numeric sample-level interface, used by Monte Carlo, heldout, and external data.
component_vector <- function(x) {
  x<-as.numeric(x);x<-x[is.finite(x)]
  if(length(x)<5L) stop('At least five finite observations needed')
  out<-setNames(rep(NA_real_,length(ESTIMATOR_NAMES)),ESTIMATOR_NAMES)
  out['mean']<-mean(x)
  out['median']<-stats::median(x)
  out['trimmed20']<-mean(x,trim=.20)
  # Revised core library: every component consumes the complete real-valued sample.
  out['trimmed10']<-mean(x,trim=.10)
  q<-stats::quantile(x,probs=c(.05,.10,.20,.25,.50,.75,.80,.90,.95),
                     names=FALSE,type=8,na.rm=TRUE)
  out['trimean']<-(q[4L]+2*q[5L]+q[6L])/4
  out['winsorized_0.05']<-mean(pmin(pmax(x,q[1L]),q[9L]))
  out['winsorized_0.1']<-mean(pmin(pmax(x,q[2L]),q[8L]))
  out['winsorized_0.2']<-mean(pmin(pmax(x,q[3L]),q[7L]))
  out['mom_k5']<-median_of_means_safe(x,5L)
  out['mom_k10']<-median_of_means_safe(x,10L)
  out['mom_k20']<-median_of_means_safe(x,20L)
  slow<-setdiff(ESTIMATOR_NAMES,names(out)[!is.na(out)])
  for(nm in slow) {
    z<-tryCatch(as.numeric(ESTIMATOR_REGISTRY[[nm]](x))[1],error=function(e) NA_real_)
    if(!is.finite(z)) stop('Estimator returned nonfinite component')
    out[nm]<-z
  }
  out
}
component_matrix <- function(samples) {
  out<-t(vapply(samples,component_vector,numeric(26L)))
  colnames(out)<-ESTIMATOR_NAMES
  out
}
