#!/usr/bin/env Rscript
# Final inference from compact immutable Actions score summaries.
# Real-world depth/child rows are retained; inference clusters at parent_dataset_id.
a<-commandArgs(trailingOnly=TRUE)
if(length(a)!=3L)stop('Usage: STAGE REDUCED_ARTIFACT_ROOT OWN_BENCHMARK_MAP.csv')
stage<-a[[1L]];root<-a[[2L]];map_path<-a[[3L]]
if(!stage%in%c('heldout','stress','realworld'))stop('Invalid stage')
source('R/00_shared/load_all.R');t2_load('.')
if(!file.exists(map_path))stop('Frozen own-benchmark map artifact is required')
benchmark_map<-read.csv(map_path,stringsAsFactors=FALSE,check.names=FALSE)
files<-list.files(root,'[.]csv[.]gz$',recursive=TRUE,full.names=TRUE)
if(!length(files))stop('No reduced tournament inputs')
parts<-lapply(files,function(p)read.csv(gzfile(p),stringsAsFactors=FALSE,check.names=FALSE))
z<-do.call(rbind,parts);rownames(z)<-NULL

t3_model_engine<-function(x) {
  x<-tolower(as.character(x));engines<-c('dirichlet','nsga2','de','ga')
  tok<-strsplit(gsub('[^a-z0-9]+','_',x),'_',fixed=TRUE)[[1L]]
  tok<-setdiff(tok,c('normal','lognormal','weibull','invgauss','exgaussian','exwald'))
  h<-engines[engines%in%tok];if(length(h))h[[1L]] else NA_character_
}
if(stage=='realworld') {
  required<-c('parent_dataset_id','dataset_id','family','evaluation_profile','transfer_scope','sample_n',
              'scenario_id','depth','model','mse','q95','n_score_rows','realworld_seed')
  if(!all(required%in%names(z)))stop('Reduced Real-world child/depth/seed schema incomplete')
  # In this protocol family is the Discovery source family assigned by the
  # outcome-blind profile matcher. The matched scenario is a profile proxy,
  # not a known data-generating family.
  z$source_family<-z$family
  z$evaluation_family<-z$family
  child_keys<-c('parent_dataset_id','dataset_id','family','source_family',
    'evaluation_family','evaluation_profile','transfer_scope','sample_n','scenario_id','depth',
    intersect(c('domain','source_sector'),names(z)),
    'realworld_seed','model')
  # Reconstruct the equal-weight training-seed mean if a repair split a
  # Discovery training-seed block across multiple immutable score artifacts.
  weighted<-z[child_keys]
  weighted$weighted_mse<-z$mse*z$n_score_rows
  weighted$weighted_q95<-z$q95*z$n_score_rows
  weighted$n_score_rows<-z$n_score_rows
  sums<-aggregate(weighted[c('weighted_mse','weighted_q95','n_score_rows')],
                  weighted[child_keys],sum)
  sums$mse<-sums$weighted_mse/sums$n_score_rows
  sums$q95<-sums$weighted_q95/sums$n_score_rows
  child_seed_scores<-sums[c(child_keys,'mse','q95','n_score_rows')]
  # One row per child/depth/model for descriptive inspection. The inferential
  # table below first averages children within each parent, then tests across
  # independent parents; children/depths/seeds are never pseudo-replicated.
  child_keys_no_seed<-setdiff(child_keys,'realworld_seed')
  pooled_child<-aggregate(child_seed_scores[c('mse','q95')],
    child_seed_scores[child_keys_no_seed],mean)
  child_groups<-c('parent_dataset_id','dataset_id','family','source_family',
    'evaluation_family','evaluation_profile','transfer_scope','sample_n','scenario_id','depth')
  child_ans<-t3_pairwise_tournament(child_seed_scores,'realworld','realworld_seed',
    child_groups,benchmark_map,alpha=ga_config$fdr_primary)
  write_dir<-file.path('artifacts','v3_confirmatory_pairwise','realworld_v3')

  parent_keys<-c('parent_dataset_id','family','source_family','evaluation_family',
    'evaluation_profile','transfer_scope','sample_n','scenario_id','depth','model')
  parent_scores<-aggregate(pooled_child[c('mse','q95')],pooled_child[parent_keys],mean)
  parent_scores$independent_unit<-parent_scores$parent_dataset_id
  groups<-c('family','source_family','evaluation_family','transfer_scope',
            'evaluation_profile','sample_n','scenario_id','depth')
  z<-parent_scores
} else {
  groups<-c('family','source_family','evaluation_family','transfer_scope',
            'sample_n','scenario_id')
  child_ans<-NULL
  child_seed_scores<-NULL
}

