# B3 deterministic five-fold cross-validation across Monte Carlo scenarios.
# Diagnostic stage: held-fold scoring of frozen candidate W; no reoptimization
# and no independent confirmation claim.
t2_b3_discovery_cv <- function(scenarios,models,k=5L) {
 stopifnot(length(scenarios)==121L,identical(as.integer(k),5L))
 ids<-vapply(scenarios,function(z)as.integer(z$scenario_id),integer(1))
 if(anyDuplicated(ids)||!identical(sort(ids),0:120))stop('CV scenario contract mismatch')
 fold<-as.integer(ids %% k)+1L
 stopifnot(length(unique(fold))==5L,all(tabulate(fold,k)>=24L))
 rows<-vector('list',length(scenarios))
 for(i in seq_along(scenarios)){
   z<-score_model_set(scenarios[[i]]$T,models,scenarios[[i]]$target)
   z$fold<-fold[[i]];z$scenario_id<-ids[[i]]
   rows[[i]]<-z
 }
 x<-do.call(rbind,rows)
 agg<-aggregate(cbind(mse,q95)~model+fold,x,mean)
 count<-aggregate(scenario_id~fold,x,function(v)length(unique(v)))
 names(count)[2]<-'scenario_count'
 agg<-merge(agg,count,by='fold')
 stopifnot(length(unique(agg$fold))==5L)
 list(folds=agg,assignments=data.frame(scenario_id=ids,fold=fold),
      scope='post_training_frozen_W_diagnostic_not_out_of_fold_retraining')
}
