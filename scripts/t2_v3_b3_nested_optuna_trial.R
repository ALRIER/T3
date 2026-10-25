#!/usr/bin/env Rscript
a<-commandArgs(TRUE)
if(length(a)!=6L)stop('Usage: FAMILY SEED OUTER_FOLD INNER_FOLD ENGINE PARAMS_JSON')
fam<-a[1];seed<-as.integer(a[2]);outer<-as.integer(a[3]);inner<-as.integer(a[4]);engine<-a[5];path<-a[6]
if(!engine%in%c('ga','nsga2','de','dirichlet')||!seed%in%0:9||!outer%in%1:5||!inner%in%1:3)stop('Invalid nested fold')
if(!requireNamespace('jsonlite',quietly=TRUE))stop('jsonlite required')
source('R/00_shared/load_all.R');t2_load('.')
source('R/00_shared/pipeline.R')
source('R/00_shared/v3_scientific_adapter.R')
source('R/00_shared/v3_downstream.R')
params<-jsonlite::fromJSON(path)
source('R/02_discovery/t2_v3_b3_nested_folds.R')
parts<-t2_b3_nested_partitions(fam,seed,outer,inner)
training_ids<-parts$training
validation_ids<-parts$validation
if(length(intersect(training_ids,validation_ids))||length(training_ids)<50L||!length(validation_ids))stop('Nested fold leakage')
training<-t2_v3_discovery_input(fam,seed,selected=training_ids)$scenarios
cfg<-ga_config
cfg$population<-as.integer(params$population)
cfg$generations<-as.integer(params$generations)
cfg$mutation_rate<-as.numeric(params$mutation_rate)
cfg$crossover_probability<-as.numeric(params$crossover_probability)
cfg$discovery_weight_regularization_lambda<-as.numeric(params$regularization_lambda)
# Adaptive stopping remains unchanged.
set.seed(t2_seed(paste('B3_nested',fam,seed,outer,inner,engine,basename(path)),821L))
fit<-switch(engine,ga=ga_discover(training,cfg,seed=sample.int(1000000000,1),shard=NULL),
nsga2=nsga_discover(training,cfg,seed=sample.int(1000000000,1),shard=NULL),
de=de_discover(training,cfg,seed=sample.int(1000000000,1),
 F=as.numeric(params$F),CR=as.numeric(params$CR),shard=NULL),
dirichlet=dirichlet_discover(training,cfg,seed=sample.int(1000000000,1),
 alpha=as.numeric(params$alpha),n_draws=cfg$population*cfg$generations,shard=NULL))
O<-as.matrix(fit$objectives);W<-as.matrix(fit$weights)
scale<-pmax(colMeans(abs(O)),1e-12)
winner<-which.min(rowSums(sweep(O,2L,scale,'/')))
w<-W[,winner,drop=FALSE]
rm(training,fit);invisible(gc(FALSE))
val<-t2_v3_discovery_input(fam,seed,selected=validation_ids)$scenarios
stats<-t(vapply(val,function(sc)as.numeric(evaluate_weights(sc$T,w,sc$target)$objectives[1,]),numeric(2)))
base<-t(vapply(val,function(sc){
 e<-(sc$T[,1L]-sc$target)^2
 c(mean(e),unname(quantile(e,.95,type=8)))
},numeric(2)))
score<-mean(stats[,1]/pmax(base[,1],1e-12))+mean(stats[,2]/pmax(base[,2],1e-12))
cat(jsonlite::toJSON(list(score=score,outer=outer,inner=inner,engine=engine,
 validation_scenarios=length(validation_ids)),auto_unbox=TRUE),'\n')
