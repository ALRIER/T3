t2_load <- function(root='.') {
 source(file.path(root,'R/00_shared/runtime_contract.R'),local=.GlobalEnv)
 source(file.path(root,'R/00_shared/artifacts.R'),local=.GlobalEnv)
 files<-c('R/00_shared/config.R','R/00_shared/estimators_26.R','R/00_shared/models.R',
 'R/01_monte_carlo/distributions.R','R/01_monte_carlo/contamination.R','R/01_monte_carlo/scenarios.R','R/01_monte_carlo/empirical_anchoring.R','R/01_monte_carlo/historical_audits.R',
 'R/01_monte_carlo/design.R','R/02_discovery/matrix_fitness.R','R/02_discovery/pareto.R',
 'R/02_discovery/adaptive_stop.R','R/02_discovery/nsga2.R','R/02_discovery/evolutionary_competitors.R','R/02_discovery/three_candidate_selection.R','R/02_discovery/portfolio_three.R','R/03_heldout/frozen_evaluation.R','R/03_heldout/heldout_audit.R',
 'R/04_real_datasets/frozen_realworld.R','R/04_real_datasets/realworld_integrated.R','R/04_real_datasets/dataset_pipeline.R','R/04_real_datasets/realworld_adapter.R',
 'R/04_real_datasets/legacy_realworld_confirmatory.R',
 'R/05_audits/precision_and_checks.R','R/05_audits/shared_inference.R','R/05_audits/hierarchical_taxonomy.R',
 'R/05_audits/q95_ci_v3.R','R/05_audits/stage_inference.R','R/05_audits/q95_and_stage_fdr.R','R/05_audits/stress_runner.R')
 for(f in files)source(file.path(root,f),local=.GlobalEnv)
 confirmatory <- file.path(root, 'R/06_confirmatory/confirmatory.R')
 if (file.exists(confirmatory)) source(confirmatory, local = .GlobalEnv)
 assert_model_registry();invisible(files)
}
