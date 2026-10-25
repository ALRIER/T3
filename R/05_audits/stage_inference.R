# Consistent inferential interface used in discovery, held-out, stress, and real data.
# BH controls multiplicity within explicitly declared groups of valid hypotheses.
# Discover-stage p-values and q-values are exploratory, NOT final proof of a winner.
paired_superiority_test <- function(candidate_squared_error,benchmark_squared_error,alternative='less') {
 a<-as.numeric(candidate_squared_error);b<-as.numeric(benchmark_squared_error)
 stopifnot(length(a)==length(b),length(a)>=4L,all(is.finite(a)),all(is.finite(b)))
 d<-a-b
 if(sd(d)==0) return(data.frame(p_value=if(mean(d)<0) 0 else 1,mean_difference=mean(d),mcse=0))
 p<-stats::t.test(d,mu=0,alternative=alternative)$p.value
 data.frame(p_value=p,mean_difference=mean(d),mcse=sd(d)/sqrt(length(d)))
}
apply_stage_fdr <- function(df,stage,alpha=ga_config$fdr_primary,group_cols=c('stage','metric')) {
 stopifnot(is.data.frame(df),'p_value'%in%names(df),all(is.finite(df$p_value)),all(df$p_value>=0&df$p_value<=1))
 df$stage<-stage
 if(!'metric'%in%names(df)) df$metric<-'mse'
 df<-bh_by_family(df,alpha,group_cols=group_cols)
 df$evidence_type<-if(stage=='discovery') 'exploratory' else 'confirmatory_if_prespecified'
 df
}
# Fixed-weight, paired squared error comparison against the benchmark of interest.
# Bootstrap CI for q95 is descriptive until a valid, preregistered null test exists.
assess_frozen_models <- function(T,models,target,baseline_id='mean',stage='heldout',alpha=.05,bootstrap_B=500L,bootstrap_seed=1L) {
 stopifnot(baseline_id %in% vapply(models,function(x)x$id,character(1)))
 baseline<-models[[which(vapply(models,function(x)x$id==baseline_id,logical(1)))[1]]]
 bs<-(model_predict(T,baseline)-target)^2
 rows<-lapply(seq_along(models),function(i){
   model<-models[[i]]
   se<-(model_predict(T,model)-target)^2
   a<-paired_superiority_test(se,bs)
   ci<-t2_q95_ci_v3(se,bs,B=bootstrap_B,seed=bootstrap_seed+i)
   data.frame(model=model$id,benchmark=baseline_id,metric='mse',mse=mean(se),
              q95=unname(quantile(se,.95,type=8)),p_value=a$p_value,
              difference=a$mean_difference,mcse=a$mcse,
              q95_lower=ci$q95_lower,q95_upper=ci$q95_upper,
              q95_delta=ci$delta,q95_delta_lower=ci$delta_lower,
              q95_delta_upper=ci$delta_upper,bootstrap_B=bootstrap_B)
 })
 apply_stage_fdr(do.call(rbind,rows),stage=stage,alpha=alpha)
}


