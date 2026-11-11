#!/usr/bin/env Rscript
# Export original frozen Discovery optimizer metadata without training,
# scoring or selecting new models. One output per sample size.
a<-commandArgs(trailingOnly=TRUE)
if(length(a)!=3L)stop('Usage: DISCOVERY_ROOT SAMPLE_N OUTPUT_CSV')
root<-a[[1L]];n<-as.integer(a[[2L]]);output<-a[[3L]]
if(!n%in%c(200L,1000L,3000L))stop('Unsupported frozen sample size')
source('R/00_shared/load_all.R');t2_load('.')
families<-c('normal','lognormal','weibull','invgauss','exgaussian','exwald')
engines<-c('ga','nsga2','de','dirichlet')
hash_bytes<-function(v) {
 file<-tempfile(pattern='frozen-hpo-sha-')
 con<-file(file,'wb');writeBin(serialize(v,NULL,version=3),con);close(con)
 out<-t2_sha256(file);unlink(file);as.character(out)
}
rows<-list()
for(family in families)for(train in 0:9) {
 p<-file.path(root,family,sprintf('seed%02d',train),paste0('n',n),'discovery.rds')
 contract<-file.path(dirname(p),'stage_contract.rds')
 if(!file.exists(p)||!file.exists(contract))stop('Missing immutable Discovery training contract: ',p)
 v<-readRDS(p);stage_contract<-readRDS(contract)
 if(!setequal(names(v$engines),engines)||is.null(v$budget_registry)||
    is.null(v$objective_budget_audit)||is.null(v$selection_policy)) {
  stop('Incomplete frozen engine/budget/selection provenance: ',p)
 }
 models<-Filter(function(z)!is.null(z$weights),v$models)
 if(length(models)!=4L||!setequal(vapply(models,function(z)z$id,character(1)),engines))
  stop('Expected exactly four selected, frozen evolutionary W vectors: ',p)
 for(engine in engines) {
  z<-v$engines[[engine]]
  model<-models[[which(vapply(models,function(x)identical(x$id,engine),logical(1)))]]
  w<-as.numeric(model$weights)
  if(length(w)!=26L||any(!is.finite(w))||any(w< -1e-10)||abs(sum(w)-1)>1e-8)
   stop('Invalid original frozen 26-component W: ',p)
  budget<-as.integer(z$evaluation_budget)
  used<-as.integer(z$evaluations_used)
  if(length(budget)!=1L||length(used)!=1L||!is.finite(budget)||
     !is.finite(used)||used<1L||budget<used)stop('Frozen budget invalid: ',p)
  term<-if(!is.null(z$termination_reason))as.character(z$termination_reason) else
   if(used<budget)'early_stop_reason_not_recorded' else 'maximum_budget_used'
  rows[[length(rows)+1L]]<-data.frame(
    family=family,sample_n=n,training_seed=train,engine=engine,
    frozen_weight_sha256=hash_bytes(w),
    original_discovery_rds_sha256=t2_sha256(p),
    original_stage_contract_sha256=t2_sha256(contract),
    objective_budget=budget,actual_evaluations=used,
    tuning_signature=hash_bytes(v$budget_registry),
    termination_reason=term,selected_W_source='training_only_original_discovery_rds',
    stringsAsFactors=FALSE)
 }
}
out<-do.call(rbind,rows)
if(nrow(out)!=240L||anyDuplicated(out[c('family','sample_n','training_seed','engine')]))
 stop('Exactly 240 original frozen units expected per n')
dir.create(dirname(output),recursive=TRUE,showWarnings=FALSE)
write.csv(out,output,row.names=FALSE)
cat('POST_RW_ORIGINAL_DISCOVERY_HPO_EXPORT_PASS',n,nrow(out),'\n')
