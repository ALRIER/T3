#!/usr/bin/env Rscript
# Posthoc Discovery diagnostics; descriptive only, never confirmatory.
args<-commandArgs(trailingOnly=TRUE)
if(length(args)!=2L)stop('Usage FAMILY SEED')
fam<-args[[1]];seed<-as.integer(args[[2]])
if(!fam%in%c('normal','lognormal','weibull','invgauss','exgaussian','exwald')||!seed%in%0:9)stop('Invalid Discovery family/seed')
source('R/00_shared/load_all.R');t2_load('.')
source('R/00_shared/pipeline.R')
source('R/00_shared/v3_scientific_adapter.R')
source('R/00_shared/v3_downstream.R')
source('R/00_shared/v3_inference.R')
p<-file.path('artifacts','discovery_v3',fam,sprintf('seed%02d',seed),'discovery.rds')
if(!file.exists(p))stop('Missing frozen Discovery')
fit<-readRDS(p);mods<-fit$models
if(length(fit$engines)!=4L || length(mods)!=8L)stop('Incomplete candidate registry')
out<-file.path('artifacts','discovery_posthoc_v3',fam,sprintf('seed%02d',seed))
dir.create(out,recursive=TRUE,showWarnings=FALSE)
results<-file.path(out,'training_diagnostics.csv');nullfile<-file.path(out,'null_diagnostics.csv')
if(file.exists(results))file.remove(results)
if(file.exists(nullfile))file.remove(nullfile)
for(id in 0:120){
 sc<-t2_v3_read_scenario('discovery',fam,seed,1000L,id)
 set.seed(t2_seed(paste(fam,seed,id,'discovery_posthoc'),908L))
 z<-t2_v3_infer_scenario(sc,mods,seed,seed,1000L,B=as.integer(ga_config$bootstrap_B))
 z$family<-fam;z$analysis_kind<-'IN_SAMPLE_DESCRIPTIVE'
 write.table(z,results,sep=',',append=id!=0L,col.names=id==0L,row.names=FALSE)
 if(id==0L){
  set.seed(t2_seed(paste(fam,seed,'null'),909L))
  fpr<-t2_v3_null_fpr(sc,mods,seed,seed,Bnull=as.integer(ga_config$bootstrap_B))
  fpr$analysis_kind<-'EXCHANGEABILITY_NULL_DIAGNOSTIC'
  write.csv(fpr,nullfile,row.names=FALSE)
 }
 rm(sc,z);if(id%%20L==0L)invisible(gc(verbose=FALSE))
}
W<-do.call(rbind,lapply(mods[5:8],function(m) data.frame(engine=m$id,
  component=ESTIMATOR_NAMES,weight=m$weights,stringsAsFactors=FALSE)))
write.csv(W,file.path(out,'weights_by_component.csv'),row.names=FALSE)
writeLines(c('NOT_CONFIRMATORY: post-selection in-sample statistics',
             'Confidence intervals are descriptive paired bootstrap intervals',
             'False positive diagnostic assumes paired label exchangeability',
             'Independent claims require reserved Held-out tests'),
           file.path(out,'interpretation.txt'))
cat('V3_DISCOVERY_POSTHOC_PASS',fam,seed,'\n')

# Publish canonical B3-named counterparts without breaking existing downstream references.
source('R/00_shared/t2_v3_b3_naming.R')
t2_b3_publish(out)
