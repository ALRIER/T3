normalize_weights <- function(W, eligible=rep(TRUE,26L)) {
  W <- as.matrix(W)
  stopifnot(nrow(W)==26L,length(eligible)==26L,any(eligible),all(is.finite(W)),all(W>=0))
  W[!eligible,] <- 0
  s <- colSums(W)
  if(any(s<=0)) stop('Invalid candidate weights')
  sweep(W,2L,s,'/')
}
precompute_benchmarks <- function(T,mu,eligible=rep(TRUE,26L)) {
  E <- (T[,eligible,drop=FALSE]-mu)^2
  list(mse=min(colMeans(E)), q95=min(apply(E,2,quantile,probs=.95,type=8,names=FALSE)))
}
evaluate_weights <- function(T,W,mu,eligible=rep(TRUE,26L),batch_size=32L,benchmark=NULL,
                             weights_normalized=FALSE) {
  if (!isTRUE(weights_normalized)) W <- normalize_weights(W,eligible)
  stopifnot(ncol(T)==26L,all(is.finite(T)),length(mu)==1L)
  if(is.null(benchmark)) benchmark<-precompute_benchmarks(T,mu,eligible)
  ans <- matrix(NA_real_,ncol(W),2,dimnames=list(NULL,c('mse','q95')))
  for(i in seq.int(1L,ncol(W),by=batch_size)) {
    ix<-i:min(ncol(W),i+batch_size-1L)
    e<-(T%*%W[,ix,drop=FALSE]-mu)^2
    ans[ix,1]<-colMeans(e)
    ans[ix,2]<-apply(e,2,quantile,probs=.95,type=8,names=FALSE)
  }
  list(objectives=ans,benchmarks=benchmark)
}
