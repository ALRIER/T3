# T2 prospective training-only domain randomization.
# The validation/test generators are separate: this file MUST NOT load their outcomes.
t2_dr_seed <- function(...) t2_seed(paste("t2_dr_v1", ..., collapse="_"), 17011L)

t2_dr_design <- function(seed, n_scenarios=120L, include_clean=TRUE) {
  stopifnot(length(seed)==1L,is.finite(seed),n_scenarios>=8L)
  set.seed(t2_dr_seed("design",seed))
  mechanisms<-ga_config$contamination_types
  ids<-rep(mechanisms,length.out=n_scenarios)
  ids<-sample(ids,length(ids),replace=FALSE)
  rates<-runif(n_scenarios,.005,.30)
  severities<-exp(runif(n_scenarios,log(1.5),log(30)))
  tab<-data.frame(scenario_id=seq_len(n_scenarios),rate=rates,scale=severities,
                  mechanism=ids,stringsAsFactors=FALSE)
  if(include_clean)tab<-rbind(data.frame(scenario_id=0L,rate=0,scale=NA_real_,
     mechanism="none",stringsAsFactors=FALSE),tab)
  tab
}

t2_dr_family_params <- function(family, seed, strength=.15) {
  stopifnot(strength>=0,strength<=.5)
  set.seed(t2_dr_seed("params",family,seed))
  p<-t2_params(family)
  positive<-intersect(names(p),c("sd","sdlog","shape","scale","mean","sigma",
                                 "tau","lambda","rate"))
  for(k in positive) if(p[[k]]>0) p[[k]]<-p[[k]]*exp(runif(1L,-strength,strength))
  if("meanlog"%in%names(p)) p$meanlog<-p$meanlog+runif(1L,-strength,strength)
  if("mu"%in%names(p)) p$mu<-p$mu+runif(1L,-strength,strength)
  p
}

t2_dr_scenarios <- function(family, seed, n=1000L, R=500L,
                            n_scenarios=120L, strength=.15) {
  stopifnot(family%in%t2_families(),n>=2L,R>=2L)
  params<-t2_dr_family_params(family,seed,strength)
  target<-analytic_mean_from_params(family,params)
  design<-t2_dr_design(seed,n_scenarios)
  set.seed(t2_dr_seed("base",family,seed,n,R))
  base<-vapply(seq_len(R),function(i)generate_population(family,n,params),numeric(n))
  scenarios<-lapply(seq_len(nrow(design)),function(i){
    row<-design[i,,drop=FALSE]
    set.seed(t2_dr_seed("replace",family,seed,i,n,R))
    samples<-lapply(seq_len(R),function(k){
      x<-base[,k]
      if(row$rate>0)x<-inject_outliers_realistic(x,contamination_rate=row$rate,
                               outlier_scale_mad=row$scale,type=row$mechanism)
      x
    })
    list(T=component_matrix(samples),target=target,
      band=if(row$rate==0)"clean" else if(row$rate<=.05)"low" else
           if(row$rate<=.10)"intermediate" else "high",
      scenario_id=row$scenario_id,rate=row$rate,
      scale=row$scale,mechanism=row$mechanism)
  })
  list(scenarios=scenarios,design=design,family=family,params=params,
       target=target,seed=seed,protocol="t2_dr_v1_training_only")
}
