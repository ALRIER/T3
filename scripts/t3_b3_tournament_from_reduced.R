#!/usr/bin/env Rscript
# Global Real-world tournament from immutable reduced score shards.
# Process one Discovery source family at a time to bound peak RAM, then apply
# BH once across the complete parent-level and child-conditional panels.
a<-commandArgs(trailingOnly=TRUE)
if(!(length(a)%in%c(3L,4L)))stop('Usage: STAGE REDUCED_ARTIFACT_ROOT OWN_BENCHMARK_MAP.csv [EMPIRICAL_FAMILY_MAP.csv]')
stage<-a[[1L]];root<-a[[2L]];map_path<-a[[3L]]
if(stage!='realworld')stop('This streaming entry point currently supports realworld only')
source('R/00_shared/load_all.R');t2_load('.')
source('R/00_shared/pipeline.R');source('R/05_audits/benchmark_tournament.R')
if(!file.exists(map_path))stop('Frozen own-benchmark map artifact is required')
benchmark_map<-read.csv(map_path,stringsAsFactors=FALSE,check.names=FALSE)
family_map_path<-a[[4L]]
family_map<-read.csv(family_map_path,stringsAsFactors=FALSE,check.names=FALSE)
if(!all(c('parent_dataset_id','dataset_id','empirical_family_assignment',
          'family_assignment_confidence','family_assignment_status')%in%names(family_map))||
   anyDuplicated(family_map$dataset_id)||any(!family_map$empirical_family_assignment%in%t2_families()))
 stop('Real-world family proximity map is incomplete or invalid')
files<-list.files(root,'[.]csv[.]gz$',recursive=TRUE,full.names=TRUE)
if(length(files)!=856L)stop('Expected 856 immutable reduced inputs; found ',length(files))
families<-t2_families()
required<-c('parent_dataset_id','dataset_id','family','source_family','evaluation_family',
 'evaluation_profile','transfer_scope','sample_n','scenario_id','depth','model','mse','q95',
 'n_score_rows','realworld_seed')
child_metric_parts<-list();child_tax_parts<-list();parent_metric_parts<-list();parent_tax_parts<-list()
cm<-ct<-pm<-pt<-0L

