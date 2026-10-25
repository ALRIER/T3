evaluate_frozen <- function(T,weights,target,eligible=rep(TRUE,26L),batch_size=32L) {
  # NO weight updates: invoke only on reserved Monte Carlo replicates and regimes.
  evaluate_weights(T,weights,target,eligible,batch_size)
}
heldout_fdr <- function(p,alpha=.05) {
  # Requires independently computed, valid predeclared p-values.
  q <- p.adjust(p,'BH');data.frame(p=p,q=q,confirmed=q<=alpha)
}


# Post-freeze descriptive q95 uncertainty, paired on the same simulation replicates.
evaluate_frozen_with_q95_ci <- function(T,weights,target,B=500L,seed=1L) {
 W<-normalize_weights(as.matrix(weights))
 point<-evaluate_frozen(T,W,target)
 ci<-t2_q95_audit_weights(T,W,target,B=B,seed=seed)
 list(point=point,q95_uncertainty=ci)
}
