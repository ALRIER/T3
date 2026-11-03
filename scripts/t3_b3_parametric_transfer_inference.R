#!/usr/bin/env Rscript
# Streaming global inference for the 40:49 within-family parameter transfer panel.
# Each family x parameter row x n cell is evaluated separately; BH is then
# recomputed once over all candidate/reference/metric/scenario hypotheses.
a<-commandArgs(trailingOnly=TRUE)
if(length(a)!=2L)stop('Usage: SCORE_ROOT OWN_BENCHMARK_MAP.csv')
root<-a[[1L]];map_path<-a[[2L]]
source('R/00_shared/load_all.R');t2_load('.')
source('R/00_shared/pipeline.R');source('R/05_audits/benchmark_tournament.R')
if(!file.exists(map_path))stop('Discovery-frozen own-benchmark map is missing')
files<-list.files(root,'^scores[.]csv$',recursive=TRUE,full.names=TRUE)
manifest_files<-list.files(root,'^score_manifest[.]csv$',recursive=TRUE,full.names=TRUE)
if(length(files)!=4980L||length(manifest_files)!=4980L)
 stop('Expected all 4,980 immutable two-part score checkpoints and manifests')
sha256<-function(path)t2_sha256(path)
meta<-vector('list',length(manifest_files));names(meta)<-manifest_files
for(i in seq_along(manifest_files)) {
 m<-read.csv(manifest_files[i],stringsAsFactors=FALSE,check.names=FALSE)
 score<-file.path(dirname(manifest_files[i]),'scores.csv')
 if(!file.exists(score)||nrow(m)!=1L||
    !identical(as.character(m$protocol[1L]),'t3_b3_parametric_transfer_score_v3')||
    as.integer(m$scenario_block_count[1L])!=2L||
    !identical(tolower(m$scores_sha256[1L]),tolower(sha256(score))))
   stop('Score manifest hash mismatch: ',manifest_files[i])
 key<-c(as.character(m$family),as.integer(m$parameter_row),as.integer(m$seed),as.integer(m$n),
   as.integer(m$scenario_block))
 meta[[i]]<-list(key=key,manifest=manifest_files[i],score=score,manifest_row=m)
}
keys<-vapply(meta,function(x)paste(x$key,collapse='|'),character(1))
if(anyDuplicated(keys))stop('Duplicate transfer score identity')
expected_families<-c('normal','lognormal','weibull','invgauss','exgaussian','exwald')
expected_rows<-list(normal=2:8,lognormal=2:6,weibull=2:12,invgauss=2:9,
 exgaussian=2:27,exwald=2:27)
expected<-unlist(lapply(expected_families,function(f)
 lapply(expected_rows[[f]],function(r)lapply(40:49,function(s)
  lapply(c(200L,1000L,3000L),function(n)paste(f,r,s,n,sep='|'))))),recursive=TRUE,use.names=FALSE)
expected_blocks<-unlist(lapply(expected,function(k)paste(k,0:1,sep='|')),use.names=FALSE)
if(length(expected)!=2490L||length(expected_blocks)!=4980L||!setequal(keys,expected_blocks))
 stop('Transfer scenario-block identity coverage differs from frozen plan')
map<-read.csv(map_path,stringsAsFactors=FALSE,check.names=FALSE)
map_req<-c('evaluation_family','scenario_id','sample_n','own_benchmark')
if(!all(map_req%in%names(map))||anyDuplicated(map[map_req[1:3]])||
 any(!map$own_benchmark%in%setdiff(ESTIMATOR_NAMES,'mean')))stop('Invalid frozen Discovery own-benchmark map')
if(any(vapply(expected_families,function(f)sum(map$evaluation_family==f),integer(1))!=241L*3L))
 stop('Frozen Discovery map must contain 241 support scenarios for each family and n')

out<-file.path(root,'aggregate')
if(dir.exists(out))stop('Refusing to overwrite immutable parametric-transfer inference')
dir.create(out,recursive=TRUE)
tmp<-file.path(out,'_unadjusted');dir.create(tmp)
panels<-list()
for(fam in expected_families)for(pr in expected_rows[[fam]])for(n in c(200L,1000L,3000L))
 panels[[length(panels)+1L]]<-c(fam,pr,n)
