# Frozen, outcome-blind scenario partition for T3 B3.
# Discovery/held-out use the clean cell plus six non-mixture mechanisms.
# Stress uses two whole mechanisms never supplied to Discovery.
t3_b3_scenario_partition <- function(grid_path='config/T2_V3_B3_prospective_321_grid.csv') {
  if(!file.exists(grid_path)) stop('Prospective Grid321 file is absent: ',grid_path)
  x <- read.csv(grid_path, stringsAsFactors=FALSE)
  required <- c('scenario_id','contamination','mad_scale','mechanism','band')
  if(!identical(sort(names(x)),sort(required)) || nrow(x)!=321L ||
     anyDuplicated(x$scenario_id) || !setequal(x$scenario_id,0:320))
    stop('Invalid committed prospective Grid321')
  stress_mechanisms <- c('mixture_bimodal_near','mixture_bimodal_far')
  x$partition <- ifelse(x$mechanism %in% stress_mechanisms,
                        'stress_exclusive','discovery_support')
  x$partition_reason <- ifelse(x$partition=='stress_exclusive',
    'mechanism_reserved_before_discovery',
    'predeclared_discovery_and_within_support_heldout')
  if(sum(x$partition=='stress_exclusive') != 80L ||
     sum(x$partition=='discovery_support') != 241L ||
     any(x$scenario_id==0L & x$partition!='discovery_support'))
    stop('Unexpected Grid321 mechanism partition')
  x[order(x$scenario_id),]
}

t3_b3_partition_ids <- function(partition=c('discovery_support','stress_exclusive')) {
  partition <- match.arg(partition)
  x <- t3_b3_scenario_partition()
  as.integer(x$scenario_id[x$partition==partition])
}

t3_b3_write_partition_manifest <- function(path) {
  x <- t3_b3_scenario_partition()
  dir.create(dirname(path),recursive=TRUE,showWarnings=FALSE)
  write.csv(x,path,row.names=FALSE)
  invisible(x)
}

# A common label vocabulary.  It describes the relation between a frozen W's
# source family and the independent evaluation environment; it never changes
# a score or decides which model is retained.
t3_b3_transfer_scope <- function(source_family,evaluation_family,stage,mechanism) {
  families<-c('normal','lognormal','weibull','invgauss','exgaussian','exwald')
  if(length(source_family)!=1L||length(evaluation_family)!=1L||
     !source_family%in%families||!evaluation_family%in%families||
     !stage%in%c('discovery','heldout','stress','realworld'))
    stop('Invalid transfer-scope identity')
  mechanism<-as.character(mechanism)
  if(source_family!=evaluation_family)
    return(ifelse(mechanism=='mixture_bimodal_near','cross_family_neighborhood_shift',
      ifelse(mechanism=='mixture_bimodal_far','cross_family_structural_shift',
        'cross_family_transfer')))
  if(stage=='discovery') return(rep('within_family_training_descriptive',length(mechanism)))
  if(stage=='heldout') return(rep('within_family_independent_replication',length(mechanism)))
  if(stage=='stress') return(ifelse(mechanism=='mixture_bimodal_near',
    'within_family_neighborhood_shift','within_family_structural_shift'))
  rep('realworld_profile_matched_transfer',length(mechanism))
}
