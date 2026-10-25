# Adapter for the completed V3 Monte Carlo production archive.
t2_v3_protocol <- function() 'v3_real26_seedplan20_mixedheldout_rlm100'
t2_v3_scientific_root <- function() Sys.getenv('T2_V3_SCIENTIFIC_ROOT', 'artifacts/mc_v3_real26')
t2_v3_block_dir <- function(role,family,seed,n,reps=500L) {
  if (!role %in% c('discovery','heldout','stress')) stop('Unknown V3 role')
  if (!family %in% t2_families()) stop('Unknown V3 family')
  valid <- switch(role,discovery=0:9,heldout=10:14,stress=15:19)
  if (length(seed)!=1L || is.na(seed) || !seed %in% valid) stop('V3 role/seed mismatch')
  if (!n %in% if(role=='discovery') 1000L else c(200L,1000L,3000L)) stop('V3 role/n mismatch')
  file.path(t2_v3_scientific_root(),t2_v3_protocol(),role,family,
            sprintf('seed%02d',as.integer(seed)),sprintf('n%d_r%d',as.integer(n),as.integer(reps)))
}
t2_v3_prepare_scenario <- function(s) {
  s$eligible <- rep(TRUE,26L)
  s$benchmark <- precompute_benchmarks(s$T,s$target,s$eligible)
  s
}
t2_v3_validate_scenario <- function(s, id, reps=500L) {
  if (!is.list(s) || !identical(as.integer(s$scenario_id),as.integer(id)) ||
      !is.matrix(s$T) || !is.numeric(s$T) ||
      !identical(dim(s$T),c(as.integer(reps),26L)) ||
      any(!is.finite(s$T)) ||
      !identical(colnames(s$T),ESTIMATOR_NAMES) ||
      !identical(s$component_names,ESTIMATOR_NAMES) ||
      !is.numeric(s$target) || length(s$target)!=1L || !is.finite(s$target))
    stop('V3 scientific scenario contract mismatch: ',id)
  invisible(TRUE)
}
t2_v3_read_block <- function(role,family,seed,n,reps=500L,selected=NULL) {
  root <- t2_v3_block_dir(role,family,seed,n,reps)
  path <- file.path(root,'canonical.rds')
  if (!file.exists(path)) stop('V3 canonical input missing: ',path)
  z <- t2_read_rds(path)
  if (!identical(z$protocol,t2_v3_protocol()) ||
      !identical(z$role,role) || !identical(z$family,family) ||
      !identical(as.integer(z$seed_index),as.integer(seed)) ||
      !identical(as.integer(z$n),as.integer(n)) ||
      !identical(as.integer(z$replications),as.integer(reps)) ||
      !identical(z$component_names,ESTIMATOR_NAMES) ||
      !is.data.frame(z$grid) || nrow(z$grid)!=121L ||
      !identical(as.integer(z$grid$scenario_id),0:120) ||
      length(z$scenarios)!=121L) stop('V3 canonical provenance mismatch')
  ids <- vapply(z$scenarios,function(s) as.integer(s$scenario_id),integer(1))
  if (!identical(ids,0:120)) stop('V3 scenario order mismatch')
  if (is.null(selected)) selected <- ids
  if (anyDuplicated(selected) || !all(selected %in% ids)) stop('V3 selected IDs mismatch')
  for (id in selected) t2_v3_validate_scenario(z$scenarios[[match(id,ids)]],id,reps)
  z$scenarios <- lapply(z$scenarios[match(selected,ids)],t2_v3_prepare_scenario)
  z
}
t2_v3_read_scenario <- function(role,family,seed,n,id,reps=500L) {
  root <- t2_v3_block_dir(role,family,seed,n,reps)
  p <- file.path(root,sprintf('scenario_%04d.rds',as.integer(id)))
  if (!file.exists(p)) stop('Missing V3 scientific scenario: ',p)
  s <- t2_read_rds(p)
  t2_v3_validate_scenario(s,id,reps)
  t2_v3_prepare_scenario(s)
}
