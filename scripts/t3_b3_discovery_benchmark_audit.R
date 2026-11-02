#!/usr/bin/env Rscript
# Training-only audit of each frozen W* against all 26 classical estimators.
# This reports Discovery performance; it deliberately makes no p-value/BH claim.
a <- commandArgs(trailingOnly=TRUE)
root <- if(length(a)) a[[1L]] else 'artifacts/discovery_v3'
source('R/00_shared/load_all.R'); t2_load('.')
files <- list.files(root,'^discovery[.]rds$',recursive=TRUE,full.names=TRUE)
files <- files[!grepl('benchmark_audit_v2',files,fixed=TRUE)]
if(!length(files)) stop('No frozen Discovery artifacts found')
get_engine <- function(x) {
  x <- tolower(as.character(x)); order <- c('dirichlet','nsga2','de','ga')
  tokens <- strsplit(gsub('[^a-z0-9]+','_',x),'_',fixed=TRUE)[[1L]]
  tokens <- setdiff(tokens,c('normal','lognormal','weibull','invgauss','exgaussian','exwald'))
  hit <- order[order %in% tokens]
  if(length(hit)) hit[[1L]] else NA_character_
}
pair_rows <- list(); candidate_rows <- list(); identities <- character(); pi <- 0L; ci <- 0L
for(path in files) {
  fit <- readRDS(path)
  if(!is.data.frame(fit$training_control_comparison)) stop('Discovery artifact lacks training score panel: ',path)
  z <- fit$training_control_comparison
  if(!all(c('model','scenario_id','mse','q95')%in%names(z))) stop('Invalid Discovery training score schema')
  z$candidate_engine <- vapply(z$model,function(m)
    if(m%in%ESTIMATOR_NAMES) NA_character_ else get_engine(m),character(1))
  candidates <- unique(z$model[!is.na(z$candidate_engine)])
  if(length(candidates)!=4L) stop('Expected four retained evolutionary W* in ',path)
  if(!all(ESTIMATOR_NAMES%in%z$model)) stop('Discovery score panel is missing a classical benchmark in ',path)
  meta <- data.frame(family=basename(dirname(dirname(dirname(path)))),stringsAsFactors=FALSE)
  # Recover identity from the canonical output path, without relying on job names.
  p <- strsplit(normalizePath(path,mustWork=FALSE),.Platform$file.sep,fixed=TRUE)[[1L]]
  ix <- match('discovery_v3',p)
  family <- if(!is.na(ix)&&length(p)>=ix+3L)p[ix+1L] else NA_character_
  seed <- if(!is.na(ix)&&length(p)>=ix+3L)sub('^seed','',p[ix+2L]) else NA_character_
  sample_n <- if(!is.na(ix)&&length(p)>=ix+3L)sub('^n','',p[ix+3L]) else NA_character_
  if(is.na(family)||is.na(seed)||is.na(sample_n))stop('Cannot recover Discovery shard identity from path: ',path)
  identities <- c(identities,paste(family,as.integer(seed),as.integer(sample_n),sep='|'))
  for(candidate_id in candidates) {
    engine <- get_engine(candidate_id)
    cdat <- z[z$model==candidate_id,c('scenario_id','mse','q95')]
    strict <- data.frame(scenario_id=cdat$scenario_id,
      beats_all26_mse=TRUE,beats_all26_q95=TRUE,beats_all26_joint=TRUE)
    for(benchmark in ESTIMATOR_NAMES) {
      b <- z[z$model==benchmark,c('scenario_id','mse','q95')]
      pair <- merge(cdat,b,by='scenario_id',suffixes=c('_candidate','_benchmark'))
      if(nrow(pair)!=nrow(cdat)) stop('Unpaired Discovery scenario scores in ',path)
      dm <- pair$mse_candidate-pair$mse_benchmark
      dq <- pair$q95_candidate-pair$q95_benchmark
      pi <- pi+1L
      pair_rows[[pi]] <- data.frame(family=family,training_seed=seed,sample_n=sample_n,
        engine=engine,benchmark=benchmark,scenarios=nrow(pair),
        mse_win_scenarios=sum(dm<0),q95_win_scenarios=sum(dq<0),
        joint_win_scenarios=sum(dm<0 & dq<0),
        mean_mse_gain_pct=mean(100*(pair$mse_benchmark-pair$mse_candidate)/pmax(abs(pair$mse_benchmark),.Machine$double.eps)),
        mean_q95_gain_pct=mean(100*(pair$q95_benchmark-pair$q95_candidate)/pmax(abs(pair$q95_benchmark),.Machine$double.eps)),
        evidence='training_only_descriptive_no_inference',stringsAsFactors=FALSE)
      strict$beats_all26_mse <- strict$beats_all26_mse & dm<0
      strict$beats_all26_q95 <- strict$beats_all26_q95 & dq<0
      strict$beats_all26_joint <- strict$beats_all26_joint & dm<0 & dq<0
    }
    ci <- ci+1L
    candidate_rows[[ci]] <- data.frame(family=family,training_seed=seed,sample_n=sample_n,
      engine=engine,scenarios=nrow(strict),
      scenarios_beating_all26_mse=sum(strict$beats_all26_mse),
      scenarios_beating_all26_q95=sum(strict$beats_all26_q95),
      scenarios_beating_all26_joint=sum(strict$beats_all26_joint),
      proportion_beating_all26_mse=mean(strict$beats_all26_mse),
      proportion_beating_all26_q95=mean(strict$beats_all26_q95),
      proportion_beating_all26_joint=mean(strict$beats_all26_joint),
      evidence='training_only_descriptive_no_inference',stringsAsFactors=FALSE)
  }
  rm(fit,z); invisible(gc(FALSE))
}
expected <- expand.grid(family=t2_families(),training_seed=0:9,
  sample_n=t2_v3_sample_sizes('discovery'),stringsAsFactors=FALSE)
