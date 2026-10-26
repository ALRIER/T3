# Adapter for the completed V3 Monte Carlo production archive.
t2_v3_protocol <- function() 't3_b3_grid321_v1'
t2_v3_scientific_root <- function() Sys.getenv('T2_V3_SCIENTIFIC_ROOT', 'artifacts/mc_t3_grid321')
t2_v3_block_dir <- function(role,family,seed,n,reps=500L) {
  if (!role %in% c('discovery','heldout','stress','realworld')) stop('Unknown V3 role')
  if (length(family)!=1L || is.na(family) || !family %in% c('normal','lognormal','weibull','invgauss','exgaussian','exwald')) stop('Unknown V3 family')
  valid <- t2_v3_indices(role)
  if (length(seed)!=1L || is.na(seed) || !seed %in% valid) stop('V3 role/seed mismatch')
  if (!n %in% t2_v3_sample_sizes(role)) stop('V3 role/n mismatch')
  file.path(t2_v3_scientific_root(),t2_v3_protocol(),role,family,
            sprintf('seed%02d',as.integer(seed)),sprintf('n%d_r%d',as.integer(n),as.integer(reps)))
}
t2_v3_prepare_scenario <- function(s) {
  s$eligible <- rep(TRUE,26L)
  s$benchmark <- precompute_benchmarks(s$T,s$target,s$eligible)
  s
}
t3_b3_scenario_metadata <- function(id,grid_path='config/T2_V3_B3_prospective_321_grid.csv') {
  g<-read.csv(grid_path,stringsAsFactors=FALSE)
  if(nrow(g)!=321L||!setequal(g$scenario_id,0:320L))stop('Invalid prospective scenario metadata')
  z<-g[g$scenario_id==as.integer(id),,drop=FALSE]
  if(nrow(z)!=1L)stop('Scenario metadata absent')
  z
}
t2_v3_validate_scenario <- function(s, id, reps=500L) {
  if (!is.list(s) || !identical(as.integer(s$scenario_id),as.integer(id)) ||
      !is.matrix(s$T) || !is.numeric(s$T) ||
      !identical(dim(s$T),c(as.integer(reps),26L)) ||
      any(!is.finite(s$T)) ||
      !identical(colnames(s$T),ESTIMATOR_NAMES) ||
      !identical(s$component_names,ESTIMATOR_NAMES) ||
      !is.numeric(s$target) || length(s$target)!=1L || !is.finite(s$target))
    stop('V3 scientific scenario contract mismatch: ',id)
  invisible(TRUE)
}
t2_v3_read_block <- function(role,family,seed,n,reps=500L,selected=NULL) {
  root <- t2_v3_block_dir(role,family,seed,n,reps)
  path <- file.path(root,'canonical.rds')
  if (!file.exists(path)) stop('V3 canonical input missing: ',path)
  z <- t2_read_rds(path)
  if (!identical(z$protocol,t2_v3_protocol()) ||
      !identical(z$role,role) || !identical(z$family,family) ||
      !identical(as.integer(z$seed_index),as.integer(seed)) ||
      !identical(as.integer(z$n),as.integer(n)) ||
      !identical(as.integer(z$replications),as.integer(reps)) ||
      !identical(z$component_names,ESTIMATOR_NAMES) ||
      !is.data.frame(z$grid) || nrow(z$grid)!=321L ||
      !identical(as.integer(z$grid$scenario_id),0:320) ||
      length(z$scenarios)!=321L) stop('V3 canonical provenance mismatch')
  ids <- vapply(z$scenarios,function(s) as.integer(s$scenario_id),integer(1))
  if (!identical(ids,0:320)) stop('V3 scenario order mismatch')
  if (is.null(selected)) selected <- ids
  if (anyDuplicated(selected) || !all(selected %in% ids)) stop('V3 selected IDs mismatch')
  for (id in selected) t2_v3_validate_scenario(z$scenarios[[match(id,ids)]],id,reps)
  z$scenarios <- lapply(z$scenarios[match(selected,ids)],t2_v3_prepare_scenario)
  z
}
t2_v3_read_scenario <- function(role,family,seed,n,id,reps=500L) {
  root <- t2_v3_block_dir(role,family,seed,n,reps)
  p <- file.path(root,sprintf('scenario_%04d.rds',as.integer(id)))
  if (!file.exists(p)) stop('Missing V3 scientific scenario: ',p)
  s <- t2_read_rds(p)
  t2_v3_validate_scenario(s,id,reps)
  meta<-t3_b3_scenario_metadata(id)
  for(key in c('contamination','mad_scale','mechanism','band'))s[[key]]<-meta[[key]][1L]
  t2_v3_prepare_scenario(s)
}


