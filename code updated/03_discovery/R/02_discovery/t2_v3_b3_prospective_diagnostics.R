# Diagnostics for prospective B3 Discovery. These functions never select
# on held-out/stress data. Intended for independent outer CV fold scoring.
t2_b3_full_pareto <- function(scores) {
 stopifnot(is.data.frame(scores),all(c('model','mse','q95')%in%names(scores)))
 if(anyDuplicated(scores$model)||any(!is.finite(scores$mse))||
    any(!is.finite(scores$q95)))stop('Invalid model scores')
 x<-as.matrix(scores[,c('mse','q95')])
 dominated<-vapply(seq_len(nrow(x)),function(i)
   any(vapply(setdiff(seq_len(nrow(x)),i),function(j)
     all(x[j,]<=x[i,])&&any(x[j,]<x[i,]),logical(1))),logical(1))
 scores$pareto_all_30<-!dominated
 scores
}
t2_b3_regime_diagnostics <- function(scenarios,models,role='outer_cv_validation') {
 if(!role%in%c('outer_cv_validation','training_diagnostic'))
   stop('Only Discovery-local nonconfirmatory roles supported')
 stopifnot(length(models)==30L,
           sum(vapply(models,function(x)is.null(x$weights),logical(1)))==26L)
 rows<-lapply(scenarios,function(sc) {
   z<-t2_b3_full_pareto(score_model_set(sc$T,models,sc$target))
   z$scenario_id<-sc$scenario_id
   z$band<-if(is.null(sc$band))'unknown' else as.character(sc$band)
   z$mechanism<-if(is.null(sc$mechanism))'unknown' else as.character(sc$mechanism)
   z$mad_scale<-if(is.null(sc$mad_scale))NA_real_ else sc$mad_scale
   z$contamination<-if(is.null(sc$contamination))NA_real_ else sc$contamination
   z$role<-role
   z
 })
 z<-do.call(rbind,rows)
 split_z<-split(z,z$scenario_id)
 z$gain_mse_against_best_of_26<-NA_real_
 z$gain_q95_against_best_of_26<-NA_real_
 for(g in split_z) {
   ix<-which(z$scenario_id==g$scenario_id[1])
   benchmark<-g[vapply(models,function(x)is.null(x$weights),logical(1)),,drop=FALSE]
   bm<-min(benchmark$mse);bq<-min(benchmark$q95)
   z$gain_mse_against_best_of_26[ix]<-100*(bm-g$mse)/max(bm,1e-12)
   z$gain_q95_against_best_of_26[ix]<-100*(bq-g$q95)/max(bq,1e-12)
 }
 z$joint_gain_26<-z$gain_mse_against_best_of_26>0&
                   z$gain_q95_against_best_of_26>0
 z
}
t2_b3_weight_stability <- function(fold_models,threshold=1/26) {
 stopifnot(length(fold_models)>=3L)
 ids<-vapply(fold_models[[1]],function(m)m$id,character(1))
 if(!all(vapply(fold_models,function(a)
     identical(vapply(a,function(m)m$id,character(1)),ids),logical(1))))
   stop('Inconsistent model registry across folds')
 rows<-lapply(seq_along(ids),function(j){
  w<-do.call(cbind,lapply(fold_models,function(a)a[[j]]$weights))
  stopifnot(nrow(w)==26L,all(is.finite(w)))
  data.frame(model=ids[j],component=seq_len(26L),
    mean_weight=rowMeans(w),sd_weight=apply(w,1,stats::sd),
    selection_rate=rowMeans(w>=threshold),
    stringsAsFactors=FALSE)
 })
 do.call(rbind,rows)
}
t2_b3_single_component_ablation <- function(T,model,target) {
 stopifnot(!is.null(model$weights),length(model$weights)==26L)
 base<-score_model_set(T,list(model),target)
 do.call(rbind,lapply(seq_len(26L),function(i){
   w<-model$weights
   if(w[i]>=1-1e-12)return(data.frame(component=i,delta_mse=NA_real_,
                                            delta_q95=NA_real_))
   w[i]<-0
   m<-new_frozen_model(paste0(model$id,'_without_',i),weights=w)
   z<-score_model_set(T,list(m),target)
   data.frame(component=i,delta_mse=z$mse-base$mse,
              delta_q95=z$q95-base$q95)
 }))
}
