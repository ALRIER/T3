#!/usr/bin/env Rscript
args<-commandArgs(TRUE)
if(length(args)!=2L)stop('Usage FAMILY SEED')
fam<-args[1L];seed<-as.integer(args[2L])
if(!seed%in%0:9)stop('Invalid Discovery seed')
source('R/00_shared/load_all.R');t2_load('.')
root<-file.path('artifacts','T2_V3_B3_discovery_cv5_refit',fam,sprintf('seed%02d',seed))
paths<-file.path(root,sprintf('fold%02d',1:5),'cv5_refit_models.rds')
if(!all(file.exists(paths)))stop('All five refitted outer folds required for stability selection')
records<-list()
for(fold in 1:5){
 fit<-readRDS(paths[[fold]])
 mods<-Filter(function(x)!is.null(x$weights),fit$models)
 if(length(mods)!=4L)stop('Four engine W expected')
 for(m in mods){
  if(length(m$weights)!=26L||any(!is.finite(m$weights)))stop('Invalid fold W')
  records[[length(records)+1L]]<-data.frame(engine=m$id,fold=fold,
    component=ESTIMATOR_NAMES,weight=as.numeric(m$weights))
 }
 rm(fit,mods)
}
z<-do.call(rbind,records)
z$selected<-z$weight>=1/26
out<-aggregate(cbind(weight,selected)~engine+component,z,mean)
names(out)[names(out)=='selected']<-'selection_frequency'
out$selection_threshold<-1/26
out$folds<-5L
dir.create(root,recursive=TRUE,showWarnings=FALSE)
write.csv(out,file.path(root,'stability_selection_components_T2_V3_B3.csv'),row.names=FALSE)
cat('T2_V3_B3_STABILITY_SELECTION_PASS',fam,seed,nrow(out),'\n')
