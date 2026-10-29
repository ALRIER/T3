#!/usr/bin/env Rscript
# Synthetic fixture: verify external inference aggregation without treating
# the fixture as Real World evidence.
source('R/00_shared/load_all.R');t2_load('.')
root<-file.path('artifacts','t2_b3_parent_aggregation_fixture')
shard<-file.path(root,'normal','profile_batch_001')
dir.create(shard,recursive=TRUE,showWarnings=FALSE)
rows<-list();j<-0L
for(parent in 1:8)for(depth in c('full','body_10_90')) {
 models<-c(ESTIMATOR_NAMES,'ga_frozen','nsga2_frozen','de_frozen','dirichlet_frozen')
 for(k in seq_along(models)) {
   j<-j+1L
   rows[[j]]<-data.frame(model=models[k],mse=if(k<=26L)1 else .90+parent*.001,
    q95=if(k<=26L)2 else 1.8+parent*.002,
    dataset_id=sprintf('fixture_%02d',parent),
    parent_dataset_id=sprintf('fixture_%02d',parent),
    family='normal',training_seed=0L,sample_n=200L,depth=depth,
    empirical_profile='normal_like',proximity_layer='direct_intraregime',
    raw_md5='synthetic',weights_sha256='synthetic')
 }
}
write.csv(do.call(rbind,rows),file.path(shard,'scores_T2_V3_B3.csv'),row.names=FALSE)
status<-system2('Rscript',c('scripts/t2_v3_b3_realworld_parent_inference.R',root))
if(status!=0L)stop('Parent inference failed')
v<-read.csv(file.path(root,'aggregation_T2_V3_B3','parent_inference_T2_V3_B3.csv'))
stopifnot(nrow(v)==8L,all(v$n_parent==8L),all(c('mse','q95')%in%v$metric),
  all(is.finite(v$ci_lower)),all(is.finite(v$q_BH)))
cat('T2_V3_B3_PARENT_AGGREGATION_SMOKE_PASS\n')
