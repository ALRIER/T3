#!/usr/bin/env Rscript
args<-commandArgs(TRUE)
if(length(args)!=1L)stop('Usage: CV5_REFIT_FOLDER')
root<-args[[1]]
source('R/02_discovery/t2_v3_b3_robust_objectives.R')
z<-read.csv(file.path(root,'out_of_fold_scores.csv'))
stopifnot(all(c('model','scenario_id','mse','q95')%in%names(z)))
models<-unique(z$model)
set.seed(27182L)
rows<-lapply(models,function(m){
 x<-z[z$model==m,,drop=FALSE]
 if(anyDuplicated(x$scenario_id))stop('Duplicate validation scenarios')
 B<-500L
 bm<-replicate(B,mean(sample(x$mse,nrow(x),TRUE)))
 bq<-replicate(B,mean(sample(x$q95,nrow(x),TRUE)))
 data.frame(model=m,bootstrap_reps=B,mse_boot_sd=sd(bm),
 q95_boot_sd=sd(bq),dro_mse=t2_b3_dro(matrix(x$mse,ncol=1),.2)[1],
 dro_q95=t2_b3_dro(matrix(x$q95,ncol=1),.2)[1])
})
write.csv(do.call(rbind,rows),file.path(root,'B3_stability_DRO_diagnostics.csv'),row.names=FALSE)
cat('T2_V3_B3_STABILITY_DRO_PASS\n')
