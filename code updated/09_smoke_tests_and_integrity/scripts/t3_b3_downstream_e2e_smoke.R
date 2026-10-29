#!/usr/bin/env Rscript
# Bounded end-to-end smoke from existing immutable MC inputs through Discovery,
# frozen held-out/stress scoring, seed-level inference and winner taxonomy.
# It never generates or overwrites Monte Carlo inputs or production W files.
archive<-Sys.getenv('T3_MC_ARCHIVE','')
if(!nzchar(archive)||!dir.exists(archive))stop('Set T3_MC_ARCHIVE to the completed MC artifact archive')
source('R/00_shared/load_all.R');t2_load('.')
source('R/00_shared/pipeline.R');source('R/00_shared/v3_scientific_adapter.R')
source('R/05_audits/stage_inference.R');source('R/00_shared/t3_b3_partitions.R')
family<-'normal';n<-200L
resolve<-function(role,seed,block_family=family){
  candidates<-list.files(archive,'^canonical[.]rds$',recursive=TRUE,full.names=TRUE)
  expected<-sprintf('b3-mc-%s-%s-s%d-n%d-run[0-9]+/seed%02d/n%d_r500/canonical[.]rds',
                    role,block_family,seed,n,seed,n)
  candidates<-candidates[grepl(expected,candidates)]
  if(length(candidates)!=1L)stop('Expected one archived MC source for ',role,' seed ',seed)
  candidates
}
read_block<-function(role,seed,block_family=family){
  path<-resolve(role,seed,block_family);z<-readRDS(path)
  if(!identical(z$protocol,t2_v3_protocol())||!identical(z$role,role)||
     !identical(z$family,block_family)||as.integer(z$seed_index)!=seed||
     as.integer(z$n)!=n||as.integer(z$replications)!=500L||length(z$scenarios)!=321L)
    stop('Archived Monte Carlo provenance failed: ',path)
  list(path=path,block=z)
}
support<-t3_b3_partition_ids('discovery_support')
smoke_hpo<-list(
 ga=list(population=8L,generations=2L,mutation_rate=.15,crossover_probability=.9,regularization_lambda=.001),
 nsga2=list(population=8L,generations=2L,mutation_rate=.15,crossover_probability=.9,regularization_lambda=.001),
 de=list(population=8L,generations=2L,mutation_rate=.15,crossover_probability=.9,regularization_lambda=.001,F=.6,CR=.8),
 dirichlet=list(population=8L,generations=2L,mutation_rate=.15,crossover_probability=.9,regularization_lambda=.001,alpha=1))
