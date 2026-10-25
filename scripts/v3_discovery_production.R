#!/usr/bin/env Rscript
args<-commandArgs(trailingOnly=TRUE)
if(length(args)!=2L)stop('Usage: FAMILY SEED')
family<-args[[1]];seed<-as.integer(args[[2]])
source('R/00_shared/load_all.R');t2_load('.')
source('R/00_shared/pipeline.R')
source('R/00_shared/v3_scientific_adapter.R')
source('R/00_shared/v3_downstream.R')
if(!seed %in% 0:9)stop('Discovery cannot use reserved seeds')
d<-t2_v3_discovery_input(family,seed,1000L,500L,0:120)
stopifnot(length(d$scenarios)==121L,all(vapply(d$scenarios,function(s)
 length(s$eligible)==26L && all(s$eligible) && all(is.finite(s$benchmark$mse)),logical(1))))
shard<-sprintf('v3-discovery-%s-seed%02d',family,seed)
start_ram <- gc(reset=TRUE)
fit<-t2_run_discovery(d,'full',shard,'all')
source('R/02_discovery/t2_v3_b3_cv5.R')
cv5<-t2_b3_discovery_cv(d$scenarios,fit$models,k=ga_config$discovery_cv_folds)
rm(d); invisible(gc(verbose=FALSE))
stopifnot(length(fit$engines)==4L,length(fit$models)>=8L)
for(m in Filter(function(x)!is.null(x$weights),fit$models))
 if(length(m$weights)!=26L || any(!is.finite(m$weights)) || abs(sum(m$weights)-1)>1e-8)stop('Frozen W invalid')
out<-file.path('artifacts','discovery_v3',family,sprintf('seed%02d',seed))
dir.create(out,recursive=TRUE,showWarnings=FALSE)
saveRDS(fit,file.path(out,'discovery.rds'))
write.csv(cv5$folds,file.path(out,'cv5_fold_performance.csv'),row.names=FALSE)
write.csv(cv5$assignments,file.path(out,'cv5_scenario_assignments.csv'),row.names=FALSE)
writeLines(cv5$scope,file.path(out,'cv5_scope.txt'))
rm(cv5);invisible(gc(verbose=FALSE))
write.csv(data.frame(family=family,seed=seed,n=1000L,reps=500L,scenarios=121L,
  engines=paste(names(fit$engines),collapse=';'),
  sha256=t2_sha256(file.path(out,'discovery.rds'))),
 file.path(out,'manifest.csv'),row.names=FALSE)
write.csv(data.frame(stage='Discovery',version='T2_V3_B3',family=family,seed=seed,
 memory_used_mb=sum(gc()[,2]),r_max_vcells_mb=max(gc()[,6])),
 file.path(out,'resource_report.csv'),row.names=FALSE)
cat('V3_DISCOVERY_PASS',family,seed,'\n')

# Publish canonical B3-named counterparts without breaking existing downstream references.
source('R/00_shared/t2_v3_b3_naming.R')
t2_b3_publish(out)
