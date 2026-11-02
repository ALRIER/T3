# Paired tournament for frozen evolutionary W*. Each candidate is compared
# only with its frozen own-regime classical benchmark and the sample mean.
t3_pairwise_tournament <- function(unit_scores, stage, unit_col, group_cols,
                                   benchmark_map, alpha=0.05) {
  if (!stage %in% c('heldout','stress','realworld')) stop('Invalid tournament stage')
  required <- unique(c(unit_col,group_cols,'model','mse','q95'))
  if (!is.data.frame(unit_scores)||!all(required%in%names(unit_scores)))
    stop('Tournament unit-score schema is incomplete')
  if (!is.data.frame(benchmark_map)||
      !all(c('source_family','sample_n','own_benchmark')%in%names(benchmark_map)))
    stop('Frozen own-benchmark map is missing')
  if (any(!is.finite(unit_scores$mse))||any(!is.finite(unit_scores$q95)))
    stop('Tournament scores must be finite')
  if (length(ESTIMATOR_NAMES)!=26L||!'mean'%in%ESTIMATOR_NAMES)
    stop('T3 baseline registry must contain 26 estimators including mean')
  if(any(!benchmark_map$own_benchmark%in%setdiff(ESTIMATOR_NAMES,'mean'))||
     anyDuplicated(benchmark_map[c('source_family','sample_n')]))
    stop('Own benchmark must be one frozen non-mean classical estimator per source family/sample size')
  if (!is.finite(alpha)||alpha<=0||alpha>=1) stop('Invalid alpha')
  engine_from_id <- function(x) {
    x<-tolower(as.character(x)); engines<-c('dirichlet','nsga2','de','ga')
    tokens<-strsplit(gsub('[^a-z0-9]+','_',x),'_',fixed=TRUE)[[1L]]
    tokens<-setdiff(tokens,c('normal','lognormal','weibull','invgauss','exgaussian','exwald'))
    z<-engines[engines%in%tokens];if(length(z))z[[1L]] else NA_character_
  }
  unit_scores$candidate_engine<-vapply(unit_scores$model,function(m)
    if(m%in%ESTIMATOR_NAMES)NA_character_ else engine_from_id(m),character(1))
  if(!any(!is.na(unit_scores$candidate_engine)))stop('No frozen evolutionary W* candidates found')
  source_col<-if('source_family'%in%group_cols)'source_family' else if('family'%in%group_cols)'family' else NA_character_
  if(is.na(source_col)||!'sample_n'%in%group_cols)stop('Own benchmark lookup requires source family and sample size')
  key<-c(group_cols,unit_col,'model')
  if(anyDuplicated(unit_scores[key]))stop('Duplicate score per independent unit/model/stratum')
  strata<-unique(unit_scores[group_cols]);results<-list();ri<-0L
  for(s in seq_len(nrow(strata))) {
    keep<-rep(TRUE,nrow(unit_scores))
    for(nm in group_cols)keep<-keep & unit_scores[[nm]]==strata[[nm]][s]
    z<-unit_scores[keep,,drop=FALSE]
    src<-as.character(strata[[source_col]][s]);n<-as.character(strata$sample_n[s])
    bm<-benchmark_map[benchmark_map$source_family==src & as.character(benchmark_map$sample_n)==n,,drop=FALSE]
    if(nrow(bm)!=1L)stop('Missing or duplicate frozen own benchmark for ',src,' n=',n)
    own<-as.character(bm$own_benchmark[1L]);comparators<-unique(c(own,'mean'))
    candidate_ids<-unique(z$model[!is.na(z$candidate_engine)])
    units<-unique(z[[unit_col]])
    for(u in units) {
      have<-as.character(z$model[z[[unit_col]]==u])
      if(!all(comparators%in%have))stop('Evaluation unit lacks own benchmark or mean')
    }
    for(candidate_id in candidate_ids) {
      cand<-z[z$model==candidate_id,c(unit_col,'mse','q95'),drop=FALSE]
      if(nrow(cand)!=length(units))stop('Candidate missing an independent evaluation unit')
      for(benchmark in comparators) {
        ref<-z[z$model==benchmark,c(unit_col,'mse','q95'),drop=FALSE]
        pair<-merge(cand,ref,by=unit_col,suffixes=c('_candidate','_benchmark'),sort=TRUE)
        if(nrow(pair)!=length(units))stop('Candidate/reference pairing is incomplete')
        for(metric in c('mse','q95')) {
          d<-pair[[paste0(metric,'_candidate')]]-pair[[paste0(metric,'_benchmark')]]
          b<-pair[[paste0(metric,'_benchmark')]]
          gain_pct<-100*(b-pair[[paste0(metric,'_candidate')]])/pmax(abs(b),.Machine$double.eps)
          if(length(d)<3L)stop('At least three independent evaluation units are required')
          if(all(d==d[[1L]])){p<-if(d[[1L]]<0)0 else 1;ci<-rep(d[[1L]],2L)} else {
            p<-stats::t.test(d,alternative='less')$p.value
            ci<-stats::t.test(d,conf.level=1-alpha)$conf.int
          }
          gain_ci<-if(all(gain_pct==gain_pct[[1L]]))rep(gain_pct[[1L]],2L) else
            stats::t.test(gain_pct,conf.level=1-alpha)$conf.int
          ri<-ri+1L
          row<-data.frame(stage=stage,candidate_model=candidate_id,
            candidate_engine=engine_from_id(candidate_id),benchmark=benchmark,
            benchmark_role=if(benchmark=='mean')'mean' else 'own_regime_classical',
            metric=metric,independent_units=length(d),difference=mean(d),
            ci_lower=ci[[1L]],ci_upper=ci[[2L]],gain_pct=mean(gain_pct),
            gain_pct_lower=gain_ci[[1L]],gain_pct_upper=gain_ci[[2L]],p_value=p,
            inference_unit=unit_col,ci_method='paired_evaluation_unit_t_interval',
            stringsAsFactors=FALSE)
          for(nm in group_cols)row[[nm]]<-strata[[nm]][s]
          results[[ri]]<-row
        }
      }
    }
  }
  metric_rows<-do.call(rbind,results)
  # BH family: W* x (own benchmark, mean) x MSE/q95 x all transfer strata.
  metric_rows$q_value_global<-stats::p.adjust(metric_rows$p_value,method='BH')
  metric_rows$passes_bh<-metric_rows$q_value_global<=alpha
  ids<-c('stage','candidate_model','candidate_engine','benchmark','benchmark_role',group_cols,
    'independent_units','inference_unit')
  wide<-reshape(metric_rows[,c(ids,'metric','difference','ci_lower','ci_upper','gain_pct',
    'gain_pct_lower','gain_pct_upper','p_value','q_value_global','passes_bh')],
    idvar=ids,timevar='metric',direction='wide')
  if(!all(c('ci_upper.mse','ci_upper.q95','passes_bh.mse','passes_bh.q95')%in%names(wide)))
    stop('Incomplete paired MSE/q95 panel')
  wm<-wide$ci_upper.mse<0;wq<-wide$ci_upper.q95<0
  fm<-wm & wide$passes_bh.mse;fq<-wq & wide$passes_bh.q95
  wide$tier1_joint_mse_q95_bh_fdr<-fm&fq
  wide$tier2_joint_mse_q95_ci<-wm&wq
  wide$tier3_mse_only_bh_fdr<-fm & !wq & wide$difference.q95>=0
  wide$tier3_q95_only_bh_fdr<-fq & !wm & wide$difference.mse>=0
  wide$tier3_mse_only_ci<-wm & !wq & wide$difference.q95>=0
  wide$tier3_q95_only_ci<-wq & !wm & wide$difference.mse>=0
  wide$tier3_pareto_bh_fdr<-wide$tier3_mse_only_bh_fdr|wide$tier3_q95_only_bh_fdr
  wide$tier3_pareto_ci<-wide$tier3_mse_only_ci|wide$tier3_q95_only_ci
  wide$tier4_retained_candidate<-TRUE
  candidate_key<-interaction(wide[c('stage','candidate_model',group_cols)],drop=TRUE,lex.order=TRUE)
  wide$comparators_evaluated<-ave(rep(1L,nrow(wide)),candidate_key,FUN=sum)
  wide$beats_own_and_mean_tier1<-ave(as.integer(wide$tier1_joint_mse_q95_bh_fdr),
    candidate_key,FUN=function(v)as.logical(all(v==1L)))
  wide$beats_own_and_mean_tier2<-ave(as.integer(wide$tier2_joint_mse_q95_ci),
    candidate_key,FUN=function(v)as.logical(all(v==1L)))
  wide$practical_mse<-wide$gain_pct.mse>=ga_config$practical_gain_pct
  wide$practical_q95<-wide$gain_pct.q95>=ga_config$practical_gain_pct
  list(metrics=metric_rows,taxonomy=wide,manifest=data.frame(stage=stage,unit=unit_col,
    comparator_policy='frozen_best_nonmean_classical_by_source_family_sample_size_plus_mean',
    candidate_engines=paste(sort(unique(wide$candidate_engine)),collapse=';'),
    primary_bh_family='all candidate x own benchmark/mean x metric x transfer strata',
    alpha=alpha,ci_method='paired_evaluation_unit_t_interval',
    code_revision=Sys.getenv('GITHUB_SHA','unverified-local'),
    workflow_run_id=Sys.getenv('GITHUB_RUN_ID','local'),stringsAsFactors=FALSE))
}
