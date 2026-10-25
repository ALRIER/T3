# Original single-objective genetic algorithm. It is intentionally separate
# from NSGA-II: scalar tournament selection and scalar elitist replacement are
# used, while the same prepared scenarios and evaluation budget are retained.
ga_discover <- function(training_scenarios,cfg=ga_config,seed=101L,eligible=rep(TRUE,26L),shard=NULL) {
 set.seed(seed); n<-cfg$population; W<-nsga_initial(n,eligible)
 fitness<-function(w) nsga_evaluate_scenarios(w,training_scenarios,cfg$batch_size,if(is.null(cfg$discovery_weight_regularization_lambda)) 0 else cfg$discovery_weight_regularization_lambda)
 O<-fitness(W); archiveW<-W; archiveO<-O; history<-numeric(); best<-Inf; stale<-0L
 start_g<-1L; last_generation<-0L
 resume<-t2_optimizer_restore(shard,'ga',cfg)
 if(!is.null(resume)) {
   st<-resume$state
   W<-st$W; O<-st$O; archiveW<-st$archiveW; archiveO<-st$archiveO
   history<-st$history; best<-st$best; stale<-st$stale
   assign('.Random.seed',resume$rng,envir=.GlobalEnv)
   start_g<-as.integer(resume$generation)+1L
   last_generation<-as.integer(resume$generation)
 }
 scalar_score<-function(obj) {
   scale<-pmax(colMeans(abs(obj)),1e-12)
   rowSums(sweep(obj,2L,scale,'/'))
 }
 if(start_g<=cfg$generations) for(g in seq.int(start_g,cfg$generations)) {
   last_generation<-g
   score<-scalar_score(O)
   winner<-function() {ix<-sample.int(ncol(W),2L); if(score[ix[1]]<=score[ix[2]]) ix[1] else ix[2]}
   parents<-W[,replicate(n,winner()),drop=FALSE]
   children<-nsga_offspring(parents,n,eligible,cfg$mutation_rate,cfg$crossover_probability)
   childO<-fitness(children)
   joined<-cbind(W,children); obj<-rbind(O,childO)
   keep<-order(scalar_score(obj),seq_len(nrow(obj)))[seq_len(n)]
   W<-joined[,keep,drop=FALSE]; O<-obj[keep,,drop=FALSE]
   archiveW<-cbind(archiveW,children); archiveO<-rbind(archiveO,childO)
   front<-pareto_front(archiveO); archiveW<-archiveW[,front,drop=FALSE]; archiveO<-archiveO[front,,drop=FALSE]
   indicator<-min(scalar_score(O)); history<-c(history,indicator)
   if(indicator < best - cfg$improvement*max(1,abs(best)) || !is.finite(best)) {best<-indicator;stale<-0L} else stale<-stale+1L
   t2_optimizer_save(shard,'ga',cfg,g,list(W=W,O=O,archiveW=archiveW,archiveO=archiveO,
     history=history,best=best,stale=stale))
   if(t2_adaptive_stop(-history,stale,cfg)) break
 }
 t2_optimizer_save(shard,'ga',cfg,last_generation,list(W=W,O=O,archiveW=archiveW,archiveO=archiveO,
   history=history,best=best,stale=stale),force=TRUE)
 list(weights=archiveW,objectives=archiveO,history=history,generations_ran=length(history),
      seed=seed,stage='training_only',engine='GA-original')
}

