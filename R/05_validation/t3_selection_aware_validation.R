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