# Integrated scientific validation: T3 B3
# T3 B3 standalone, versioned cross-stage exchange envelope.
# A stage may run separately and publish its own envelope. Consumers validate inputs.
t3_contract_version <- function() "t3_b3_universal_v1"
t3_stage_names <- function() c("montecarlo","discovery","heldout","stress","realworld")
t3_contract_new <- function(stage, experiment_id, payload, provenance,
                            parent_ids=character(), schema="t3_b3_grid321_v1") {
  if(length(stage)!=1L || !stage %in% t3_stage_names())stop("Unknown stage")
  if(length(experiment_id)!=1L || is.na(experiment_id) ||
     !grepl("^[A-Za-z0-9][A-Za-z0-9_.-]+$",experiment_id))
    stop("Invalid experiment id")
  if(!is.list(payload)||!is.list(provenance))stop("Invalid stage payload/provenance")
  mandatory<-c("family","seed","sample_n","replications","code_revision")
  if(!all(mandatory %in% names(provenance)))stop("Missing provenance field")
  if(!is.character(parent_ids)||anyNA(parent_ids)||anyDuplicated(parent_ids))
    stop("Invalid parent IDs")
  x<-list(contract_version=t3_contract_version(),schema=schema,
          experiment_id=experiment_id,stage=stage,artifact_id=paste(experiment_id,stage,
            provenance$family,provenance$seed,provenance$sample_n,sep="__"),
          parent_ids=parent_ids,provenance=provenance,payload=payload)
  t3_contract_validate(x,stage,experiment_id)
  x
}
t3_contract_validate <- function(x,stage=NULL,experiment_id=NULL) {
  if(!is.list(x)||!identical(x$contract_version,t3_contract_version())||
     !identical(x$schema,"t3_b3_grid321_v1")||
     !is.character(x$artifact_id)||length(x$artifact_id)!=1L||
     !x$stage %in% t3_stage_names()||!is.list(x$payload)||
     !is.list(x$provenance))stop("Unknown or invalid T3 contract")
  if(!is.null(stage)&&!identical(x$stage,stage))stop("Stage mismatch")
  if(!is.null(experiment_id)&&!identical(x$experiment_id,experiment_id))
    stop("Experiment mismatch")
  p<-x$provenance
  # A stage artifact must identify a seed reserved for its own role.
  role<-if(x$stage=="montecarlo") {
    if(is.null(p$seed_role))stop("Monte Carlo requires an explicit downstream seed_role")
    as.character(p$seed_role)
  } else x$stage
  if(!role%in%c("discovery","heldout","stress","realworld")||
     length(p$seed)!=1L||is.na(p$seed)||
     !as.integer(p$seed)%in%t2_v3_indices(role))
    stop("Cross-stage seed leakage or invalid role")
  if(!all(c("family","seed","sample_n","replications","code_revision")%in%names(p))||
     any(vapply(p[c("family","code_revision")],function(y)
       length(y)!=1L||is.na(y)||!nzchar(as.character(y)),logical(1)))||
     any(!is.finite(as.numeric(unlist(p[c("seed","sample_n","replications")]))))||
     p$sample_n<1||p$replications<1)stop("Invalid scientific provenance")
  if(!is.null(x$payload$scenario_ids)) {
    ids<-x$payload$scenario_ids
    if(!is.numeric(ids)||anyNA(ids)||anyDuplicated(ids)||
       any(ids<0)||any(ids>320)||any(ids!=as.integer(ids)))
      stop("Invalid 321-design scenario IDs")
  }
  if(!is.null(x$payload$weights)) {
    W<-as.matrix(x$payload$weights)
    if(nrow(W)!=26L||any(!is.finite(W))||any(W<0)||
       any(abs(colSums(W)-1)>1e-8))stop("Invalid 26-component W")
  }
  invisible(TRUE)
}
t3_contract_write <- function(x,path) {
  t3_contract_validate(x)
  if(file.exists(path))stop("Refuse overwriting immutable stage artifact")
  dir.create(dirname(path),recursive=TRUE,showWarnings=FALSE)
  tmp<-tempfile(tmpdir=dirname(path))
  on.exit(unlink(tmp),add=TRUE)
  saveRDS(x,tmp,version=3)
  if(!file.rename(tmp,path))stop("Atomic artifact publication failed")
  invisible(path)
}
t3_contract_read <- function(path,stage=NULL,experiment_id=NULL) {
  if(!file.exists(path))stop("Stage input missing; standalone stage remains independently runnable")
  x<-readRDS(path)
  t3_contract_validate(x,stage,experiment_id)
  x
}
t3_contract_consume <- function(path,required_stage,experiment_id,
                                expected_family=NULL,expected_n=NULL,
                                expected_revision=NULL) {
  x<-t3_contract_read(path,required_stage,experiment_id)
  if(!is.null(expected_family)&&!identical(x$provenance$family,expected_family))
    stop("Family mismatch")
  if(!is.null(expected_n)&&!identical(as.integer(x$provenance$sample_n),as.integer(expected_n)))
    stop("Sample n mismatch")
  if(!is.null(expected_revision)&&!identical(x$provenance$code_revision,expected_revision))
    stop("Code revision mismatch")
  x
}

# Strict per-stage artifact emission; immutable stage provenance.
t3_stage_publish <- function(stage,experiment_id,payload,family,seed,n,reps,
                             path,parents=character(),seed_role=NULL) {
  role<-if(stage=="montecarlo")seed_role else stage
  if(length(role)!=1L||!role%in%c("discovery","heldout","stress","realworld"))
    stop("Stage seed role required")
  if(!seed%in%t2_v3_indices(role))stop("Seed belongs to another stage")
  provenance<-list(family=family,seed=as.integer(seed),sample_n=as.integer(n),
     replications=as.integer(reps),
     code_revision=Sys.getenv("GITHUB_SHA","unverified-local"),
     seed_role=role,seed_plan="B3_40_DISJOINT_V1")
  envelope<-t3_contract_new(stage,experiment_id,payload,provenance,parents)
  t3_contract_write(envelope,path)
}
t3_stage_require <- function(path,stage,experiment_id,family,seed,n) {
  x<-t3_contract_consume(path,stage,experiment_id,
                         expected_family=family,expected_n=n)
  role<-if(stage=="montecarlo")x$provenance$seed_role else stage
  if(!identical(as.integer(x$provenance$seed),as.integer(seed))||
     !seed%in%t2_v3_indices(role)||
     !identical(x$provenance$seed_plan,"B3_40_DISJOINT_V1"))
    stop("Cross-stage artifact/seed-plan provenance mismatch")
  x
}
