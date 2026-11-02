#!/usr/bin/env Rscript
# Derive and freeze one own-regime classical benchmark per source family/n,
# then compare each selected W* only with that benchmark and with mean.
# Discovery outputs are training diagnostics, never confirmatory inference.
a<-commandArgs(trailingOnly=TRUE)
root<-if(length(a))a[[1L]] else 'artifacts/discovery_v3'
source('R/00_shared/load_all.R');t2_load('.')
files<-list.files(root,'^discovery[.]rds$',recursive=TRUE,full.names=TRUE)
files<-files[!grepl('benchmark_audit_v2',files,fixed=TRUE)]
if(!length(files))stop('No frozen Discovery artifacts found')
engine_from_id<-function(x){
 x<-tolower(as.character(x));engines<-c('dirichlet','nsga2','de','ga')
 tok<-strsplit(gsub('[^a-z0-9]+','_',x),'_',fixed=TRUE)[[1L]]
 tok<-setdiff(tok,c('normal','lognormal','weibull','invgauss','exgaussian','exwald'))
 z<-engines[engines%in%tok];if(length(z))z[[1L]] else NA_character_
}
identity<-function(path){
 p<-strsplit(normalizePath(path,mustWork=FALSE),.Platform$file.sep,fixed=TRUE)[[1L]]
 i<-match('discovery_v3',p)
 if(is.na(i)||length(p)<i+3L)stop('Cannot recover Discovery identity: ',path)
 list(family=p[i+1L],seed=as.integer(sub('^seed','',p[i+2L])),
      sample_n=as.integer(sub('^n','',p[i+3L])))
}
base_parts<-list();scale_parts<-list();identities<-character()
for(path in files){
 fit<-readRDS(path);z<-fit$training_control_comparison
 if(!is.data.frame(z)||!all(c('model','scenario_id','mse','q95')%in%names(z)))
   stop('Discovery artifact lacks the saved training comparison panel: ',path)
 id<-identity(path);identities<-c(identities,paste(id$family,id$seed,id$sample_n,sep='|'))
 if(!all(ESTIMATOR_NAMES%in%z$model))stop('Discovery training panel misses a benchmark: ',path)
 all_classic<-z[z$model%in%ESTIMATOR_NAMES,,drop=FALSE]
 b<-all_classic[all_classic$model!='mean',,drop=FALSE]
 x<-aggregate(b[c('mse','q95')],b['model'],mean)
 x$family<-id$family;x$sample_n<-id$sample_n;base_parts[[length(base_parts)+1L]]<-x
 per_scenario<-aggregate(all_classic[c('mse','q95')],all_classic['scenario_id'],min)
 sc<-data.frame(scale_mse=mean(per_scenario$mse),scale_q95=mean(per_scenario$q95),
   family=id$family,sample_n=id$sample_n)
 scale_parts[[length(scale_parts)+1L]]<-sc
 rm(fit,z,b,x,per_scenario);invisible(gc(FALSE))
}
expected<-expand.grid(family=t2_families(),training_seed=0:9,
 sample_n=t2_v3_sample_sizes('discovery'),stringsAsFactors=FALSE)
expected_ids<-with(expected,paste(family,training_seed,sample_n,sep='|'))
if(anyDuplicated(identities)||!setequal(identities,expected_ids))
 stop('Need exactly one Discovery artifact per family x seed x sample size')