metric_paths<-character(length(panels));panel_paths<-character(length(panels))
panel_index<-vector('list',length(panels));p_count<-0L
groups<-c('family','source_family','evaluation_family','transfer_scope','parameter_row','sample_n','scenario_id')
for(pi in seq_along(panels)) {
 id<-panels[[pi]];fam<-id[[1L]];pr<-as.integer(id[[2L]]);n<-as.integer(id[[3L]])
 selected<-Filter(function(x)x$key[[1L]]==fam&&as.integer(x$key[[2L]])==pr&&as.integer(x$key[[4L]])==n,meta)
 seed_block_pairs<-vapply(selected,function(x)paste(as.integer(x$key[[3L]]),as.integer(x$key[[5L]]),sep='|'),character(1))
 required_pairs<-as.vector(outer(40:49,0:1,function(s,b)paste(s,b,sep='|')))
 if(length(selected)!=20L||!setequal(vapply(selected,function(x)as.integer(x$key[[3L]]),integer(1)),rep(40:49,each=2L))||
    !setequal(seed_block_pairs,required_pairs))
   stop('Panel lacks two scenario halves for each independent seed 40:49: ',fam,'/',pr,'/n',n)
 x<-do.call(rbind,lapply(selected,function(s)
   read.csv(s$score,stringsAsFactors=FALSE,check.names=FALSE)))
 if(any(x$family!=fam)||any(x$parameter_row!=pr)||any(x$sample_n!=n)||
    any(!is.finite(x$mse))||any(!is.finite(x$q95)))stop('Invalid panel score identities or values')
 if(any(x$training_seed_count!=10L)||any(!vapply(strsplit(x$training_seed_set,';',fixed=TRUE),
   function(v)setequal(as.integer(v),0:9),logical(1))))stop('Frozen Discovery training-seed averaging contract failed')
 scenario_ids<-sort(unique(as.integer(x$scenario_id)))
 if(length(scenario_ids)!=241L||!setequal(scenario_ids,as.integer(map$scenario_id[map$evaluation_family==fam&as.integer(map$sample_n)==n])))
   stop('Transfer scores do not match the 241 Discovery-support scenario map')
 if(anyDuplicated(x[c(groups,'parametric_seed','model')]))stop('Duplicate score cell in transfer panel')
 ans<-t3_pairwise_tournament(x,'parametric_transfer','parametric_seed',groups,map,
   alpha=ga_config$fdr_primary)
 # Discard local q-values. The complete 40:49 transfer family gets one global BH pass below.
 ans$metrics$q_value_global<-NA_real_;ans$metrics$passes_bh<-FALSE
 ans$taxonomy$q_value_global.mse<-NA_real_;ans$taxonomy$q_value_global.q95<-NA_real_
 panel_dir<-file.path(tmp,fam,sprintf('parameter_row%02d_n%d',pr,n))
 dir.create(panel_dir,recursive=TRUE)
 mp<-file.path(panel_dir,'metrics_unadjusted.csv.gz')
 con<-gzfile(mp,'wt');write.csv(ans$metrics,con,row.names=FALSE);close(con)
 metric_paths[pi]<-mp
 panel_index[[pi]]<-data.frame(panel=pi,path=substring(mp,nchar(tmp)+2L),
  family=fam,parameter_row=pr,sample_n=n,metric_rows=nrow(ans$metrics),stringsAsFactors=FALSE)
 p_count<-p_count+nrow(ans$metrics)
 rm(x,ans);if(pi%%25L==0L){message('PARAMETRIC_INFER_PANEL_PROGRESS ',pi,'/',length(panels));invisible(gc())}
}
# Exact global Benjamini-Hochberg across all parameter rows, scenarios, engines,
# comparator roles, and metrics. Hold only the p-value vector in memory.
p_values<-numeric(p_count);offsets<-integer(length(metric_paths)+1L);offsets[1L]<-0L
for(i in seq_along(metric_paths)) {
 con<-gzfile(metric_paths[i],'rt');tab<-read.csv(con,stringsAsFactors=FALSE,check.names=FALSE,
   colClasses=NA);close(con)
 p<-tab$p_value;offsets[i+1L]<-offsets[i]+length(p)
 p_values[(offsets[i]+1L):offsets[i+1L]]<-p
 rm(tab,p);if(i%%50L==0L)invisible(gc(FALSE))
}
q_values<-p.adjust(p_values,method='BH')
alpha<-ga_config$fdr_primary
all_input_manifest<-do.call(rbind,lapply(meta,function(z)data.frame(
  family=z$key[[1L]],parameter_row=as.integer(z$key[[2L]]),seed=as.integer(z$key[[3L]]),
  sample_n=as.integer(z$key[[4L]]),scenario_block=as.integer(z$key[[5L]]),
  score_path=z$score,score_sha256=sha256(z$score),
  manifest_path=z$manifest,stringsAsFactors=FALSE)))
