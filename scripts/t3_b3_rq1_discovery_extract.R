#!/usr/bin/env Rscript
# Export training-only scores and immutable optimizer accounting from restored
# original Discovery RDS. Never refit, retune, or change frozen candidates.
a<-commandArgs(trailingOnly=TRUE)
if(length(a)!=3L)stop("Usage: INPUT_DISCOVERY_DIR N OUTPUT_DIR")
root<-a[[1L]];n<-as.integer(a[[2L]]);out<-a[[3L]]
if(!n%in%c(200L,1000L,3000L))stop("Wrong Discovery sample size")
methods<-c("ga","nsga2","de","dirichlet")
families<-c("normal","lognormal","weibull","invgauss","exgaussian","exwald")
engine<-function(x) {
 tok<-strsplit(gsub("[^a-z0-9]+","_",tolower(as.character(x))),"_",fixed=TRUE)[[1L]]
 m<-methods[methods%in%tok]
 if(length(m))m[[1L]] else NA_character_
}
files<-list.files(root,"^discovery[.]rds$",recursive=TRUE,full.names=TRUE)
if(length(files)!=60L)stop("Expected 60 original RDS for one sample size, found ",length(files))
score_parts<-list();cost_parts<-list();controls<-list();keys<-character()
for(path in files) {
 components<-strsplit(normalizePath(path,mustWork=TRUE),.Platform$file.sep,fixed=TRUE)[[1L]]
 ix<-grep("^seed[0-9]{2}$",components)
 if(length(ix)!=1L||ix<2L||ix+2L!=length(components)||
    components[[ix+1L]]!=paste0("n",n))stop("Bad Discovery fit location: ",path)
 family<-components[[ix-1L]];seed<-as.integer(sub("^seed","",components[[ix]]))
 if(!family%in%families||!seed%in%0:9)stop("Unexpected frozen Discovery identity")
 keys<-c(keys,paste(family,seed,n,sep="|"))
 fit<-readRDS(path);z<-fit$training_control_comparison
 if(!is.data.frame(z)||!all(c("model","scenario_id","mse","q95")%in%names(z)))
    stop("Frozen training score panel missing: ",path)
 if(any(!is.finite(z$mse))||any(!is.finite(z$q95)))stop("Nonfinite training scores")
 eng<-vapply(z$model,engine,character(1))
 for(method in methods) {
   d<-z[!is.na(eng)&eng==method,c("scenario_id","mse","q95"),drop=FALSE]
   if(nrow(d)<241L)stop("Missing evolutionary training scores: ",method," ",path)
   d<-aggregate(d[c("mse","q95")],d["scenario_id"],mean)
   if(nrow(d)!=241L||anyDuplicated(d$scenario_id))stop("Incomplete frozen training catalogue: ",path)
   score_parts[[length(score_parts)+1L]]<-data.frame(family=family,sample_n=n,
      training_seed=seed,method=method,d,stringsAsFactors=FALSE)
   e<-fit$engines[[method]]
   if(is.null(e)||length(e$evaluations_used)!=1L||
      length(e$evaluation_budget)!=1L)stop("Missing immutable search cost information")
   used<-as.integer(e$evaluations_used);budget<-as.integer(e$evaluation_budget)
   if(!is.finite(used)||!is.finite(budget)||used<1L||used>budget)
      stop("Invalid actual optimizer evaluations for ",method)
   models<-Filter(function(q)!is.null(q$weights)&&identical(q$id,method),fit$models)
   if(length(models)!=1L)stop("Original selected W vector missing: ",method)
   w<-as.numeric(models[[1L]]$weights)
   if(length(w)!=26L||any(!is.finite(w))||any(w< -1e-10)||abs(sum(w)-1)>1e-7)
      stop("Invalid original simplex vector: ",path)
   w<-pmax(0,w);w<-w/sum(w)
   cost_parts[[length(cost_parts)+1L]]<-data.frame(
      family=family,sample_n=n,training_seed=seed,method=method,
      actual_evaluations=used,evaluation_budget=budget,
      evaluation_fraction=used/budget,top_component_weight=max(w),
      effective_component_count=1/sum(w*w),weight_entropy=-sum(w[w>0]*log(w[w>0])),
      stringsAsFactors=FALSE)
 }
 sel<-z[z$model%in%c("convex_mse","local_deterministic"),
        c("scenario_id","model","mse","q95"),drop=FALSE]
 if(nrow(sel)>0L) {
   sel<-aggregate(sel[c("mse","q95")],sel[c("scenario_id","model")],mean)
   controls[[length(controls)+1L]]<-data.frame(family=family,sample_n=n,
     training_seed=seed,sel,scope="training_only_not_independent",stringsAsFactors=FALSE)
 }
 rm(fit,z);invisible(gc(FALSE))
}
if(anyDuplicated(keys)||length(keys)!=60L)stop("Frozen training identities duplicated")
scores<-do.call(rbind,score_parts);costs<-do.call(rbind,cost_parts)
if(nrow(scores)!=60L*4L*241L||nrow(costs)!=60L*4L)stop("Frozen RQ1 export count mismatch")
if(length(controls)) det<-do.call(rbind,controls) else det<-data.frame(
   family=character(),sample_n=integer(),training_seed=integer(),
   scenario_id=integer(),model=character(),mse=numeric(),q95=numeric(),
   scope=character(),stringsAsFactors=FALSE)
dir.create(out,recursive=TRUE,showWarnings=FALSE)
write_gzip<-function(z,path) {
 con<-gzfile(path,"wt");on.exit(close(con));write.csv(z,con,row.names=FALSE)
}
write_gzip(scores,file.path(out,"training_method_scores.csv.gz"))
write_gzip(det,file.path(out,"training_deterministic_controls.csv.gz"))
write.csv(costs,file.path(out,"training_optimizer_costs.csv"),row.names=FALSE)
writeLines(c("Discovery scores and deterministic controls are training-only.",
 "Original RDS restored from repository backup: no frozen weights changed.",
 "Do not claim independent optimizer superiority from Discovery ranks.",
 "Evaluation-count comparisons exclude wall-clock and hyperparameter tuning."),
 file.path(out,"SCOPE.txt"))
cat("R1_DISCOVERY_EXPORT_PASS",n,nrow(scores),nrow(costs),nrow(det),"\n")