# Differential evolution (DE/rand/1/bin) with Pareto environmental selection.
# Identical T matrices and objectives to NSGA-II; no use of held-out data.
de_discover <- function(training_scenarios,cfg=ga_config,seed=101L,eligible=rep(TRUE,26L),F=.6,CR=.9,shard=NULL) {
 set.seed(seed); n<-cfg$population; W<-nsga_initial(n,eligible)
 fitness<-function(w) nsga_evaluate_scenarios(w,training_scenarios,cfg$batch_size,if(is.null(cfg$discovery_weight_regularization_lambda)) 0 else cfg$discovery_weight_regularization_lambda)
 O<-fitness(W);history<-numeric(); archiveW<-W;archiveO<-O; best<- -Inf;stale<-0L
 start_g<-1L; last_generation<-0L
 resume<-t2_optimizer_restore(shard,'de',cfg)
 if(!is.null(resume)) {
  st<-resume$state; W<-st$W; O<-st$O; archiveW<-st$archiveW; archiveO<-st$archiveO
  history<-st$history; best<-st$best; stale<-st$stale
  assign('.Random.seed',resume$rng,envir=.GlobalEnv)
  start_g<-as.integer(resume$generation)+1L; last_generation<-as.integer(resume$generation)
 }
 if(start_g<=cfg$generations) for(g in seq.int(start_g,cfg$generations)) {
  last_generation<-g
  kids<-W
  for(i in seq_len(n)) {
   ids<-sample(setdiff(seq_len(n),i),3L,replace=FALSE)
   mutant<-W[,ids[1]]+F*(W[,ids[2]]-W[,ids[3]])
   mutant<-pmax(0,mutant);mutant[!eligible]<-0
   if(sum(mutant)==0) mutant<-W[,ids[1]]
   choose<-runif(26L)<CR;choose[sample(which(eligible),1L)]<-TRUE
   kids[choose,i]<-mutant[choose]
  }
  kids<-normalize_weights(kids,eligible); childO<-fitness(kids)
  combined<-cbind(W,kids);co<-rbind(O,childO)
  keep<-nsga_select(co,n);W<-combined[,keep,drop=FALSE];O<-co[keep,,drop=FALSE]
  archiveW<-cbind(archiveW,kids);archiveO<-rbind(archiveO,childO)
  front<-pareto_front(archiveO);archiveW<-archiveW[,front,drop=FALSE];archiveO<-archiveO[front,,drop=FALSE]
  indicator<- -min(rowSums(sweep(O,2L,pmax(colMeans(abs(O)),1e-12),'/')))
  history<-c(history,indicator)
  if(!is.finite(best)||indicator>best+cfg$improvement*max(1,abs(best))) {best<-indicator;stale<-0L} else stale<-stale+1L
  t2_optimizer_save(shard,'de',cfg,g,list(W=W,O=O,archiveW=archiveW,archiveO=archiveO,
    history=history,best=best,stale=stale))
  if(t2_adaptive_stop(history,stale,cfg))break
 }
 t2_optimizer_save(shard,'de',cfg,last_generation,list(W=W,O=O,archiveW=archiveW,archiveO=archiveO,
   history=history,best=best,stale=stale),force=TRUE)
 list(weights=archiveW,objectives=archiveO,history=history,generations_ran=length(history),seed=seed,stage='training_only',engine='DE-Pareto')
}
# Random Dirichlet search is a frozen control, not an evolutionary GA.
dirichlet_discover <- function(training_scenarios,cfg=ga_config,seed=101L,eligible=rep(TRUE,26L),n_draws=NULL,alpha=1,shard=NULL) {
 set.seed(seed);if(is.null(n_draws))n_draws<-cfg$population*cfg$generations
 W<-matrix(numeric(),nrow=26L,ncol=0L); O<-matrix(numeric(),nrow=0L,ncol=2L)
 next_draw<-1L; chunk<-max(1L,as.integer(cfg$population))
 resume<-t2_optimizer_restore(shard,'dirichlet',cfg)
 if(!is.null(resume)) {
  W<-resume$state$W; O<-resume$state$O; next_draw<-as.integer(resume$state$next_draw)
  assign('.Random.seed',resume$rng,envir=.GlobalEnv)
 }
 while(next_draw<=n_draws) {
  take<-min(chunk,n_draws-next_draw+1L)
  Wi<-matrix(stats::rgamma(26L*take,shape=alpha),nrow=26L)
  Wi<-normalize_weights(Wi,eligible); Oi<-nsga_evaluate_scenarios(Wi,training_scenarios,cfg$batch_size,if(is.null(cfg$discovery_weight_regularization_lambda)) 0 else cfg$discovery_weight_regularization_lambda)
  W<-cbind(W,Wi); O<-rbind(O,Oi); next_draw<-next_draw+take
  t2_optimizer_save(shard,'dirichlet',cfg,ceiling((next_draw-1L)/chunk),
    list(W=W,O=O,next_draw=next_draw))
 }
 t2_optimizer_save(shard,'dirichlet',cfg,ceiling(n_draws/chunk),list(W=W,O=O,next_draw=next_draw),force=TRUE)
 ix<-pareto_front(O)
 list(weights=W[,ix,drop=FALSE],objectives=O[ix,,drop=FALSE],draws=n_draws,seed=seed,engine='Dirichlet',stage='training_only')
}
