#!/usr/bin/env Rscript
source('R/00_shared/load_all.R');t2_load('.')
root <- 'artifacts/discovery_v3'
families <- c('normal','lognormal','weibull','invgauss','exgaussian','exwald')
rows <- list(); k<-0L
for(family in families)for(seed in 0:9) {
  p <- file.path(root,family,sprintf('seed%02d',seed),'discovery.rds')
  if(!file.exists(p)) stop('Missing discovery artifact ',p)
  fit <- readRDS(p)
  for(engine in names(fit$engines)) {
    z <- fit$engines[[engine]]
    O <- as.matrix(z$objectives)
    W <- as.matrix(z$weights)
    if(ncol(O)!=2L || nrow(O)!=ncol(W) || nrow(W)!=26L ||
       any(!is.finite(O)) || any(!is.finite(W)))stop('Invalid model matrix')
    ix_mse<-which.min(O[,1L]);ix_q95<-which.min(O[,2L])
    scale <- pmax(colMeans(abs(O)),1e-12)
    ix_balanced<-which.min(rowSums(sweep(O,2L,scale,'/')))
    for(goal in c('mse','q95','balanced')) {
      idx <- switch(goal,mse=ix_mse,q95=ix_q95,balanced=ix_balanced)
      k<-k+1L
      rows[[k]]<-data.frame(family=family,seed=seed,engine=engine,
                            goal=goal,mse=O[idx,1L],q95=O[idx,2L],
                            candidate_index=idx,
                            weights=paste(sprintf('%.9f',W[,idx]),collapse=';'))
    }
  }
  rm(fit); if(seed %% 3L == 0L) invisible(gc(verbose=FALSE))
}
out <- do.call(rbind,rows)
dir.create('artifacts/discovery_analysis',recursive=TRUE,showWarnings=FALSE)
write.csv(out,'artifacts/discovery_analysis/training_candidates.csv',row.names=FALSE)
agg <- aggregate(cbind(mse,q95)~family+engine+goal,out,mean)
write.csv(agg,'artifacts/discovery_analysis/training_summary.csv',row.names=FALSE)
# Fully defined descriptive two-metric candidate taxonomy, without
# treating Discovery training objectives as independent p-value evidence.
# Relative gains use the strongest *within-family* single-engine/goal
# performance reference as a descriptive training comparator.
baseline<-aggregate(cbind(mse,q95)~family,out,min)
names(baseline)[2:3]<-c('training_best_mse','training_best_q95')
out<-merge(out,baseline,by='family',sort=FALSE)
out$mse_gain<-out$training_best_mse-out$mse
out$q95_gain<-out$training_best_q95-out$q95
# Pareto membership is defensible when there is no independent baseline.
out$taxonomy<-ifelse(out$goal=='balanced','joint_mse_q95_candidate',
  ifelse(out$goal=='mse','mse_specialist_candidate','q95_specialist_candidate'))
out$taxonomy_scope<-'discovery_descriptive_candidate_role_only'
write.csv(out,'artifacts/discovery_analysis/candidate_taxonomy_T2_V3_B3.csv',row.names=FALSE)
cat('V3_DISCOVERY_WINNER_REPORT_PASS',nrow(out),'rows\n')

# Component-level weight contribution and seed stability. These are
# descriptive quantities, not causal importance or inferential significance.
component_rows <- list(); ix <- 0L
for(family in families) for(seed in 0:9) {
  fit <- readRDS(file.path(root,family,sprintf('seed%02d',seed),'discovery.rds'))
  for(engine in names(fit$engines)) {
    z <- fit$engines[[engine]]
    O <- as.matrix(z$objectives);W <- as.matrix(z$weights)
    scales <- pmax(colMeans(abs(O)),1e-12)
    chosen <- c(mse=which.min(O[,1L]),q95=which.min(O[,2L]),
                balanced=which.min(rowSums(sweep(O,2L,scales,'/'))))
    for(goal in names(chosen)){
      w <- W[,chosen[[goal]]]
      for(j in seq_along(w)) {
        ix <- ix + 1L
        component_rows[[ix]] <- data.frame(family=family,seed=seed,
          engine=engine,goal=goal,component=ESTIMATOR_NAMES[j],
          weight=w[j],stringsAsFactors=FALSE)
      }
    }
  }
  rm(fit); if(seed %% 3L == 0L) invisible(gc(verbose=FALSE))
}
weights <- do.call(rbind,component_rows)
write.csv(weights,'artifacts/discovery_analysis/component_weights_by_seed.csv',row.names=FALSE)
stat <- aggregate(weight~family+engine+goal+component,weights,
                  function(w)c(mean=mean(w),sd=stats::sd(w),
                               min=min(w),max=max(w)))
summary_weights <- data.frame(stat[1:4],stat$weight,check.names=FALSE)
write.csv(summary_weights,'artifacts/discovery_analysis/component_weight_stability.csv',row.names=FALSE)
cat('V3_DISCOVERY_WEIGHT_STABILITY_PASS',nrow(summary_weights),'rows\n')

# Publish canonical B3-named counterparts without breaking existing downstream references.
source('R/00_shared/t2_v3_b3_naming.R')
t2_b3_publish("artifacts/discovery_analysis")
