# q95 squared error uncertainty via paired Monte Carlo bootstrap.
# Resampling the SAME replicate indices across model and control preserves pairing.
paired_q95_bootstrap <- function(candidate_se,control_se,B=500L,seed=101L,q=.95) {
 a<-as.numeric(candidate_se);b<-as.numeric(control_se);n<-length(a)
 stopifnot(n==length(b),n>=20L,all(is.finite(a)),all(is.finite(b)),B>=100L)
 set.seed(seed);diff<-numeric(B)
 for(k in seq_len(B)){ ix<-sample.int(n,n,replace=TRUE);diff[k]<-unname(quantile(a[ix],q,type=8)-quantile(b[ix],q,type=8)) }
 point<-unname(quantile(a,q,type=8)-quantile(b,q,type=8))
 ci<-unname(quantile(diff,c(.025,.975),type=8))
 # Percentile CI describes uncertainty; not a general valid null p-value.
 data.frame(metric='q95',difference=point,ci_low=ci[1],ci_high=ci[2],
   bootstrap_B=B,mcse_boot=sd(diff)/sqrt(B),p_value=NA_real_)
}

# Paired randomization test for the q95 loss contrast. Within each replicate,
# candidate/control labels are swapped jointly; this preserves the pairing and
# tests the exchangeability null without treating q95 as a mean statistic.
paired_q95_permutation <- function(candidate_se, control_se, B=1000L,
                                   seed=101L, q=.95) {
 a <- as.numeric(candidate_se); b <- as.numeric(control_se); n <- length(a)
 stopifnot(length(a) == length(b), n >= 20L, all(is.finite(a)),
           all(is.finite(b)), B >= 100L)
 observed <- unname(quantile(a, q, type=8) - quantile(b, q, type=8))
 set.seed(seed); null <- numeric(B)
 for (k in seq_len(B)) {
   swap <- sample(c(FALSE, TRUE), n, replace=TRUE)
   left <- ifelse(swap, b, a); right <- ifelse(swap, a, b)
   null[k] <- unname(quantile(left, q, type=8) - quantile(right, q, type=8))
 }
 p <- (1 + sum(null <= observed)) / (B + 1)
 data.frame(metric='q95', difference=observed, p_value=p,
            permutation_B=B, stringsAsFactors=FALSE)
}
# Inference family includes all prespecified candidate-vs-control hypotheses
# for a given stage and metric. Do not condition the multiplicity family on wins.
stage_fdr_all_models <- function(comparisons,stage,alpha=.05) {
 stopifnot(all(c('model','benchmark','metric','p_value')%in%names(comparisons)))
 comparisons$stage<-stage; comparisons$q_value<-NA_real_
 for(m in unique(comparisons$metric)){i<-which(comparisons$metric==m & is.finite(comparisons$p_value))
  if(length(i))comparisons$q_value[i]<-p.adjust(comparisons$p_value[i],'BH')
 }
 comparisons$confirmed<-is.finite(comparisons$q_value)&comparisons$q_value<=alpha
 comparisons$evidence_type<-if(stage=='discovery')'exploratory' else 'requires_independent_prespecified_test'
 comparisons
}
# Synthetic Monte Carlo observations are independent across replicates; this
# primary MSE test uses paired replicate differences with a one-sided t-test.
model_comparison_table <- function(T,models,target,benchmark_id='mean',stage='heldout',B=500L,seed=101L) {
 ids<-vapply(models,function(x)x$id,character(1)); stopifnot(benchmark_id%in%ids)
 b<-(model_predict(T,models[[match(benchmark_id,ids)]])-target)^2
 rows<-lapply(seq_along(models),function(j){
  a<-(model_predict(T,models[[j]])-target)^2
  d<-a-b; p<-if(ids[j]==benchmark_id) 1 else if(sd(d)==0) {if(mean(d)<0)0 else 1} else t.test(d,alternative='less')$p.value
   q<-paired_q95_bootstrap(a,b,B,seed+j)
   perm_B <- suppressWarnings(as.integer(Sys.getenv('T2_Q95_PERMUTATION_B', unset='250')))
   if (!is.finite(perm_B) || perm_B < 100L) perm_B <- 250L
   qp<-paired_q95_permutation(a,b,perm_B,seed+j)
  data.frame(model=ids[j],benchmark=benchmark_id,metric='mse',
   estimate=mean(a),difference=mean(d),ci_low=if(sd(d)==0)mean(d) else mean(d)-qt(.975,length(d)-1)*sd(d)/sqrt(length(d)),
   ci_high=if(sd(d)==0)mean(d) else mean(d)+qt(.975,length(d)-1)*sd(d)/sqrt(length(d)),p_value=p,
   q95_difference=q$difference,q95_ci_low=q$ci_low,q95_ci_high=q$ci_high,
   q95_p_value=qp$p_value,q95_permutation_B=qp$permutation_B)
 })
 out <- stage_fdr_all_models(do.call(rbind,rows),stage)
 out$q95_q_value <- NA_real_
 ok <- is.finite(out$q95_p_value)
 out$q95_q_value[ok] <- p.adjust(out$q95_p_value[ok], method='BH')
 out$q95_confirmed <- ok & out$q95_q_value <= ga_config$fdr_primary
 out
}
