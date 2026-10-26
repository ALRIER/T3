#!/usr/bin/env Rscript
# Stable command name for stage-wide primary inference.
args<-commandArgs(trailingOnly=TRUE)
if(length(args)!=1L)stop('Usage: STAGE (heldout|stress)')
source('scripts/v3_stage_aggregate_panel.R',local=.GlobalEnv)
