# Callable full-selection null replay. Executor MUST re-tune and refit in each replay.
# Discovery and confirmation generators are injectable to keep stages independent.
t3_full_selection_replay <- function(B, null_training, null_confirmation,
                                     fit_and_select, score_selected,
                                     expected_models, master_seed=4101L) {
  if(!exists("t3_calibrate_selection_fpr",mode="function"))
    stop("Load selection-aware validation module first")
  if(!is.function(null_training)||!is.function(null_confirmation)||
     !is.function(fit_and_select)||!is.function(score_selected)||
     B<19||length(expected_models)<1L||anyDuplicated(expected_models))
    stop("Incomplete full-selection replay specification")
  set.seed(master_seed)
  seeds<-matrix(sample.int(.Machine$integer.max,2L*B),ncol=2L)
  lapply(seq_len(B),function(i) {
    train<-null_training(seeds[i,1L],i)
    confirm<-null_confirmation(seeds[i,2L],i)
    if(!is.list(train)||!is.list(confirm)||
       is.null(train$sample_ids)||is.null(confirm$sample_ids)||
       length(intersect(as.character(train$sample_ids),
                        as.character(confirm$sample_ids)))>0L)
      stop("Null training/confirmation sample IDs must be disjoint")
    # fit_and_select must invoke the same hyperparameter optimizer, model ranking,
    # and t3_select_models common W rule as the observed workflow.
    selected<-fit_and_select(train,i)
    if(!is.list(selected)||!identical(selected$selection_reexecuted,TRUE)||
       !identical(selected$w_policy,"T3_EQUAL_MSE_Q95_BASELINE26_TRAIN_ONLY_V1"))
      stop("Full tuning/model/W reselection not demonstrated")
    stats<-score_selected(selected,confirm,i)
    if(!is.data.frame(stats)||!all(c("model","statistic")%in%names(stats))||
       !setequal(as.character(stats$model),expected_models))
      stop("Null confirmation statistics incomplete")
    list(reselected=TRUE,independent_confirmation=TRUE,statistics=stats,
         training_seed=seeds[i,1L],confirmation_seed=seeds[i,2L],
         selection_policy=selected$w_policy)
  })
}
