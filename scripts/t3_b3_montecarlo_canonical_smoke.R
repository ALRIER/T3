#!/usr/bin/env Rscript
# Small-format integration fixture: 321 canonical R scenarios, 3 replicates.
source('R/00_shared/load_all.R');t2_load('.')
source('R/00_shared/v3_scientific_adapter.R')
grid<-read.csv('config/T2_V3_B3_prospective_321_grid.csv',stringsAsFactors=FALSE)
stopifnot(nrow(grid)==321L,identical(as.integer(grid$scenario_id),0:320))
old<-Sys.getenv('T2_V3_SCIENTIFIC_ROOT',unset=NA_character_)
root<-tempfile('t3-mc321-r-smoke-')
Sys.setenv(T2_V3_SCIENTIFIC_ROOT=root)
family<-'normal';seed<-0L;n<-200L;reps<-3L
set.seed(912L)
scenarios<-lapply(0:320,function(id){
 T<-matrix(rnorm(reps*26L),nrow=reps,ncol=26L)
 colnames(T)<-ESTIMATOR_NAMES
 list(scenario_id=as.integer(id),T=T,target=0,
      component_names=ESTIMATOR_NAMES)
})
canonical<-list(protocol=t2_v3_protocol(),role='discovery',family=family,
 seed_index=seed,n=n,replications=reps,component_names=ESTIMATOR_NAMES,
 grid=grid,scenarios=scenarios)
out<-t2_v3_block_dir('discovery',family,seed,n,reps)
dir.create(out,recursive=TRUE,showWarnings=FALSE)
saveRDS(canonical,file.path(out,'canonical.rds'))
got<-t2_v3_read_block('discovery',family,seed,n,reps,selected=c(0L,1L,320L))
stopifnot(length(got$scenarios)==3L,identical(vapply(got$scenarios,
 function(x)x$scenario_id,integer(1)),c(0L,1L,320L)))
stopifnot(inherits(try(t2_v3_block_dir('discovery',family,10L,n,reps),
 silent=TRUE),'try-error'))
stopifnot(inherits(try(t2_v3_read_block('discovery',family,seed,n,reps,
 selected=c(0L,321L)),silent=TRUE),'try-error'))
cat('T3_MC_321_R_CANONICAL_DISCOVERY_READER_PASS\\n')
if(is.na(old))Sys.unsetenv('T2_V3_SCIENTIFIC_ROOT') else Sys.setenv(T2_V3_SCIENTIFIC_ROOT=old)
unlink(root,recursive=TRUE)
