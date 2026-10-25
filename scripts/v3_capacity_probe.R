#!/usr/bin/env Rscript
source("R/00_shared/load_all.R");t2_load(".")
source("R/00_shared/pipeline.R")
source("R/01_monte_carlo/v3_generation.R")
before<-proc.time()[["elapsed"]]
z<-t2_v3_generate("discovery","normal",0L,1000L,R=500L,n_scenarios=8L,
 root="artifacts/v3_full_smoke/load_data")
elapsed<-proc.time()[["elapsed"]]-before
warnings_file<-file.path("artifacts/v3_full_smoke/load_data",
 "v3_real26_seedplan20_mixedheldout_rlm100","discovery","normal","seed00","n1000_r500","numeric_warnings.csv")
T<-z$scenarios[[2L]]$T
err<-(T[,2L]-z$target)^2
ref<-(T[,1L]-z$target)^2
ci<-t2_q95_ci_v3(err,ref,B=500L,seed=t2_seed_for_v3("discovery","normal",0L,1000L,-80L))
saveRDS(ci,"artifacts/v3_full_smoke/q95_ci_probe.rds")
warnings_count<-if(file.exists(warnings_file))nrow(read.csv(warnings_file)) else 0L
dir.create("artifacts/v3_full_smoke",recursive=TRUE,showWarnings=FALSE)
write.csv(data.frame(n=1000L,reps=500L,scenarios=nrow(z$grid),
 elapsed_seconds=elapsed,numeric_warning_count=warnings_count,
 q95=ci$q95,q95_lower=ci$q95_lower,q95_upper=ci$q95_upper,
 q95_delta_lower=ci$delta_lower,q95_delta_upper=ci$delta_upper),
 "artifacts/v3_full_smoke/capacity.csv",row.names=FALSE)
if(warnings_count>0L)cat("NUMERIC_WARNING_REVIEW_REQUIRED ",warnings_count,"\\n")
cat("V3_CAPACITY_PROBE_COMPLETE\\n")