if(stage=='stress') {
  # Freeze the best classical baseline on Stress seeds 20–24; infer only on
  # disjoint Stress seeds 25–29. No confirmation seed selects its comparator.
  stress_seeds<-sort(unique(as.integer(z$independent_unit)))
  if(!identical(stress_seeds,as.integer(t2_v3_indices('stress'))))
    stop('Stress evaluation seed set differs from the frozen role')
  calibration_seeds<-head(stress_seeds,length(stress_seeds)%/%2L)
  confirmation_seeds<-setdiff(stress_seeds,calibration_seeds)
  benchmark_map<-t3_stress_crossfit_benchmark_map(z,'independent_unit')
  z<-z[z$independent_unit%in%confirmation_seeds,,drop=FALSE]
} else if(stage!='realworld') {
  calibration_seeds<-integer();confirmation_seeds<-sort(unique(as.integer(z$independent_unit)))
}

ans<-t3_pairwise_tournament(z,stage,'independent_unit',groups,benchmark_map,
  alpha=ga_config$fdr_primary)
scenario_grid<-read.csv('config/T2_V3_B3_prospective_321_grid.csv',stringsAsFactors=FALSE)
add_scenario_labels<-function(x) {
  ix<-match(as.character(x$scenario_id),as.character(scenario_grid$scenario_id))
  x$scenario_mechanism<-scenario_grid$mechanism[ix]
  x$scenario_contamination<-scenario_grid$contamination[ix]
  x$scenario_mad_scale<-scenario_grid$mad_scale[ix]
  x$scenario_band<-scenario_grid$band[ix]
  x$scenario_is_empirical_proxy<-stage=='realworld'
  x
}
ans$metrics<-add_scenario_labels(ans$metrics)
ans$taxonomy<-add_scenario_labels(ans$taxonomy)
if(stage=='realworld') {
  child_ans$metrics<-add_scenario_labels(child_ans$metrics)
  child_ans$taxonomy<-add_scenario_labels(child_ans$taxonomy)
}
out<-if(stage=='realworld')write_dir else
  file.path('artifacts','v3_confirmatory_pairwise',paste0(stage,'_v3'))
if(dir.exists(out))stop('Refusing to overwrite immutable tournament output')
dir.create(out,recursive=TRUE,showWarnings=FALSE)
write.csv(z,file.path(out,'independent_unit_scores.csv'),row.names=FALSE)
write.csv(ans$metrics,file.path(out,'own_benchmark_and_mean_inference.csv'),row.names=FALSE)
write.csv(ans$taxonomy,file.path(out,'four_tier_winner_matrix.csv'),row.names=FALSE)
if(stage=='realworld') {
  write.csv(pooled_child,file.path(out,'child_dataset_depth_scores_descriptive.csv'),row.names=FALSE)
  write.csv(child_seed_scores,file.path(out,'child_dataset_depth_seed_scores.csv'),row.names=FALSE)
  write.csv(child_ans$metrics,file.path(out,'within_dataset_depth_inference.csv'),row.names=FALSE)
  write.csv(child_ans$taxonomy,file.path(out,'within_dataset_depth_taxonomy.csv'),row.names=FALSE)
  write.csv(child_ans$manifest,file.path(out,'within_dataset_depth_panel_manifest.csv'),row.names=FALSE)
}
write.csv(ans$manifest,file.path(out,'panel_manifest.csv'),row.names=FALSE)
write.csv(benchmark_map,file.path(out,'frozen_own_benchmark_map.csv'),row.names=FALSE)
write.csv(data.frame(path=files,sha256=vapply(files,t2_sha256,character(1))),
  file.path(out,'input_manifest.csv'),row.names=FALSE)
role_lines<-if(stage=='stress')c(
  paste0('stress_baseline_calibration_seeds=',paste(calibration_seeds,collapse=';')),
  paste0('stress_confirmatory_seeds=',paste(confirmation_seeds,collapse=';'))
) else character()
writeLines(c(paste0('code_revision=',Sys.getenv('GITHUB_SHA','unverified-local')),
             paste0('workflow_run_id=',Sys.getenv('GITHUB_RUN_ID','local')),
             role_lines),file.path(out,'run_provenance.txt'))
cat('T3_PAIRWISE_REDUCED_TOURNAMENT_PASS',stage,'inputs',length(files),
  'hypotheses',nrow(ans$metrics),'independent_units',
  length(unique(z$independent_unit)),'\n')
