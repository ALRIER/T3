#!/usr/bin/env Rscript
# T2 V3 B3: parent-level Real World inference
a<-commandArgs(trailingOnly=TRUE)
root<-if(length(a))a[[1]] else 'artifacts/realworld_T2_V3_B3'
source('R/00_shared/load_all.R');t2_load('.')
source('R/00_shared/pipeline.R')
source('R/00_shared/t2_v3_b3_resources.R')
paths<-list.files(root,'^scores_T2_V3_B3[.]csv$',recursive=TRUE,full.names=TRUE)
if(!length(paths))stop('Missing real-world scores')
# Reduce one immutable shard at a time; never concatenate raw score catalogs.
reduce_parent_shard<-function(path){
  x<-read.csv(path,stringsAsFactors=FALSE)
  key<-interaction(x$dataset_id,x$family,x$training_seed,x$sample_n,x$depth,drop=TRUE)
  rows<-lapply(split(x,key),function(d){
    ref<-if(d$empirical_profile[1]=='normal_like')'mean' else
      if(d$empirical_profile[1]=='empirical_unknown')'huber' else 'trimmed20'
    base<-d[d$model==ref,,drop=FALSE]
    learn<-d[!d$model%in%ESTIMATOR_NAMES,,drop=FALSE]
    if(nrow(base)!=1L||nrow(learn)!=4L)stop('Invalid parent comparison: ',path)
    data.frame(parent_dataset_id=learn$parent_dataset_id,family=learn$family,
      proximity_layer=learn$proximity_layer,model=learn$model,reference=ref,
      mse_gain=base$mse-learn$mse,q95_gain=base$q95-learn$q95)
  })
  d<-do.call(rbind,rows)
  aggregate(cbind(mse_gain,q95_gain)~parent_dataset_id+family+
    proximity_layer+model+reference,d,mean)
}
chunks<-vector('list',length(paths))
for(i in seq_along(paths)){
  chunks[[i]]<-reduce_parent_shard(paths[[i]])
  if(i%%20L==0L){invisible(gc(verbose=FALSE));
    t2_b3_ram_guard('realworld_parent',file.path(root,'aggregation_T2_V3_B3'),paste0('shard_',i))}
}
tmp<-do.call(rbind,chunks);rm(chunks);invisible(gc(verbose=FALSE))
# Safety: if a parent appears across multiple catalog fragments, collapse it
# before inference so repeated views never count as new independent datasets.
parents<-aggregate(cbind(mse_gain,q95_gain)~parent_dataset_id+family+
  proximity_layer+model+reference,tmp,mean)
rm(tmp);invisible(gc(verbose=FALSE))
out<-file.path(root,'aggregation_T2_V3_B3');dir.create(out,recursive=TRUE,showWarnings=FALSE)
t2_b3_inputs_manifest(paths,out,'realworld_parent')
write.csv(parents,file.path(out,'parent_effects_T2_V3_B3.csv'),row.names=FALSE)
panels<-split(parents,interaction(parents$family,parents$proximity_layer,parents$model,drop=TRUE))
res<-list()
for(g in panels)for(metric in c('mse','q95')) {
  x<-g[[paste0(metric,'_gain')]];nn<-length(x)
  if(nn<2L)next
  set.seed(t2_seed(paste(g$family[1],g$proximity_layer[1],g$model[1],metric),17291L))
  B<-2000L
  bs<-replicate(B,mean(sample(x,nn,replace=TRUE)))
  ci<-unname(quantile(bs,c(.025,.975),type=8))
  se<-sd(x)
  p<-if(se>0)pt(-mean(x)/(se/sqrt(nn)),df=nn-1L) else if(mean(x)>0)0 else 1
  vals<-replicate(500L,mean(x*sample(c(-1,1),nn,replace=TRUE)))
  np<-if(se>0)pt(-vals/(se/sqrt(nn)),df=nn-1L) else rep(1,length(vals))
  res[[length(res)+1L]]<-data.frame(family=g$family[1],proximity_layer=g$proximity_layer[1],
    model=g$model[1],reference=g$reference[1],metric=metric,n_parent=nn,
    gain=mean(x),ci_lower=ci[1],ci_upper=ci[2],p_value=p,
    null_method='parent_sign_symmetry',null_reps=length(np),null_fpr=mean(np<.05))
}
if(!length(res))stop('No independent parent-level hypotheses')
v<-do.call(rbind,res)
v$q_BH<-p.adjust(v$p_value,'BH')
v$p_holm<-p.adjust(v$p_value,'holm')
v$supported<-v$gain>0 & v$ci_lower>0 & v$q_BH<=.05
key<-paste(v$family,v$proximity_layer,v$model,sep=':')
m<-v$metric=='mse';q<-v$metric=='q95'
mok<-v$supported[match(key,paste(v$family[m],v$proximity_layer[m],v$model[m],sep=':'))]
qok<-v$supported[match(key,paste(v$family[q],v$proximity_layer[q],v$model[q],sep=':'))]
if(anyNA(mok)||anyNA(qok))stop('Incomplete Real World taxonomy pair')
v$taxonomy<-ifelse(mok&qok,'mse_and_q95_bh_fdr',ifelse(mok,'mse_only_bh_fdr',
 ifelse(qok,'q95_only_bh_fdr','no_supported_gain')))
