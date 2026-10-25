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
