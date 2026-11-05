#!/usr/bin/env Rscript
# Reconstruct immutable 720-W registry from the actual Discovery RDS artifacts.
args <- commandArgs(trailingOnly=TRUE)
if(length(args)!=2L)stop('Usage: DISCOVERY_ROOT OUTPUT.csv')
root <- normalizePath(args[1L],mustWork=TRUE)
output <- args[2L]
source('R/00_shared/load_all.R');t2_load('.')
files <- list.files(root,'^discovery[.]rds$',recursive=TRUE,full.names=TRUE)
if(length(files)!=180L)stop('Expected 180 individual frozen Discovery RDS, found ',length(files))
families <- c('normal','lognormal','weibull','invgauss','exgaussian','exwald')
engines <- c('ga','nsga2','de','dirichlet')
digest_weights <- function(w) {
 con <- rawConnection(raw(),'wb')
 writeBin(as.double(w),con,size=8L,endian='big')
 bytes <- rawConnectionValue(con);close(con)
 p <- tempfile();writeBin(bytes,p)
 h <- t2_sha256(p);unlink(p);h
}
rows <- vector('list',720L);i <- 0L
for(path in files) {
 parts <- strsplit(normalizePath(path,mustWork=TRUE),.Platform$file.sep,fixed=TRUE)[[1L]]
 family <- parts[length(parts)-3L]
 seed <- as.integer(sub('^seed','',parts[length(parts)-2L]))
 n <- as.integer(sub('^n','',parts[length(parts)-1L]))
 if(!family%in%families||is.na(seed)||!seed%in%0:9||is.na(n)||!n%in%c(200L,1000L,3000L))
  stop('Malformed Discovery input path: ',path)
 fit <- readRDS(path)
 registry_file <- file.path(dirname(path),'frozen_w_registry.csv')
 if(!file.exists(registry_file))stop('Missing frozen_w_registry.csv: ',path)
 registry <- read.csv(registry_file,stringsAsFactors=FALSE)
 if(nrow(registry)!=104L)stop('Expected 4x26 frozen weights: ',registry_file)
 discovered <- Filter(function(x)!is.null(x$weights),fit$models)
 if(length(discovered)!=4L)stop('Expected four selected optimizers: ',path)
 for(engine in engines) {
  indexes <- which(vapply(discovered,function(m)identical(as.character(m$id),engine),logical(1)))
  if(length(indexes)!=1L)stop('Missing/duplicated optimizer: ',engine)
  w <- as.double(discovered[[indexes]]$weights)
  r <- registry[registry$engine==engine,,drop=FALSE]
  r <- r[order(as.integer(r$component)),,drop=FALSE]
  if(length(w)!=26L||nrow(r)!=26L||!identical(as.integer(r$component),1:26)||
   any(!is.finite(w))||any(w<0)||abs(sum(w)-1)>1e-8||
   max(abs(w-as.double(r$weight)))>1e-12)stop('Registry/RDS weight mismatch: ',path,': ',engine)
  i <- i+1L
  rows[[i]]<-data.frame(candidate_id=sprintf('%s|%s|seed%02d|n%d',family,engine,seed,n),
    engine=engine,source_family=family,training_seed=seed,sample_n=n,
    weights_sha256=digest_weights(w),discovery_sha256=t2_sha256(path),
    weight_count=26L,weight_sum=sum(w),stringsAsFactors=FALSE)
 }
 rm(fit,discovered);invisible(gc(FALSE))
}
out <- do.call(rbind,rows)
expected <- expand.grid(source_family=families,engine=engines,training_seed=0:9,
  sample_n=c(200L,1000L,3000L),stringsAsFactors=FALSE)
if(nrow(out)!=720L||anyDuplicated(out$candidate_id)||
 !setequal(with(out,paste(source_family,engine,training_seed,sample_n)),
 with(expected,paste(source_family,engine,training_seed,sample_n))))stop('720-candidate coverage invalid')
dir.create(dirname(output),recursive=TRUE,showWarnings=FALSE)
if(file.exists(output))stop('Never overwrite an existing candidate registry')
write.csv(out,output,row.names=FALSE)
cat('HELDOUT_FROZEN_W_REGISTRY_PASS',nrow(out),'unique_W_hashes',
 length(unique(out$weights_sha256)),'\n')