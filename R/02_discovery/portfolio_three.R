t2_portfolio_roles <- function() c("mse","q95","both")
t2_portfolio_write <- function(root, role, ids, W, metadata) {
 if(!role %in% t2_portfolio_roles())stop("Invalid role")
 stopifnot(is.matrix(W),nrow(W)==26L,ncol(W)==length(ids),
           identical(rownames(W),ESTIMATOR_NAMES),
           all(is.finite(W)),all(W>=0),all(abs(colSums(W)-1)<1e-7),
           !anyDuplicated(ids))
 path<-file.path(root,role)
 dir.create(path,recursive=TRUE,showWarnings=FALSE)
 target<-file.path(path,"portfolio.rds")
 if(file.exists(target))stop("Frozen portfolio already exists")
 saveRDS(list(schema="t2_three_portfolios_v1",role=role,ids=ids,
              weights=W,components=ESTIMATOR_NAMES,metadata=metadata,
              status="unconfirmed_candidates"),target)
 invisible(target)
}
t2_portfolio_read <- function(root,role) {
 if(!role %in% t2_portfolio_roles())stop("Invalid role")
 x<-readRDS(file.path(root,role,"portfolio.rds"))
 if(!identical(x$schema,"t2_three_portfolios_v1") ||
    !identical(x$role,role) || !identical(x$components,ESTIMATOR_NAMES) ||
    !identical(rownames(x$weights),ESTIMATOR_NAMES) ||
    !identical(x$status,"unconfirmed_candidates") ||
    nrow(x$weights)!=26L || ncol(x$weights)!=length(x$ids) ||
    any(!is.finite(x$weights)) || any(x$weights<0) ||
    any(abs(colSums(x$weights)-1)>1e-7))stop("Incompatible frozen portfolio")
 x
}
t2_portfolio_score <- function(T,root,target) {
 stopifnot(is.matrix(T),identical(colnames(T),ESTIMATOR_NAMES),
           all(is.finite(T)),length(target)==1L,is.finite(target))
 p<-lapply(t2_portfolio_roles(),function(role)t2_portfolio_read(root,role))
 W<-do.call(cbind,lapply(p,function(x)x$weights))
 # Shared multiplication; no duplicate fitted-model scoring.
 key<-apply(signif(W,14),2,paste,collapse=",")
 ix<-match(key,unique(key));uniqueW<-W[,!duplicated(key),drop=FALSE]
 E<-(sweep(T%*%uniqueW,1L,target,"-"))^2
 mse<-colMeans(E);q95<-apply(E,2,stats::quantile,probs=.95,type=8,names=FALSE)
 out<-data.frame(role=rep(t2_portfolio_roles(),lengths(lapply(p,function(x)x$ids))),
                 model_id=unlist(lapply(p,function(x)x$ids),use.names=FALSE),
                 mse=mse[ix],q95=q95[ix],stringsAsFactors=FALSE)
 list(by_role=split(out,out$role),n_unique=ncol(uniqueW),
      n_role_entries=ncol(W))
}
