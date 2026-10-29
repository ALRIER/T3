#!/usr/bin/env Rscript
# Parent-cluster bootstrap and one global BH panel for every reported layer.
a <- commandArgs(TRUE)
root <- if(length(a)) a[[1L]] else 'artifacts/realworld_T3_B3'
source('R/00_shared/load_all.R'); t2_load('.')
source('R/00_shared/pipeline.R')
files <- list.files(root,'^scores_T2_V3_B3[.]csv$',recursive=TRUE,full.names=TRUE)
if(!length(files)) files <- list.files(root,'^scores[.]csv$',recursive=TRUE,full.names=TRUE)
if(!length(files)) stop('No real-world T3 score shards')
parts <- lapply(files,read.csv,stringsAsFactors=FALSE,check.names=FALSE)
x <- do.call(rbind,parts)
required <- c('dataset_id','parent_dataset_id','family','transfer_scope','model','mse','q95')
if(!all(required%in%names(x))||any(!is.finite(x$mse))||any(!is.finite(x$q95)))
 stop('Incomplete or invalid parent-child score schema')
if(anyNA(x$parent_dataset_id)||any(!nzchar(x$parent_dataset_id)))stop('Missing parent IDs')
# The benchmark is fixed to the sample mean. Children, depths, training seeds,
# and sample sizes are paired first and then collapsed inside their parent.
pair_keys <- c(intersect(c('dataset_id','family','transfer_scope','matched_scenario_id',
  'sample_n','n','depth','training_seed','realworld_seed'),names(x)))
if(!'dataset_id'%in%pair_keys)stop('Child dataset identifier absent')
means <- x[x$model=='mean',c(pair_keys,'mse','q95'),drop=FALSE]
if(!nrow(means)||anyDuplicated(means[pair_keys]))stop('Mean-reference rows missing or duplicated')
means$model <- NULL; names(means)[(length(pair_keys)+1L):(length(pair_keys)+2L)]<-c('mean_mse','mean_q95')
candidates <- x[x$model!='mean',,drop=FALSE]
paired <- merge(candidates,means,by=pair_keys,all=FALSE,suffixes=c('_candidate','_mean'))
if(!nrow(paired))stop('No paired candidate-versus-mean outcomes')
paired$mse_gain <- paired$mean_mse-paired$mse
paired$q95_gain <- paired$mean_q95-paired$q95
paired$mse_gain_pct <- 100*paired$mse_gain/pmax(paired$mean_mse,.Machine$double.eps)
paired$q95_gain_pct <- 100*paired$q95_gain/pmax(paired$mean_q95,.Machine$double.eps)
parent_keys <- intersect(c('parent_dataset_id','family','transfer_scope','sample_n','model'),names(paired))
if(!all(c('parent_dataset_id','family','transfer_scope','sample_n','model')%in%parent_keys))
 stop('Parent-level inference needs family, scope, sample size, model, and parent ID')
# Average every child variable, depth, evaluation seed, and repeated frozen W
# within the independent parent first. The matched 321-cell remains a
# descriptive diagnostic; it is not a confirmatory stratum with sparse n.
parent <- aggregate(paired[,c('mse_gain','q95_gain','mse_gain_pct','q95_gain_pct')],
                    paired[,parent_keys,drop=FALSE],mean)
if(anyDuplicated(parent[parent_keys]))stop('Parent aggregation did not yield unique units')
panel_keys <- c('family','transfer_scope','sample_n','model')
panels <- split(parent,interaction(parent[panel_keys],drop=TRUE,lex.order=TRUE))
res <- list()
for(g in panels) {
 if(nrow(g)<5L) next
 for(metric in c('mse','q95')) {
  v <- g[[paste0(metric,'_gain')]]; n <- length(v)
  set.seed(t2_seed(paste('T3_RW_PARENT_BOOT',g$family[1],g$transfer_scope[1],
    g$sample_n[1],g$model[1],metric),37191L))
  boot <- replicate(5000L,mean(sample(v,n,replace=TRUE)))
  ci <- unname(quantile(boot,c(.025,.975),type=8))
  pct <- g[[paste0(metric,'_gain_pct')]]
  pct_boot <- replicate(5000L,mean(sample(pct,n,replace=TRUE)))
  pct_ci <- unname(quantile(pct_boot,c(.025,.975),type=8))
  if(sd(v)==0) p <- if(mean(v)>0)0 else 1 else p <- t.test(v,mu=0,alternative='greater')$p.value
  res[[length(res)+1L]] <- data.frame(stage='realworld',family=g$family[1],
   transfer_scope=g$transfer_scope[1],sample_n=g$sample_n[1],
   model=g$model[1],metric=metric,
   benchmark='mean',independent_parent_datasets=n,
   gain=mean(v),ci_lower=ci[1],ci_upper=ci[2],relative_gain_pct=mean(pct),
   relative_gain_ci_lower=pct_ci[1],relative_gain_ci_upper=pct_ci[2],p_value=p,
   ci_method='parent_cluster_percentile_bootstrap',bootstrap_B=5000L,
   evidence_unit='parent_dataset_id',stringsAsFactors=FALSE)
 }
}
if(!length(res))stop('No family/scope/sample-size panel has five independent parent datasets')
inf <- do.call(rbind,res)
inf$q_value_global <- p.adjust(inf$p_value,'BH')
inf$winner_supported <- inf$gain>0 & inf$ci_lower>0 & inf$q_value_global<=.05
inf$practical_gain_threshold_pct <- ga_config$practical_gain_pct
parent$practical_mse <- parent$mse_gain_pct>=ga_config$practical_gain_pct
parent$practical_q95 <- parent$q95_gain_pct>=ga_config$practical_gain_pct
scenario_parent_keys <- intersect(c('parent_dataset_id','family','transfer_scope','sample_n',
  'matched_scenario_id','model'),names(paired))
