# Prospective fixed budgets; settings apply equally to GA and competitors.
ga_config <- list(
 train_n=1000L, heldout_n=c(200L,1000L,3000L),
 contamination_rates=c(0,.01,.05,.10,.20,.30),
 mad_scales=c(1.5,3,4.5,6,9,12,15,20,30),
 contamination_types=c('upper_tail','lower_tail','symmetric_t','point_mass','clustered_upper','clustered_symmetric','mixture_bimodal_near','mixture_bimodal_far'),
 population=150L, generations=80L, seeds=10L,
 discovery_cv_folds=5L, discovery_cv_inner_folds=3L,
 discovery_cv_scheme='scenario_stratified_deterministic_v1',
 discovery_weight_regularization_lambda=0.001,
 discovery_dro_tail_fraction=0.20,
 discovery_stability_bootstrap=500L,
 training_seed_indices=0:9, heldout_seed_index=10L, bootstrap_B=500L,
 patience=10L, early_stop_enabled=TRUE, improvement=.001, training_fraction=.8, batch_size=32L,
 objective_names=c('mse','q95'), fdr_primary=.05, fdr_sensitivity=.10,
 mutation_rate=.15, crossover_probability=.9, evaluation_replicates=500L,
 training_bands=list(clean=0,low=c(.01,.05),intermediate=.10,high=c(.20,.30)),
 external_realworld_target='full_data_mean_proxy'
)

# Prospective v3 partition: immutable master seed roles, with disjoint random streams.
t2_seed_plan_v3 <- list(discovery=0:9,heldout=10:14,stress=15:19,
                        discovery_n=1000L,validation_n=c(200L,1000L,3000L),
                        realworld_n=c(200L,1000L),schema="t2_seed_plan_v3")
t2_assert_seed_plan_v3 <- function(plan=t2_seed_plan_v3) {
 all_indices<-unlist(plan[c("discovery","heldout","stress")],use.names=FALSE)
 stopifnot(identical(sort(as.integer(all_indices)),0:19),
           length(unique(all_indices))==20L,
           identical(as.integer(plan$discovery_n),1000L),
           identical(as.integer(plan$validation_n),c(200L,1000L,3000L)))
 invisible(TRUE)
}
t2_seed_for_v3 <- function(stage,family,index,n,scenario_id=0L,replicate=0L) {
 t2_assert_seed_plan_v3()
 if(!stage%in%c("discovery","heldout","stress")||
    !family%in%c("normal","lognormal","weibull","invgauss","exgaussian","exwald")||
    !index%in%t2_seed_plan_v3[[stage]]) stop("Seed role mismatch")
 if(length(n)!=1L||!is.finite(n)||n<2L)stop("Invalid n")
 # Polynomial rolling hash avoids collisions from simple weighted character sums.
 bytes<-utf8ToInt(paste("v3_real26",stage,family,index,n,scenario_id,replicate,sep=":"))
 h<-104729
 for(b in bytes)h<-(h*131+as.double(b))%%2147483646
 as.integer(h+1)
}

# Prospective stage accessors. Legacy single-heldout-seed references must not be used in V3.
t2_v3_indices <- function(stage) {
 if(!stage %in% c("discovery","heldout","stress")) stop("Unknown V3 seed role")
 as.integer(t2_seed_plan_v3[[stage]])
}
t2_v3_sample_sizes <- function(stage) {
 if(identical(stage,"discovery"))return(as.integer(t2_seed_plan_v3$discovery_n))
 if(stage %in% c("heldout","stress"))return(as.integer(t2_seed_plan_v3$validation_n))
 if(identical(stage,"realworld"))return(as.integer(t2_seed_plan_v3$realworld_n))
 stop("Unknown V3 stage")
}
t2_v3_candidate_roles <- function() c("both","mse","q95")
t2_v3_expected_role_entries <- function() 6L*4L*length(t2_v3_indices("discovery"))*length(t2_v3_candidate_roles())