fit_source<-function(source_family){
 training_source<-read_block('discovery',0L,source_family)$block
 meta<-training_source$grid
 selected<-unlist(lapply(c('clean','low','intermediate','high'),function(b){
  ids<-meta$scenario_id[meta$band==b & meta$scenario_id%in%support]
  if(!length(ids))stop('Missing Discovery contamination band: ',b)
  ids[1L]
 }),use.names=FALSE)
 selected<-unique(as.integer(selected))
 training<-lapply(selected,function(id){
  s<-training_source$scenarios[[id+1L]];m<-t3_b3_scenario_metadata(id)
  for(key in c('contamination','mad_scale','mechanism','band'))s[[key]]<-m[[key]][1L]
  t2_v3_prepare_scenario(s)
 })
 training_data<-list(role='discovery',family=source_family,seed_index=0L,n=n,
   replications=500L,scenarios=training,canonical_id='existing_mc_smoke_only')
 fit<-t2_run_discovery(training_data,'smoke',paste0('t3_downstream_e2e_smoke_',source_family),'all',smoke_hpo)
 if(length(fit$engines)!=4L||length(fit$non_evolutionary_controls)!=2L||length(fit$models)!=30L)
   stop('Discovery did not produce four engines and two frozen controls')
 models<-c(lapply(ESTIMATOR_NAMES,function(id)new_frozen_model(id,component=id)),
   Filter(function(m)!is.null(m$weights),fit$models),
   lapply(names(fit$non_evolutionary_controls),function(id){
    w<-as.numeric(fit$non_evolutionary_controls[[id]]$weights)
    new_frozen_model(id,weights=w,family=id)
   }))
 if(length(models)!=32L||anyDuplicated(vapply(models,function(m)m$id,character(1))))
   stop('Frozen evaluation model panel is not 32 unique models')
 list(models=models,training_scenarios=length(training))
}
model_panels<-setNames(lapply(c('normal','lognormal'),fit_source),c('normal','lognormal'))
score_role<-function(role,seeds,ids){
 rows<-list();k<-0L
 for(seed in seeds){
  ev<-read_block(role,seed)$block
  for(source_family in names(model_panels))for(id in ids){
   sc<-t2_v3_prepare_scenario(ev$scenarios[[id+1L]])
   q<-score_model_set(sc$T,model_panels[[source_family]]$models,sc$target)
   q$scenario_id<-id;q$training_seed<-0L;q[[paste0(role,'_seed')]]<-seed
   q$family<-family;q$source_family<-source_family;q$evaluation_family<-family
   q$sample_n<-n;q$transfer_scope<-t3_b3_transfer_scope(source_family,family,role,
      ev$grid$mechanism[match(id,ev$grid$scenario_id)])
   k<-k+1L;rows[[k]]<-q
  }
 }
 scores<-do.call(rbind,rows)
 inf<-t3_confirmatory_seed_summary(scores,role)
 tax<-t3_winner_taxonomy(inf)
 if(!setequal(unique(inf$model),c('ga','nsga2','de','dirichlet','convex_mse','local_deterministic'))||
    !setequal(unique(inf$source_family),c('normal','lognormal'))||
    !setequal(unique(inf$metric),c('mse','q95'))||any(!is.finite(inf$q_value_global))||
    !all(c('winner_mse','winner_q95','winner_joint_mse_q95',
      'winner_mse_only','winner_q95_only','winner_joint_mse_q95_bh_fdr',
      'winner_mse_only_bh_fdr','winner_q95_only_bh_fdr','winner_pareto',
      'winner_pareto_bh_fdr')%in%names(tax)))
   stop('Stage-wide confirmatory inference/taxonomy smoke failed')
 list(scores=scores,inference=inf,taxonomy=tax)
}
heldout_ids<-head(t3_b3_partition_ids('discovery_support'),4L)
stress_ids<-head(t3_b3_partition_ids('stress_exclusive'),4L)
heldout<-score_role('heldout',10:12,heldout_ids)
stress<-score_role('stress',20:22,stress_ids)
out<-Sys.getenv('T3_SMOKE_OUT',tempdir());dir.create(out,recursive=TRUE,showWarnings=FALSE)
for(stage in c('heldout','stress')){
 z<-get(stage)
 write.csv(z$inference,file.path(out,paste0(stage,'_inference.csv')),row.names=FALSE)
 write.csv(z$taxonomy,file.path(out,paste0(stage,'_taxonomy.csv')),row.names=FALSE)
}
write.csv(data.frame(status='PASS',mc_generation='not_run',archive=normalizePath(archive),
 evaluation_family=family,source_families=paste(names(model_panels),collapse=';'),training_seed=0L,
 training_scenarios=paste(vapply(model_panels,`[[`,integer(1),'training_scenarios'),collapse=';'),
 heldout_seeds='10;11;12',stress_seeds='20;21;22',models_per_source=32L,
 smoke_hpo='bounded_fixture_not_production_selection',
 interpretation='execution and artifact contract only; no scientific conclusion'),
 file.path(out,'e2e_manifest.csv'),row.names=FALSE)
cat('T3_B3_DOWNSTREAM_E2E_SMOKE_PASS outputs=',out,'\n')
