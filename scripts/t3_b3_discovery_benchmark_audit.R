#!/usr/bin/env Rscript
# Freeze the strongest non-mean classical estimator separately for every
# Discovery family x scenario x n cell; report each W* against that comparator
# and mean. Training taxonomies/intervals are descriptive, with no BH inference.
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
 h<-engines[engines%in%tok];if(length(h))h[[1L]] else NA_character_
}
identity<-function(path){
 p<-strsplit(normalizePath(path,mustWork=FALSE),.Platform$file.sep,fixed=TRUE)[[1L]]
 i<-match('discovery_v3',p);if(is.na(i)||length(p)<i+3L)stop('Cannot recover shard identity: ',path)
 list(family=p[i+1L],seed=as.integer(sub('^seed','',p[i+2L])),sample_n=as.integer(sub('^n','',p[i+3L])))
}
score_parts<-list();scale_parts<-list();identities<-character()
for(path in files){
 fit<-readRDS(path);z<-fit$training_control_comparison;id<-identity(path)
 if(!is.data.frame(z)||!all(c('model','scenario_id','mse','q95')%in%names(z)))stop('Missing Discovery training score panel: ',path)
 allb<-z[z$model%in%ESTIMATOR_NAMES,,drop=FALSE]
 if(!all(ESTIMATOR_NAMES%in%allb$model))stop('Discovery panel omits a classical estimator: ',path)
 if(length(unique(z$model[!z$model%in%ESTIMATOR_NAMES & !z$model%in%c('convex_mse','local_deterministic')]))!=4L)
   stop('Expected four selected evolutionary W* in ',path)
 identities<-c(identities,paste(id$family,id$seed,id$sample_n,sep='|'))
 allb$family<-id$family;allb$training_seed<-id$seed;allb$sample_n<-id$sample_n
 score_parts[[length(score_parts)+1L]]<-allb[c('family','sample_n','training_seed','scenario_id','model','mse','q95')]
 sc<-aggregate(allb[c('mse','q95')],allb['scenario_id'],min)
 sc$family<-id$family;sc$sample_n<-id$sample_n;sc$training_seed<-id$seed
 scale_parts[[length(scale_parts)+1L]]<-sc
 rm(fit,z,allb,sc);invisible(gc(FALSE))
}
frozen_families<-c('normal','lognormal','weibull','invgauss','exgaussian','exwald')
expected<-expand.grid(family=frozen_families,training_seed=0:9,
 sample_n=t2_v3_sample_sizes('discovery'),stringsAsFactors=FALSE)
expected_ids<-with(expected,paste(family,training_seed,sample_n,sep='|'))
if(anyDuplicated(identities)||!setequal(identities,expected_ids))stop('Discovery artifacts do not cover the complete frozen family x seed x n grid')
scores<-do.call(rbind,score_parts);scales<-do.call(rbind,scale_parts)
scale_family<-aggregate(scales[c('mse','q95')],scales[c('family','sample_n')],mean)
names(scale_family)[3:4]<-c('mse_scale','q95_scale')
classical<-scores[scores$model%in%setdiff(ESTIMATOR_NAMES,'mean'),,drop=FALSE]
classical_mean<-aggregate(classical[c('mse','q95')],
 classical[c('family','sample_n','scenario_id','model')],mean)
classical_mean<-merge(classical_mean,scale_family,by=c('family','sample_n'),sort=FALSE)
classical_mean$selection_score<-.5*(classical_mean$mse/classical_mean$mse_scale+
 classical_mean$q95/classical_mean$q95_scale)
