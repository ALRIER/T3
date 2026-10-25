# Versioned, stage-specific prospective Monte Carlo design.
# Disjoint parameter intervals prevent test-set reuse during development.
t2_v3_design <- function(role,family,index,n,n_scenarios=120L) {
 stopifnot(role%in%c("discovery","heldout","stress"),
           index%in%t2_v3_indices(role),family%in%t2_families(),
           n_scenarios>=8L)
 boundaries<-switch(role,
   discovery=list(rate=c(.005,.20),mad=c(1.5,12),perturb=.15),
   heldout=list(rate=c(.005,.30),mad=c(1.5,30),perturb=.22),
   stress=list(rate=c(.305,.40),mad=c(30.5,50),perturb=.30))
 set.seed(t2_seed_for_v3(role,family,index,n,-1L))
 mechanisms<-sample(rep(ga_config$contamination_types,length.out=n_scenarios))
 tab<-data.frame(
   scenario_id=seq_len(n_scenarios),
   rate=runif(n_scenarios,boundaries$rate[1],boundaries$rate[2]),
   scale=exp(runif(n_scenarios,log(boundaries$mad[1]),log(boundaries$mad[2]))),
   mechanism=mechanisms,stringsAsFactors=FALSE)
 if(role=="heldout") {
   # Split confirmatory cases deterministically into interpolation and extrapolation.
   take<-seq_len(n_scenarios)<=floor(n_scenarios/2)
   tab$rate[take]<-runif(sum(take),.005,.20)
   tab$scale[take]<-exp(runif(sum(take),log(1.5),log(12)))
   tab$rate[!take]<-runif(sum(!take),.205,.30)
   tab$scale[!take]<-exp(runif(sum(!take),log(12.5),log(30)))
 }
 tab$domain<-ifelse(tab$rate<=.20,"in_domain","out_of_domain")
 tab<-rbind(data.frame(scenario_id=0L,rate=0,scale=NA_real_,
                       mechanism="none",domain="clean",stringsAsFactors=FALSE),tab)
 stopifnot(nrow(tab)==n_scenarios+1L)
 list(grid=tab,bounds=boundaries,protocol="v3_continuous_role_disjoint")
}
t2_v3_params <- function(role,family,index,n,strength) {
 set.seed(t2_seed_for_v3(role,family,index,n,-2L))
 p<-t2_params(family)
 positive<-intersect(names(p),c("sd","sdlog","shape","scale","mean","sigma","tau","lambda","rate"))
 for(k in positive)if(p[[k]]>0) p[[k]]<-p[[k]]*exp(runif(1L,-strength,strength))
 if("meanlog"%in%names(p))p$meanlog<-p$meanlog+runif(1,-strength,strength)
 if("mu"%in%names(p))p$mu<-p$mu+runif(1,-strength,strength)
 p
}
t2_v3_generate <- function(role,family,index,n,R=500L,n_scenarios=120L,
                           root="artifacts/mc_v3_real26") {
 if(!role%in%c("discovery","heldout","stress")||
    !index%in%t2_v3_indices(role))stop("Unassigned stage seed")
 allowed_n<-if(role=="discovery")1000L else c(200L,1000L,3000L)
 if(!(n%in%allowed_n))stop("Invalid stage sample size")
 if(R<2L||n_scenarios<8L)stop("Invalid simulation size")
 design<-t2_v3_design(role,family,index,n,n_scenarios)
 params<-t2_v3_params(role,family,index,n,design$bounds$perturb)
 target<-analytic_mean_from_params(family,params)
 folder<-file.path(root,"v3_real26_seedplan20_mixedheldout_rlm100",role,family,
                  sprintf("seed%02d",index),sprintf("n%s_r%s",n,R))
 dir.create(folder,recursive=TRUE,showWarnings=FALSE)
 canonical<-file.path(folder,"canonical.rds")
 if(file.exists(canonical)) {
   z<-t2_read_rds(canonical)
   if(!identical(z$protocol,"v3_real26_seedplan20_mixedheldout_rlm100")||
      !identical(z$grid,design$grid)||
      !identical(z$component_names,ESTIMATOR_NAMES))stop("Incompatible checkpoint")
   return(z)
 }
 # Separate parent sample pools across the three mechanism folds, so even
 # the uncontaminated observations in omitted folds are unseen in fitting.
 mechanism_folds<-list(
   c("upper_tail","clustered_upper","point_mass"),
   c("lower_tail","clustered_symmetric","mixture_bimodal_near"),
   c("symmetric_t","mixture_bimodal_far"))
 t2_v3_fold<-function(mechanism) {
   if(mechanism=="none")return(0L)
   k<-which(vapply(mechanism_folds,function(g)mechanism%in%g,logical(1)))
   if(length(k)!=1L)stop("Unassigned contamination mechanism")
   as.integer(k)
 }
 pools<-vector("list",4L)
 for(fold in 0:3) {
   base_file<-file.path(folder,sprintf("base_fold%d.rds",fold))
   if(file.exists(base_file)) {
     base<-t2_read_rds(base_file)
   } else {
     set.seed(t2_seed_for_v3(role,family,index,n,-30L-fold))
     base<-vapply(seq_len(R),function(k)generate_population(family,n,params),numeric(n))
     t2_atomic_save(base,base_file)
   }
   if(!identical(dim(base),c(as.integer(n),as.integer(R))))
     stop("Fold base pool shape mismatch")
   pools[[fold+1L]]<-base
 }
 sc<-vector("list",nrow(design$grid))
 for(i in seq_len(nrow(design$grid))) {
   row<-design$grid[i,,drop=FALSE]
   fold<-t2_v3_fold(row$mechanism)
   base<-pools[[fold+1L]]
   piece<-file.path(folder,sprintf("scenario_%04d.rds",row$scenario_id))
   if(file.exists(piece)) {
     z<-t2_read_rds(piece)
     if(!identical(z$component_names,ESTIMATOR_NAMES)||
        !identical(z$scenario_id,row$scenario_id)||
        !identical(z$rate,row$rate)||!identical(z$scale,row$scale)||
        !identical(z$mechanism,row$mechanism)||!identical(z$domain,row$domain))stop("Scenario checkpoint mismatch")
   } else {
     set.seed(t2_seed_for_v3(role,family,index,n,row$scenario_id))
     samples<-lapply(seq_len(R),function(k){
       x<-base[,k]
       if(row$rate>0) x<-inject_outliers_realistic(x,row$rate,row$scale,row$mechanism)
       x
     })
     audit_path<-file.path(folder,"numeric_warnings.csv")
     options(t2.audit.path=audit_path)
     for(k in seq_along(samples)) {
       options(t2.audit.context=list(stage=role,family=family,seed=index,n=n,
         scenario=row$scenario_id,replicate=k))
       # calculate with context for each replicate rather than an opaque matrix batch
       if(k==1L)T<-matrix(NA_real_,length(samples),N_EST)
       T[k,]<-component_vector(samples[[k]])
     }
     colnames(T)<-ESTIMATOR_NAMES
     options(t2.audit.context=NULL,t2.audit.path=NULL)
     if(!identical(colnames(T),ESTIMATOR_NAMES)||any(!is.finite(T)))
       stop("Invalid revised component matrix")
     z<-list(T=T,target=target,scenario_id=row$scenario_id,
       rate=row$rate,scale=row$scale,mechanism=row$mechanism,
       band=if(row$rate==0)"clean" else if(row$rate<=.05)"low" else
         if(row$rate<=.1)"intermediate" else "high",
       domain=row$domain,fold=fold,component_names=ESTIMATOR_NAMES)
     t2_atomic_save(z,piece)
   }
   sc[[i]]<-z
 }
 out<-list(protocol="v3_real26_seedplan20_mixedheldout_rlm100",role=role,family=family,
           seed_index=as.integer(index),n=as.integer(n),replications=as.integer(R),
           scenarios=sc,grid=design$grid,bounds=design$bounds,
           params=params,target=target,component_names=ESTIMATOR_NAMES)
 t2_atomic_save(out,canonical)
 out
}
