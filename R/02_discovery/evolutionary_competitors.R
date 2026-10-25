# Original single-objective genetic algorithm. It is intentionally separate
# from NSGA-II: scalar tournament selection and scalar elitist replacement are
# used, while the same prepared scenarios and evaluation budget are retained.
ga_discover <- function(training_scenarios,cfg=ga_config,seed=101L,eligible=rep(TRUE,26L),shard=NULL) {
 cfg<-t3_equal_budget_config(cfg);scales<-t3_training_reference_scales(training_scenarios);set.seed(seed); n<-cfg$population; W<-nsga_initial(n,eligible)
 fitness<-function(w) nsga_evaluate_scenarios(w,training_scenarios,cfg$batch_size,if(is.null(cfg$discovery_weight_regularization_lambda)) 0 else cfg$discovery_weight_regularization_lambda,
  dro_fraction=if(is.null(cfg$discovery_dro_tail_fraction)) 0 else cfg$discovery_dro_tail_fraction)
 O<-fitness(W); trace<-list(t3_convergence_point(O,n,scales)); archiveW<-W; archiveO<-O; history<-numeric(); best<-Inf; stale<-0L
 start_g<-1L; last_generation<-0L
 resume<-t2_optimizer_restore(shard,'ga',cfg)
 if(!is.null(resume)) {
   st<-resume$state
   W<-st$W; O<-st$O; archiveW<-st$archiveW; archiveO<-st$archiveO
   history<-st$history; best<-st$best; stale<-st$stale
   trace<-st$trace
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
   trace[[length(trace)+1L]]<-t3_convergence_point(archiveO,n*(g+1L),scales)
   indicator<-min(scalar_score(O)); history<-c(history,indicator)
   if(indicator < best - cfg$improvement*max(1,abs(best)) || !is.finite(best)) {best<-indicator;stale<-0L} else stale<-stale+1L
   t2_optimizer_save(shard,'ga',cfg,g,list(W=W,O=O,archiveW=archiveW,archiveO=archiveO,
     history=history,best=best,stale=stale,trace=trace))
   if(t2_adaptive_stop(-history,stale,cfg)) break
 }
 t2_optimizer_save(shard,'ga',cfg,last_generation,list(W=W,O=O,archiveW=archiveW,archiveO=archiveO,
   history=history,best=best,stale=stale,trace=trace),force=TRUE)
 t3_budget_finalize(list(weights=archiveW,objectives=archiveO,history=history,
      generations_ran=length(history),evaluations_used=n*(1L+length(history)),
      evaluation_steps=n*seq.int(1L,length(history)+1L),convergence=trace,seed=seed,
      stage='training_only',engine='GA-original'),cfg,'ga')
}

