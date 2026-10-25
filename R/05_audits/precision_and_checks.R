paired_mcse <- function(sqerr_candidate,sqerr_benchmark) {
  d<-sqerr_candidate-sqerr_benchmark
  c(delta=mean(d),mcse=sd(d)/sqrt(length(d)))
}
bootstrap_index <- function(n,B=ga_config$bootstrap_B,seed=101L) {
  set.seed(seed); matrix(sample.int(n,n*B,replace=TRUE),nrow=n)
}
verify_matrix_equivalence <- function(seed=1L) {
  set.seed(seed);T<-matrix(rnorm(2600),ncol=26)
  W<-matrix(rexp(26*25),nrow=26);W<-normalize_weights(W)
  fast<-evaluate_weights(T,W,mu=.5)$objectives
  slow<-t(vapply(seq_len(ncol(W)),function(i){e<-(drop(T%*%W[,i])-.5)^2;c(mean(e),unname(quantile(e,.95,type=8)))},numeric(2)))
  stopifnot(isTRUE(all.equal(unname(fast),unname(slow),tolerance=1e-12)))
  TRUE
}
