#!/usr/bin/env Rscript
# Independent canonical Monte Carlo generation for the prospective seed plan.
args<-commandArgs(trailingOnly=TRUE)
if(length(args)!=4L)stop("Usage: Rscript scripts/v3_montecarlo_stage.R ROLE FAMILY SEED N")
role<-args[1];family<-args[2];index<-as.integer(args[3]);n<-as.integer(args[4])
source("R/00_shared/load_all.R");t2_load(".");source("R/00_shared/pipeline.R")
t2_assert_seed_plan_v3()
if(!role %in% c("discovery","heldout","stress"))stop("Invalid role")
if(!index %in% t2_v3_indices(role))stop("Seed not assigned to requested role")
if(!n %in% if(role=="discovery")1000L else c(200L,1000L,3000L))
 stop("Sample size not assigned to requested role")
# Cache namespace segregates the revised 26-column library from historical matrices.
Sys.setenv(T2_CANONICAL_MC_ROOT="artifacts/mc_v3_real26")
replications<-as.integer(Sys.getenv("T2_V3_REPS","500"))
if(replications<2L)stop("At least two replications required")
# New implementation: role-scoped random streams and continuously sampled regimes.
source("R/01_monte_carlo/v3_generation.R")
n_scenarios<-as.integer(Sys.getenv("T2_V3_SCENARIOS","120"))
mc<-t2_v3_generate(role,family,index,n,R=replications,n_scenarios=n_scenarios)
stopifnot(identical(mc$role,role),identical(mc$protocol,"v3_real26_seedplan20_mixedheldout_rlm100"),
          identical(mc$component_names,ESTIMATOR_NAMES),
          nrow(mc$grid)==n_scenarios+1L)
cat(sprintf("V3_GENERATED role=%s family=%s seed=%02d n=%d scenarios=%d\\n",
 role,family,index,n,nrow(mc$grid)))

# Publish an immutable contract alongside the Monte Carlo archive.
t2_save_taxonomy_contract(file.path("artifacts","mc_v3_real26","taxonomy_contract.rds"))
