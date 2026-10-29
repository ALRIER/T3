#!/usr/bin/env Rscript
# V3 full smoke: shared actual generator, role isolation, checkpoint restoration.
source("R/00_shared/load_all.R");t2_load(".")
source("R/00_shared/pipeline.R")
source("R/01_monte_carlo/v3_generation.R")
t2_assert_seed_plan_v3()
stopifnot(t2_v3_expected_role_entries()==720L)
root<-"artifacts/v3_full_smoke/data"
dir.create(root,recursive=TRUE,showWarnings=FALSE)
cases<-list(c("discovery","0","1000"),c("heldout","10","200"),c("stress","15","200"))
rows<-list()
for(case in cases) {
 role<-case[1];seed<-as.integer(case[2]);n<-as.integer(case[3])
 started<-proc.time()[["elapsed"]]
 result<-t2_v3_generate(role,"normal",seed,n,R=5L,n_scenarios=8L,root=root)
 stopifnot(length(result$scenarios)==9L,
           all(vapply(result$scenarios,function(x)
             identical(colnames(x$T),ESTIMATOR_NAMES)&&
             identical(dim(x$T),c(5L,26L))&&all(is.finite(x$T)),logical(1))))
 rerun<-t2_v3_generate(role,"normal",seed,n,R=5L,n_scenarios=8L,root=root)
 stopifnot(identical(result$grid,rerun$grid))
 rows[[length(rows)+1L]]<-data.frame(role=role,seed=seed,n=n,
                          elapsed_seconds=proc.time()[["elapsed"]]-started)
}
# Recover an interrupted archive: remove canonical+one scenario; keep intact others.
folder<-file.path(root,"v3_real26_seedplan20_mixedheldout_rlm100","discovery","normal","seed00","n1000_r5")
canonical<-file.path(folder,"canonical.rds")
piece<-file.path(folder,"scenario_0008.rds")
original<-t2_read_rds(canonical)
stopifnot(file.exists(canonical),file.exists(piece))
unlink(c(canonical,piece))
stopifnot(!file.exists(canonical),!file.exists(piece))
restored<-t2_v3_generate("discovery","normal",0L,1000L,R=5L,n_scenarios=8L,root=root)
stopifnot(identical(original$grid,restored$grid),
          identical(original$scenarios,restored$scenarios),
          file.exists(canonical),file.exists(piece))
# Compare recovery to clean production using identical RNG contract and parameters.
clean<-t2_v3_generate("discovery","normal",0L,1000L,R=5L,n_scenarios=8L,
                      root="artifacts/v3_full_smoke/clean")
stopifnot(identical(clean$scenarios,restored$scenarios))
write.csv(do.call(rbind,rows),"artifacts/v3_full_smoke/performance.csv",row.names=FALSE)
writeLines('{"seed_roles":"PASS","scenarios":"PASS","matrices":"PASS","interruption_recovery":"PASS","clean_replay":"PASS"}',
           "artifacts/v3_full_smoke/smoke_report.json")
cat("V3_FULL_SMOKE_PASS\n")
