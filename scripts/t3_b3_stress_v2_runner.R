#!/usr/bin/env Rscript
# Independent Stress V2: frozen original W*, fresh seeds 50:59, or near-adapted 60:69.
# Original Monte Carlo, Discovery, Held-out and Stress files are NEVER mutated.
a<-commandArgs(trailingOnly=TRUE)
if(length(a)<5L)stop('MODE FAMILY SEED N OUTPUT [DISCOVERY_ROOT] [ADAPTED_ROOT] [ORIGINAL_NEW_MC_ROOT]')
mode<-a[1L];fam<-a[2L];seed<-as.integer(a[3L]);n<-as.integer(a[4L]);out<-a[5L]
droot<-if(length(a)>=6L)a[6L] else ''
aroot<-if(length(a)>=7L)a[7L] else ''
mcroot<-if(length(a)>=8L)a[8L] else ''
families<-c('normal','lognormal','weibull','invgauss','exgaussian','exwald')
if(!mode%in%c('smoke','smoke-adapt','score-new','score-adapt','train-adapt','index-adapt','pack-original','pack-adapted'))stop('Invalid mode')
if(!mode%in%c('index-adapt','pack-original','pack-adapted')&&(!fam%in%families||!n%in%c(200L,1000L,3000L)||
 !seed%in%if(mode%in%c('train-adapt','smoke-adapt'))60:69 else 50:59))stop('Seed role/family/n mismatch')