process_family<-function(source_family) {
  message('REALWORLD_STREAM_SOURCE_BEGIN ',source_family)
  chunks<-vector('list',0L)
  for(path in files) {
    d<-read.csv(gzfile(path),stringsAsFactors=FALSE,check.names=FALSE)
    if(!all(required%in%names(d)))stop('Reduced Real-world schema incomplete: ',path)
    sf<-unique(as.character(d$source_family))
    if(length(sf)!=1L)stop('A reduced shard mixes source families: ',path)
    if(sf==source_family) {
      keep<-unique(c(required,'empirical_family_relation','family_assignment_confidence',
        'family_assignment_status',intersect(c('domain','source_sector'),names(d))))
      chunks[[length(chunks)+1L]]<-d[keep]
    }
    rm(d);if(length(chunks)%%24L==0L)invisible(gc(FALSE))
  }
  if(!length(chunks))stop('No reduced inputs for source family ',source_family)
  z<-do.call(rbind,chunks);rm(chunks);rownames(z)<-NULL
  if(any(!is.finite(z$mse))||any(!is.finite(z$q95))||any(!is.finite(z$n_score_rows))||any(z$n_score_rows<=0))
    stop('Nonfinite score or invalid row weights for ',source_family)
  if(any(z$source_family!=source_family))stop('Source-family partition contamination')
  # Match the frozen dataset classification and preserve the existing weighted
  # training-seed reconstruction and equal-weight child/parent aggregation.
  ix<-match(as.character(z$dataset_id),as.character(family_map$dataset_id))
  if(anyNA(ix)||any(as.character(z$parent_dataset_id)!=as.character(family_map$parent_dataset_id[ix])))
    stop('Reduced child/parent identity is absent from the frozen family map')
  for(nm in setdiff(names(family_map),c('dataset_id','parent_dataset_id')))
    if(nm%in%names(z)&&any(as.character(z[[nm]])!=as.character(family_map[[nm]][ix])))
      stop('Reduced classification differs from frozen map: ',nm)
  child_keys<-c('parent_dataset_id','dataset_id','family','source_family','evaluation_family',
    'evaluation_profile','empirical_family_relation','family_assignment_status',
    intersect('family_assignment_confidence',names(z)),
    'transfer_scope','sample_n','scenario_id','depth',
    intersect(c('domain','source_sector'),names(z)),'realworld_seed','model')
  weighted<-z[child_keys]
  weighted$weighted_mse<-z$mse*z$n_score_rows
  weighted$weighted_q95<-z$q95*z$n_score_rows
  weighted$n_score_rows<-z$n_score_rows
  sums<-aggregate(weighted[c('weighted_mse','weighted_q95','n_score_rows')],weighted[child_keys],sum)
  sums$mse<-sums$weighted_mse/sums$n_score_rows
  sums$q95<-sums$weighted_q95/sums$n_score_rows
  child_seed_scores<-sums[c(child_keys,'mse','q95','n_score_rows')]
  child_groups<-c('parent_dataset_id','dataset_id','family','source_family','evaluation_family',
    'evaluation_profile','empirical_family_relation','family_assignment_status',
    'transfer_scope','sample_n','scenario_id','depth')
  child_ans<-t3_pairwise_tournament(child_seed_scores,'realworld','realworld_seed',
    child_groups,benchmark_map,alpha=ga_config$fdr_primary)
  pooled_child<-aggregate(child_seed_scores[c('mse','q95')],
    child_seed_scores[setdiff(child_keys,'realworld_seed')],mean)
  parent_keys<-c('parent_dataset_id','family','source_family','evaluation_family',
    'evaluation_profile','empirical_family_relation','family_assignment_status',
    'transfer_scope','sample_n','scenario_id','depth','model')
  parent_scores<-aggregate(pooled_child[c('mse','q95')],pooled_child[parent_keys],mean)
  if('family_assignment_confidence'%in%names(pooled_child)) {
    confidence_keys<-setdiff(parent_keys,'model')
    confidence<-aggregate(pooled_child['family_assignment_confidence'],pooled_child[confidence_keys],mean)
    parent_scores<-merge(parent_scores,confidence,by=confidence_keys,sort=FALSE)
  }
  parent_scores$independent_unit<-parent_scores$parent_dataset_id
  parent_groups<-c('family','source_family','evaluation_family','transfer_scope',
    'evaluation_profile','empirical_family_relation','family_assignment_status',
    'sample_n','scenario_id','depth')
  parent_ans<-t3_pairwise_tournament(parent_scores,'realworld','independent_unit',
    parent_groups,benchmark_map,alpha=ga_config$fdr_primary)
  if('family_assignment_confidence'%in%names(parent_scores)) {
    confidence<-aggregate(parent_scores['family_assignment_confidence'],parent_scores[parent_groups],mean)
    names(confidence)[names(confidence)=='family_assignment_confidence']<-'mean_family_assignment_confidence'
    parent_ans$metrics<-merge(parent_ans$metrics,confidence,by=parent_groups,all.x=TRUE,sort=FALSE)
    parent_ans$taxonomy<-merge(parent_ans$taxonomy,confidence,by=parent_groups,all.x=TRUE,sort=FALSE)
  }
  message('REALWORLD_STREAM_SOURCE_PASS ',source_family,
    ' child_units=',length(unique(child_seed_scores$dataset_id)),
    ' parent_units=',length(unique(parent_scores$parent_dataset_id)),
    ' rows=',nrow(z))
  list(child=child_ans,parent=parent_ans,parent_scores=parent_scores,
       child_seed_scores=child_seed_scores,pooled_child=pooled_child)
}

for(fam in families) {
  res<-process_family(fam)
  cm<-cm+1L;child_metric_parts[[cm]]<-res$child$metrics
  ct<-ct+1L;child_tax_parts[[ct]]<-res$child$taxonomy
  pm<-pm+1L;parent_metric_parts[[pm]]<-res$parent$metrics
  pt<-pt+1L;parent_tax_parts[[pt]]<-res$parent$taxonomy
  if(fam==families[[1L]]) {
    pooled_child_out<-res$pooled_child
    child_seed_out<-res$child_seed_scores
    parent_scores_out<-res$parent_scores
  } else {
    pooled_child_out<-rbind(pooled_child_out,res$pooled_child)
    child_seed_out<-rbind(child_seed_out,res$child_seed_scores)
    parent_scores_out<-rbind(parent_scores_out,res$parent_scores)
  }
  rm(res);invisible(gc())
}

