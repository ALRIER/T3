#!/usr/bin/env Rscript
# Sanity check ONE V3 production partition already downloaded from Actions.
args <- commandArgs(trailingOnly=TRUE)
if(length(args)!=4L) stop('Usage: ROLE FAMILY SEED N')
role <- args[[1L]]; family <- args[[2L]]
seed <- as.integer(args[[3L]]); n <- as.integer(args[[4L]])
source('R/00_shared/load_all.R'); t2_load('.')
source('R/00_shared/pipeline.R')
source('R/00_shared/v3_scientific_adapter.R')
root <- t2_v3_block_dir(role,family,seed,n,500L)
canonical <- t2_v3_read_block(role,family,seed,n)
if (nrow(canonical$grid)!=121L || length(canonical$scenarios)!=121L)
  stop('V3 scenario coverage mismatch')
for (id in 0:120) {
  p <- file.path(root,sprintf('scenario_%04d.rds',id))
  if (!file.exists(p)) stop('Missing separate scenario file: ',p)
  s <- t2_v3_read_scenario(role,family,seed,n,id)
  other <- canonical$scenarios[[id+1L]]
  if (!identical(s$T,other$T) || !identical(s$target,other$target) ||
      !identical(s$scenario_id,other$scenario_id))
    stop('Canonical versus per-scenario mismatch: ',id)
}
cat(sprintf('PASS V3 sanity role=%s family=%s seed=%02d n=%d R=500 scenarios=121 components=26\\n',
            role,family,seed,n))