source('R/00_shared/load_all.R');t2_load('.')
source('R/00_shared/pipeline.R')
source('R/00_shared/v3_scientific_adapter.R')
seedv2<-function(role,seed,n,id=-1L,replicate=0L,distribution=fam){
 bytes<-utf8ToInt(paste('T3_B3_STRESS_V2_20261105',role,distribution,seed,n,id,replicate,sep=':'))
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
# Preserve the original four-fold parent-pool structure; reuse uncontaminated
# samples across adjacent severity conditions and across all 80 Stress scenarios.
# Each base replicate has a deterministic seed independent of R fork scheduling.
mechanism_fold<-function(m){
 if(m=='none')return(0L)
 if(m%in%c('upper_tail','clustered_upper','point_mass'))return(1L)
 if(m%in%c('lower_tail','clustered_symmetric','mixture_bimodal_near'))return(2L)
 if(m%in%c('symmetric_t','mixture_bimodal_far'))return(3L)
 stop('Unknown mechanism in B3 fold design: ',m)
}
base_pool_cache<-new.env(hash=TRUE,parent=emptyenv())
base_pool<-function(fold,role,params,reps){
 key<-paste(role,fold,reps,sep='|')
 if(exists(key,envir=base_pool_cache,inherits=FALSE))return(get(key,envir=base_pool_cache))
 worker<-function(b){
  set.seed(seedv2(paste0(role,'_base_fold',fold),seed,n,-30L-fold,b))
  generate_population(fam,n,params)
 }
 cores<-as.integer(Sys.getenv('T3_STRESS_MC_WORKERS','2'))
 if(is.na(cores)||!cores%in%c(1L,2L))stop('Invalid base pool parallelism')
 if(.Platform$OS.type=='unix'&&cores>1L&&reps>=50L){
  ans<-parallel::mclapply(seq_len(reps),worker,mc.cores=cores,
   mc.set.seed=FALSE,mc.preschedule=TRUE)
  if(any(vapply(ans,inherits,logical(1),'try-error')))stop('Base pool worker failed')
  pool<-vapply(ans,as.double,numeric(n))
 } else pool<-vapply(seq_len(reps),worker,numeric(n))
 if(!identical(dim(pool),c(as.integer(n),as.integer(reps)))||any(!is.finite(pool)))
  stop('Invalid common Monte Carlo base pool')
 assign(key,pool,envir=base_pool_cache)
 pool
}
make_scenario<-function(id,role,params,reps){
 row<-grid[grid$scenario_id==id,,drop=FALSE]
 pool<-base_pool(mechanism_fold(as.character(row$mechanism)),role,params,reps)
 worker<-function(b){
  # Same uncontaminated replicate is shared across severity cells in its mechanism fold.
  # Distinct scenario RNG streams randomize contamination independently.
  set.seed(seedv2(role,seed,n,id,b))
  x<-pool[,b]
  if(row$contamination>0)x<-inject_outliers_realistic(x,
    as.numeric(row$contamination),as.numeric(row$mad_scale),
    as.character(row$mechanism))
  component_vector(x)
 }
 cores<-as.integer(Sys.getenv('T3_STRESS_MC_WORKERS','2'))
 if(is.na(cores)||cores<1L||cores>2L)stop('MC worker count must be 1 or 2')
 if(reps<50L)cores<-1L
 if(cores>1L&&.Platform$OS.type=='unix'){
  pieces<-parallel::mclapply(seq_len(reps),worker,
   mc.cores=cores,mc.set.seed=FALSE,mc.preschedule=TRUE)
  if(any(vapply(pieces,inherits,logical(1),'try-error')))stop('MC worker failed')
  mat<-t(vapply(pieces,as.double,numeric(26L)))
 } else {
  mat<-t(vapply(seq_len(reps),worker,numeric(26L)))
 }
 colnames(mat)<-ESTIMATOR_NAMES
 if(!identical(dim(mat),c(as.integer(reps),26L))||any(!is.finite(mat)))
  stop('Nonfinite or incomplete component matrix')
 sc<-list(T=mat,target=analytic_mean_from_params(fam,params),
  scenario_id=as.integer(id),contamination=as.numeric(row$contamination),
  mad_scale=as.numeric(row$mad_scale),mechanism=as.character(row$mechanism),
  band=as.character(row$band),component_names=ESTIMATOR_NAMES)
 # Original scoring needs only (T,target). Precomputed calibration benchmarks
 # are required solely by the four optimizer fitness functions.
 if(mode=='train-adapt')t2_v3_prepare_scenario(sc) else sc
}
load_models<-function(root,n,adapted=FALSE){
 if(!nzchar(root)||!dir.exists(root))stop('Model root missing')
 packed<-file.path(root,sprintf('%s_W_n%d.rds',if(adapted)'adapted' else 'original',n))
 if(file.exists(packed)){
  z<-readRDS(packed)
  if(!is.list(z)||length(z)!=240L||anyDuplicated(vapply(z,function(x)x$candidate_id,character(1))))stop('Bad compact model bundle')
  for(m in z){
   if(length(m$weights)!=26L||any(!is.finite(m$weights))||any(m$weights<0)||abs(sum(m$weights)-1)>1e-8||
    !identical(sha_weights(m$weights),m$weights_sha256)||!nzchar(m$discovery_sha256))stop('Compact model weight/hash corruption')
  }
  return(z)
 }
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
if(mode%in%c('pack-original','pack-adapted')){
 adapted<-mode=='pack-adapted'
 root<-if(adapted)aroot else droot
 if(!nzchar(root)||!dir.exists(root))stop('Source model root unavailable for packing')
 dir.create(out,recursive=TRUE,showWarnings=FALSE)
 for(nn in c(200L,1000L,3000L)){
  models<-load_models(root,nn,adapted)
  p<-file.path(out,sprintf('%s_W_n%d.rds',if(adapted)'adapted' else 'original',nn))
  if(file.exists(p))stop('Packed weights already exist: ',p)
  saveRDS(models,p,compress='gzip')
  check<-readRDS(p)
  if(length(check)!=240L||!identical(vapply(check,function(x)x$weights_sha256,character(1)),
   vapply(models,function(x)x$weights_sha256,character(1))))stop('Packed W round trip validation failed')
  rm(models,check);invisible(gc(FALSE))
 }
 cat('STRESS_V2_COMPACT_W_PACK_PASS',mode,'720 candidates\n')
 quit(save='no',status=0L)
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
role<-if(mode%in%c('train-adapt','smoke-adapt'))'training_60_69' else 'eval_50_59'
reps<-if(mode%in%c('smoke','smoke-adapt'))12L else 500L
ids<-if(mode=='smoke')test_ids[c(1L,41L)] else if(mode=='smoke-adapt'){
   unique(c(0L,
    head(as.integer(grid$scenario_id[grid$band=='low' & grid$mechanism!='mixture_bimodal_far']),2L),
    head(as.integer(grid$scenario_id[grid$band=='intermediate' & grid$mechanism!='mixture_bimodal_far']),2L),
    head(as.integer(grid$scenario_id[grid$band=='high' & !grid$mechanism%in%c('mixture_bimodal_near','mixture_bimodal_far')]),2L),
    head(as.integer(grid$scenario_id[grid$mechanism=='mixture_bimodal_near']),1L)))
 } else if(mode=='train-adapt')train_ids else test_ids
if(mode=='smoke-adapt' && (length(ids)!=8L||!all(c('clean','low','intermediate','high')%in%grid$band[match(ids,grid$scenario_id)])))stop('Smoke training must include every severity band')
params<-params_v2(role)
if(mode%in%c('train-adapt','smoke-adapt')){
 hpopath<-file.path(droot,fam,sprintf('seed%02d',seed-60L),
   sprintf('n%d',n),'frozen_hyperparameters.json')
 if(!file.exists(hpopath)||!requireNamespace('jsonlite',quietly=TRUE))
  stop('Adapted training requires frozen independent HPO')
 hpo<-jsonlite::fromJSON(hpopath,simplifyVector=FALSE)
 if(!identical(hpo$protocol,'T3_B3_nested_5x3_hpo_freeze_v2_equal_budget')||
    !setequal(names(hpo$engines),c('ga','nsga2','de','dirichlet')))
   stop('Cannot modify original four-engine HPO policy')
 sc<-lapply(ids,function(id)make_scenario(id,role,params,reps))
 if(length(sc)!=(if(mode=='smoke-adapt')8L else 281L)||
   any(vapply(sc,function(z)z$mechanism=='mixture_bimodal_far',logical(1))))
  stop('Adapted training leaked far mechanism')
 result<-t2_run_discovery(list(scenarios=sc,seed_index=seed,family=fam,n=n),
   if(mode=='smoke-adapt')'smoke' else 'full',sprintf('stressv2_adapt_%s_%02d_n%d',fam,seed,n),'all',
   hyperparameters=if(mode=='smoke-adapt')list() else hpo$engines)
 if(length(Filter(function(x)!is.null(x$weights),result$models))!=4L)
  stop('Adapted training did not recover four W')
 result$training_design<-if(mode=='smoke-adapt')'smoke_8_scenarios_no_far' else '241_support_plus_40_near_0_far_V1'
 result$independent_training_seed<-seed
 result$frozen_hpo_sha256<-t2_sha256(hpopath)
 saveRDS(result,file.path(out,'adapted.rds'))
 write.csv(data.frame(family=fam,training_seed=seed,sample_n=n,
   train_support=sum(!grid$mechanism[match(ids,grid$scenario_id)]%in%c('mixture_bimodal_near','mixture_bimodal_far')),train_near=sum(grid$mechanism[match(ids,grid$scenario_id)]=='mixture_bimodal_near'),train_far=0L,
   replications=reps,fit_sha256=t2_sha256(file.path(out,'adapted.rds')),
   hpo_sha256=t2_sha256(hpopath)),file.path(out,'manifest.csv'),row.names=FALSE)
 cat(if(mode=='smoke-adapt')'STRESS_V2_ADAPT_TRAIN_SMOKE_PASS' else 'STRESS_V2_NEAR_ADAPTED_DISCOVERY_PASS',fam,seed,n,'\n')
 quit(save='no',status=0L)
}
models<-if(mode=='score-adapt')load_models(aroot,n,TRUE) else load_models(droot,n,FALSE)
if(length(models)!=240L)stop('Candidate panel incomplete')
if(mode=='score-adapt'){
 if(!nzchar(mcroot)||!dir.exists(mcroot))stop('Missing frozen 50:59 Monte Carlo checkpoint')
 meta_path<-file.path(mcroot,'score_manifest.csv')
 original<-file.path(mcroot,'scores.csv')
 if(!file.exists(meta_path)||!file.exists(original))stop('Independent test checkpoint missing')
 meta<-read.csv(meta_path,stringsAsFactors=FALSE)
 if(nrow(meta)!=1L||as.integer(meta$seed)!=seed||as.integer(meta$n)!=n||
   as.character(meta$family)!=fam||as.character(meta$score_sha256)!=t2_sha256(original)||
   as.integer(meta$adapted_candidates)!=0L)stop('Independent Monte Carlo provenance mismatch')
 if(!file.copy(original,file.path(out,'scores.csv'),overwrite=FALSE))stop('Cannot copy immutable original W score')
}
W<-do.call(cbind,lapply(models,function(x)x$weights))
if(!identical(dim(W),c(26L,240L)))stop('Invalid vectorized W scoring matrix')
Sys.setenv(OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
target<-file.path(out,'scores.csv')
for(i in seq_along(ids)){
 sc<-if(mode=='score-adapt')readRDS(file.path(mcroot,'mc',sprintf('scenario_%04d.rds',ids[[i]]))) else make_scenario(ids[[i]],role,params,reps)
 if(mode=='score-adapt' && (identical(sc$scenario_id,ids[[i]])==FALSE||!identical(dim(sc$T),c(500L,26L))))stop('Corrupt independent MC checkpoint')
 if(mode=='score-new'){
  dir.create(file.path(out,'mc'),showWarnings=FALSE)
  saveRDS(sc,file.path(out,'mc',sprintf('scenario_%04d.rds',sc$scenario_id)),compress='gzip')
 }
 T<-sc$T;mu<-sc$target
 classical<-if(mode=='score-adapt')NULL else lapply(seq_along(ESTIMATOR_NAMES),function(k){
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
 z<-if(mode=='score-adapt')learned else rbind(do.call(rbind,classical),learned)
 z$evaluation_family<-fam;z$evaluation_seed<-seed;z$sample_n<-n
 z$scenario_id<-sc$scenario_id;z$mechanism<-sc$mechanism
 z$contamination<-sc$contamination;z$mad_scale<-sc$mad_scale;z$band<-sc$band
 write.table(z,target,sep=',',row.names=FALSE,col.names=if(mode=='score-adapt')FALSE else i==1L,
   append=(mode=='score-adapt'||i>1L),qmethod='double')
 if(i%%10L==0L)message('STRESS_V2_SCORE_PROGRESS ',fam,' seed ',seed,' n ',n,' ',i,'/',length(ids))
 rm(sc,z,loss,learned,classical)
 if(i%%10L==0L)invisible(gc(FALSE))
}
expected<-length(ids)*(if(mode=='score-adapt')26L+240L+length(models) else 26L+length(models))
write.csv(data.frame(protocol='T3_B3_STRESS_V2',
 family=fam,seed=seed,n=n,reps=reps,scenarios=length(ids),
 original_candidates=240L,adapted_candidates=if(mode=='score-adapt')240L else 0L,
 rows=expected,seed_role=role,score_sha256=t2_sha256(target),
 original_Discovery_retrained=FALSE,
 input_weight_count=length(models),score_precision='float64',mc_compression='gzip',
 peak_R_vcells_mb=gc()[2L,6L],peak_R_ncells_mb=gc()[1L,6L],
 source_mc_sha256=if(mode=='score-adapt')t2_sha256(file.path(mcroot,'score_manifest.csv')) else '',
 stringsAsFactors=FALSE),file.path(out,'score_manifest.csv'),row.names=FALSE)
cat('STRESS_V2_NEW_SCORE_PASS',fam,seed,n,expected,'\n')
