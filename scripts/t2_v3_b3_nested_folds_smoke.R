#!/usr/bin/env Rscript
# Purely synthetic fixture; never writes to frozen Monte Carlo or Discovery roots.
source('R/02_discovery/t2_v3_b3_nested_folds.R')
tmp<-tempfile('b3cvtest');dir.create(tmp)
t2_v3_block_dir<-function(role,family,seed,n)tmp
for(i in 0:120){
  b<-c('clean','low','intermediate','high')[(i%%4)+1]
  m<-paste0('mechanism', (i%%7)+1)
  saveRDS(list(scenario_id=i,band=b,mechanism=m,
    T=matrix(i,2,2),target=0),
    file.path(tmp,sprintf('scenario_%04d.rds',i)))
}
for(outer in 1:5){
 p<-t2_b3_nested_partitions('normal',0L,outer)
 stopifnot(length(intersect(p$training,p$validation))==0,
   length(union(p$training,p$validation))==121L,
   length(p$validation)%in%c(24L,25L))
 for(inner in 1:3){
  q<-t2_b3_nested_partitions('normal',0L,outer,inner)
  stopifnot(!length(intersect(q$training,q$validation)),
   setequal(union(q$training,q$validation),p$training),
   !length(intersect(q$training,p$validation)),
   !length(intersect(q$validation,p$validation)))
 }
}
a<-t2_b3_nested_partitions('normal',0L,1L)
b<-t2_b3_nested_partitions('normal',0L,1L)
stopifnot(identical(a$outer,b$outer))
unlink(tmp,recursive=TRUE)
cat('T2_B3_STRICT_STRATIFIED_NESTED_5X3_PASS\n')
