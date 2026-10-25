# Prospectively fixed, equal-weight normalized MSE/q95 selection.
# Objective scales are derived exclusively from the 26 classical estimators
# on the current training scenarios, never from optimizer archives or test data.
t3_training_reference_scales <- function(scenarios) {
 stopifnot(length(scenarios)>0L)
 x<-t(vapply(scenarios,function(z){
   if(!is.matrix(z$T)||ncol(z$T)!=26L)stop('Invalid 26-estimator component matrix')
   sc<-score_model_set(z$T,lapply(ESTIMATOR_NAMES,function(nm)
     new_frozen_model(nm,component=nm)),z$target)
   c(min(sc$mse),min(sc$q95))
 },numeric(2L)))
 setNames(pmax(colMeans(x),.Machine$double.eps),c('mse','q95'))
}
t3_select_weights <- function(result,scales) {
 O<-as.matrix(result$objectives);W<-as.matrix(result$weights)
 if(!all(c('mse','q95')%in%colnames(O)) && ncol(O)==2L)
   colnames(O)<-c('mse','q95')
 stopifnot(nrow(W)==26L,ncol(W)==nrow(O),all(is.finite(O)),
   all(is.finite(W)),all(W>=0),all(c('mse','q95')%in%names(scales)),
   all(is.finite(scales)),all(scales>0))
 # Common scalarization; no implicit algorithm-specific scaling.
 loss<-rowMeans(sweep(O[,c('mse','q95'),drop=FALSE],
                         2L,scales[c('mse','q95')],'/'))
 idx<-order(loss,O[,'mse'],O[,'q95'],seq_len(nrow(O)))[1L]
 list(index=idx,weights=W[,idx],normalized_loss=loss[idx],
      mse=O[idx,'mse'],q95=O[idx,'q95'],
      scales=scales,policy='T3_EQUAL_MSE_Q95_BASELINE26_TRAIN_ONLY_V1')
}
t3_select_models <- function(engines,training_scenarios) {
 if(length(engines)>1L)t3_assert_engine_budget_parity(engines)
 scales<-t3_training_reference_scales(training_scenarios)
 chosen<-lapply(names(engines),function(engine)
   t3_select_weights(engines[[engine]],scales))
 names(chosen)<-names(engines)
 models<-lapply(ESTIMATOR_NAMES,function(nm)new_frozen_model(nm,component=nm))
 models<-c(models,lapply(names(chosen),function(engine)
   new_frozen_model(engine,weights=chosen[[engine]]$weights,family=engine)))
 stopifnot(length(models)==26L+length(engines))
 list(models=models,selection=chosen,scales=scales)
}


