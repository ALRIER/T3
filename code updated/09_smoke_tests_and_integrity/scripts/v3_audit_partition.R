#!/usr/bin/env Rscript
# Audit the exact scientific output of one existing V3 production partition.
args <- commandArgs(trailingOnly=TRUE)
if(length(args)!=4L) stop('Usage: ROLE FAMILY SEED N')
role<-args[[1L]];family<-args[[2L]];seed<-as.integer(args[[3L]]);n<-as.integer(args[[4L]])
source('R/00_shared/load_all.R');t2_load('.')
source('R/00_shared/pipeline.R')
source('R/00_shared/v3_scientific_adapter.R')
root<-t2_v3_block_dir(role,family,seed,n)
expected<-c('canonical.rds',sprintf('scenario_%04d.rds',0:120))
if(!all(file.exists(file.path(root,expected))))stop('Missing canonical/scenario RDS')
x<-t2_v3_read_block(role,family,seed,n)
for(id in 0:120) {
  s<-t2_v3_read_scenario(role,family,seed,n,id)
  z<-x$scenarios[[id+1L]]
  if(!identical(s$T,z$T)||!identical(s$target,z$target)||
     !identical(s$scenario_id,z$scenario_id))
    stop('Canonical/scenario mismatch: ',id)
  g<-x$grid[id+1L,,drop=FALSE]
  if(!identical(as.integer(g$scenario_id),as.integer(s$scenario_id))||
     !isTRUE(all.equal(as.numeric(g$rate),as.numeric(s$rate)))||
     !isTRUE(all.equal(as.numeric(g$scale),as.numeric(s$scale)))||
     !identical(as.character(g$mechanism),as.character(s$mechanism)))
    stop('Grid/scenario mismatch: ',id)
}
checksums<-file.path('artifacts','mc_v3_real26','SHA256SUMS')
if(!file.exists(checksums))stop('Missing producer SHA256SUMS')
# Verify every listed file with the repository-relative manifest.
status<-system2('sha256sum',c('-c',shQuote(checksums)),stdout=FALSE,stderr=FALSE)
if(status!=0L)stop('Producer SHA256SUMS mismatch')
out<-file.path('artifacts','v3_audit',sprintf('%s-%s-seed%02d-n%d.csv',role,family,seed,n))
dir.create(dirname(out),recursive=TRUE,showWarnings=FALSE)
write.csv(data.frame(role=role,family=family,seed=seed,n=n,reps=500L,
  scenarios=121L,estimators=26L,status='PASS',
  canonical_sha256=t2_sha256(file.path(root,'canonical.rds'))),
  out,row.names=FALSE)
cat('V3_PARTITION_AUDIT_PASS ',role,' ',family,' ',seed,' ',n,'\n',sep='')
