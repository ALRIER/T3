#!/usr/bin/env Rscript
# RQ1 nonparametric Q95 Monte Carlo precision from ORIGINAL 500-replicate
# Held Out Monte Carlo matrices and ORIGINAL frozen Discovery weights.
# No new random draws, optimization, weight selection, or MC generation.
a<-commandArgs(trailingOnly=TRUE)
if(length(a)!=5L)stop('Usage: FAMILY N RESTORED_DISCOVERY_DIR VERIFIED_MC_DIR OUTPUT_DIR')
family<-as.character(a[[1L]]);n<-as.integer(a[[2L]])
droot<-a[[3L]];mcroot<-a[[4L]];out<-a[[5L]]
families<-c('normal','lognormal','weibull','invgauss','exgaussian','exwald')
methods<-c('ga','nsga2','de','dirichlet','convex_mse','local_deterministic')
if(!family%in%families||!n%in%c(200L,1000L,3000L))stop('Unregistered original simulation block')
source('R/00_shared/load_all.R');t2_load('.')
source('R/00_shared/t3_b3_partitions.R')
ids<-t3_b3_partition_ids('discovery_support')
stopifnot(length(ids)==241L)
fits<-list.files(droot,'^discovery[.]rds$',recursive=TRUE,full.names=TRUE)
fits<-fits[grepl(paste0('/',family,'/seed[0-9]{2}/n',n,'/discovery[.]rds$'),fits)]
if(length(fits)!=10L)stop('Expected exactly ten frozen original Discovery models')
weights<-matrix(NA_real_,26L,60L)
labels<-data.frame(training_seed=integer(),method=character(),stringsAsFactors=FALSE)
k<-0L
for(seed in 0:9) {
 p<-fits[grepl(sprintf('/seed%02d/',seed),fits)]
 if(length(p)!=1L)stop('Missing original frozen training seed in restored bundle')
 fit<-readRDS(p)
 if(length(fit$models)<4L||!is.list(fit$non_evolutionary_controls)||
    !setequal(names(fit$non_evolutionary_controls),methods[5:6]))
    stop('Incomplete original six-method frozen model family')
 for(method in methods) {
  if(method%in%methods[1:4]){
   m<-Filter(function(x)!is.null(x$weights)&&identical(x$id,method),fit$models)
   if(length(m)!=1L)stop('Missing evolutionary frozen W')
   w<-as.numeric(m[[1L]]$weights)
  }else{
   ctr<-fit$non_evolutionary_controls[[method]]
   w<-as.numeric(ctr$weights)
  }
  if(length(w)!=26L||any(!is.finite(w))||any(w< -1e-9)||abs(sum(w)-1)>1e-7)
     stop('Original frozen weight is invalid for ',method,' ',seed)
  k<-k+1L;weights[,k]<-w
  labels<-rbind(labels,data.frame(training_seed=seed,method=method))
 }
 rm(fit)
}
if(k!=60L||anyDuplicated(labels))stop('Missing/duplicated original six-method W selection')
mc_files<-list.files(mcroot,'^canonical[.]rds$',recursive=TRUE,full.names=TRUE)
if(length(mc_files)!=10L)stop('Expected one original Held Out canonical matrix per evaluation seed')
root_seeds<-vapply(10:19,function(s){
 z<-mc_files[grepl(paste0('/seed',s,'/canonical[.]rds$'),mc_files)]
 if(length(z)!=1L)stop('Missing independently frozen Monte Carlo seed ',s)
 z
},character(1))
R<-500L
# Exact distribution-free binomial order-statistic interval for the
# population 95th quantile conditional on iid observations per scenario.
# This is quantile Monte Carlo precision, not coverage calibration of
# an optimizer difference across independent seeds.
klo<-max(1L,as.integer(qbinom(.025,R,.95)))
khi<-min(R,as.integer(qbinom(.975,R,.95)+1L))
if(klo>=khi)stop('Invalid binomial order-statistic interval')
summ<-list();examples<-list()
for(s in 10:19) {
 path<-root_seeds[as.character(s)]
 z<-readRDS(path)
 if(!identical(as.character(z$role),'heldout')||
    !identical(as.character(z$family),family)||
    as.integer(z$seed_index)!=s||as.integer(z$n)!=n||
    as.integer(z$replications)!=R||length(z$scenarios)!=321L)
    stop('Canonical original Monte Carlo sample identity mismatch: ',path)
 accum_mse<-numeric(k);accum_q95<-numeric(k)
 accum_width<-numeric(k);accum_rel<-numeric(k)
 accum_gt10<-integer(k);accum_gt20<-integer(k)
 selected_ids<-vapply(z$scenarios,function(x)as.integer(x$scenario_id),integer(1L))
 if(!identical(selected_ids,0:320))stop('Original 321 MC scenario sequence differs')
 for(id in ids) {
  sc<-z$scenarios[[id+1L]]
  T<-sc$T
  if(!is.matrix(T)||!identical(dim(T),c(R,26L))||
     !identical(colnames(T),ESTIMATOR_NAMES)||
     any(!is.finite(T))||length(sc$target)!=1L||
     !is.finite(sc$target))stop('Invalid original 500 by 26 MC component matrix')
  error<-(T%*%weights-as.numeric(sc$target))^2
  accum_mse<-accum_mse+colMeans(error)
  for(m in seq_len(k)){
   ordered<-sort(error[,m],na.last=NA)
   # Match the original model scoring's documented type-8 quantile.
   q<-as.numeric(quantile(ordered,probs=.95,type=8,names=FALSE))
   lo<-ordered[[klo]];hi<-ordered[[khi]]
   rel<-(hi-lo)/max(q,1e-12)
   accum_q95[[m]]<-accum_q95[[m]]+q
   accum_width[[m]]<-accum_width[[m]]+hi-lo
   accum_rel[[m]]<-accum_rel[[m]]+rel
   accum_gt10[[m]]<-accum_gt10[[m]]+as.integer(rel>.10)
   accum_gt20[[m]]<-accum_gt20[[m]]+as.integer(rel>.20)
   if(id%in%c(0L,1L,100L,200L)&&labels$training_seed[[m]]==0L) {
     examples[[length(examples)+1L]]<-data.frame(
       family=family,sample_n=n,eval_seed=s,scenario_id=id,
       training_seed=0L,method=labels$method[[m]],
       original_MC_reps=R,q95=q,order_stat_lower=lo,
       order_stat_upper=hi,relative_width=rel)
   }
  }
 }
 one<-data.frame(family=family,sample_n=n,eval_seed=s,
   training_seed=labels$training_seed,method=labels$method,
   mse=accum_mse/length(ids),q95=accum_q95/length(ids),
   average_q95_interval_width=accum_width/length(ids),
   average_q95_interval_relative_width=accum_rel/length(ids),
   frac_scenarios_mc_q95_width_gt10=accum_gt10/length(ids),
   frac_scenarios_mc_q95_width_gt20=accum_gt20/length(ids),
   conditional_MC_replicates=R,binomial_order_rank_lower=klo,
   binomial_order_rank_upper=khi)
 summ[[length(summ)+1L]]<-one
 rm(z);invisible(gc(FALSE))
 cat('R1_ORIGINAL_MONTE_CARLO_Q95_SEED_PASS',family,n,s,'\n')
}
all<-do.call(rbind,summ)
if(nrow(all)!=600L||anyDuplicated(all[c('eval_seed','training_seed','method')]))
 stop('Incompletely recovered original frozen control/method evaluation grid')
