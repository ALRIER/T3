# Shared paired-bootstrap pass for MSE and q95; no repeated bootstrap streams.
t2_v3_infer_scenario <- function(sc,models,training_seed,heldout_seed,n,
                                 B=500L,alpha=.05,reference='mean') {
  stopifnot(is.matrix(sc$T),ncol(sc$T)==26L,nrow(sc$T)>=100L,
            B>=30L,alpha>0,alpha<1)
  R<-nrow(sc$T)
  ids<-vapply(models,function(m)m$id,character(1))
  if(anyDuplicated(ids)||!reference%in%ids)stop('Invalid reference/candidate panel')
  E<-vapply(models,function(m)(model_predict(sc$T,m)-sc$target)^2,numeric(R))
  colnames(E)<-ids
  ref_idx<-match(reference,ids)
  # Use a C-backed column quantile implementation when already installed.
  quantile_cols<-function(mat) {
    if(requireNamespace('matrixStats',quietly=TRUE))
      as.numeric(matrixStats::colQuantiles(mat,probs=.95,type=8))
    else apply(mat,2L,stats::quantile,probs=.95,type=8,names=FALSE)
  }
  observed<-list(mse=colMeans(E),q95=quantile_cols(E))
  bootstrap<-list(mse=matrix(NA_real_,B,length(ids)),
                  q95=matrix(NA_real_,B,length(ids)))
  for(b in seq_len(B)){
    ix<-sample.int(R,R,replace=TRUE)
    eb<-E[ix,,drop=FALSE]
    means<-colMeans(eb)
    bootstrap$mse[b,]<-means[ref_idx]-means
    tails<-quantile_cols(eb)
    bootstrap$q95[b,]<-tails[ref_idx]-tails
  }
  results<-lapply(c('mse','q95'),function(metric){
    obs<-observed[[metric]]
    gain<-obs[ref_idx]-obs
    bs<-bootstrap[[metric]]
    limits<-apply(bs,2L,stats::quantile,probs=c(alpha/2,1-alpha/2),
                  names=FALSE,type=8)
    p<-vapply(seq_along(ids),function(j){
      if(j==ref_idx)return(1)
      if(metric=='mse'){
        d<-E[,ref_idx]-E[,j]
        dev<-stats::sd(d)
        if(!is.finite(dev)||dev==0)return(if(mean(d)>0)0 else 1)
        return(stats::pt(-mean(d)/(dev/sqrt(R)),df=R-1L))
      }
      se<-stats::sd(bs[,j])
      if(!is.finite(se)||se==0)return(if(gain[j]>0)0 else 1)
      stats::pnorm(-gain[j]/se)
    },numeric(1))
    data.frame(model=ids,metric=metric,reference=reference,
      gain=as.numeric(gain),
      relative_gain_pct=if(obs[ref_idx]>0)100*gain/obs[ref_idx] else NA_real_,
      ci_lower=as.numeric(limits[1L,]),ci_upper=as.numeric(limits[2L,]),
      reference_loss=obs[ref_idx],candidate_loss=as.numeric(obs),
      bootstrap_null_p=if(metric=='q95')p else NA_real_,p_value=p,
      stringsAsFactors=FALSE)
  })
  z<-do.call(rbind,results)
  z$training_seed<-training_seed;z$heldout_seed<-heldout_seed
  z$sample_n<-n;z$scenario_id<-sc$scenario_id;z$replications<-R
  z
}
t2_v3_adjust_inference <- function(z,alpha=.05) {
  # Family-wise correction over all reported models, metrics and scenarios.
  z$p_holm<-NA_real_
  z$q_BH<-NA_real_
  i<-which(!is.na(z$p_value) & z$model!=z$reference)
  z$p_holm[i]<-stats::p.adjust(z$p_value[i],method='holm')
  z$q_BH[i]<-stats::p.adjust(z$p_value[i],method='BH')
  # Existing T2 taxonomy uses BH-FDR at alpha .05; Holm is additionally
  # reported as a stricter familywise diagnostic, never substituted silently.
  z$confirmed_mse_gain<-z$metric=='mse' & !is.na(z$q_BH) &
    z$q_BH<=alpha & z$gain>0 & z$ci_lower>0
  z$confirmed_q95_gain<-z$metric=='q95' & !is.na(z$q_BH) &
    z$q_BH<=alpha & z$gain>0 & z$ci_lower>0
  z
}

# Paired label-exchangeability calibration under a precisely declared null:
# for each replicate reference/candidate errors are exchangeable. Per metric
# p-values are empirical ranks in the same null world; each simulated world
# is corrected by Holm across *both metrics and all candidate contrasts*.
t2_v3_null_fpr <- function(sc, models, train_seed, eval_seed, Bnull=500L, alpha=.05,reference='median') {
  stopifnot(Bnull>=30L,alpha>0,alpha<1)
  E<-vapply(models,function(m)(model_predict(sc$T,m)-sc$target)^2,numeric(nrow(sc$T)))
  colnames(E)<-vapply(models,function(m)m$id,character(1))
  if(!reference %in%colnames(E))stop('Null reference absent')
  baseline<-E[,reference];ids<-setdiff(colnames(E),reference)
  R<-length(baseline)
  nullstats<-matrix(NA_real_,nrow=Bnull,ncol=length(ids)*2L,
    dimnames=list(NULL,as.vector(rbind(paste0(ids,'_mse'),paste0(ids,'_q95')))))
  for(j in seq_along(ids)){
    e<-E[,ids[j]]
    for(b in seq_len(Bnull)){
      swap<-sample.int(2L,R,replace=TRUE)==1L
      ref<-ifelse(swap,e,baseline)
      alt<-ifelse(swap,baseline,e)
      nullstats[b,2L*j-1L]<-mean(ref)-mean(alt)
      nullstats[b,2L*j]<-as.numeric(stats::quantile(ref,.95,type=8))-
        as.numeric(stats::quantile(alt,.95,type=8))
    }
  }
  # Conservative permutation-rank p-values, including the evaluated world.
  P<-apply(nullstats,2L,function(v) vapply(v,function(x)sum(v>=x)/Bnull,numeric(1)))
  P<-matrix(P,nrow=Bnull,ncol=ncol(nullstats),dimnames=dimnames(nullstats))
  adj<-t(apply(P,1L,stats::p.adjust,method='holm'))
  fwer<-mean(rowSums(adj<=alpha)>0)
  out<-data.frame(model=rep(ids,each=2L),
    metric=rep(c('mse','q95'),length(ids)),reference=reference,
    nominal_alpha=alpha,null_reps=Bnull,
    false_positives=colSums(adj<=alpha),
    empirical_fpr=colMeans(adj<=alpha),
    joint_familywise_fpr=fwer,
    null_method='paired_label_exchangeability_Holm_both_metrics',
    training_seed=train_seed,heldout_seed=eval_seed,
    scenario_id=sc$scenario_id,sample_n=R,stringsAsFactors=FALSE)
  out
}