base<-do.call(rbind,base_parts);scales<-do.call(rbind,scale_parts)
base_mean<-aggregate(base[c('mse','q95')],base[c('family','sample_n','model')],mean)
scale_mean<-aggregate(scales[c('scale_mse','scale_q95')],scales[c('family','sample_n')],mean)
own_rows<-list();oi<-0L
for(i in seq_len(nrow(scale_mean))){
 f<-scale_mean$family[i];n<-scale_mean$sample_n[i]
 b<-base_mean[base_mean$family==f & base_mean$sample_n==n,,drop=FALSE]
 b$balanced_training_score<-0.5*(b$mse/scale_mean$scale_mse[i]+b$q95/scale_mean$scale_q95[i])
 b<-b[order(b$balanced_training_score,match(b$model,ESTIMATOR_NAMES)),,drop=FALSE]
 if(!nrow(b))stop('No eligible non-mean classical benchmark for ',f,' n=',n)
 oi<-oi+1L;own_rows[[oi]]<-data.frame(source_family=f,sample_n=n,
   own_benchmark=b$model[1L],balanced_training_score=b$balanced_training_score[1L],
   own_training_mse=b$mse[1L],own_training_q95=b$q95[1L],
   selection='minimum equal-weight normalized training MSE/q95 among non-mean classical estimators',
   mean_separately_compared=TRUE,stringsAsFactors=FALSE)
}
own_map<-do.call(rbind,own_rows)
pair_rows<-list();summary_rows<-list();pi<-0L;si<-0L
for(path in files){
 fit<-readRDS(path);z<-fit$training_control_comparison;id<-identity(path)
 map<-own_map[own_map$source_family==id$family & own_map$sample_n==id$sample_n,,drop=FALSE]
 if(nrow(map)!=1L)stop('Frozen own benchmark lookup failed')
 cand_ids<-unique(z$model[!z$model%in%ESTIMATOR_NAMES &
   !z$model%in%c('convex_mse','local_deterministic')])
 if(length(cand_ids)!=4L)stop('Expected four frozen evolutionary W* in ',path)
 for(cid in cand_ids){
  cdat<-z[z$model==cid,c('scenario_id','mse','q95')]
  wins<-list()
  for(role in c('own','mean')){
   bm<-if(role=='own')map$own_benchmark[1L] else 'mean'
   ref<-z[z$model==bm,c('scenario_id','mse','q95')]
   pair<-merge(cdat,ref,by='scenario_id',suffixes=c('_candidate','_benchmark'))
   if(nrow(pair)!=nrow(cdat))stop('Unpaired Discovery training scores in ',path)
   dm<-pair$mse_candidate-pair$mse_benchmark;dq<-pair$q95_candidate-pair$q95_benchmark
   pi<-pi+1L;pair_rows[[pi]]<-data.frame(family=id$family,training_seed=id$seed,
     sample_n=id$sample_n,engine=engine_from_id(cid),candidate_model=cid,
     benchmark_role=role,benchmark=bm,scenarios=nrow(pair),
     mse_win_scenarios=sum(dm<0),q95_win_scenarios=sum(dq<0),
     joint_win_scenarios=sum(dm<0 & dq<0),
     mean_mse_gain_pct=mean(100*(pair$mse_benchmark-pair$mse_candidate)/pmax(abs(pair$mse_benchmark),.Machine$double.eps)),
     mean_q95_gain_pct=mean(100*(pair$q95_benchmark-pair$q95_candidate)/pmax(abs(pair$q95_benchmark),.Machine$double.eps)),
     evidence='training_only_descriptive_no_inference',stringsAsFactors=FALSE)
   wins[[role]]<-list(mse=dm<0,q95=dq<0)
  }
  si<-si+1L;summary_rows[[si]]<-data.frame(family=id$family,training_seed=id$seed,
    sample_n=id$sample_n,engine=engine_from_id(cid),candidate_model=cid,
    scenarios=length(wins$own$mse),beats_own_mse=sum(wins$own$mse),
    beats_own_q95=sum(wins$own$q95),beats_own_joint=sum(wins$own$mse&wins$own$q95),
    beats_mean_mse=sum(wins$mean$mse),beats_mean_q95=sum(wins$mean$q95),
    beats_mean_joint=sum(wins$mean$mse&wins$mean$q95),
    beats_own_and_mean_joint=sum(wins$own$mse&wins$own$q95&wins$mean$mse&wins$mean$q95),
    evidence='training_only_descriptive_no_inference',stringsAsFactors=FALSE)
 }
 rm(fit,z);invisible(gc(FALSE))
}
out<-file.path(root,'benchmark_audit_v2')
if(dir.exists(out))stop('Refusing to overwrite immutable Discovery benchmark audit')
dir.create(out,recursive=TRUE,showWarnings=FALSE)
write.csv(own_map,file.path(out,'own_benchmark_map.csv'),row.names=FALSE)
write.csv(do.call(rbind,pair_rows),file.path(out,'candidate_vs_own_and_mean_training.csv'),row.names=FALSE)
write.csv(do.call(rbind,summary_rows),file.path(out,'scenario_win_summary.csv'),row.names=FALSE)
write.csv(data.frame(path=files,sha256=vapply(files,t2_sha256,character(1))),
 file.path(out,'input_manifest.csv'),row.names=FALSE)
writeLines(c('Four W* per family/seed/sample size are retained; Discovery does not require them to win.',
 'Own benchmark is frozen per source family/sample size using Discovery-only training scores: best non-mean classical under equal-weight normalized MSE/q95.',
 'The arithmetic mean is an additional comparator; it is not treated as the theoretical target.',
 'Training comparisons are descriptive only and have no confirmatory p-values/BH-FDR.',
 'Held-out, Stress, and Real-world compare each W* only with this frozen own benchmark and mean.'),
 file.path(out,'analysis_contract.txt'))
writeLines(c(paste0('code_revision=',Sys.getenv('GITHUB_SHA','unverified-local')),
             paste0('workflow_run_id=',Sys.getenv('GITHUB_RUN_ID','local'))),
 file.path(out,'run_provenance.txt'))
cat('T3_DISCOVERY_OWN_BENCHMARK_AUDIT_PASS','maps',nrow(own_map),
 'candidate comparisons',nrow(do.call(rbind,pair_rows)),'\n')
