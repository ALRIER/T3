#!/usr/bin/env Rscript
# Strict T2 V3 B3 5-fold refit: five independent train/validation partitions.
args<-commandArgs(trailingOnly=TRUE)
if(length(args)!=3L)stop('Usage: FAMILY DISCOVERY_SEED FOLD_1_TO_5')
fam<-args[[1L]];seed<-as.integer(args[[2L]]);fold<-as.integer(args[[3L]])
if(!fam%in%c('normal','lognormal','weibull','invgauss','exgaussian','exwald')||
   is.na(seed)||!seed%in%0:9||is.na(fold)||!fold%in%1:5)stop('Invalid CV shard')
source('R/00_shared/load_all.R');t2_load('.')
source('R/00_shared/pipeline.R')
source('R/00_shared/v3_scientific_adapter.R')
source('R/00_shared/v3_downstream.R')
source('R/00_shared/t2_v3_b3_resources.R')
source('R/00_shared/t2_v3_b3_naming.R')
stopifnot(ga_config$discovery_cv_folds==5L)
source('R/02_discovery/t2_v3_b3_nested_folds.R')
parts<-t2_b3_nested_partitions(fam,seed,fold)
ids<-parts$outer$scenario_id
foldid<-parts$outer$fold
training<-parts$training
validation<-parts$validation
stopifnot(length(training)+length(validation)==121L,!any(training%in%validation))
out<-file.path('artifacts','T2_V3_B3_discovery_cv5_refit',fam,sprintf('seed%02d',seed),sprintf('fold%02d',fold))
dir.create(out,recursive=TRUE,showWarnings=FALSE)
source_root<-t2_v3_block_dir('discovery',fam,seed,1000L)
t2_b3_inputs_manifest(file.path(source_root,sprintf('scenario_%04d.rds',ids)),out,'discovery_cv5_refit')
t2_b3_ram_guard('discovery_cv5_refit',out,'start')
d<-t2_v3_discovery_input(fam,seed,1000L,500L,training)
shard<-sprintf('T2_V3_B3_cv5_%s_seed%02d_fold%d',fam,seed,fold)
# Outer fold is never supplied to Optuna. Refit each engine with the
# configurations selected by three internal folds.
if(!requireNamespace('jsonlite',quietly=TRUE))stop('jsonlite required')
hpo_root<-file.path('artifacts','T2_V3_B3_nested_optuna',fam,
 sprintf('seed%02d',seed),sprintf('fold%02d',fold))
engines<-list()
for(engine in c('ga','nsga2','de','dirichlet')){
 selected<-file.path(hpo_root,paste0(engine,'_best.json'))
 if(!file.exists(selected))stop('Missing nested Optuna configuration: ',selected)
 chosen<-jsonlite::fromJSON(selected)$best_params
 cfg<-ga_config
 cfg$population<-as.integer(chosen$population)
 cfg$generations<-as.integer(chosen$generations)
 cfg$mutation_rate<-as.numeric(chosen$mutation_rate)
 cfg$crossover_probability<-as.numeric(chosen$crossover_probability)
 cfg$discovery_weight_regularization_lambda<-as.numeric(chosen$regularization_lambda)
 engine_seed<-t2_seed(paste(shard,engine),7231L)
 engines[[engine]]<-switch(engine,
   ga=ga_discover(d$scenarios,cfg,seed=engine_seed,shard=NULL),
   nsga2=nsga_discover(d$scenarios,cfg,seed=engine_seed,shard=NULL),
   de=de_discover(d$scenarios,cfg,seed=engine_seed,F=chosen$F,CR=chosen$CR,shard=NULL),
   dirichlet=dirichlet_discover(d$scenarios,cfg,seed=engine_seed,
       alpha=chosen$alpha,n_draws=cfg$population*cfg$generations,shard=NULL))
}
fit<-list(engines=engines,models=t2_models(engines),config=ga_config,
 training_seed_index=seed,nested_cv=TRUE,outer_fold=fold)
rm(d);invisible(gc(verbose=FALSE))
stopifnot(length(fit$engines)==4L)
for(m in Filter(function(x)!is.null(x$weights),fit$models))
 if(length(m$weights)!=26L||any(!is.finite(m$weights))||abs(sum(m$weights)-1)>1e-8)
   stop('Fold-trained W invalid')
scores<-file.path(out,'out_of_fold_scores.csv')
for(i in seq_along(validation)){
 sc<-t2_v3_read_scenario('discovery',fam,seed,1000L,validation[[i]])
 z<-score_model_set(sc$T,fit$models,sc$target)
 z$family<-fam;z$seed<-seed;z$fold<-fold;z$scenario_id<-validation[[i]]
 z$training_scenarios<-length(training)
 write.table(z,scores,sep=',',append=i>1L,col.names=i==1L,row.names=FALSE)
 rm(sc,z);if(i%%10L==0L)invisible(gc(verbose=FALSE))
}
saveRDS(fit,file.path(out,'cv5_refit_models.rds'))
write.csv(data.frame(scenario_id=ids,fold=foldid,
  role=ifelse(foldid==fold,'validation','training')),file.path(out,'cv5_partition.csv'),row.names=FALSE)
writeLines(c('Strict out-of-fold 5-fold refitting; no heldout/stress seeds used',
 'Fold-specific weights are research diagnostics, not replacements for frozen production Discovery W',
 'Do not use in-sample CV score report as independent confirmatory evidence'),
 file.path(out,'cv5_protocol.txt'))
t2_b3_ram_guard('discovery_cv5_refit',out,'done')
t2_b3_publish(out)
cat('T2_V3_B3_DISCOVERY_CV5_REFIT_PASS',fam,seed,fold,'\\n')