map_key<-c('family','sample_n','scenario_id')
split_map<-split(classical_mean,interaction(classical_mean[map_key],drop=TRUE,lex.order=TRUE))
own_map<-do.call(rbind,lapply(split_map,function(b){
 b<-b[order(b$selection_score,match(b$model,ESTIMATOR_NAMES)),,drop=FALSE]
 b[1L,c('family','sample_n','scenario_id','model','selection_score','mse','q95')]
}))
names(own_map)[names(own_map)=='family']<-'evaluation_family'
names(own_map)[names(own_map)=='model']<-'own_benchmark'
names(own_map)[names(own_map)=='mse']<-'benchmark_training_mse'
names(own_map)[names(own_map)=='q95']<-'benchmark_training_q95'
score_grid<-read.csv('config/T2_V3_B3_prospective_321_grid.csv',stringsAsFactors=FALSE)
own_map<-merge(own_map,score_grid,by='scenario_id',all.x=TRUE,sort=FALSE)
if(anyNA(own_map$mechanism)||anyDuplicated(own_map[c('evaluation_family','sample_n','scenario_id')]))stop('Scenario benchmark map is incomplete or duplicated')
raw_pairs<-list();pi<-0L
for(path in files){
 fit<-readRDS(path);z<-fit$training_control_comparison;id<-identity(path)
 candidates<-unique(z$model[!z$model%in%ESTIMATOR_NAMES & !z$model%in%c('convex_mse','local_deterministic')])
 for(cid in candidates){
  cdat<-z[z$model==cid,c('scenario_id','mse','q95')]
  for(role in c('own','mean')){
   if(role=='own'){
    m<-own_map[own_map$evaluation_family==id$family&own_map$sample_n==id$sample_n,,drop=FALSE]
    ref<-z[z$model%in%m$own_benchmark,c('scenario_id','model','mse','q95')]
    p<-merge(cdat,m[c('scenario_id','own_benchmark')],by='scenario_id')
    p<-merge(p,ref,by.x=c('scenario_id','own_benchmark'),by.y=c('scenario_id','model'),suffixes=c('_candidate','_benchmark'))
    p$benchmark<-p$own_benchmark
   } else {
    ref<-z[z$model=='mean',c('scenario_id','mse','q95')]
    p<-merge(cdat,ref,by='scenario_id',suffixes=c('_candidate','_benchmark'))
    p$benchmark<-'mean'
   }
   if(nrow(p)!=nrow(cdat))stop('Unpaired Discovery score at ',path,' model ',cid)
   pi<-pi+1L;raw_pairs[[pi]]<-data.frame(family=id$family,training_seed=id$seed,
    sample_n=id$sample_n,scenario_id=p$scenario_id,engine=engine_from_id(cid),
    candidate_model=cid,benchmark_role=role,benchmark=p$benchmark,
    mse_difference=p$mse_candidate-p$mse_benchmark,
    q95_difference=p$q95_candidate-p$q95_benchmark,
    mse_gain_pct=100*(p$mse_benchmark-p$mse_candidate)/pmax(abs(p$mse_benchmark),.Machine$double.eps),
    q95_gain_pct=100*(p$q95_benchmark-p$q95_candidate)/pmax(abs(p$q95_benchmark),.Machine$double.eps),
    stringsAsFactors=FALSE)
  }
 }
 rm(fit,z);invisible(gc(FALSE))
}
raw<-do.call(rbind,raw_pairs)
summary_keys<-c('family','sample_n','scenario_id','engine','benchmark_role','benchmark')
panels<-split(raw,interaction(raw[summary_keys],drop=TRUE,lex.order=TRUE))
summary_rows<-lapply(panels,function(g){
 ci_fun<-function(v){if(length(v)<3L)c(NA_real_,NA_real_) else if(all(v==v[1L]))rep(v[1L],2L) else stats::t.test(v)$conf.int}
 ci_m<-ci_fun(g$mse_difference);ci_q<-ci_fun(g$q95_difference)
 z<-g[1L,summary_keys,drop=FALSE];z$n_training_seeds<-nrow(g)
 z$mse_difference<-mean(g$mse_difference);z$mse_ci_lower<-ci_m[1L];z$mse_ci_upper<-ci_m[2L]
 z$q95_difference<-mean(g$q95_difference);z$q95_ci_lower<-ci_q[1L];z$q95_ci_upper<-ci_q[2L]
 z$mse_gain_pct<-mean(g$mse_gain_pct);z$q95_gain_pct<-mean(g$q95_gain_pct)
 z$taxonomy<-if(z$mse_difference<0&&z$q95_difference<0)'joint_MSE_q95_descriptive'
  else if(z$mse_difference<0)'MSE_only_descriptive' else if(z$q95_difference<0)'q95_only_descriptive' else 'no_descriptive_gain'
 z$confidence_role<-'training_seed_descriptive_interval_not_confirmatory';z
})
summary<-do.call(rbind,summary_rows)
summary$tier4_retained_candidate<-TRUE
out<-file.path(root,'benchmark_audit_v2')
if(dir.exists(out))stop('Refusing to overwrite immutable Discovery training audit')
dir.create(out,recursive=TRUE,showWarnings=FALSE)
write.csv(own_map,file.path(out,'own_benchmark_map.csv'),row.names=FALSE)
write.csv(raw,file.path(out,'candidate_scenario_training_scores.csv'),row.names=FALSE)
write.csv(summary,file.path(out,'scenario_taxonomy_descriptive.csv'),row.names=FALSE)
write.csv(data.frame(path=files,sha256=vapply(files,t2_sha256,character(1))),file.path(out,'input_manifest.csv'),row.names=FALSE)
writeLines(c('Comparator policy: for each family x scenario_id x n, freeze the best non-mean classical estimator using Discovery-only equal-weight normalized MSE/q95.',
 'Each W* is compared only with that cell-specific classical benchmark and mean.',
 'Discovery is development data. The scenario taxonomy and intervals are descriptive; no BH-FDR or confirmatory claims are made.',
 'All four W* remain retained; no benchmark-win gate is applied.'),file.path(out,'analysis_contract.txt'))
writeLines(c(paste0('code_revision=',Sys.getenv('GITHUB_SHA','unverified-local')),
 paste0('workflow_run_id=',Sys.getenv('GITHUB_RUN_ID','local'))),file.path(out,'run_provenance.txt'))
cat('T3_DISCOVERY_SCENARIO_OWN_BENCHMARK_PASS','map_cells',nrow(own_map),
 'taxonomy_rows',nrow(summary),'\n')