# Recompute BH across the full predeclared panel, not separately by source family.
finalize_panel<-function(metric_parts,tax_parts,unit_col,panel_id) {
  inf<-do.call(rbind,metric_parts);rownames(inf)<-NULL
  valid<-is.finite(inf$p_value)
  inf$q_value_global<-NA_real_;inf$q_value_global[valid]<-p.adjust(inf$p_value[valid],method='BH')
  inf$passes_bh<-is.finite(inf$q_value_global)&inf$q_value_global<=ga_config$fdr_primary
  inf$inference_scope<-if(unit_col=='realworld_seed')'within_dataset_conditional_resampling' else 'between_parent_dataset_generalization'
  inf$bh_panel_id<-panel_id
  ids<-c('stage','candidate_model','candidate_engine','benchmark','benchmark_role',
    'family','source_family','evaluation_family','transfer_scope','evaluation_profile',
    'empirical_family_relation','family_assignment_status','sample_n','scenario_id','depth',
    'independent_units','inference_unit')
  vals<-c('difference','ci_lower','ci_upper','gain_pct','gain_pct_lower','gain_pct_upper',
    'p_value','q_value_global','passes_bh')
  wide<-reshape(inf[,c(ids,'metric',vals),drop=FALSE],idvar=ids,timevar='metric',direction='wide')
  wm<-is.finite(wide$ci_upper.mse)&wide$ci_upper.mse<0
  wq<-is.finite(wide$ci_upper.q95)&wide$ci_upper.q95<0
  fm<-wm&wide$passes_bh.mse;fq<-wq&wide$passes_bh.q95
  wide$tier1_joint_mse_q95_bh_fdr<-fm&fq
  wide$tier2_joint_mse_q95_ci<-wm&wq
  wide$tier3_mse_only_bh_fdr<-fm&!wq&wide$difference.q95>=0
  wide$tier3_q95_only_bh_fdr<-fq&!wm&wide$difference.mse>=0
  wide$tier3_mse_only_ci<-wm&!wq&wide$difference.q95>=0
  wide$tier3_q95_only_ci<-wq&!wm&wide$difference.mse>=0
  wide$tier3_pareto_bh_fdr<-wide$tier3_mse_only_bh_fdr|wide$tier3_q95_only_bh_fdr
  wide$tier3_pareto_ci<-wide$tier3_mse_only_ci|wide$tier3_q95_only_ci
  wide$tier4_retained_candidate<-TRUE
  wide$highest_bh_supported_tier<-ifelse(wide$tier1_joint_mse_q95_bh_fdr,'tier1_joint_mse_q95_bh_fdr',
    ifelse(wide$tier3_pareto_bh_fdr,'tier3_pareto_single_metric_bh_fdr','tier4_retained_no_bh_win'))
  wide$highest_ci_supported_tier<-ifelse(wide$tier2_joint_mse_q95_ci,'tier2_joint_mse_q95_ci',
    ifelse(wide$tier3_pareto_ci,'tier3_pareto_single_metric_ci','tier4_retained_no_joint_ci_win'))
  wide$benchmarks_evaluated<-2L
  scope_key<-interaction(wide[c('stage','candidate_model','family','source_family',
    'evaluation_family','transfer_scope','evaluation_profile','empirical_family_relation',
    'family_assignment_status','sample_n','scenario_id','depth')],drop=TRUE,lex.order=TRUE)
  wide$beats_own_and_mean_tier1<-ave(as.integer(wide$tier1_joint_mse_q95_bh_fdr),scope_key,
    FUN=function(v)as.logical(all(v==1L)))
  wide$beats_own_and_mean_tier2<-ave(as.integer(wide$tier2_joint_mse_q95_ci),scope_key,
    FUN=function(v)as.logical(all(v==1L)))
  wide$practical_mse<-wide$gain_pct.mse>=ga_config$practical_gain_pct
  wide$practical_q95<-wide$gain_pct.q95>=ga_config$practical_gain_pct
  wide$inference_scope<-if(unit_col=='realworld_seed')'within_dataset_conditional_resampling' else 'between_parent_dataset_generalization'
  wide$bh_panel_id<-panel_id
  list(metrics=inf,taxonomy=wide,manifest=data.frame(stage='realworld',unit=unit_col,
    inference_scope=unique(inf$inference_scope),bh_panel_id=panel_id,
    own_benchmark_policy='Discovery-frozen best non-mean classical estimator per target scenario plus mean',
    primary_bh_family='complete panel across all source/evaluation families, scopes, profiles, depths, scenarios, candidates, benchmarks, and metrics',
    alpha=ga_config$fdr_primary,ci_method='paired_evaluation_unit_t_interval',
    code_revision=Sys.getenv('GITHUB_SHA','unverified-local'),workflow_run_id=Sys.getenv('GITHUB_RUN_ID','local'),
    stringsAsFactors=FALSE))
}
child_final<-finalize_panel(child_metric_parts,child_tax_parts,'realworld_seed','realworld_within_dataset_conditional_panel')
parent_final<-finalize_panel(parent_metric_parts,parent_tax_parts,'independent_unit','realworld_between_parent_generalization_panel')
scenario_grid<-read.csv('config/T2_V3_B3_prospective_321_grid.csv',stringsAsFactors=FALSE)
add_scenario_labels<-function(x) {
  ix<-match(as.character(x$scenario_id),as.character(scenario_grid$scenario_id))
  x$scenario_mechanism<-scenario_grid$mechanism[ix]
  x$scenario_contamination<-scenario_grid$contamination[ix]
  x$scenario_mad_scale<-scenario_grid$mad_scale[ix]
  x$scenario_band<-scenario_grid$band[ix]
  x$scenario_is_empirical_proxy<-TRUE
  x
}
child_final$metrics<-add_scenario_labels(child_final$metrics)
child_final$taxonomy<-add_scenario_labels(child_final$taxonomy)
parent_final$metrics<-add_scenario_labels(parent_final$metrics)
parent_final$taxonomy<-add_scenario_labels(parent_final$taxonomy)
out<-file.path('artifacts','v3_confirmatory_pairwise','realworld_v3')
if(dir.exists(out))stop('Refusing to overwrite immutable tournament output')
dir.create(out,recursive=TRUE,showWarnings=FALSE)
write.csv(parent_scores_out,file.path(out,'independent_unit_scores.csv'),row.names=FALSE)
write.csv(parent_final$metrics,file.path(out,'own_benchmark_and_mean_inference.csv'),row.names=FALSE)
write.csv(parent_final$taxonomy,file.path(out,'four_tier_winner_matrix.csv'),row.names=FALSE)
write.csv(pooled_child_out,file.path(out,'child_dataset_depth_scores_descriptive.csv'),row.names=FALSE)
write.csv(child_seed_out,file.path(out,'child_dataset_depth_seed_scores.csv'),row.names=FALSE)
write.csv(child_final$metrics,file.path(out,'within_dataset_depth_inference.csv'),row.names=FALSE)
write.csv(child_final$taxonomy,file.path(out,'within_dataset_depth_taxonomy.csv'),row.names=FALSE)
write.csv(child_final$manifest,file.path(out,'within_dataset_depth_panel_manifest.csv'),row.names=FALSE)
write.csv(parent_final$manifest,file.path(out,'panel_manifest.csv'),row.names=FALSE)
write.csv(benchmark_map,file.path(out,'frozen_own_benchmark_map.csv'),row.names=FALSE)
write.csv(family_map,file.path(out,'empirical_family_proximity.csv'),row.names=FALSE)
write.csv(data.frame(path=files,sha256=vapply(files,t2_sha256,character(1))),file.path(out,'input_manifest.csv'),row.names=FALSE)
writeLines(c(paste0('code_revision=',Sys.getenv('GITHUB_SHA','unverified-local')),
  paste0('workflow_run_id=',Sys.getenv('GITHUB_RUN_ID','local')),
  'streaming_partition=source_family; all families recombined before each global BH adjustment',
  'empirical_family_assignment=nearest standardized moment-manifold compatibility; bootstrap stability is reported',
  'empirical_family_assignment_is_true_generator_class=FALSE',
  'cross_family_transfer=source Discovery family versus outcome-blind empirical proximity class'),
  file.path(out,'run_provenance.txt'))
cat('T3_PAIRWISE_STREAMING_TOURNAMENT_PASS realworld inputs=',length(files),
  ' parent_hypotheses=',nrow(parent_final$metrics),' child_hypotheses=',nrow(child_final$metrics),
  ' parents=',length(unique(parent_scores_out$parent_dataset_id)),'\n',sep='')
