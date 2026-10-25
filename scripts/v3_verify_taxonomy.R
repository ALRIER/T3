#!/usr/bin/env Rscript
# Verify shared taxonomy settings against an upstream stage handoff.
args<-commandArgs(trailingOnly=TRUE)
if(length(args)!=1L)stop("Usage: Rscript scripts/v3_verify_taxonomy.R PATH_TO_UPSTREAM_CONTRACT")
source("R/00_shared/load_all.R");t2_load(".")
if(!file.exists(args[1]))stop("Missing upstream taxonomy contract: ",args[1])
t2_verify_taxonomy_contract(readRDS(args[1]))
cat("V3_TAXONOMY_CONTRACT_MATCH\n")
