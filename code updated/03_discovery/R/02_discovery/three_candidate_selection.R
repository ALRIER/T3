# Prespecified selection of three *candidate roles*, never winner labels.
t2_select_three_candidates <- function(weights,objectives) {
 W<-as.matrix(weights);O<-as.matrix(objectives)
 stopifnot(nrow(W)==26L,ncol(W)==nrow(O),ncol(O)==2L,nrow(O)>0L,
           all(is.finite(W)),all(W>=0),all(is.finite(O)),
           all(abs(colSums(W)-1)<1e-7))
 frontier<-pareto_front(O)
 F<-O[frontier,,drop=FALSE]
 # Ideal/nadir normalization of the non-dominated set, predeclared.
 low<-apply(F,2,min); high<-apply(F,2,max)
 Z<-sweep(sweep(F,2,low,"-"),2,pmax(high-low,1e-12),"/")
 role<-c(both=which.min(rowSums(Z^2)),
         mse=which.min(F[,1]),q95=which.min(F[,2]))
 ix<-frontier[role]
 data.frame(role=names(ix),candidate_index=unname(as.integer(ix)),
            mse=O[ix,1],q95=O[ix,2],stringsAsFactors=FALSE)
}
