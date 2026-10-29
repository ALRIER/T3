#!/usr/bin/env Rscript
# Add-on transfer generator.  It is intentionally separate from the B3 core:
# W is trained only once on the base parameterization, then evaluated without
# retuning on an excluded parameter-grid row from the same distribution family.
args <- commandArgs(trailingOnly=TRUE)
if(length(args)!=5L) stop('Usage: FAMILY PARAMETER_ROW TRANSFER_SEED REPS N')
family<-args[[1L]]; parameter_row<-as.integer(args[[2L]])
seed<-as.integer(args[[3L]]); reps<-as.integer(args[[4L]]); n<-as.integer(args[[5L]])
if(!family%in%c('normal','lognormal','weibull','invgauss','exgaussian','exwald') ||
   is.na(parameter_row)||parameter_row<2L||is.na(seed)||!seed%in%40:49 ||
   reps!=500L||!n%in%c(200L,1000L,3000L)) stop('Invalid prospective transfer shard')
source('R/00_shared/load_all.R');t2_load('.')
grid<-read.csv('config/T2_V3_B3_prospective_321_grid.csv',stringsAsFactors=FALSE)
params_grid<-build_param_grids(families=family)[[family]]
if(parameter_row>nrow(params_grid))stop('Parameter row outside family grid')
params<-as.list(params_grid[parameter_row,,drop=FALSE])
target<-analytic_mean_from_params(family,params)
if(!is.finite(target))stop('Nonfinite transfer target')
root<-file.path('artifacts','t3_b3_parametric_transfer_mc',family,
  sprintf('parameter_row%02d',parameter_row),sprintf('seed%02d',seed),sprintf('n%d_r%d',n,reps))
if(dir.exists(root))stop('Refusing overwrite of immutable transfer shard')
dir.create(root,recursive=TRUE)
scenarios<-vector('list',nrow(grid))
for(j in seq_len(nrow(grid))) {
  row<-grid[j,,drop=FALSE]; id<-as.integer(row$scenario_id)
  T<-matrix(NA_real_,reps,26L,dimnames=list(NULL,ESTIMATOR_NAMES))
  for(b in seq_len(reps)) {
    set.seed(t2_seed(paste('T3_parametric_transfer',family,parameter_row,seed,n,id,b),761L))
    sample<-generate_population(family,n,params)
    if(id!=0L) sample<-inject_outliers_realistic(sample,as.numeric(row$contamination),
      as.numeric(row$mad_scale),as.character(row$mechanism))
    T[b,]<-component_vector(sample)
  }
  if(any(!is.finite(T)))stop('Nonfinite transfer scenario ',id)
  scenarios[[j]]<-list(scenario_id=id,T=T,target=target,component_names=ESTIMATOR_NAMES)
}
z<-list(protocol='t3_b3_parametric_transfer_v1',role='parametric_transfer',
 family=family,parameter_row=parameter_row,seed_index=seed,n=n,replications=reps,
 component_names=ESTIMATOR_NAMES,grid=grid,scenarios=scenarios,parameters=params,target=target,
 scientific_scope='secondary_intra_family_transfer_no_W_retuning')
saveRDS(z,file.path(root,'canonical.rds'),compress='xz')
sha<-t2_sha256(file.path(root,'canonical.rds'))
write.csv(data.frame(family,parameter_row,seed,n,reps,target,sha256=sha,
 scope='secondary_intra_family_transfer_no_W_retuning'),file.path(root,'manifest.csv'),row.names=FALSE)
cat('T3_B3_PARAMETRIC_TRANSFER_MC_PASS',family,parameter_row,seed,n,sha,'\n')
