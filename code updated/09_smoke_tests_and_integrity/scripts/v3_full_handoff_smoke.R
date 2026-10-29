#!/usr/bin/env Rscript
# V3 production handoff smoke: identical scientific inputs, distinct streams.
source('R/00_shared/load_all.R'); t2_load('.')
source('R/00_shared/pipeline.R')
source('R/00_shared/v3_scientific_adapter.R')
source('R/00_shared/v3_downstream.R')
family <- Sys.getenv('T2_SMOKE_FAMILY','normal')
for (job in list(list(role='discovery',seed=0L,n=1000L),
                 list(role='heldout',seed=10L,n=200L),
                 list(role='stress',seed=15L,n=200L))) {
  args <- job
  root <- t2_v3_block_dir(args$role,family,args$seed,args$n)
  x <- t2_v3_read_block(args$role,family,args$seed,args$n,selected=c(0L,1L,120L))
  if (!identical(vapply(x$scenarios,function(s)s$scenario_id,integer(1L)),c(0L,1L,120L)))
    stop('Scenario ordering mismatch')
  manifest <- t2_v3_dependency_manifest(args$role,family,args$seed,args$n)
  if (nrow(manifest)!=121L) stop('Incomplete scientific scenario manifest')
  for (id in c(0L,1L,120L)) {
    s <- t2_v3_read_scenario(args$role,family,args$seed,args$n,id)
    if (!identical(s$T,x$scenarios[[match(id,c(0L,1L,120L))]]$T))
      stop('Canonical and separate scenario differ')
  }
  cat('V3_INPUT_PASS',args$role,family,args$seed,args$n,'\n')
}
training_grid <- t2_v3_read_block('discovery',family,0L,1000L,selected=0:120)$grid
bands <- ifelse(training_grid$rate==0,'clean',
         ifelse(training_grid$rate<=.05,'low',
         ifelse(training_grid$rate<=.1,'intermediate','high')))
selected_training <- vapply(c('clean','low','intermediate','high'),
                           function(b) training_grid$scenario_id[which(bands==b)[1L]],integer(1))
if(anyNA(selected_training)) stop('Missing training contamination band')
d <- t2_v3_discovery_input(family,0L,selected=unname(selected_training))
fit <- t2_run_discovery(d,'smoke','v3-smoke-independent',engine='all')
if (length(fit$engines)!=4L || length(fit$models)<5L) stop('Discovery engine smoke failed')
learned <- Filter(function(m)!is.null(m$weights),fit$models)
if (!length(learned)) stop('No frozen W candidates')
for (role in c('heldout','stress')) {
  seed <- if(role=='heldout') 10L else 15L
  score <- t2_v3_stream_scores(role,family,seed,200L,fit$models,selected=c(0L,1L,120L))
  if (!nrow(score) || any(!is.finite(score$mse)) || any(!is.finite(score$q95)))
    stop('Invalid V3 downstream inference scores')
  if (!all(vapply(learned,function(m) abs(sum(m$weights)-1)<1e-8,logical(1))))
    stop('Frozen W simplex contract failed')
  cat('V3_SCORE_PASS',role,nrow(score),'\n')
}
cat('V3_HANDOFF_SMOKE_PASS\n')
