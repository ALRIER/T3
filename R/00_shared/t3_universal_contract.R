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
