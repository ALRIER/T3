t2_q95_ci_v3 <- function(candidate_errors,reference_errors,B=500L,seed=1L) {
 x<-as.numeric(candidate_errors); y<-as.numeric(reference_errors)
 stopifnot(length(x)==length(y),length(x)>=30L,B>=200L,
           all(is.finite(x)),all(is.finite(y)),all(x>=0),all(y>=0))
 set.seed(seed)
 q<-function(z)unname(stats::quantile(z,.95,type=8))
 boot<-replicate(B,{
  i<-sample.int(length(x),length(x),replace=TRUE)
  c(q(x[i]),q(x[i])-q(y[i]))
 })
 ci<-t(apply(boot,1,stats::quantile,probs=c(.025,.975),type=8))
 list(q95=q(x),q95_lower=ci[1,1],q95_upper=ci[1,2],
      delta=q(x)-q(y),delta_lower=ci[2,1],delta_upper=ci[2,2],
      method="paired_replicate_bootstrap",B=B)
}

# Fixed-weight audit, called only after optimization and candidate freezing.
t2_q95_audit_weights <- function(T,W,target,baseline_col=1L,B=500L,seed=1L) {
 T<-as.matrix(T); W<-as.matrix(W)
 stopifnot(nrow(T)>=30L,ncol(T)==nrow(W),all(is.finite(T)),
           all(is.finite(W)),all(W>=0),all(abs(colSums(W)-1)<1e-8))
 baseline<-(T[,baseline_col]-target)^2
 out<-lapply(seq_len(ncol(W)),function(j) {
   se<-(drop(T%*%W[,j])-target)^2
   ci<-t2_q95_ci_v3(se,baseline,B=B,seed=as.integer((seed+j*7919)%%2147483646+1))
   data.frame(candidate=j,q95=ci$q95,q95_lower=ci$q95_lower,q95_upper=ci$q95_upper,
     q95_delta=ci$delta,q95_delta_lower=ci$delta_lower,q95_delta_upper=ci$delta_upper,
     ci_method=ci$method,bootstrap_B=B)
 })
 do.call(rbind,out)
}
