dominates <- function(a,b) all(a<=b) && any(a<b)
pareto_front <- function(O) {
  O<-as.matrix(O); stopifnot(all(is.finite(O)), ncol(O) >= 1L)
  if (ncol(O) != 2L) {
    return(which(vapply(seq_len(nrow(O)),function(i)
      !any(vapply(setdiff(seq_len(nrow(O)),i),function(j) dominates(O[j,],O[i,]),logical(1))),logical(1))))
  }
  # Exact O(n log n) frontier for two minimization objectives. Equal-objective
  # duplicates are retained, matching the previous all-pairs definition.
  ord <- order(O[,1L], O[,2L], seq_len(nrow(O)))
  keep <- logical(nrow(O)); best_second <- Inf; i <- 1L
  while (i <= nrow(O)) {
    j <- i
    while (j < nrow(O) && O[ord[j+1L],1L] == O[ord[i],1L]) j <- j + 1L
    vals <- O[ord[i:j],2L]; m <- min(vals)
    if (m < best_second) {
      keep[ord[i:j][vals == m]] <- TRUE
      best_second <- m
    }
    i <- j + 1L
  }
  which(keep)
}
bh_training_diagnostic <- function(p) {
  # Exploratory only: training selection and testing share data.
  p.adjust(p,method='BH')
}