refpath<-file.path('R1','runs','44310024979','heldout',paste0(family,'-n',n),'candidate_by_eval.csv')
ref<-read.csv(refpath,stringsAsFactors=FALSE)
test<-merge(all[all$method%in%methods[1:4],c('eval_seed','training_seed','method','mse','q95')],
            ref,by=c('eval_seed','training_seed','method'),all=TRUE,suffixes=c('_mc','_r1'))
if(nrow(test)!=400L||anyNA(test$mse_mc)||anyNA(test$mse_r1))stop('Original R1 candidate keys do not match MC matrices')
for(metric in c('mse','q95')) {
 actual<-test[[paste0(metric,'_mc')]]
 expected<-test[[paste0(metric,'_r1')]]
 bad<-abs(actual-expected) > 1e-7*pmax(1,abs(expected))
 if(any(bad))stop('Original independent MC reconstruction does not reproduce published R1 scoring metric: ',metric,' failures ',sum(bad),' first ',actual[which(bad)[1]],' versus ',expected[which(bad)[1]])
}
dir.create(out,recursive=TRUE,showWarnings=FALSE)
write.csv(all,file.path(out,'original_q95_mc_uncertainty_by_candidate_seed.csv'),row.names=FALSE)
write.csv(do.call(rbind,examples),file.path(out,'q95_order_stat_scenario_examples.csv'),row.names=FALSE)
aggregate_results<-aggregate(all[c('average_q95_interval_width',
    'average_q95_interval_relative_width','frac_scenarios_mc_q95_width_gt10',
    'frac_scenarios_mc_q95_width_gt20')],by=all[c('family','sample_n','method')],
    FUN=mean)
write.csv(aggregate_results,file.path(out,'q95_mc_uncertainty_by_method.csv'),row.names=FALSE)
src_files<-list.files(mcroot,'^SOURCE_LINEAGE[.]json$',recursive=TRUE,full.names=TRUE)
if(length(src_files)!=10L)stop('Missing archived source provenance')
writeLines(c('# Q95 precision from original Monte Carlo matrices',
  'Original 500-replicate component matrices on 241 support scenarios, 10 evaluation seeds,',
  '10 frozen training seeds and all six original optimizer and deterministic weights.',
  'No new Monte Carlo draws, no refitting, and no new weight choices.',
  'The original 400 evolutionary candidate-evaluation averages were reproduced from matrices.',
  sprintf('Binomial order statistic interval for Q95: ranks %d through %d out of 500.',klo,khi),
  'This interval concerns the conditional distribution of the within-scenario Q95 statistic.',
  'It is not a confidence interval for an optimizer performance difference, nor a',
  'validated nominal coverage rate for the 216 original between-method hypotheses.',
  'Cross-scenario observations may share base sample pools; no false independent scenario units are claimed.',
  paste('Original MC source SHA256 manifests:',paste(src_files,collapse=';'))),
 file.path(out,'Q95_PRECISION_SCOPE.txt'))
cat('R1_ORIGINAL_Q95_MC_BLOCK_PASS',family,n,nrow(all),'\n')