final_metrics<-file.path(out,'metrics_by_panel');dir.create(final_metrics)
final_taxonomy<-file.path(out,'taxonomy_by_panel');dir.create(final_taxonomy)
for(i in seq_along(metric_paths)) {
 con<-gzfile(metric_paths[i],'rt');inf<-read.csv(con,stringsAsFactors=FALSE,check.names=FALSE);close(con)
 lo<-offsets[i]+1L;hi<-offsets[i+1L]
 inf$q_value_global<-q_values[lo:hi]
 inf$passes_bh<-is.finite(inf$q_value_global)&inf$q_value_global<=alpha
 ids<-c('stage','candidate_model','candidate_engine','benchmark','benchmark_role',groups,
   'independent_units','inference_unit')
 value_cols<-c('difference','ci_lower','ci_upper','gain_pct','gain_pct_lower','gain_pct_upper',
   'p_value','q_value_global','passes_bh')
 wide<-reshape(inf[,c(ids,'metric',value_cols),drop=FALSE],idvar=ids,timevar='metric',direction='wide')
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
 scope_key<-interaction(wide[c('stage','candidate_model','family','source_family','evaluation_family',
   'transfer_scope','parameter_row','sample_n','scenario_id')],drop=TRUE,lex.order=TRUE)
 wide$beats_own_and_mean_tier1<-ave(as.integer(wide$tier1_joint_mse_q95_bh_fdr),scope_key,
   FUN=function(v)as.logical(all(v==1L)))
 wide$beats_own_and_mean_tier2<-ave(as.integer(wide$tier2_joint_mse_q95_ci),scope_key,
   FUN=function(v)as.logical(all(v==1L)))
 wide$practical_mse<-wide$gain_pct.mse>=ga_config$practical_gain_pct
 wide$practical_q95<-wide$gain_pct.q95>=ga_config$practical_gain_pct
 base<-panel_index[[i]]
 rel<-sub('metrics_unadjusted[.]csv[.]gz$','',base$path)
 metric_out<-file.path(final_metrics,paste0(gsub('/','_',rel),'metrics.csv.gz'))
 tax_out<-file.path(final_taxonomy,paste0(gsub('/','_',rel),'taxonomy.csv.gz'))
 con<-gzfile(metric_out,'wt');write.csv(inf,con,row.names=FALSE);close(con)
 con<-gzfile(tax_out,'wt');write.csv(wide,con,row.names=FALSE);close(con)
 rm(inf,wide);if(i%%25L==0L){message('PARAMETRIC_INFER_FINALIZE_PROGRESS ',i,'/',length(metric_paths));invisible(gc())}
}
write.csv(all_input_manifest,file.path(out,'input_manifest.csv'),row.names=FALSE)
write.csv(do.call(rbind,panel_index),file.path(out,'panel_manifest.csv'),row.names=FALSE)
writeLines(c('status=COMPLETE','stage=parametric_transfer',
 'independent_unit=parametric_transfer_seed_40_to_49',
 'checkpointing=241 Discovery-support scenarios split into two immutable disjoint halves',
 'training_seed_handling=average frozen Discovery seeds 0:9 within each transfer seed before inference',
 'scenario_scope=241 predeclared Discovery-support scenarios; 80 mixture stress-exclusive scenarios are excluded',
 'benchmark=Discovery-frozen best non-mean classical estimator for each family/scenario/n plus mean',
 'BH=one global panel over all transfer parameter rows, scenarios, candidates, comparator roles, metrics, and sample sizes',
 paste0('hypotheses=',p_count),'alpha=0.05'),file.path(out,'inference.status'))
unlink(tmp,recursive=TRUE)
cat('T3_B3_PARAMETRIC_TRANSFER_GLOBAL_INFERENCE_PASS panels=',length(panels),
 ' hypotheses=',p_count,' files=',length(files),'\n',sep='')
