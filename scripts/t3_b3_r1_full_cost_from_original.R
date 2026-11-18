#!/usr/bin/env Rscript
# Analyze ORIGINAL Discovery training metadata and optimizer cost accounting.
# No HPO tuning, optimization, scoring, or artificial runtime estimates.
a<-commandArgs(trailingOnly=TRUE)
if(length(a)!=3L)stop('Usage: ORIGINAL_DISCOVERY_DIRECTORY SAMPLE_N OUT_DIRECTORY')
root<-a[[1L]];n<-as.integer(a[[2L]]);out<-a[[3L]]
if(!n%in%c(200L,1000L,3000L))stop('Wrong frozen sample size')
families<-c('normal','lognormal','weibull','invgauss','exgaussian','exwald')
methods<-c('ga','nsga2','de','dirichlet')
files<-list.files(root,'^discovery[.]rds$',recursive=TRUE,full.names=TRUE)
if(length(files)!=60L)stop('Incomplete original Discovery training RDS')
rows<-list();fields<-list()
extract_numeric_time<-function(x){
 if(!is.list(x))return(list(value=NA_real_,field='not_recorded'))
 ix<-names(x)
 if(is.null(ix))return(list(value=NA_real_,field='not_recorded'))
 matches<-grep('^(elapsed(_seconds)?|wall(_time)?(_seconds)?|duration(_seconds)?|runtime(_seconds)?|execution_time(_seconds)?|time_elapsed)$',ix,ignore.case=TRUE,value=TRUE)
 for(name in matches) {
  v<-x[[name]]
  if(is.numeric(v)&&length(v)==1L&&is.finite(v)&&v>=0)
    return(list(value=as.numeric(v),field=name))
 }
 list(value=NA_real_,field='not_recorded')
}
for(p in files) {
 path<-gsub('\\\\','/',p)
 m<-regexec('/(normal|lognormal|weibull|invgauss|exgaussian|exwald)/seed([0-9]{2})/n(200|1000|3000)/discovery[.]rds$',path)
 g<-regmatches(path,m)[[1L]]
 if(length(g)!=4L||as.integer(g[[4L]])!=n)stop('Incorrect original frozen fit provenance: ',path)
 f<-g[[2L]];seed<-as.integer(g[[3L]])
 fit<-readRDS(p)
 if(!setequal(names(fit$engines),methods)||!is.list(fit$budget_registry)||
   is.null(fit$objective_budget_audit))stop('Incomplete optimizer HPO/evaluation provenance')
 for(method in methods) {
  z<-fit$engines[[method]]
  used<-as.integer(z$evaluations_used)
  budget<-as.integer(z$evaluation_budget)
  if(length(used)!=1L||length(budget)!=1L||!is.finite(used)||!is.finite(budget)||
     used<1L||budget<used)stop('Original optimizer budget invalid')
  timing<-extract_numeric_time(z)
  rows[[length(rows)+1L]]<-data.frame(family=f,sample_n=n,training_seed=seed,
    method=method,actual_evaluations=used,declared_budget=budget,
    fraction_budget_used=used/budget,optimizer_wall_seconds=timing$value,
    wall_seconds_field=timing$field,wall_time_verified=is.finite(timing$value),
    original_discovery_source=p,stringsAsFactors=FALSE)
  fields[[length(fields)+1L]]<-data.frame(family=f,sample_n=n,training_seed=seed,
    method=method,engine_fields=paste(names(z),collapse=';'),
    hpo_registry_fields=paste(names(fit$budget_registry),collapse=';'),
    objective_budget_fields=paste(names(fit$objective_budget_audit),collapse=';'),
    stringsAsFactors=FALSE)
 }
 rm(fit)
}
z<-do.call(rbind,rows);metadata<-do.call(rbind,fields)
if(nrow(z)!=240L||anyDuplicated(z[c('family','sample_n','training_seed','method')]))
 stop('Incomplete frozen cost accounting')
prior<-read.csv(file.path('R1','runs','44310024979','discovery',paste0('n',n),'training_optimizer_costs.csv'))
verified<-merge(z,prior[,c('family','sample_n','training_seed','method','actual_evaluations','evaluation_budget')],
               by=c('family','sample_n','training_seed','method'),suffixes=c('_source','_r1'))
if(nrow(verified)!=240L||any(verified$actual_evaluations_source!=verified$actual_evaluations_r1)||
   any(verified$declared_budget!=verified$evaluation_budget))
 stop('Original Discovery RDS cost counts do not match previously archived R1')
dir.create(out,recursive=TRUE,showWarnings=FALSE)
write.csv(z,file.path(out,'verified_original_training_optimizer_costs.csv'),row.names=FALSE)
write.csv(metadata,file.path(out,'optimizer_timing_hpo_source_fields.csv'),row.names=FALSE)
write.csv(aggregate(z[c('actual_evaluations','fraction_budget_used')],by=z['method'],
                    FUN=mean),file.path(out,'mean_evaluation_cost_by_method.csv'),row.names=FALSE)
good<-sum(z$wall_time_verified)
writeLines(c('# Original full optimizer cost feasibility and fairness audit',
 sprintf('Sample size n=%d. Complete verified 240 frozen optimizer evaluation records.',n),
 'Original Discovery RDS records agree exactly with published R1 counts.',
 sprintf('Explicit verifiable per-engine elapsed-time fields: %d/240.',good),
 'Original nested HPO provenance metadata fields are inventoried, not guessed.',
 'Do not equate maximum budget or raw evaluations with complete wall-clock or HPO compute.',
 'If no original duration records exist, the full end-to-end compute comparison is UNRESOLVED.',
 'The repository-held source archives remain immutable; no optimizer or HPO rerun occurred.'),
 file.path(out,'COST_SCOPE.txt'))
cat('R1_ORIGINAL_DISCOVERY_COST_AUDIT_PASS',n,nrow(z),good,'\n')
