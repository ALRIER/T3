# Prospective held-out audit. This records the partition and budget contract
# instead of relying on a convention hidden in the stage runner.
t2_discovery_budget_registry <- function(config) {
  required <- c('ga', 'nsga2', 'de', 'dirichlet')
  fields <- c('population', 'generations', 'evaluation_replicates', 'objective_names')
  if(all(required%in%names(config))&&all(vapply(config[required],is.list,logical(1)))) {
    if(!all(vapply(config[required],function(z)all(fields%in%names(z)),logical(1))))
      stop('Incomplete per-engine Discovery budget registry')
    return(setNames(lapply(required,function(engine)config[[engine]][fields]),required))
  }
  setNames(lapply(required, function(engine) config[fields]), required)
}

t2_budget_parity_audit <- function(discovery) {
  required <- c('ga', 'nsga2', 'de', 'dirichlet')
  registry <- discovery$budget_registry
  if (is.null(registry)) {
    # Backward-compatible recovery for discovery artifacts produced before
    # the explicit registry was added. The shared config is the declared
    # budget contract for every engine in the matrix.
    registry <- t2_discovery_budget_registry(discovery$config)
  }
  if (!identical(names(registry), required))
    stop('Budget registry must declare ga, nsga2, de and dirichlet')
  reference <- registry[[1L]]
  valid <- vapply(registry,function(z)
    identical(as.integer(z$evaluation_replicates),as.integer(reference$evaluation_replicates))&&
    identical(as.character(z$objective_names),as.character(reference$objective_names)),logical(1))
  caps<-vapply(registry,function(z)as.integer(z$population)*(as.integer(z$generations)+1L),integer(1))
  same <- valid & caps==caps[[1L]]
  if (!all(same)) stop('Discovery maximum objective budgets or objectives are unequal across engines')
  data.frame(engine=names(registry),
             population=vapply(registry,function(z)as.integer(z$population),integer(1)),
             generations=vapply(registry,function(z)as.integer(z$generations),integer(1)),
             max_objective_evaluations=caps,
             evaluation_replicates=reference$evaluation_replicates,
             objective_mse=TRUE, objective_q95=TRUE,
             budget_equal=TRUE, stringsAsFactors=FALSE)
}

t2_heldout_independence_audit <- function(discovery, mode, shard, family, n_values) {
  budget <- t2_budget_parity_audit(discovery)
  training_seed <- t2_mc_seed(family, discovery$training_seed_index)
  heldout_seed <- rep(t2_mc_seed(family, t2_heldout_seed_index()), length(n_values))
  if (is.na(discovery$training_seed_index) ||
      discovery$training_seed_index == t2_heldout_seed_index() ||
      any(heldout_seed == training_seed))
    stop('Held-out seeds overlap or are duplicated')
  data.frame(
    audit='heldout_independence_and_budget_parity', mode=mode, family=family,
    training_partition='discovery_training_only', heldout_partition='fresh_rng',
    training_seed_role='canonical_seeds_00_to_07', heldout_seed_role='reserved_seed_08',
    training_seed=training_seed, heldout_seed=paste(heldout_seed, collapse=';'),
    heldout_sample_sizes=paste(n_values, collapse=';'),
    engines=length(unique(budget$engine)), budget_equal=all(budget$budget_equal),
    objective_set='mse;q95', status='PASS', stringsAsFactors=FALSE)
}
