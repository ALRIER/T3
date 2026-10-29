build_contamination_grid <- function(cfg=ga_config) {
  z <- expand.grid(rate=cfg$contamination_rates[-1],scale=cfg$mad_scales,
                   mechanism=cfg$contamination_types, stringsAsFactors=FALSE)
  z <- rbind(data.frame(rate=0,scale=NA_real_,mechanism='none'),z)
  z$scenario_id <- seq_len(nrow(z))
  stopifnot(nrow(z)==361L)
  z
}
partition_regimes <- function(grid, frac=ga_config$training_fraction, seed=42L) {
  # Independent, prespecified regime-level split. Clean replicate transfer uses fresh seeds.
  set.seed(seed); grid$partition <- 'heldout'
  for (tp in unique(grid$mechanism)) for (rate in unique(grid$rate[grid$mechanism==tp])) {
    ix <- which(grid$mechanism==tp & grid$rate==rate)
    if (length(ix)==1L) {grid$partition[ix] <- 'training'; next}
    grid$partition[sample(ix, max(1L,min(length(ix)-1L,round(length(ix)*frac))))] <- 'training'
  }
  grid
}
