#!/usr/bin/env Rscript
source('R/00_shared/load_all.R');t2_load('.')
source('R/00_shared/pipeline.R')
source('R/00_shared/v3_scientific_adapter.R')
source('R/00_shared/v3_downstream.R')
ids<-c(0L,1L,60L,120L)
new<-t2_v3_discovery_input('normal',0L,selected=ids)
old<-t2_v3_read_block('discovery','normal',0L,1000L,selected=ids)
stopifnot(identical(vapply(new$scenarios,function(z)z$scenario_id,integer(1)),ids))
for(i in seq_along(ids)) {
 stopifnot(identical(new$scenarios[[i]]$T,old$scenarios[[i]]$T))
 stopifnot(identical(new$scenarios[[i]]$target,old$scenarios[[i]]$target))
 stopifnot(identical(new$scenarios[[i]]$eligible,old$scenarios[[i]]$eligible))
}
rm(old,new);invisible(gc())
cat('T2_V3_B3_DISCOVERY_RAM_EQUIVALENCE_PASS\n')
