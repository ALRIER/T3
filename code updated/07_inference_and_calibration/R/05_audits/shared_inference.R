# Paired diagnostic shared by ALL engines and stages.
# Inferential p values must come from a valid predeclared test, not raw bootstrap sign frequency.
paired_error_diagnostic <- function(candidate,control) {
  stopifnot(length(candidate)==length(control),length(candidate)>2L,
            all(is.finite(candidate)),all(is.finite(control)))
  d<-candidate-control
  c(mean_difference=mean(d),mcse=sd(d)/sqrt(length(d)),
    ci_lower=mean(d)-qt(.975,length(d)-1L)*sd(d)/sqrt(length(d)),
    ci_upper=mean(d)+qt(.975,length(d)-1L)*sd(d)/sqrt(length(d)))
}
bh_by_family <- function(comparisons,alpha=.05,group_cols=c('stage')) {
  stopifnot(is.data.frame(comparisons),all(c('p_value',group_cols)%in%names(comparisons)))
  if(any(!is.finite(comparisons$p_value)) || any(comparisons$p_value<0|comparisons$p_value>1)) stop('Invalid p values')
  comparison_group<-interaction(comparisons[,group_cols,drop=FALSE],drop=TRUE)
  comparisons$q_value<-ave(comparisons$p_value,comparison_group,FUN=function(p)p.adjust(p,'BH'))
  comparisons$confirmed<-comparisons$q_value<=alpha
  comparisons
}
negative_control_audit <- function(result_table,control_ids,decision_col='confirmed') {
  stopifnot(all(c('model',decision_col)%in%names(result_table)))
  z<-result_table[result_table$model %in% control_ids,,drop=FALSE]
  if(!nrow(z)) return(data.frame(n_controls=0L,positive_flags=NA_integer_,flag_rate=NA_real_))
  data.frame(n_controls=nrow(z),positive_flags=sum(z[[decision_col]],na.rm=TRUE),
             flag_rate=mean(z[[decision_col]],na.rm=TRUE))
}
# Once per dataset, after condition-level probes: no double-counting of nested probes.
dataset_saturation <- function(results,dataset_col='dataset_id',win_col='confirmed',cap=3L) {
  stopifnot(all(c(dataset_col,win_col)%in%names(results)))
  x<-split(results,results[[dataset_col]])
  do.call(rbind,lapply(names(x),function(key){
    z<-x[[key]]; n<-sum(z[[win_col]],na.rm=TRUE)
    data.frame(dataset_id=key,uncapped_wins=n,countable_wins=min(cap,n),
               saturated=n>cap,stringsAsFactors=FALSE)
  }))
}
