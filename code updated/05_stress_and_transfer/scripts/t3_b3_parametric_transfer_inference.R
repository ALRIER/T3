#!/usr/bin/env Rscript
# Seed-level paired inference, one global BH family across the complete transfer panel.
source('R/00_shared/load_all.R'); t2_load('.')
source('R/00_shared/pipeline.R'); source('R/05_audits/stage_inference.R')
root <- 'artifacts/t3_b3_parametric_transfer'
files <- list.files(root,'^scores[.]csv$',recursive=TRUE,full.names=TRUE)
if (!length(files)) stop('No parametric-transfer score shards found')
x <- do.call(rbind,lapply(files,read.csv,stringsAsFactors=FALSE,check.names=FALSE))
need <- c('family','source_family','evaluation_family','transfer_scope','parameter_row',
  'parametric_seed','sample_n','scenario_id','training_seed','model','mse','q95')
if (!all(need %in% names(x)) || any(!is.finite(x$mse)) || any(!is.finite(x$q95)))
  stop('Incomplete/nonfinite transfer scores')
key <- c('family','parameter_row','sample_n','scenario_id','parametric_seed','training_seed','model')
if (anyDuplicated(x[key])) stop('Duplicate frozen-transfer score keys')
# Discovery seeds are repeated frozen fits; average them within each independent
# transfer seed. The unit of inference remains the separately reserved seed 40:49.
eval_keys <- c('family','source_family','evaluation_family','transfer_scope',
  'parameter_row','sample_n','scenario_id','parametric_seed','model')
z <- aggregate(x[,c('mse','q95')],x[,eval_keys],mean)
group_keys <- c('family','parameter_row','sample_n','scenario_id',
  'source_family','evaluation_family','transfer_scope')
groups <- interaction(z[group_keys],drop=TRUE,lex.order=TRUE)
out <- list(); k <- 0L
for (g in levels(groups)) {
  q <- z[groups==g,,drop=FALSE]
  ref <- q[q$model=='mean',,drop=FALSE]
  if (nrow(ref)!=length(unique(q$parametric_seed)) || anyDuplicated(ref$parametric_seed))
    stop('Missing/duplicate mean benchmark seed for transfer stratum')
  for (model in setdiff(unique(q$model),'mean')) {
    cand <- q[q$model==model,,drop=FALSE]
    pair <- merge(cand,ref,by=c('family','parameter_row','sample_n','scenario_id',
      'source_family','evaluation_family','transfer_scope','parametric_seed'),
      suffixes=c('_candidate','_reference'))
    if (nrow(pair)!=10L || !setequal(pair$parametric_seed,40:49))
      stop('Complete independent parametric seed panel 40:49 is required')
    for (metric in c('mse','q95')) {
      delta <- pair[[paste0(metric,'_candidate')]]-pair[[paste0(metric,'_reference')]]
      if (all(delta==delta[1])) { pv <- if (delta[1]<0) 0 else 1; ci <- rep(delta[1],2) }
      else { tt <- t.test(delta,alternative='less'); pv <- tt$p.value; ci <- tt$conf.int }
      gain <- 100*(pair[[paste0(metric,'_reference')]]-pair[[paste0(metric,'_candidate')]]) /
        pmax(pair[[paste0(metric,'_reference')]],.Machine$double.eps)
      if (all(gain==gain[1])) gain_ci <- rep(gain[1],2) else gain_ci <- t.test(gain)$conf.int
      k <- k+1L; row <- data.frame(stage='parametric_transfer',group='global_transfer_panel',
        model=model,metric=metric,benchmark='mean',independent_seeds=nrow(pair),
        difference=mean(delta),lower=ci[1],upper=ci[2],p_value=pv,
        gain_pct=mean(gain),gain_pct_lower=gain_ci[1],gain_pct_upper=gain_ci[2],
        negative_control=FALSE,inference_unit='parametric_transfer_seed',stringsAsFactors=FALSE)
      for (nm in group_keys) row[[nm]] <- pair[[nm]][1]
      out[[k]] <- row
    }
  }
}
inf <- do.call(rbind,out)
inf$q_value_global <- p.adjust(inf$p_value,'BH')
inf$passes_global_gate <- inf$q_value_global<=.05
inf$practical_gain_pct <- ga_config$practical_gain_pct
inf$practical_gain <- inf$gain_pct>=ga_config$practical_gain_pct
ids <- c('stage','group',group_keys,'model')
wide <- reshape(inf[,c(ids,'metric','difference','upper','q_value_global','gain_pct',
  'gain_pct_lower','gain_pct_upper','practical_gain'),drop=FALSE],idvar=ids,
  timevar='metric',direction='wide')
wide$winner_mse_only_bh_fdr <- wide$difference.mse<0 & wide$upper.mse<0 & wide$q_value_global.mse<=.05
wide$winner_q95_only_bh_fdr <- wide$difference.q95<0 & wide$upper.q95<0 & wide$q_value_global.q95<=.05
wide$winner_joint_mse_q95_bh_fdr <- wide$winner_mse_only_bh_fdr & wide$winner_q95_only_bh_fdr
wide$winner_joint_practical <- wide$winner_joint_mse_q95_bh_fdr &
  wide$gain_pct.mse>=ga_config$practical_gain_pct & wide$gain_pct.q95>=ga_config$practical_gain_pct
dest <- file.path(root,'aggregate')
if (dir.exists(dest)) stop('Refusing to overwrite immutable transfer aggregate')
dir.create(dest,recursive=TRUE)
write.csv(inf,file.path(dest,'global_inference.csv'),row.names=FALSE)
write.csv(wide,file.path(dest,'winner_taxonomy.csv'),row.names=FALSE)
write.csv(data.frame(score_file=files,sha256=vapply(files,t2_sha256,character(1))),
  file.path(dest,'input_manifest.csv'),row.names=FALSE)
writeLines(c('status=COMPLETE','bh_scope=one_global_panel_over_all_models_metrics_parameter_rows_scenarios_and_sample_sizes',
  'independent_unit=seed_40_to_49','weights=frozen_discovery_only','benchmark=sample_mean'),
  file.path(dest,'inference.status'))
cat('T3_B3_PARAMETRIC_TRANSFER_INFERENCE_PASS hypotheses=',nrow(inf),'\n',sep='')
