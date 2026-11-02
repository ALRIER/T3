#!/usr/bin/env Rscript
# Outcome-blind empirical proximity to the six Discovery distribution families.
# This is a family-compatibility descriptor, not a claim about the true DGP.
a <- commandArgs(trailingOnly=TRUE)
if(length(a)!=3L) stop('Usage: CATALOG_ROOT FROZEN_PARENT_CHILD_MANIFEST OUTPUT.csv')
root <- normalizePath(a[1L],mustWork=TRUE)
manifest_path <- a[2L]; output <- a[3L]
if(!file.exists(manifest_path)) stop('Frozen Real-world manifest is missing')
source('R/00_shared/load_all.R'); t2_load('.')
source('R/00_shared/pipeline.R')
tab <- read.csv(manifest_path,stringsAsFactors=FALSE,check.names=FALSE)
need <- c('parent_dataset_id','dataset_id','processed_path','processed_sha256')
if(!all(need%in%names(tab))) stop('Family proximity input schema is incomplete')
tab <- tab[!duplicated(tab$dataset_id),,drop=FALSE]
families <- c('normal','lognormal','weibull','invgauss','exgaussian','exwald')

# Theoretical standardized skewness/excess-kurtosis manifolds. Location and
# scale do not affect these features. Positive-support families are eligible
# only when every observed value is strictly positive.
proto <- list()
add <- function(family,skew,kurt) proto[[length(proto)+1L]] <<-
  data.frame(family=family,skew=as.numeric(skew),kurt=as.numeric(kurt))
add('normal',0,0)
rgrid<-seq(0,.999,length.out=161L);add('exgaussian',2*rgrid^3,6*rgrid^4)
for(s in seq(.03,3,length.out=161L)) {
  v <- exp(s^2)-1
  add('lognormal',sqrt(v)*(exp(s^2)+2),exp(4*s^2)+2*exp(3*s^2)+3*exp(2*s^2)-6)
}
for(k in exp(seq(log(.15),log(20),length.out=161L))) {
  m1<-gamma(1+1/k);m2<-gamma(1+2/k);m3<-gamma(1+3/k);m4<-gamma(1+4/k)
  v<-m2-m1^2
  sk<-(m3-3*m2*m1+2*m1^3)/v^(3/2)
  ku<-(m4-4*m3*m1+6*m2*m1^2-3*m1^4)/v^2-3
  add('weibull',sk,ku)
}
qgrid<-exp(seq(log(1e-4),log(100),length.out=161L))
add('invgauss',3*sqrt(qgrid),15*qgrid)
theta_grid<-exp(seq(log(1e-3),log(30),length.out=40L))
q<-rep(qgrid,each=length(theta_grid));theta<-rep(theta_grid,times=length(qgrid))
k2<-q+theta^2;k3<-3*q^2+2*theta^3;k4<-15*q^3+6*theta^4
add('exwald',k3/k2^(3/2),k4/k2^2)
proto<-do.call(rbind,proto)
proto<-proto[is.finite(proto$skew)&is.finite(proto$kurt),,drop=FALSE]
proto$u<-asinh(proto$skew);proto$v<-asinh(proto$kurt)
family_proto<-split(proto,proto$family)
classify <- function(x) {
  x<-as.numeric(x);x<-x[is.finite(x)]
  if(length(x)<150L)
    return(c(family='unclassified',runner_up='unclassified',confidence='0',margin='0'))
  if(!is.finite(stats::sd(x)))
    return(c(family='unclassified',runner_up='unclassified',confidence='0',margin='0'))
  if(stats::sd(x)==0)
    return(c(family='normal',runner_up='normal',confidence='0',margin='0'))
  s<-stats::sd(x); sk<-mean((x-mean(x))^3)/s^3; ku<-mean((x-mean(x))^4)/s^4-3
  if(!is.finite(sk)||!is.finite(ku)) return(c(family='unclassified',runner_up='unclassified',confidence='0',margin='0'))
  eligible<-if(all(x>0))families else c('normal','exgaussian')
  u<-asinh(sk);v<-asinh(ku)
  by_family<-vapply(eligible,function(f) {
    p<-family_proto[[f]]
    min(((u-p$u)/.5)^2+((v-p$v)/.75)^2)
  },numeric(1))
  by_family<-sort(by_family)
  best<-names(by_family)[1L];second<-if(length(by_family)>1L)names(by_family)[2L] else best
  c(family=best,runner_up=second,confidence='NA',margin=as.character(by_family[2L]-by_family[1L]))
}
B<-99L
out<-vector('list',nrow(tab))
for(i in seq_len(nrow(tab))) {
  p<-as.character(tab$processed_path[i]);if(!grepl('^/',p))p<-file.path(root,p)
  if(!file.exists(p)||!identical(tolower(t2_sha256(p)),tolower(as.character(tab$processed_sha256[i]))))
    stop('Processed child hash mismatch: ',tab$dataset_id[i])
  x<-as.numeric(readRDS(p));x<-x[is.finite(x)]
  point<-classify(x);nboot<-min(length(x),3000L)
  seed<-t2_seed(paste('T3_REALWORLD_FAMILY_PROXIMITY',tab$parent_dataset_id[i],tab$dataset_id[i]),71391L)
  set.seed(seed);picked<-character(B)
  for(b in seq_len(B)) picked[b]<-unname(classify(sample(x,nboot,replace=TRUE))['family'])
  confidence<-mean(picked==unname(point['family']))
  freq<-sort(table(picked),decreasing=TRUE)
  compatible<-names(freq)[as.numeric(freq)/B>=.10]
  if(!length(compatible))compatible<-unname(point['family'])
  status<-if(unname(point['family'])=='unclassified')'unclassified' else
    if(stats::sd(x)==0)'degenerate_nearest_normal_limit' else if(confidence>=.80)'stable' else 'ambiguous'
  out[[i]]<-data.frame(parent_dataset_id=tab$parent_dataset_id[i],dataset_id=tab$dataset_id[i],
    empirical_family_assignment=unname(point['family']),family_assignment_runner_up=unname(point['runner_up']),
    family_assignment_confidence=confidence,family_assignment_margin=as.numeric(point['margin']),
    family_assignment_compatible_set=paste(compatible,collapse=';'),
    family_assignment_status=status,family_assignment_method='nearest_standardized_moment_manifold_bootstrap_v1',
    family_assignment_bootstrap_B=B,family_assignment_seed=seed,stringsAsFactors=FALSE)
  if(i%%100L==0L)cat('REALWORLD_FAMILY_PROFILE_CLASSIFIED',i,'of',nrow(tab),'\n')
}
ans<-do.call(rbind,out)
if(anyDuplicated(ans$dataset_id)||any(!ans$empirical_family_assignment%in%c(families,'unclassified')))
  stop('Invalid or duplicate family proximity assignment')
dir.create(dirname(output),recursive=TRUE,showWarnings=FALSE)
write.csv(ans,output,row.names=FALSE)
cat('T3_REALWORLD_FAMILY_PROXIMITY_PASS',nrow(ans),'children; bootstrap',B,'\n')
