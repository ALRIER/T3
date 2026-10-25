# Reproducible training and held-out design, no data-dependent regime assignment.
regime_manifest <- function(cfg=ga_config,seed=42L) {
 x<-partition_regimes(build_contamination_grid(cfg),cfg$training_fraction,seed)
 x$band<-ifelse(x$rate==0,'clean',ifelse(x$rate<=.05,'low',ifelse(x$rate<=.10,'intermediate','high')))
 x$train_n<-cfg$train_n
 x
}
training_weight <- function(manifest) {
 d<-manifest[manifest$partition=='training',,drop=FALSE]
 if(!all(c('clean','low','intermediate','high')%in%d$band))stop('Missing contamination band')
 d$weight<-1/4/as.numeric(table(d$band)[d$band]);d
}