expected_ids <- with(expected,paste(family,training_seed,sample_n,sep='|'))
if(anyDuplicated(identities)||!setequal(identities,expected_ids))
  stop('Discovery audit requires exactly one frozen artifact for every family x seed x sample-size shard')
out <- file.path(root,'benchmark_audit_v2')
if(dir.exists(out)) stop('Refusing to overwrite immutable Discovery benchmark audit')
dir.create(out,recursive=TRUE,showWarnings=FALSE)
write.csv(do.call(rbind,pair_rows),file.path(out,'candidate_vs_each_benchmark.csv'),row.names=FALSE)
write.csv(do.call(rbind,candidate_rows),file.path(out,'beats_all_26_by_scenario.csv'),row.names=FALSE)
write.csv(data.frame(path=files,sha256=vapply(files,t2_sha256,character(1))),
  file.path(out,'input_manifest.csv'),row.names=FALSE)
writeLines(c(paste0('code_revision=',Sys.getenv('GITHUB_SHA','unverified-local')),
             paste0('workflow_run_id=',Sys.getenv('GITHUB_RUN_ID','local'))),
  file.path(out,'run_provenance.txt'))
writeLines(c('Discovery creates and freezes four new convex W* estimators per family/seed/sample size.',
 'All 26 benchmarks including mean are evaluated on the same Discovery scenarios.',
 'These are training-set diagnostics only; selection and evaluation reuse the Discovery portfolio, so no confirmatory p-values or BH-FDR are reported.',
 'The output counts scenarios where each W* beats every one of the 26 simultaneously, separately for MSE, q95, and both.'),
 file.path(out,'analysis_contract.txt'))
cat('T3_DISCOVERY_ALL_BENCHMARK_AUDIT_PASS','models',length(candidate_rows),
 'pairwise_rows',length(pair_rows),'\n')
