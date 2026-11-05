#!/usr/bin/env Rscript
# Independent Stress V2: frozen original W*, fresh seeds 50:59, or near-adapted 60:69.
# Original Monte Carlo, Discovery, Held-out and Stress files are NEVER mutated.
a<-commandArgs(trailingOnly=TRUE)
if(length(a)<5L)stop('MODE FAMILY SEED N OUTPUT [DISCOVERY_ROOT] [ADAPTED_ROOT]')
mode<-a[1L];fam<-a[2L];seed<-as.integer(a[3L]);n<-as.integer(a[4L]);out<-a[5L]
droot<-if(length(a)>=6L)a[6L] else ''
aroot<-if(length(a)>=7L)a[7L] else ''
families<-c('normal','lognormal','weibull','invgauss','exgaussian','exwald')
if(!mode%in%c('smoke','score-new','train-adapt','index-adapt'))stop('Invalid mode')
if(mode!='index-adapt'&&(!fam%in%families||!n%in%c(200L,1000L,3000L)||
 !seed%in%if(mode=='train-adapt')60:69 else 50:59))stop('Seed role/family/n mismatch')
source('R/00_shared/load_all.R');t2_load('.')
source('R/00_shared/pipeline.R')
source('R/00_shared/v3_scientific_adapter.R')
seedv2<-function(role,seed,n,id=-1L,rep=0L,fam=fam){
 bytes<-utf8ToInt(paste('T3_B3_STRESS_V2_20261105',role,fam,seed,n,id,rep,sep=':'))
 h<-104729
 for(b in bytes)h<-(h*131+as.double(b))%%2147483646
 as.integer(h+1)
}
sha_weights<-function(w){
 c<-rawConnection(raw(),'wb');writeBin(as.double(w),c,size=8L,endian='big')
 b<-rawConnectionValue(c);close(c)
 p<-tempfile();writeBin(b,p);h<-t2_sha256(p);unlink(p);h
}
grid<-read.csv('config/T2_V3_B3_prospective_321_grid.csv',stringsAsFactors=FALSE)
if(nrow(grid)!=321L||!setequal(grid$scenario_id,0:320L)||
 sum(grid$mechanism=='mixture_bimodal_near')!=40L||
 sum(grid$mechanism=='mixture_bimodal_far')!=40L)stop('Prospective Grid321 violated')
