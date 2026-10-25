# T3 prospectively frozen 321-condition grid, shared across all stages.
t2_v3_design <- function(role,family,index,n,n_scenarios=320L) {
 stopifnot(role%in%c("discovery","heldout","stress","realworld"),
   index%in%t2_v3_indices(role),family%in%t2_families(),
   identical(as.integer(n_scenarios),320L))
 path<-"config/T2_V3_B3_prospective_321_grid.csv"
 if(!file.exists(path)) stop("T3 321-grid manifest missing: ",path)
 tab<-read.csv(path,stringsAsFactors=FALSE)
 if(nrow(tab)!=321L||!identical(as.integer(tab$scenario_id),0:320L)||
    anyDuplicated(tab$scenario_id)) stop("T3 manifest contract mismatch")
 tab$rate<-as.numeric(tab$contamination)
 tab$scale<-as.numeric(tab$mad_scale)
 tab$scale[tab$scenario_id==0L]<-NA_real_
 tab$mechanism[tab$scenario_id==0L]<-"none"
 tab$domain<-ifelse(tab$rate==0,"clean",
     ifelse(tab$rate<=.20,"in_domain","out_of_domain"))
 # Other stages use disjoint simulated samples and RNG streams, even when
 # their evaluation regime labels match the prospective design grid.
 boundaries<-switch(role,
   discovery=list(rate=c(0,.30),mad=c(1.5,30),perturb=.15),
   heldout=list(rate=c(0,.30),mad=c(1.5,30),perturb=.22),
   stress=list(rate=c(0,.30),mad=c(1.5,30),perturb=.30),
   realworld=list(rate=c(0,.30),mad=c(1.5,30),perturb=.30))
 list(grid=tab,bounds=boundaries,protocol="t3_b3_grid321_v1")
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
t2_v3_generate <- function(role,family,index,n,R=500L,n_scenarios=320L,
                           root="artifacts/mc_t3_grid321") {
 if(!role%in%c("discovery","heldout","stress","realworld")||
    !index%in%t2_v3_indices(role))stop("Unassigned stage seed")
 allowed_n<-t2_v3_sample_sizes(role)
 if(!(n%in%allowed_n))stop("Invalid stage sample size")
 if(R<2L||n_scenarios<8L)stop("Invalid simulation size")
 design<-t2_v3_design(role,family,index,n,n_scenarios)
 params<-t2_v3_params(role,family,index,n,design$bounds$perturb)
 target<-analytic_mean_from_params(family,params)
 folder<-file.path(root,"t3_b3_grid321_v1",role,family,
                  sprintf("seed%02d",index),sprintf("n%s_r%s",n,R))
 dir.create(folder,recursive=TRUE,showWarnings=FALSE)
 canonical<-file.path(folder,"canonical.rds")
 if(file.exists(canonical)) {
   z<-t2_read_rds(canonical)
   if(!identical(z$protocol,"t3_b3_grid321_v1")||
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
       band=as.character(row$band),mad_scale=as.numeric(row$scale),
       contamination=as.numeric(row$rate),
       domain=row$domain,fold=fold,component_names=ESTIMATOR_NAMES)
     t2_atomic_save(z,piece)
   }
   sc[[i]]<-z
 }
 out<-list(protocol="t3_b3_grid321_v1",role=role,family=family,
           seed_index=as.integer(index),n=as.integer(n),replications=as.integer(R),
           scenarios=sc,grid=design$grid,bounds=design$bounds,
           params=params,target=target,component_names=ESTIMATOR_NAMES)
 t2_atomic_save(out,canonical)
 out
}
