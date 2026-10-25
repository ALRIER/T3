#!/usr/bin/env Rscript
source('R/00_shared/load_all.R');t2_load('.')
source('R/01_monte_carlo/v3_generation.R')
source('R/00_shared/v3_scientific_adapter.R')
ids<-0:320
for(role in c('discovery','heldout','stress'))for(n in c(200L,1000L,3000L)){
 d<-t2_v3_design(role,'normal',t2_v3_indices(role)[1],n,320L)
 stopifnot(nrow(d$grid)==321L,identical(as.integer(d$grid$scenario_id),ids),
   length(unique(d$grid$mechanism))==9L,
   identical(t2_v3_protocol(),'t3_b3_grid321_v1'),
   n%in%t2_v3_sample_sizes(role))
}
tmp<-tempfile('t3folds');dir.create(tmp)
t2_v3_block_dir<-function(role,family,seed,n,reps=500L)
  file.path(tmp,sprintf('n%d',n))
for(n in c(200L,1000L,3000L)){
 root<-t2_v3_block_dir('discovery','normal',0L,n)
 dir.create(root,recursive=TRUE)
 for(i in ids)saveRDS(list(scenario_id=i,band=c('clean','low','intermediate','high')[(i%%4)+1],
   mechanism=paste0('mechanism',(i%%8)+1),mad_scale=c(1.5,3,6,12,30)[i%%5+1],
   contamination=c(0,.01,.05,.10,.30)[i%%5+1]),
   file.path(root,sprintf('scenario_%04d.rds',i)))
}
source('R/02_discovery/t2_v3_b3_nested_folds.R')
for(n in c(200L,1000L,3000L))for(outer in 1:5){
 p<-t2_b3_nested_partitions('normal',0L,outer,n=n)
 stopifnot(length(p$validation)%in%c(64L,65L),
   !length(intersect(p$training,p$validation)),
   setequal(c(p$training,p$validation),ids))
 for(inner in 1:3){
   q<-t2_b3_nested_partitions('normal',0L,outer,inner,n=n)
   stopifnot(!length(intersect(q$training,q$validation)),
     !length(intersect(q$validation,p$validation)),
     !length(intersect(q$training,p$validation)),
     setequal(c(q$training,q$validation),p$training))
 }
}
unlink(tmp,recursive=TRUE)
cat('T3_GRID321_THREE_N_NESTED_5x3_SMOKE_PASS\n')
