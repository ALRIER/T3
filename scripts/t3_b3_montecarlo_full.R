#!/usr/bin/env Rscript
# T3/B3 production-path pilot: actual distribution draws and estimator calculations.
args<-commandArgs(trailingOnly=TRUE)
if(length(args)!=5L)stop('Usage: FAMILY ROLE SEED REPS N')
family<-args[[1L]];role<-args[[2L]]
seed<-as.integer(args[[3L]]);reps<-as.integer(args[[4L]])
if(is.na(reps)||reps!=500L)stop('Production requires exactly 500 replications')
if(!family%in%c('normal','lognormal','weibull','invgauss','exgaussian','exwald'))stop('Unknown family')
if(!role%in%c('discovery','heldout','stress'))stop('No synthetic Real World role')
source('R/00_shared/load_all.R');t2_load('.')
source('R/00_shared/v3_scientific_adapter.R')
grid<-read.csv('config/T2_V3_B3_prospective_321_grid.csv',stringsAsFactors=FALSE)
stopifnot(nrow(grid)==321L,identical(as.integer(grid$scenario_id),0:320))
n<-as.integer(args[[5L]]);stopifnot(n%in%c(200L,1000L,3000L),seed%in%t2_v3_indices(role))
params<-as.list(build_param_grids(families=family)[[family]][1L,,drop=FALSE])
target<-analytic_mean_from_params(family,params)
if(!is.finite(target))stop('Nonfinite population target')
root<-t2_v3_block_dir(role,family,seed,n,reps)
dir.create(root,recursive=TRUE,showWarnings=FALSE)
scenarios<-vector('list',321L)
for(j in seq_len(321L)){
 row<-grid[j,,drop=FALSE];id<-as.integer(row$scenario_id)
 T<-matrix(NA_real_,reps,26L,dimnames=list(NULL,ESTIMATOR_NAMES))
 for(b in seq_len(reps)){
  set.seed(t2_seed_for_v3(role,family,seed,n,id,b))
  sample<-generate_population(family,n,params)
  if(id!=0L)sample<-inject_outliers_realistic(sample,
    contamination_rate=as.numeric(row$contamination),
    outlier_scale_mad=as.numeric(row$mad_scale),
    type=as.character(row$mechanism))
  T[b,]<-component_vector(sample)
 }
 if(any(!is.finite(T)))stop('Nonfinite estimator at scenario ',id)
 scenarios[[j]]<-list(scenario_id=id,T=T,target=target,component_names=ESTIMATOR_NAMES)
 if(j%%10L==0L){saveRDS(list(scenarios=scenarios[seq_len(j)],completed=j,role=role,family=family,seed=seed,n=n,reps=reps),file.path(root,'checkpoint.rds'));cat('MC_FULL_PROGRESS',j,'/321\n')}
}
z<-list(protocol=t2_v3_protocol(),role=role,family=family,seed_index=seed,
 n=n,replications=reps,component_names=ESTIMATOR_NAMES,grid=grid,
 scenarios=scenarios,parameters=params,target=target,scientific_generator='b3_actual_sample_full_v1')
path<-file.path(root,'canonical.rds')
if(file.exists(path))stop('Refusing overwrite of scientific canonical result')
saveRDS(z,path,compress='xz')
check<-t2_v3_read_block(role,family,seed,n,reps,selected=c(0L,1L,320L))
stopifnot(length(check$scenarios)==3L)
if(file.exists(file.path(root,'checkpoint.rds')))unlink(file.path(root,'checkpoint.rds'))
sha<-t2_sha256(path)
write.csv(data.frame(role=role,family=family,seed=seed,n=n,reps=reps,
 scenarios=321L,target=target,sha256=sha,revision=Sys.getenv('GITHUB_SHA','local')),
 file.path(root,'manifest.csv'),row.names=FALSE)
cat('T3_B3_MC_FULL_500_REPS_321_SCENARIOS_PASS',sha,'\n')
