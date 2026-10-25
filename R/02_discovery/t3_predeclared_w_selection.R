# Prospectively fixed, equal-weight normalized MSE/q95 selection.
# Objective scales are derived exclusively from the 26 classical estimators
# on the current training scenarios, never from optimizer archives or test data.
t3_training_reference_scales <- function(scenarios) {
 stopifnot(length(scenarios)>0L)
 x<-t(vapply(scenarios,function(z){
   if(!is.matrix(z$T)||ncol(z$T)!=26L)stop('Invalid 26-estimator component matrix')
   sc<-score_model_set(z$T,lapply(ESTIMATOR_NAMES,function(nm)
     new_frozen_model(nm,component=nm)),z$target)
   c(min(sc$mse),min(sc$q95))
 },numeric(2L)))
 setNames(pmax(colMeans(x),.Machine$double.eps),c('mse','q95'))
}
t3_select_weights <- function(result,scales) {
 O<-as.matrix(result$objectives);W<-as.matrix(result$weights)
 if(!all(c('mse','q95')%in%colnames(O)) && ncol(O)==2L)
   colnames(O)<-c('mse','q95')
 stopifnot(nrow(W)==26L,ncol(W)==nrow(O),all(is.finite(O)),
   all(is.finite(W)),all(W>=0),all(c('mse','q95')%in%names(scales)),
   all(is.finite(scales)),all(scales>0))
 # Common scalarization; no implicit algorithm-specific scaling.
 loss<-rowMeans(sweep(O[,c('mse','q95'),drop=FALSE],
                         2L,scales[c('mse','q95')],'/'))
 idx<-order(loss,O[,'mse'],O[,'q95'],seq_len(nrow(O)))[1L]
 list(index=idx,weights=W[,idx],normalized_loss=loss[idx],
      mse=O[idx,'mse'],q95=O[idx,'q95'],
      scales=scales,policy='T3_EQUAL_MSE_Q95_BASELINE26_TRAIN_ONLY_V1')
}
t3_select_models <- function(engines,training_scenarios) {
 scales<-t3_training_reference_scales(training_scenarios)
 chosen<-lapply(names(engines),function(engine)
   t3_select_weights(engines[[engine]],scales))
 names(chosen)<-names(engines)
 models<-lapply(ESTIMATOR_NAMES,function(nm)new_frozen_model(nm,component=nm))
 models<-c(models,lapply(names(chosen),function(engine)
   new_frozen_model(engine,weights=chosen[[engine]]$weights,family=engine)))
 stopifnot(length(models)==26L+length(engines))
 list(models=models,selection=chosen,scales=scales)
}
