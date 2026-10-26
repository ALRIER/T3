#!/usr/bin/env Rscript
args<-commandArgs(trailingOnly=TRUE)
if(length(args)!=3L)stop('Usage: FAMILY SEED N')
family<-args[[1]];seed<-as.integer(args[[2]]);n<-as.integer(args[[3]])
source('R/00_shared/load_all.R');t2_load('.')
source('R/00_shared/pipeline.R')
source('R/00_shared/v3_scientific_adapter.R')
source('R/00_shared/v3_downstream.R')
source('R/00_shared/t3_b3_partitions.R')
if(!seed %in% 0:9)stop('Discovery cannot use reserved seeds')
if(!n%in%t2_v3_sample_sizes('discovery'))stop('Invalid discovery n')
scenario_ids<-t3_b3_partition_ids('discovery_support')
d<-t2_v3_discovery_input(family,seed,n,500L,scenario_ids)
stopifnot(length(d$scenarios)==length(scenario_ids),all(vapply(d$scenarios,function(s)
 length(s$eligible)==26L && all(s$eligible) && all(is.finite(s$benchmark$mse)),logical(1))))
shard<-sprintf('v3-discovery-%s-seed%02d-n%d',family,seed,n)
start_ram <- gc(reset=TRUE)
hpo_path<-Sys.getenv('T3_B3_HPO_REGISTRY','')
if(!nzchar(hpo_path)||!file.exists(hpo_path))stop('Production Discovery requires a frozen nested-CV HPO registry')
if(!requireNamespace('jsonlite',quietly=TRUE))stop('jsonlite required for frozen HPO registry')
hpo<-jsonlite::fromJSON(hpo_path,simplifyVector=FALSE)
if(!identical(hpo$protocol,'T3_B3_nested_5x3_hpo_freeze_v2_equal_budget')||
   !identical(hpo$family,family)||as.integer(hpo$seed)!=seed||as.integer(hpo$sample_n)!=n||
   !identical(as.integer(hpo$outer_folds),5L)||!identical(as.integer(hpo$inner_folds),3L)||
   !setequal(names(hpo$engines),c('ga','nsga2','de','dirichlet')))
  stop('Frozen nested HPO registry provenance mismatch')
fit<-t2_run_discovery(d,'full',shard,'all',hyperparameters=hpo$engines)
# Optional, capped 2x2 scientific ablation. It uses Discovery inputs only.
# Run on prospectively chosen representative seeds; never select production W from it.
if(identical(Sys.getenv('T3_RUN_ABLATION','0'),'1')) {
  abr<-file.path('artifacts','discovery_v3',family,sprintf('seed%02d',seed),
                 sprintf('n%d',n),'ablation')
  dir.create(abr,recursive=TRUE,showWarnings=FALSE)
  subids<-seq_len(min(length(d$scenarios),as.integer(
     Sys.getenv('T3_ABLATION_SCENARIOS','32'))))
  if(length(subids)<4L)stop('Ablation requires at least four scenarios')
  absc<-d$scenarios[subids]
  for(reg in c(FALSE,TRUE))for(dro in c(FALSE,TRUE)) {
    acfg<-ga_config
    acfg$population<-min(12L,as.integer(ga_config$population))
    acfg$generations<-min(6L,as.integer(ga_config$generations))
    acfg$discovery_weight_regularization_lambda<-
      if(reg)ga_config$discovery_weight_regularization_lambda else 0
    acfg$discovery_dro_tail_fraction<-
      if(dro)ga_config$discovery_dro_tail_fraction else 0
    name<-sprintf('reg%s_dro%s',as.integer(reg),as.integer(dro))
    z<-ga_discover(absc,acfg,seed=t2_seed(paste(shard,'ablation',name),131L),shard=NULL)
    attr(z,'ablation_config')<-list(regularization=reg,DRO=dro,
       role='discovery_training_diagnostic',n_scenarios=length(absc))
    saveRDS(z,file.path(abr,paste0(name,'.rds')))
  }
  writeLines('Exploratory training-only ablation; no selection or inference on heldout.',
             file.path(abr,'README.txt'))
}
rm(d); invisible(gc(verbose=FALSE))
stopifnot(length(fit$engines)==4L,length(fit$models)>=8L)
for(m in Filter(function(x)!is.null(x$weights),fit$models))
 if(length(m$weights)!=26L || any(!is.finite(m$weights)) || abs(sum(m$weights)-1)>1e-8)stop('Frozen W invalid')
out<-file.path('artifacts','discovery_v3',family,sprintf('seed%02d',seed),sprintf('n%d',n))
dir.create(out,recursive=TRUE,showWarnings=FALSE)
saveRDS(fit,file.path(out,'discovery.rds'))
if(!is.null(fit$computational_ledger))
 write.csv(fit$computational_ledger,file.path(out,'computational_budget_ledger.csv'),row.names=FALSE)
if(!is.null(fit$convergence_audit))
 write.csv(fit$convergence_audit,file.path(out,'normalized_convergence.csv'),row.names=FALSE)
# Publish only the frozen training W; no heldout/stress data enters this audit.
w_registry<-do.call(rbind,lapply(Filter(function(m)!is.null(m$weights),fit$models),
 function(m)data.frame(family=family,engine=m$id,seed=seed,fold=0L,
                        sample_n=n,component=seq_len(26L),
                        weight=as.numeric(m$weights),stringsAsFactors=FALSE)))
write.csv(w_registry,file.path(out,'frozen_w_registry.csv'),row.names=FALSE)
t3_b3_write_partition_manifest(file.path(out,'scenario_partition.csv'))
file.copy(hpo_path,file.path(out,'frozen_hyperparameters.json'),overwrite=FALSE)
writeLines(c('Production Discovery was fit only on the predeclared discovery_support partition.',
 'Nested 5x3 tuning is a separate training-only protocol; this production fit is not an in-sample CV claim.',
 'No Discovery p-value, BH-FDR result, or false-positive rate is a confirmatory result.'),
 file.path(out,'discovery_scope.txt'))
write.csv(data.frame(family=family,seed=seed,n=n,reps=500L,scenarios=length(scenario_ids),
  engines=paste(names(fit$engines),collapse=';'),
  sha256=t2_sha256(file.path(out,'discovery.rds'))),
 file.path(out,'manifest.csv'),row.names=FALSE)
write.csv(data.frame(stage='Discovery',version='T2_V3_B3',family=family,seed=seed,
 memory_used_mb=sum(gc()[,2]),r_max_vcells_mb=max(gc()[,6])),
 file.path(out,'resource_report.csv'),row.names=FALSE)
# Separate immutable cross-stage envelope; never store training matrices in it.
t3_stage_publish('discovery',sprintf('b3_%s_n%d',family,n),
  list(model_path=file.path(out,'discovery.rds'),
       model_sha256=t2_sha256(file.path(out,'discovery.rds')),
       scenario_ids=scenario_ids),
  family,seed,n,500L,file.path(out,'stage_contract.rds'))
cat('V3_DISCOVERY_PASS',family,seed,'\n')

# Publish canonical B3-named counterparts without breaking existing downstream references.
source('R/00_shared/t2_v3_b3_naming.R')
t2_b3_publish(out)