# Joint null diagnostics require the same parent-level BH taxonomy, not
# isolated unadjusted null contrasts. Kept separate from scientific claims.
set.seed(t2_seed('B3_RW_parent_joint_null',27181L))
Bnull<-500L
hyp<-split(parents,interaction(parents$family,parents$proximity_layer,parents$model,drop=TRUE))
null_rej<-numeric(Bnull)
for(b in seq_len(Bnull)){
  null_p<-numeric(0)
  # A parent receives one common null sign across all its appearances,
  # preserving cross-family/metric dependence instead of treating repeats as independent.
  parent_ids<-unique(parents$parent_dataset_id)
  parent_flips<-setNames(sample(c(-1,1),length(parent_ids),replace=TRUE),parent_ids)
  for(h in hyp){
    if(nrow(h)<2L)next
    flips<-unname(parent_flips[as.character(h$parent_dataset_id)])
    for(metric in c('mse','q95')){
      x<-h[[paste0(metric,'_gain')]]*flips
      if(!is.finite(sd(x))||sd(x)==0){p<-if(mean(x)>0)0 else 1}
      else p<-pt(-mean(x)/(sd(x)/sqrt(length(x))),df=length(x)-1L)
      null_p<-c(null_p,p)
    }
  }
  if(!length(null_p))stop('Missing parent null family')
  null_rej[b]<-sum(p.adjust(null_p,'BH')<=.05)
}
write.csv(data.frame(null_iteration=seq_len(Bnull),discoveries=null_rej,
 any_false_discovery=null_rej>0),file.path(out,'parent_null_calibration_T2_V3_B3.csv'),row.names=FALSE)
writeLines(c(sprintf('null_worlds=%d',Bnull),
 sprintf('empirical_global_null_FWER=%.6f',mean(null_rej>0)),
 sprintf('mean_global_null_discoveries=%.6f',mean(null_rej)),
 'Diagnostic only: parent sign symmetry and jointly adjusted BH p-values',
 'Does not emulate independent collection, profile matching, or model selection'),
 file.path(out,'parent_null_scope_T2_V3_B3.txt'))
write.csv(v,file.path(out,'parent_inference_T2_V3_B3.csv'),row.names=FALSE)
writeLines(c('Real-world targets are empirical proxies, not known population truths',
  'Repeated depth and sample sizes are aggregated within independent parent datasets',
  'False-positive rate is a diagnostic under parent sign symmetry',
  'BH false discovery rate across the complete exported parent-level test panel'),
  file.path(out,'scientific_scope_T2_V3_B3.txt'))
cat('T2_V3_B3_REALWORLD_PARENT_PASS',nrow(v),'hypotheses\n')
