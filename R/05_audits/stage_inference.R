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
