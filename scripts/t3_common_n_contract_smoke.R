#!/usr/bin/env Rscript
source('R/00_shared/config.R')
target<-as.integer(c(200,1000,3000))
for(stage in c('discovery','heldout','stress','realworld')){
 stopifnot(identical(t2_v3_sample_sizes(stage),target))
}
t2_assert_seed_plan_v3()
stopifnot(identical(as.integer(ga_config$train_n),target))
cat('T3_COMMON_N_200_1000_3000_CONTRACT_PASS\n')