# Differential evolution (DE/rand/1/bin) with Pareto environmental selection.
# Identical T matrices and objectives to NSGA-II; no use of held-out data.
de_discover <- function(training_scenarios,cfg=ga_config,seed=101L,eligible=rep(TRUE,26L),F=.6,CR=.9,shard=NULL) {
 cfg<-t3_equal_budget_config(cfg);scales<-t3_training_reference_scales(training_scenarios);set.seed(seed); n<-cfg$population; W<-nsga_initial(n,eligible)
 fitness<-function(w) nsga_evaluate_scenarios(w,training_scenarios,cfg$batch_size,if(is.null(cfg$discovery_weight_regularization_lambda)) 0 else cfg$discovery_weight_regularization_lambda,
  dro_fraction=if(is.null(cfg$discovery_dro_tail_fraction)) 0 else cfg$discovery_dro_tail_fraction)
 O<-fitness(W);trace<-list(t3_convergence_point(O,n,scales));history<-numeric(); archiveW<-W;archiveO<-O; best<- -Inf;stale<-0L
 start_g<-1L; last_generation<-0L
 resume<-t2_optimizer_restore(shard,'de',cfg)
 if(!is.null(resume)) {
  st<-resume$state; W<-st$W; O<-st$O; archiveW<-st$archiveW; archiveO<-st$archiveO
  history<-st$history; best<-st$best; stale<-st$stale
   trace<-st$trace
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
  trace[[length(trace)+1L]]<-t3_convergence_point(archiveO,n*(g+1L),scales)
  indicator<- -min(rowSums(sweep(O,2L,pmax(colMeans(abs(O)),1e-12),'/')))
  history<-c(history,indicator)
  if(!is.finite(best)||indicator>best+cfg$improvement*max(1,abs(best))) {best<-indicator;stale<-0L} else stale<-stale+1L
  t2_optimizer_save(shard,'de',cfg,g,list(W=W,O=O,archiveW=archiveW,archiveO=archiveO,
    history=history,best=best,stale=stale,trace=trace))
  if(t2_adaptive_stop(history,stale,cfg))break
 }
 t2_optimizer_save(shard,'de',cfg,last_generation,list(W=W,O=O,archiveW=archiveW,archiveO=archiveO,
   history=history,best=best,stale=stale,trace=trace),force=TRUE)
 t3_budget_finalize(list(weights=archiveW,objectives=archiveO,history=history,
      generations_ran=length(history),evaluations_used=n*(1L+length(history)),
      evaluation_steps=n*seq.int(1L,length(history)+1L),convergence=trace,seed=seed,
      stage='training_only',engine='DE-Pareto'),cfg,'de')
}
# Random Dirichlet search is a frozen control, not an evolutionary GA.
dirichlet_discover <- function(training_scenarios,cfg=ga_config,seed=101L,eligible=rep(TRUE,26L),n_draws=NULL,alpha=1,shard=NULL) {
 cfg<-t3_equal_budget_config(cfg);scales<-t3_training_reference_scales(training_scenarios);set.seed(seed);if(is.null(n_draws))n_draws<-t3_common_budget(cfg)
 if(n_draws!=t3_common_budget(cfg))stop('Dirichlet budget must equal the common objective budget')
 W<-matrix(numeric(),nrow=26L,ncol=0L); O<-matrix(numeric(),nrow=0L,ncol=2L)
 next_draw<-1L; chunk<-max(1L,as.integer(cfg$population))
 trace<-list();history<-numeric();best<-Inf;stale<-0L
 resume<-t2_optimizer_restore(shard,'dirichlet',cfg)
 if(!is.null(resume)) {
  W<-resume$state$W; O<-resume$state$O; next_draw<-as.integer(resume$state$next_draw)
  trace<-resume$state$trace;history<-resume$state$history
  best<-resume$state$best;stale<-resume$state$stale
  assign('.Random.seed',resume$rng,envir=.GlobalEnv)
 }
 while(next_draw<=n_draws) {
  take<-min(chunk,n_draws-next_draw+1L)
  Wi<-matrix(stats::rgamma(26L*take,shape=alpha),nrow=26L)
  Wi<-normalize_weights(Wi,eligible); Oi<-nsga_evaluate_scenarios(Wi,training_scenarios,cfg$batch_size,if(is.null(cfg$discovery_weight_regularization_lambda)) 0 else cfg$discovery_weight_regularization_lambda,
  dro_fraction=if(is.null(cfg$discovery_dro_tail_fraction)) 0 else cfg$discovery_dro_tail_fraction)
  W<-cbind(W,Wi); O<-rbind(O,Oi); next_draw<-next_draw+take
  trace[[length(trace)+1L]]<-t3_convergence_point(O,next_draw-1L,scales)
  indicator<- -trace[[length(trace)]]['joint_normalized'];history<-c(history,indicator)
  if(!is.finite(best)||-indicator<best-cfg$improvement*max(1,abs(best))) {best<- -indicator;stale<-0L} else stale<-stale+1L
  t2_optimizer_save(shard,'dirichlet',cfg,ceiling((next_draw-1L)/chunk),
    list(W=W,O=O,next_draw=next_draw,trace=trace,history=history,best=best,stale=stale))
  if(t2_adaptive_stop(history,stale,cfg))break
 }
 t2_optimizer_save(shard,'dirichlet',cfg,ceiling(n_draws/chunk),list(W=W,O=O,next_draw=next_draw,trace=trace,history=history,best=best,stale=stale),force=TRUE)
 ix<-pareto_front(O)
 t3_budget_finalize(list(weights=W[,ix,drop=FALSE],objectives=O[ix,,drop=FALSE],
      draws=next_draw-1L,evaluations_used=next_draw-1L,
      evaluation_steps=vapply(trace,function(x)unname(x['evaluations']),numeric(1)),convergence=trace,
      seed=seed,engine='Dirichlet',stage='training_only'),cfg,'dirichlet')
}