# Confirmation-only paired bootstrap: MSE and Q95 deltas (candidate minus
# comparator). Resample independent replication units within a frozen shard.
t3_paired_dual_metric_ci <- function(candidate_errors,reference_errors,
                                     B=500L,seed=1L,level=.95) {
 x<-as.numeric(candidate_errors);y<-as.numeric(reference_errors)
 if(length(x)!=length(y)||length(x)<30L||any(!is.finite(x))||
    any(!is.finite(y))||any(x<0)||any(y<0)||B<200L||
    level<=0||level>=1)stop('Invalid paired inference input')
 q95<-function(z)unname(stats::quantile(z,.95,type=8))
 set.seed(seed)
 boot<-replicate(B,{
   k<-sample.int(length(x),length(x),replace=TRUE)
   c(mse_delta=mean(x[k]-y[k]),q95_delta=q95(x[k])-q95(y[k]))
 })
 limits<-t(apply(boot,1,stats::quantile,
   probs=c((1-level)/2,1-(1-level)/2),type=8))
 data.frame(metric=c('mse','q95'),
   difference=c(mean(x-y),q95(x)-q95(y)),
   lower=limits[,1],upper=limits[,2],
   level=level,bootstrap_B=B,
   method='paired_replication_percentile_bootstrap',
   evidence_role='descriptive_until_prespecified_confirmation')
}
# Negative controls require known null labels; near-gate flags are
# sensitivity diagnostics, never retrospective threshold optimization.
t3_gate_diagnostics <- function(df,alpha=.05,bandwidth=.01,
                                group_cols=c('stage','metric')) {
 needed<-c('model','p_value','negative_control')
 if(!is.data.frame(df)||!all(needed%in%names(df))||
    any(!is.finite(df$p_value))||any(df$p_value<0|df$p_value>1)||
    anyNA(df$negative_control)||!is.logical(df$negative_control)||
    alpha<=0||alpha>=1||bandwidth<0)
   stop('Invalid near-gate/negative-control inputs')
 keys<-intersect(group_cols,names(df))
 grp<-if(length(keys))interaction(df[keys],drop=TRUE) else
   factor(rep('all',nrow(df)))
 df$q_value<-NA_real_
 for(k in levels(grp)){
   ix<-which(grp==k)
   df$q_value[ix]<-p.adjust(df$p_value[ix],method='BH')
 }
 df$near_gate<-abs(df$q_value-alpha)<=bandwidth
 df$passes_gate<-df$q_value<=alpha
 df$negative_control_false_win<-df$negative_control&df$passes_gate
 df$gate_alpha<-alpha
 df$near_gate_bandwidth<-bandwidth
 df
}


# Post-run only: paired comparisons across independent seed-level summaries.
# Individual scenario scores are NOT treated as independent inferential units.
t3_confirmatory_seed_summary <- function(scores,stage,reference='mean',
                                        alpha=.05,near_band=.01) {
 needed<-c('model','mse','q95','training_seed')
 if(!is.data.frame(scores)||!all(needed%in%names(scores))||
    !stage%in%c('heldout','stress','realworld')||
    any(!is.finite(scores$mse))||any(!is.finite(scores$q95)))
   stop('Invalid confirmatory stage scores')
 eval_col<-switch(stage,heldout='heldout_seed',stress='stress_seed',
                  realworld='realworld_seed')
 if(!eval_col%in%names(scores))stop('Missing independent evaluation seed')
 if(!reference%in%as.character(scores$model))stop('Missing benchmark')
 if(anyDuplicated(scores[c(groups<-intersect(c('family','sample_n','dataset_id','parent_dataset_id'),names(scores)),eval_col,'training_seed','model',intersect('scenario_id',names(scores)))]))stop('Duplicate stage score keys')
 # Independent evaluation seed is the test unit; training seeds and scenarios
 # form repeated measures and are averaged before inference.
 groups<-intersect(c('family','sample_n','dataset_id','parent_dataset_id'),names(scores))
 keys<-c(groups,eval_col,'model')
 z<-aggregate(scores[,c('mse','q95'),drop=FALSE],
              scores[,keys,drop=FALSE],mean)
 idvars<-c(groups,eval_col)
 group_id<-if(length(groups))interaction(z[groups],drop=TRUE) else
   factor(rep('all',nrow(z)))
 ans<-list()
 for(group in levels(group_id)) {
  zz<-z[group_id==group,,drop=FALSE]
  base<-zz[zz$model==reference,,drop=FALSE]
  if(anyDuplicated(base[idvars]))stop('Duplicate reference seed')
  for(model in setdiff(unique(as.character(zz$model)),reference)) {
    candidate<-zz[zz$model==model,,drop=FALSE]
    join<-merge(candidate,base,by=idvars,suffixes=c('_candidate','_reference'))
    if(nrow(join)!=nrow(candidate)||nrow(join)!=nrow(base)||
       nrow(join)<3L)stop('Unpaired or insufficient independent evaluation seeds')
    for(metric in c('mse','q95')) {
      delta<-join[[paste0(metric,'_candidate')]]-
             join[[paste0(metric,'_reference')]]
      if(all(delta==delta[1L])) {
        pv<-if(delta[1L]<0) 0 else 1
        limits<-rep(delta[1L],2L)
      } else {
        test<-stats::t.test(delta,alternative='less')
        pv<-test$p.value
        limits<-stats::t.test(delta,conf.level=.95)$conf.int
      }
      ans[[length(ans)+1L]]<-data.frame(stage=stage,group=group,
        model=model,metric=metric,benchmark=reference,
        independent_seeds=nrow(join),difference=mean(delta),
        lower=limits[1L],upper=limits[2L],p_value=pv,
        negative_control=FALSE,
        inference_unit='evaluation_seed',
        stringsAsFactors=FALSE)
    }
  }
 }
 if(!length(ans))stop('No confirmatory comparisons')
 out<-do.call(rbind,ans)
 out<-t3_gate_diagnostics(out,alpha,near_band,group_cols=c('stage','group','metric'))
 out$evidence_status<-'provisional_seed_level_subject_to_design_review'
 out
}


