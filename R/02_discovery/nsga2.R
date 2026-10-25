# Single-stage NEST26 NSGA-II implementation; all fitness evaluations training-only.
# Objectives: balanced mean MSE and q95 squared error, both minimized.
nsga_fast_sort <- function(O) {
 O<-as.matrix(O); n<-nrow(O); if(!n) stop('empty objective matrix')
 wins<-vector('list',n); losses<-integer(n); ranks<-integer(n); fronts<-list(); first<-integer()
 for(i in seq_len(n)) for(j in seq_len(n)) if(i!=j) {
   if(dominates(O[i,],O[j,])) wins[[i]]<-c(wins[[i]],j)
   else if(dominates(O[j,],O[i,])) losses[i]<-losses[i]+1L
 }
 first<-which(losses==0L); fronts[[1]]<-first; ranks[first]<-1L; k<-1L
 while(length(fronts[[k]])) {
   nxt<-integer()
   for(i in fronts[[k]]) for(j in wins[[i]]) {losses[j]<-losses[j]-1L;if(losses[j]==0L) {ranks[j]<-k+1L;nxt<-c(nxt,j)}}
   if(!length(nxt)) break
   k<-k+1L;fronts[[k]]<-unique(nxt)
 }
 list(fronts=fronts,ranks=ranks)
}
nsga_crowding <- function(O) {
 O<-as.matrix(O);n<-nrow(O);d<-numeric(n);if(n<=2L) return(rep(Inf,n))
 for(j in seq_len(ncol(O))) {ix<-order(O[,j],seq_len(n)); spread<-diff(range(O[,j]));d[ix[c(1,n)]]<-Inf
   if(spread>0) for(k in 2:(n-1L)) d[ix[k]]<-d[ix[k]]+(O[ix[k+1L],j]-O[ix[k-1L],j])/spread
 }
 d
}
nsga_select <- function(O,n_keep) {
 info<-nsga_fast_sort(O);chosen<-integer()
 for(ix in info$fronts) {
   if(length(chosen)+length(ix)<=n_keep) chosen<-c(chosen,ix)
   else {d<-nsga_crowding(O[ix,,drop=FALSE]);chosen<-c(chosen,ix[order(-d,ix)[seq_len(n_keep-length(chosen))]]);break}
 }
 chosen
}
nsga_initial <- function(n,eligible) {
 W<-matrix(rexp(26L*n),nrow=26L);normalize_weights(W,eligible)
}
nsga_offspring <- function(W,n,eligible,mutation_rate=.15,crossover_probability=.9) {
 O<-matrix(0,26L,n);k<-ncol(W)
 for(i in seq_len(n)) {
   a<-sample.int(k,1L);b<-sample.int(k,1L);w<-W[,a]
   if(runif(1)<crossover_probability) {z<-runif(1);w<-z*w+(1-z)*W[,b]}
   if(runif(1)<mutation_rate) {j<-sample(which(eligible),min(3L,sum(eligible)));w[j]<-pmax(0,w[j]+rnorm(length(j),sd=.08))}
   O[,i]<-w
 }
 normalize_weights(O,eligible)
}
# training_scenarios is a list of list(T=R x 26 matrix,target=numeric,
# band=clean/low/intermediate/high,mechanism=string,eligible=logical).
# The same prepared Monte Carlo matrices are reused for every generation.
nsga_evaluate_scenarios <- function(W,training_scenarios,batch_size=32L,lambda=0) {
 if(!length(training_scenarios)) stop('No training scenarios')
 bands<-c('clean','low','intermediate','high'); accum<-matrix(0,ncol(W),2L)
 present<-bands[vapply(bands,function(b)any(vapply(training_scenarios,function(z)
  identical(as.character(z$band),b),logical(1))),logical(1))]
 if(!length(present))stop('No valid bands in CV training partition')
 for(band in present) {
   sc<-training_scenarios[vapply(training_scenarios,function(z)
     identical(as.character(z$band),band),logical(1))]
   if(!length(sc)) stop(paste('Missing training band:',band))
   eligible_keys <- vapply(sc, function(z) paste(as.integer(z$eligible), collapse=''), character(1))
   groups <- split(seq_along(sc), eligible_keys)
   band_values <- lapply(groups, function(ix) {
     eligible <- sc[[ix[1L]]]$eligible
     normalized <- normalize_weights(W, eligible)
     Reduce('+', lapply(ix, function(k) evaluate_weights(sc[[k]]$T, normalized,
       sc[[k]]$target, eligible=eligible, batch_size=batch_size,
       benchmark=sc[[k]]$benchmark, weights_normalized=TRUE)$objectives))/length(ix)
   })
   # Equal within-band scenario weights, equal total weight across four bands.
   # explicit average avoids depending on replicate/sample counts
   band_result<-Reduce('+',Map(function(v,ix) v*(length(ix)/length(sc)), band_values, groups))
   accum<-accum+band_result/length(present)
 }
 if(lambda>0){
  # Same dimensionless regularizer for both objectives after normalization
  pen<-lambda*colSums((normalize_weights(W)-1/26)^2)
  accum<-accum + cbind(pen,pen)
 }
 colnames(accum)<-c('mse','q95');accum
}
nsga_discover <- function(training_scenarios,cfg=ga_config,seed=101L,eligible=rep(TRUE,26L),shard=NULL) {
 set.seed(seed);n<-cfg$population; W<-nsga_initial(n,eligible)
 fitness<-function(w) nsga_evaluate_scenarios(w,training_scenarios,cfg$batch_size,if(is.null(cfg$discovery_weight_regularization_lambda)) 0 else cfg$discovery_weight_regularization_lambda)
 O<-fitness(W);history<-numeric();archiveW<-W;archiveO<-O; best_prior<- -Inf;stale<-0L
 start_g<-1L; last_generation<-0L
 resume<-t2_optimizer_restore(shard,'nsga2',cfg)
 if(!is.null(resume)) {
  st<-resume$state; W<-st$W; O<-st$O; archiveW<-st$archiveW; archiveO<-st$archiveO
  history<-st$history; best_prior<-st$best_prior; stale<-st$stale
  assign('.Random.seed',resume$rng,envir=.GlobalEnv)
  start_g<-as.integer(resume$generation)+1L; last_generation<-as.integer(resume$generation)
 }
 if(start_g<=cfg$generations) for(g in seq.int(start_g,cfg$generations)) {
  last_generation<-g
   sort_info<-nsga_fast_sort(O); ranks<-sort_info$ranks; crowd<-numeric(ncol(W))
   for(ix in sort_info$fronts) crowd[ix]<-nsga_crowding(O[ix,,drop=FALSE])
   # binary tournaments using Pareto ranks + crowding distance
   winner<-function() {ix<-sample.int(ncol(W),2L); if(ranks[ix[1]]<ranks[ix[2]]) return(ix[1]);if(ranks[ix[2]]<ranks[ix[1]])return(ix[2]);if(crowd[ix[1]]>=crowd[ix[2]])ix[1] else ix[2]}
   parents<-W[,replicate(n,winner()),drop=FALSE]
   children<-nsga_offspring(parents,n,eligible,cfg$mutation_rate,cfg$crossover_probability)
   joined<-cbind(W,children);obj<-rbind(O,fitness(children));keep<-nsga_select(obj,n)
   W<-joined[,keep,drop=FALSE];O<-obj[keep,,drop=FALSE]
   archiveW<-cbind(archiveW,children);archiveO<-rbind(archiveO,obj[(n+1L):nrow(obj),,drop=FALSE])
   front<-pareto_front(archiveO);archiveW<-archiveW[,front,drop=FALSE];archiveO<-archiveO[front,,drop=FALSE]
   # bounded convergence proxy (training-only), positive improvement = lower normalized objectives
   indicator<- -min(rowSums(sweep(O,2L,pmax(colMeans(abs(O)),1e-12),'/')))
   history<-c(history,indicator)
   if(indicator>best_prior+cfg$improvement*max(1,abs(best_prior)) || !is.finite(best_prior)) {best_prior<-indicator;stale<-0L} else stale<-stale+1L
   t2_optimizer_save(shard,'nsga2',cfg,g,list(W=W,O=O,archiveW=archiveW,archiveO=archiveO,
     history=history,best_prior=best_prior,stale=stale))
   if(t2_adaptive_stop(history,stale,cfg)) break
 }
 t2_optimizer_save(shard,'nsga2',cfg,last_generation,list(W=W,O=O,archiveW=archiveW,archiveO=archiveO,
   history=history,best_prior=best_prior,stale=stale),force=TRUE)
 list(weights=archiveW,objectives=archiveO,history=history,generations_ran=length(history),seed=seed,stage='training_only')
}
