# Dataset-level correction for the complete shared model registry.
# Input: each dataset has frozen model predictions evaluated on the same subsamples.
realworld_integrated_audit <- function(datasets,models,sample_sizes=c(200L,1000L,3000L),R=500L,seed=101L,control='mean',prepared=NULL) {
 rows<-list();k<-0L
 for(id in names(datasets)){
  local_prepared <- if (is.null(prepared)) realworld_prepare(datasets[[id]],sample_sizes,R,seed+match(id,names(datasets))) else prepared[[id]]
  if (is.null(local_prepared)) stop('Prepared real-world bundle lacks dataset: ', id)
  for(nm in names(local_prepared)){
   z<-local_prepared[[nm]];m<-model_comparison_table(z$T,models,z$target,control,
                      stage='realworld_exploratory',B=500L,seed=seed+k)
   m$dataset_id<-id;m$sample_n<-z$sample_n;m$reference_type<-'full_sample_mean_proxy';
   k<-k+1L;rows[[k]]<-m
  }
 }
 ans<-do.call(rbind,rows)
 # within-dataset test occasions conservatively with Bonferroni.
 keys<-interaction(ans$dataset_id,ans$model,drop=TRUE)
 primary<-do.call(rbind,lapply(split(ans,keys),function(x){
    out<-x[1,,drop=FALSE]
    out$p_value<-min(1,min(x$p_value,na.rm=TRUE)*nrow(x))
    out$q95_p_value<-min(1,min(x$q95_p_value,na.rm=TRUE)*nrow(x))
    out$sample_n<-NA_integer_;out
 }))
 primary<-stage_fdr_all_models(primary,'realworld_dataset_level',.05)
 primary$q95_q_value <- NA_real_
 ok <- is.finite(primary$q95_p_value)
 primary$q95_q_value[ok] <- p.adjust(primary$q95_p_value[ok], method='BH')
 primary$q95_confirmed <- ok & primary$q95_q_value <= .05
 list(condition_rows=ans,dataset_level=primary)
}
