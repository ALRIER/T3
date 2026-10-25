#!/usr/bin/env Rscript
source('R/00_shared/load_all.R');t2_load('.')
source('R/00_shared/pipeline.R')
source('R/02_discovery/t3_predeclared_w_selection.R')
set.seed(412L)
scenarios<-lapply(1:5,function(i) {
 T<-matrix(rnorm(30L*26L),30L,26L)
 colnames(T)<-ESTIMATOR_NAMES
 list(T=T,target=0)
})
s<-t3_training_reference_scales(scenarios)
stopifnot(identical(names(s),c('mse','q95')),all(s>0))
mk<-function() {
 W<-matrix(rexp(26L*3L),26L,3L);W<-sweep(W,2,colSums(W),'/')
 O<-matrix(c(1,3,2,2,3,1),ncol=2)
 colnames(O)<-c('mse','q95')
 list(weights=W,objectives=O)
}
engines<-setNames(replicate(4,mk(),simplify=FALSE),c('ga','nsga2','de','dirichlet'))
z<-t3_select_models(engines,scenarios)
stopifnot(length(z$models)==30L,
  identical(vapply(z$models[1:26],function(x)x$id,character(1)),ESTIMATOR_NAMES),
  identical(vapply(z$models[27:30],function(x)x$id,character(1)),names(engines)),
  all(vapply(z$selection,function(x)identical(x$scales,z$scales),logical(1))),
  all(vapply(z$selection,function(x)abs(sum(x$weights)-1)<1e-10,logical(1))))
d<-score_model_set(scenarios[[1]]$T,z$models,0)
stopifnot(nrow(d)==30L,all(is.finite(d$mse)),all(is.finite(d$q95)))
cat('T3_26_BENCHMARK_COMMON_W_SELECTION_PASS\n')
