# Post-production V3 consumers. Every read is read-only and role-aware.
t2_v3_dependency_manifest <- function(role,family,seed,n,reps=500L) {
  root <- t2_v3_block_dir(role,family,seed,n,reps)
  ids <- 0:320
  paths <- file.path(root,sprintf('scenario_%04d.rds',ids))
  if (any(!file.exists(paths))) stop('Incomplete V3 scenario shard')
  data.frame(protocol=t2_v3_protocol(),role=role,family=family,
             seed_index=seed,n=n,replications=reps,scenario_id=ids,
             relative_path=basename(paths),
             sha256=vapply(paths,t2_sha256,character(1)),
             stringsAsFactors=FALSE)
}
t2_v3_stream_scores <- function(role,family,seed,n,models,reps=500L,
                                selected=0:320) {
  if (!role %in% c('heldout','stress')) stop('Scores require independent heldout or stress inputs')
  if (!length(selected) || anyDuplicated(selected) || !all(selected %in% 0:320))
    stop('Invalid selected scenarios')
  if (!is.list(models) || !length(models)) stop('Frozen candidate list missing')
  ids <- vapply(models,function(m) m$id,character(1))
  if (anyDuplicated(ids)) stop('Duplicate frozen candidates')
  rows <- vector('list',length(selected))
  for (i in seq_along(selected)) {
    sc <- t2_v3_read_scenario(role,family,seed,n,selected[[i]],reps)
    z <- score_model_set(sc$T,models,sc$target)
    z$scenario_id <- sc$scenario_id
    z$contamination <- sc$contamination
    z$mad_scale <- sc$mad_scale
    z$mechanism <- sc$mechanism
    z$band <- sc$band
    z$role <- role
    z$family <- family
    z$seed_index <- seed
    z$sample_n <- n
    rows[[i]] <- z
  }
  do.call(rbind,rows)
}
t2_v3_discovery_input <- function(family,seed,n=1000L,reps=500L,
                                  selected=0:320) {
  # Prefer individual immutable scenario shards, avoiding a redundant canonical
  # 321-scenario object in RAM alongside the optimizer training list.
  ids <- as.integer(selected)
  if(!length(ids)||anyDuplicated(ids)||!all(ids %in% 0:320))stop('Invalid training IDs')
  scenarios <- lapply(ids,function(id)t2_v3_read_scenario('discovery',family,seed,n,id,reps))
  list(protocol=t2_v3_protocol(),role='discovery',family=family,
       seed_index=seed,n=n,replications=reps,
       scenarios=scenarios,canonical_id=sprintf('v3_discovery_%s_seed%02d_n%d',family,seed,n))
}


# Preflight / postflight structural audit. Does not run Monte Carlo, fit models,
# change seeds, or read external data; fail closed on missing stage outputs.
t3_stage_preflight <- function(role,family,seed,n,reps=500L,
                                require_scenarios=TRUE) {
 if(!role%in%c('discovery','heldout','stress','realworld')||
    !family%in%t2_families()||
    length(seed)!=1L||!seed%in%t2_v3_indices(role)||
    !n%in%t2_v3_sample_sizes(role))
   stop('B3 stage role/family/seed/sample size invalid')
 if(require_scenarios&&role!='realworld') {
   root<-t2_v3_block_dir(role,family,seed,n,reps)
   paths<-file.path(root,sprintf('scenario_%04d.rds',0:320))
   if(!all(file.exists(paths)))stop('Missing 321 scenario shard inputs')
   if(anyDuplicated(paths))stop('Duplicate scenario shard path')
 }
 invisible(TRUE)
}
t3_stage_postflight <- function(path,role,family,seed,n,
                                 expected_files=character()) {
 x<-t3_stage_require(path,role,sprintf('b3_%s_n%d',family,n),
                     family,seed,n)
 if(length(expected_files)) {
   if(anyDuplicated(expected_files)||!all(file.exists(expected_files)))
     stop('Missing or duplicate stage result files')
   hashes<-vapply(expected_files,t2_sha256,character(1))
   if(anyNA(hashes)||any(!nzchar(hashes)))stop('Invalid result digest')
 }
 invisible(x)
}