scenario_parent <- aggregate(paired[,c('mse_gain','q95_gain','mse_gain_pct','q95_gain_pct')],
  paired[scenario_parent_keys],mean)
scenario_keys <- setdiff(scenario_parent_keys,'parent_dataset_id')
scenario_diag <- aggregate(scenario_parent[,c('mse_gain','q95_gain','mse_gain_pct','q95_gain_pct')],
  scenario_parent[scenario_keys],mean)
scenario_n <- aggregate(parent_dataset_id~family+transfer_scope+sample_n+matched_scenario_id+model,
  scenario_parent,function(z)length(unique(z)))
names(scenario_n)[names(scenario_n)=='parent_dataset_id'] <- 'descriptive_parent_count'
scenario_diag <- merge(scenario_diag,scenario_n,by=scenario_keys)
scenario_diag$inference_status <- 'descriptive_sparse_or_overlapping_matched_scenario; no_p_or_BH'
wide <- reshape(inf[,c('family','transfer_scope','sample_n','model','metric','gain','ci_lower','ci_upper',
  'relative_gain_pct','relative_gain_ci_lower','relative_gain_ci_upper','q_value_global','winner_supported'),drop=FALSE],
  idvar=c('family','transfer_scope','sample_n','model'),
  timevar='metric',direction='wide')
if(!all(c('winner_supported.mse','winner_supported.q95')%in%names(wide)))
 stop('Incomplete joint MSE/Q95 taxonomy panel')
wide$winner_joint_mse_q95_bh_fdr <- wide$winner_supported.mse & wide$winner_supported.q95
wide$winner_mse_only_bh_fdr <- wide$winner_supported.mse & !wide$winner_supported.q95
wide$winner_q95_only_bh_fdr <- wide$winner_supported.q95 & !wide$winner_supported.mse
wide$winner_pareto_bh_fdr <- wide$winner_mse_only_bh_fdr|wide$winner_q95_only_bh_fdr
wide$winner_joint_mse_q95_descriptive <- wide$gain.mse>0 & wide$gain.q95>0
wide$winner_mse_only_descriptive <- wide$gain.mse>0 & wide$gain.q95<=0
wide$winner_q95_only_descriptive <- wide$gain.q95>0 & wide$gain.mse<=0
wide$winner_pareto_descriptive <- wide$winner_mse_only_descriptive|wide$winner_q95_only_descriptive
wide$winner_joint_practical <- wide$winner_joint_mse_q95_bh_fdr &
  wide$relative_gain_pct.mse>=ga_config$practical_gain_pct &
  wide$relative_gain_pct.q95>=ga_config$practical_gain_pct
wide$winner_joint_assured_practical <- wide$winner_joint_mse_q95_bh_fdr &
  wide$relative_gain_ci_lower.mse>=ga_config$practical_gain_pct &
  wide$relative_gain_ci_lower.q95>=ga_config$practical_gain_pct
dest <- file.path(root,'parent_inference_T3_B3')
if(dir.exists(dest))stop('Refusing to overwrite immutable parent inference')
dir.create(dest,recursive=TRUE)
write.csv(parent,file.path(dest,'parent_effects.csv'),row.names=FALSE)
write.csv(inf,file.path(dest,'global_parent_inference.csv'),row.names=FALSE)
write.csv(wide,file.path(dest,'winner_taxonomy_by_family_scope.csv'),row.names=FALSE)
write.csv(parent,file.path(dest,'parent_relative_gain_audit.csv'),row.names=FALSE)
write.csv(scenario_diag,file.path(dest,'scenario_diagnostics_descriptive.csv'),row.names=FALSE)
write.csv(data.frame(path=files,sha256=vapply(files,t2_sha256,character(1))),
 file.path(dest,'input_manifest.csv'),row.names=FALSE)
writeLines(c('benchmark=sample_mean','independent_unit=parent_dataset_id',
 'bootstrap=resample independent parents; 5000 replicates; percentile 95% CI',
 'BH=one global panel over family x transfer_scope x sample_n x model x metric hypotheses',
 'parent inference averages child variables, depth slices, evaluation seeds, and training seeds within each parent',
 'matched scenario cell is descriptive only; sparse scenario cells receive no p-value or BH claim',
 'scope=within_regime; within_family_neighborhood; cross_family_transfer',
 'realworld_target=evaluated_child_depth_mean_proxy_not_unknown_population_truth'),
 file.path(dest,'scientific_scope.txt'))
cat('T3_B3_REALWORLD_PARENT_INFERENCE_PASS',nrow(inf),'hypotheses; parent effects',nrow(parent),
 'scenario diagnostics',nrow(scenario_diag),'\n')
