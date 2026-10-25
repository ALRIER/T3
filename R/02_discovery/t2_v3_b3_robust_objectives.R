t2_b3_weight_penalty <- function(W,lambda=0) {
 W<-as.matrix(W)
 stopifnot(nrow(W)==26L,all(is.finite(W)),all(W>=0),lambda>=0)
 lambda*colSums((W-1/26)^2)
}
t2_b3_dro <- function(losses,tail_fraction=.2) {
 losses<-as.matrix(losses)
 stopifnot(all(is.finite(losses)),tail_fraction>0,tail_fraction<=1)
 count<-max(1L,ceiling(nrow(losses)*tail_fraction))
 apply(losses,2L,function(x)mean(sort(x,decreasing=TRUE)[seq_len(count)]))
}