# Aggregate ONLY complete independent evaluation-seed shards. Do not infer
# significance from scenario rows or training-seed duplicates.
t3_aggregate_confirmatory_shards <- function(stage,family,n,root='artifacts',
                                              alpha=.05,near_band=.01) {
 if(!stage%in%c('heldout','stress','realworld')||
    !family%in%t2_families()||!n%in%t2_v3_sample_sizes(stage))
   stop('Invalid aggregate target')
 seeds<-t2_v3_indices(stage)
 shard<-function(seed)switch(stage,
  heldout=file.path(root,'heldout_v3',family,sprintf('seed%02d_n%d',seed,n)),
  stress=file.path(root,'v3_stress_scoring',family,sprintf('seed%02d_n%d',seed,n)),
  realworld=file.path(root,'realworld_v3',family,sprintf('seed%02d_n%d',seed,n)))
 rows<-list()
 for(seed in seeds){
   dir<-shard(seed)
   contract<-file.path(dir,'stage_contract.rds')
   t3_stage_require(contract,stage,sprintf('b3_%s_n%d',family,n),
                    family,seed,n)
   paths<-if(stage=='realworld')
      file.path(dir,sprintf('train_seed%02d_scores.csv',t2_v3_indices('discovery')))
      else file.path(dir,if(stage=='heldout')'non_evolutionary_control_scores.csv' else 'scores.csv')
   if(!all(file.exists(paths)))stop('Missing complete evaluation shard: ',dir)
   part<-do.call(rbind,lapply(paths,function(path)read.csv(path,stringsAsFactors=FALSE)))
   seed_col<-paste0(stage,'_seed')
   if(!all(c('training_seed','model','mse','q95',seed_col)%in%names(part))||
      any(part[[seed_col]]!=seed)||!setequal(unique(part$training_seed),t2_v3_indices('discovery'))||
      length(unique(part$model))!=32L)stop('Incomplete 32-model evaluation shard: ',dir)
   part$family<-family
   part$sample_n<-n
   rows[[length(rows)+1L]]<-part
 }
 combined<-do.call(rbind,rows)
 # Real World has a dataset-level reference proxy, not population truth.
 # The seed-level test is only a descriptive sensitivity diagnostic until
 # datasets and their parent clusters are prespecified and verified.
 inference<-t3_confirmatory_seed_summary(combined,stage,alpha=alpha,
                                         near_band=near_band)
 if(stage=='realworld')
   inference$evidence_status<-'descriptive_proxy_not_population_confirmation'
 list(scores=combined,inference=inference,
      manifest=data.frame(stage=stage,family=family,n=n,seeds=seeds,
       evidence_status='complete_40_seed_partition_stage'))
}