# Non-evolutionary baselines kept in the existing Discovery implementation.
# Each objective call evaluates exactly one candidate W on identical scenarios.
t3_project_simplex <- function(x) {
  u<-sort(as.numeric(x),decreasing=TRUE)
  rho<-max(which(u-(cumsum(u)-1)/seq_along(u)>0))
  pmax(x-(sum(u[seq_len(rho)])-1)/rho,0)
}
t3_control_optimize <- function(training_scenarios,cfg=ga_config,seed=101L,
                                method=c('convex_mse','local_deterministic'),
                                eligible=rep(TRUE,26L)) {
  method<-match.arg(method)
  cfg<-t3_equal_budget_config(cfg)
  budget<-t3_common_budget(cfg)
  if(length(eligible)!=26L||!any(eligible))stop('Invalid eligible set')
  active<-which(eligible);k<-length(active)
  set.seed(seed)
  # Convex objective: balanced mean of scenario MSEs; local objective:
  # frozen normalized joint MSE/Q95 policy, trained on the same scenarios.
  scales<-t3_training_reference_scales(training_scenarios)
  evaluate<-function(w) {
    W<-matrix(w,26L,1L)
    as.numeric(nsga_evaluate_scenarios(W,training_scenarios,cfg$batch_size,
      lambda=if(is.null(cfg$discovery_weight_regularization_lambda)) 0 else cfg$discovery_weight_regularization_lambda,
      dro_fraction=if(is.null(cfg$discovery_dro_tail_fraction)) 0 else cfg$discovery_dro_tail_fraction)[1L,])
  }
  reference<-if(method=='convex_mse') function(o)o[1L] else
    function(o)mean(o/as.numeric(scales[c('mse','q95')]))
  w<-numeric(26L);w[active]<-1/k
  start<-proc.time()[['elapsed']]
  obj<-evaluate(w);used<-1L
  best<-reference(obj);trace<-list(c(evaluations=used,mse=obj[1],q95=obj[2]))
  history<-numeric();stale<-0L;step<-0.2
  W<-matrix(w,26L,1L);O<-matrix(obj,nrow=1L,dimnames=list(NULL,c('mse','q95')))
  while(used<budget) {
    prev<-best
    if(method=='convex_mse') {
      # Deterministic projected finite-difference descent for convex MSE.
      # KKT-compatible simplex projection; each finite difference is counted.
      g<-numeric(k);base<-obj[1L]
      for(j in seq_len(k)) {
        if(used>=budget)break
        trial<-w;trial[active[j]]<-trial[active[j]]+1e-5
        trial[active]<-t3_project_simplex(trial[active])
        eo<-evaluate(trial);used<-used+1L
        g[j]<-(eo[1L]-base)/max(sum(abs(trial-w)),1e-12)
      }
      trial<-w;trial[active]<-t3_project_simplex(w[active]-step*g)
      if(used<budget) {
        eo<-evaluate(trial);used<-used+1L
        W<-cbind(W,trial);O<-rbind(O,eo)
        if(reference(eo)<best){w<-trial;obj<-eo;best<-reference(eo)}
      }
    } else {
      # Deterministic simplex coordinate-transfer search; no RNG mutation.
      improved<-FALSE
      for(j in seq_len(k)) {
        if(used>=budget)break
        trial<-w
        from<-active[j];to<-active[(j%%k)+1L]
        delta<-min(step,trial[from])
        trial[from]<-trial[from]-delta;trial[to]<-trial[to]+delta
        eo<-evaluate(trial);used<-used+1L
        W<-cbind(W,trial);O<-rbind(O,eo)
        if(reference(eo)<best){w<-trial;obj<-eo;best<-reference(eo);improved<-TRUE}
      }
      if(!improved)step<-step/2
    }
    stale<-if(best<prev-cfg$improvement*max(1,abs(prev)))0L else stale+1L
    history<-c(history,-best)
    trace[[length(trace)+1L]]<-c(evaluations=used,mse=obj[1],q95=obj[2])
    if(t2_adaptive_stop(history,stale,cfg))break
    if(step<1e-10)break
  }
  # One returned candidate is the best W; selection policy remains common.
  res<-list(weights=matrix(w,ncol=1L),objectives=matrix(obj,nrow=1L,
              dimnames=list(NULL,c('mse','q95'))),
            evaluations_used=used,convergence=trace,
            seed=seed,stage='training_only',engine=method,
            elapsed_seconds=proc.time()[['elapsed']]-start)
  t3_budget_finalize(res,cfg,method)
}