# Integrated scientific validation: T3 B3
# T3 scientific validation contracts. All null replicates must rerun Discovery.
# Never estimate selection-aware FPR from fixed winning weights.
t3_calibrate_selection_fpr <- function(observed, null_replays, alpha=0.05) {
  stopifnot(is.data.frame(observed), all(c("model","statistic") %in% names(observed)),
            is.list(null_replays), length(null_replays)>=19L,
            is.finite(alpha),alpha>0,alpha<1)
  if(anyDuplicated(observed$model) || any(!is.finite(observed$statistic)))
    stop("Invalid observed, unique model statistics required")
  ids <- as.character(observed$model)
  # Each replay must be produced by refitting optimizers, reselecting W and
  # evaluating on an independent null-confirmation sample.
  extract <- function(z) {
    if(!is.list(z) || !identical(z$reselected, TRUE) ||
       !identical(z$independent_confirmation, TRUE) ||
       !is.data.frame(z$statistics) ||
       !all(c("model","statistic") %in% names(z$statistics)))
      stop("Null replay must reselect W and use independent confirmation")
    v<-z$statistics
    if(anyDuplicated(v$model)|| !setequal(as.character(v$model), ids) ||
       any(!is.finite(v$statistic))) stop("Null model list/statistics mismatch")
    as.numeric(v$statistic[match(ids,as.character(v$model))])
  }
  null <- t(vapply(null_replays, extract, numeric(length(ids))))
  # Larger statistic = stronger evidence. Familywise maxT adjustment.
  maximum <- apply(null,1L,max)
  raw <- vapply(seq_along(ids),function(j)
    (1+sum(null[,j]>=observed$statistic[j]))/(nrow(null)+1),numeric(1))
  adjusted <- vapply(observed$statistic,function(x)
    (1+sum(maximum>=x))/(nrow(null)+1),numeric(1))
  data.frame(model=ids,statistic=observed$statistic,p_empirical=raw,
             p_maxT=adjusted,significant=adjusted<=alpha,
             replay_count=nrow(null),selection_replayed=TRUE,
             stringsAsFactors=FALSE)
}
# Scenario metadata: scenario_id, rate, scale, mechanism.
# Scenarios excluded from fitting are never returned in training.
t3_transfer_partition <- function(grid, excluded_mechanisms, neighborhoods,
                                  tolerance=1e-10) {
  required<-c("scenario_id","rate","scale","mechanism")
  if(!is.data.frame(grid)||!all(required%in%names(grid))||
     anyDuplicated(grid$scenario_id) || any(!is.finite(grid$rate)) ||
     any(!is.finite(grid$scale)))stop("Invalid scenario grid")
  if(!length(excluded_mechanisms)||!length(neighborhoods))
    stop("Declare excluded mechanisms and neighborhoods prospectively")
  if(!all(excluded_mechanisms%in%grid$mechanism))
    stop("Requested excluded mechanism absent")
  if(!is.data.frame(neighborhoods)||!all(c("rate","scale")%in%names(neighborhoods))||
     any(!is.finite(as.matrix(neighborhoods[c("rate","scale")]))))
    stop("Invalid neighborhood coordinates")
  neighborhood <- Reduce(`|`,lapply(seq_len(nrow(neighborhoods)),function(i)
    abs(grid$rate-neighborhoods$rate[i])<=tolerance &
    abs(grid$scale-neighborhoods$scale[i])<=tolerance),
    init=rep(FALSE,nrow(grid)))
  excluded<-grid$mechanism%in%excluded_mechanisms
  group<-ifelse(excluded & neighborhood,"both",
                ifelse(excluded,"excluded_mechanism",
                       ifelse(neighborhood,"excluded_neighborhood","training")))
  if(!any(group=="training")||!any(excluded)||!any(neighborhood))
    stop("Empty training or requested transfer groups")
  data.frame(scenario_id=grid$scenario_id,group=group,
             in_training=group=="training", stringsAsFactors=FALSE)
}
t3_transfer_score <- function(partition, scores) {
  if(!is.data.frame(scores)||!all(c("scenario_id","model","mse","q95")%in%names(scores)) ||
     any(!is.finite(scores$mse))||any(!is.finite(scores$q95)))
    stop("Missing transfer scores")
  if(anyDuplicated(scores[c("scenario_id","model")]))
    stop("Duplicate model-scenario score")
  if(!all(unique(scores$scenario_id)%in%partition$scenario_id))
    stop("Unregistered scenario IDs")
  s<-merge(scores,partition,by="scenario_id",sort=FALSE)
  groups<-setdiff(unique(partition$group),"training")
  if(!all(groups%in%unique(s$group)))stop("Transfer groups lack scores")
  out<-aggregate(cbind(mse,q95)~model+group,data=s[s$group!="training",],FUN=mean)
  out$n_scenarios<-vapply(seq_len(nrow(out)),function(i)
    length(unique(s$scenario_id[s$model==out$model[i] & s$group==out$group[i]])),integer(1))
  out
}


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

# Equal evaluation accounting before any downstream model comparison.
t3_assert_engine_budget_parity <- function(engines) {
  if(!length(engines))stop('No optimization results')
  evaluations<-vapply(engines,function(x)as.integer(x$evaluations_used),integer(1))
  budgets<-vapply(engines,function(x)as.integer(x$evaluation_budget),integer(1))
  if(anyNA(evaluations)||anyNA(budgets)||length(unique(evaluations))!=1L||
     any(evaluations!=budgets)||any(vapply(engines,function(x)
       !identical(x$budget_policy,'B3_EQUAL_CANDIDATE_EVALUATIONS_V1'),logical(1))))
    stop('Discovery engine objective-budget mismatch')
  data.frame(engine=names(engines),candidate_evaluations=evaluations,
             planned_evaluations=budgets,stringsAsFactors=FALSE)
}