test_ids<-as.integer(grid$scenario_id[grid$mechanism%in%c('mixture_bimodal_near','mixture_bimodal_far')])
train_ids<-as.integer(grid$scenario_id[grid$mechanism!='mixture_bimodal_far'])
stopifnot(length(test_ids)==80L,length(train_ids)==281L)
params_v2<-function(role){
 set.seed(seedv2(role,seed,n,-2L))
 p<-t2_params(fam)
 for(k in intersect(names(p),c('sd','sdlog','shape','scale','mean','sigma','tau','lambda','rate')))
  if(p[[k]]>0)p[[k]]<-p[[k]]*exp(runif(1L,-.30,.30))
 if('meanlog'%in%names(p))p$meanlog<-p$meanlog+runif(1,-.30,.30)
 if('mu'%in%names(p))p$mu<-p$mu+runif(1,-.30,.30)
 p
}
make_scenario<-function(id,role,params,reps){
 row<-grid[grid$scenario_id==id,,drop=FALSE]
 mat<-matrix(NA_real_,reps,26L,dimnames=list(NULL,ESTIMATOR_NAMES))
 for(b in seq_len(reps)){
  set.seed(seedv2(role,seed,n,id,b))
  x<-generate_population(fam,n,params)
  if(row$contamination>0)x<-inject_outliers_realistic(x,
    as.numeric(row$contamination),as.numeric(row$mad_scale),
    as.character(row$mechanism))
  mat[b,]<-component_vector(x)
 }
 if(any(!is.finite(mat)))stop('Nonfinite component matrix')
 t2_v3_prepare_scenario(list(T=mat,target=analytic_mean_from_params(fam,params),
  scenario_id=as.integer(id),contamination=as.numeric(row$contamination),
  mad_scale=as.numeric(row$mad_scale),mechanism=as.character(row$mechanism),
  band=as.character(row$band),component_names=ESTIMATOR_NAMES))
}
load_models<-function(root,n,adapted=FALSE){
 if(!nzchar(root)||!dir.exists(root))stop('Model root missing')
 items<-list();j<-0L
 for(f in families)for(ss in if(adapted)60:69 else 0:9){
  p<-file.path(root,f,sprintf('seed%02d',ss),sprintf('n%d',n),
   if(adapted)'adapted.rds' else 'discovery.rds')
  if(!file.exists(p))stop('Required frozen model missing: ',p)
  fit<-readRDS(p)
  learned<-Filter(function(x)!is.null(x$weights),fit$models)
  if(length(learned)!=4L)stop('Invalid four engine candidate registry')
  for(x in learned){
   w<-as.numeric(x$weights)
   if(!x$id%in%c('ga','nsga2','de','dirichlet')||length(w)!=26L||
      any(!is.finite(w))||any(w<0)||abs(sum(w)-1)>1e-8)
     stop('Invalid optimizer W')
   j<-j+1L
   items[[j]]<-list(candidate_id=if(adapted)
     sprintf('adapted|%s|%s|seed%02d|n%d',f,x$id,ss,n) else
     sprintf('%s|%s|seed%02d|n%d',f,x$id,ss,n),
     engine=x$id,source_family=f,training_seed=as.integer(ss),
     weights=w,weights_sha256=sha_weights(w),
     discovery_sha256=t2_sha256(p))
  }
 }
 if(length(items)!=240L||anyDuplicated(vapply(items,function(x)x$candidate_id,character(1))))
  stop('Expected exactly 240 independent candidate W for one n')
 items
}
if(mode=='index-adapt'){
 root<-normalizePath(out,mustWork=TRUE)
 paths<-list.files(root,'^adapted[.]rds$',recursive=TRUE,full.names=TRUE)
 if(length(paths)!=180L)stop('Require 180 separately trained adapted models')
 rows<-list();k<-0L
 for(nn in c(200L,1000L,3000L))for(x in load_models(root,nn,TRUE)){
  k<-k+1L
  rows[[k]]<-data.frame(candidate_id=x$candidate_id,
   source_family=x$source_family,engine=x$engine,training_seed=x$training_seed,
   sample_n=nn,weight_count=26L,weight_sum=sum(x$weights),
   weights_sha256=x$weights_sha256,discovery_sha256=x$discovery_sha256,
   stringsAsFactors=FALSE)
 }
 if(k!=720L)stop('Adapted registry is incomplete')
 dst<-file.path(root,'adapted_candidate_registry.csv')
 if(file.exists(dst))stop('Do not overwrite existing adapted registry')
 write.csv(do.call(rbind,rows),dst,row.names=FALSE)
 cat('STRESS_V2_ADAPTED_REGISTRY_PASS 720\n')
 quit(save='no',status=0L)
}
if(dir.exists(out))stop('Refusing to overwrite immutable output')
dir.create(out,recursive=TRUE)
role<-if(mode=='train-adapt')'training_60_69' else 'eval_50_59'
reps<-if(mode=='smoke')12L else 500L
ids<-if(mode=='smoke')test_ids[c(1L,41L)] else if(mode=='train-adapt')train_ids else test_ids
params<-params_v2(role)
if(mode=='train-adapt'){
 hpopath<-file.path(droot,fam,sprintf('seed%02d',seed-60L),
   sprintf('n%d',n),'frozen_hyperparameters.json')
 if(!file.exists(hpopath)||!requireNamespace('jsonlite',quietly=TRUE))
  stop('Adapted training requires frozen independent HPO')
 hpo<-jsonlite::fromJSON(hpopath,simplifyVector=FALSE)
 if(!identical(hpo$protocol,'T3_B3_nested_5x3_hpo_freeze_v2_equal_budget')||
    !setequal(names(hpo$engines),c('ga','nsga2','de','dirichlet')))
   stop('Cannot modify original four-engine HPO policy')
 sc<-lapply(ids,function(id)make_scenario(id,role,params,reps))
 if(length(sc)!=281L||any(vapply(sc,function(z)z$mechanism=='mixture_bimodal_far',logical(1))))
  stop('Adapted training leaked far mechanism')
 result<-t2_run_discovery(list(scenarios=sc,seed_index=seed,family=fam,n=n),
   'full',sprintf('stressv2_adapt_%s_%02d_n%d',fam,seed,n),'all',
   hyperparameters=hpo$engines)
 if(length(Filter(function(x)!is.null(x$weights),result$models))!=4L)
  stop('Adapted training did not recover four W')
 result$training_design<-'241_support_plus_40_near_0_far_V1'
 result$independent_training_seed<-seed
 result$frozen_hpo_sha256<-t2_sha256(hpopath)
 saveRDS(result,file.path(out,'adapted.rds'))
 write.csv(data.frame(family=fam,training_seed=seed,sample_n=n,
   train_support=241L,train_near=40L,train_far=0L,
   replications=reps,fit_sha256=t2_sha256(file.path(out,'adapted.rds')),
   hpo_sha256=t2_sha256(hpopath)),file.path(out,'manifest.csv'),row.names=FALSE)
 cat('STRESS_V2_NEAR_ADAPTED_DISCOVERY_PASS',fam,seed,n,'\n')
 quit(save='no',status=0L)
}
models<-c(load_models(droot,n,FALSE),if(nzchar(aroot))load_models(aroot,n,TRUE))
if(length(models)!=(if(nzchar(aroot))480L else 240L))stop('Candidate panel incomplete')
W<-do.call(cbind,lapply(models,function(x)x$weights))
target<-file.path(out,'scores.csv')
for(i in seq_along(ids)){
 sc<-make_scenario(ids[[i]],role,params,reps)
 if(mode=='score-new'){
  dir.create(file.path(out,'mc'),showWarnings=FALSE)
  saveRDS(sc,file.path(out,'mc',sprintf('scenario_%04d.rds',sc$scenario_id)),compress='xz')
 }
 T<-sc$T;mu<-sc$target
 classical<-lapply(seq_along(ESTIMATOR_NAMES),function(k){
  loss<-(T[,k]-mu)^2
  data.frame(candidate_id='',model=ESTIMATOR_NAMES[k],source_family=fam,
   training_seed=-1L,weights_sha256='',discovery_sha256='',
   mse=mean(loss),q95=unname(quantile(loss,.95,type=8)),
   stringsAsFactors=FALSE)
 })
 loss<-(T%*%W-mu)^2
 learned<-data.frame(candidate_id=vapply(models,function(z)z$candidate_id,character(1)),
  model=vapply(models,function(z)z$engine,character(1)),
  source_family=vapply(models,function(z)z$source_family,character(1)),
  training_seed=vapply(models,function(z)z$training_seed,integer(1)),
  weights_sha256=vapply(models,function(z)z$weights_sha256,character(1)),
  discovery_sha256=vapply(models,function(z)z$discovery_sha256,character(1)),
  mse=colMeans(loss),q95=apply(loss,2L,quantile,probs=.95,type=8,names=FALSE),
  stringsAsFactors=FALSE)
 z<-rbind(do.call(rbind,classical),learned)
 z$evaluation_family<-fam;z$evaluation_seed<-seed;z$sample_n<-n
 z$scenario_id<-sc$scenario_id;z$mechanism<-sc$mechanism
 z$contamination<-sc$contamination;z$mad_scale<-sc$mad_scale;z$band<-sc$band
 write.table(z,target,sep=',',row.names=FALSE,col.names=i==1L,
   append=i>1L,qmethod='double')
 if(i%%10L==0L)message('STRESS_V2_SCORE_PROGRESS ',fam,' seed ',seed,' n ',n,' ',i,'/',length(ids))
 rm(sc,z,loss,learned);invisible(gc(FALSE))
}
expected<-length(ids)*(26L+length(models))
write.csv(data.frame(protocol='T3_B3_STRESS_V2',
 family=fam,seed=seed,n=n,reps=reps,scenarios=length(ids),
 original_candidates=240L,adapted_candidates=length(models)-240L,
 rows=expected,seed_role=role,score_sha256=t2_sha256(target),
 original_Discovery_retrained=FALSE,
 stringsAsFactors=FALSE),file.path(out,'score_manifest.csv'),row.names=FALSE)
cat('STRESS_V2_NEW_SCORE_PASS',fam,seed,n,expected,'\n')
