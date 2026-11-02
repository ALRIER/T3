# Paired tournament for frozen evolutionary W*. Compare each candidate only
# with the best frozen classical benchmark for its target scenario and mean.
t3_pairwise_tournament <- function(unit_scores,stage,unit_col,group_cols,
                                   benchmark_map,alpha=0.05) {
 if(!stage%in%c('heldout','stress','realworld'))stop('Invalid tournament stage')
 req<-unique(c(unit_col,group_cols,'model','mse','q95'))
 if(!is.data.frame(unit_scores)||!all(req%in%names(unit_scores)))stop('Incomplete unit-score schema')
 map_req<-c('evaluation_family','scenario_id','sample_n','own_benchmark')
 if(!is.data.frame(benchmark_map)||!all(map_req%in%names(benchmark_map)))stop('Scenario benchmark map missing')
 if(any(!is.finite(unit_scores$mse))||any(!is.finite(unit_scores$q95)))stop('Nonfinite tournament scores')
 if(length(ESTIMATOR_NAMES)!=26L||!'mean'%in%ESTIMATOR_NAMES)stop('Invalid 26-classical registry')
 if(any(!benchmark_map$own_benchmark%in%setdiff(ESTIMATOR_NAMES,'mean')))stop('Own reference must be a non-mean classical estimator')
 map_key<-c('evaluation_family','scenario_id','sample_n')
 if(anyDuplicated(benchmark_map[map_key]))stop('Duplicate scenario benchmark-map key')
 if(!is.finite(alpha)||alpha<=0||alpha>=1)stop('Invalid alpha')
 engine_from_id<-function(x){
  x<-tolower(as.character(x));e<-c('dirichlet','nsga2','de','ga')
  tok<-strsplit(gsub('[^a-z0-9]+','_',x),'_',fixed=TRUE)[[1L]]
  tok<-setdiff(tok,c('normal','lognormal','weibull','invgauss','exgaussian','exwald'))
  h<-e[e%in%tok];if(length(h))h[[1L]] else NA_character_
 }
 unit_scores$candidate_engine<-vapply(unit_scores$model,function(m)
   if(m%in%ESTIMATOR_NAMES)NA_character_ else engine_from_id(m),character(1))
 if(!any(!is.na(unit_scores$candidate_engine)))stop('No evolutionary W* candidates')
 eval_col<-if('evaluation_family'%in%group_cols)'evaluation_family' else if('family'%in%group_cols)'family' else NA_character_
 if(is.na(eval_col)||!'scenario_id'%in%group_cols||!'sample_n'%in%group_cols)
   stop('Tournament strata must include target family, scenario_id, and sample_n')
 score_key<-c(group_cols,unit_col,'model')
 if(anyDuplicated(unit_scores[score_key]))stop('Duplicate unit/model score in stratum')
 strata<-unique(unit_scores[group_cols]);rows<-list();ri<-0L
 for(si in seq_len(nrow(strata))){
  keep<-rep(TRUE,nrow(unit_scores))
  for(nm in group_cols)keep<-keep & unit_scores[[nm]]==strata[[nm]][si]
  z<-unit_scores[keep,,drop=FALSE]
  ef<-as.character(strata[[eval_col]][si]);sid<-as.character(strata$scenario_id[si]);n<-as.character(strata$sample_n[si])
  bm<-benchmark_map[benchmark_map$evaluation_family==ef &
    as.character(benchmark_map$scenario_id)==sid & as.character(benchmark_map$sample_n)==n,,drop=FALSE]
  if(nrow(bm)!=1L)stop('Expected one frozen own benchmark for target ',ef,' scenario ',sid,' n=',n)
  cand_ids<-unique(z$model[!is.na(z$candidate_engine)]);units<-unique(z[[unit_col]])
  if(unit_col%in%names(benchmark_map)&&!setequal(as.character(bm[[unit_col]]),as.character(units)))
    stop('Cross-fitted benchmark map does not cover every independent evaluation unit')
  for(u in units){
   have<-as.character(z$model[z[[unit_col]]==u])
   if(!'mean'%in%have)stop('Evaluation unit lacks mean comparator')
   if(!as.character(bm$own_benchmark[1L])%in%have)stop('Evaluation unit lacks frozen own benchmark')
  }
  for(cid in cand_ids){
   cand<-z[z$model==cid,c(unit_col,'mse','q95'),drop=FALSE]
   if(nrow(cand)!=length(units))stop('Candidate lacks an independent evaluation unit')
   for(role in c('own','mean')){
    if(role=='own'){
     mapped<-cand;mapped$own_benchmark<-as.character(bm$own_benchmark[1L])
     ref<-z[z$model==mapped$own_benchmark[1L],c(unit_col,'model','mse','q95'),drop=FALSE]
     pair<-merge(mapped,ref,by.x=c(unit_col,'own_benchmark'),by.y=c(unit_col,'model'),
       suffixes=c('_candidate','_benchmark'),sort=TRUE)
     used<-as.character(bm$own_benchmark[1L])
    } else {
     ref<-z[z$model=='mean',c(unit_col,'mse','q95'),drop=FALSE]
     pair<-merge(cand,ref,by=unit_col,suffixes=c('_candidate','_benchmark'),sort=TRUE)
     benchmark_label<-'mean';used<-'mean'
    }
    if(nrow(pair)!=length(units))stop('Candidate/reference pairing is incomplete')
    for(metric in c('mse','q95')){
     d<-pair[[paste0(metric,'_candidate')]]-pair[[paste0(metric,'_benchmark')]]
     b<-pair[[paste0(metric,'_benchmark')]]
     gain_pct<-100*(b-pair[[paste0(metric,'_candidate')]])/pmax(abs(b),.Machine$double.eps)
     if(length(d)>=3L){
      if(all(d==d[[1L]])){p<-if(d[[1L]]<0)0 else 1;ci<-rep(d[[1L]],2L)} else {
       p<-stats::t.test(d,alternative='less')$p.value;ci<-stats::t.test(d,conf.level=1-alpha)$conf.int
      }
      gain_ci<-if(all(gain_pct==gain_pct[[1L]]))rep(gain_pct[[1L]],2L) else
       stats::t.test(gain_pct,conf.level=1-alpha)$conf.int
     } else {p<-NA_real_;ci<-c(NA_real_,NA_real_);gain_ci<-c(NA_real_,NA_real_)}
     ri<-ri+1L;row<-data.frame(stage=stage,candidate_model=cid,
      candidate_engine=engine_from_id(cid),benchmark=if(role=='mean')'mean' else paste(used,collapse=';'),
      benchmark_role=role,metric=metric,independent_units=length(d),difference=mean(d),
      ci_lower=ci[1L],ci_upper=ci[2L],gain_pct=mean(gain_pct),
      gain_pct_lower=gain_ci[1L],gain_pct_upper=gain_ci[2L],p_value=p,
      inference_unit=unit_col,ci_method='paired_independent_unit_t_interval',
      stringsAsFactors=FALSE)
     for(nm in group_cols)row[[nm]]<-strata[[nm]][si]
     rows[[ri]]<-row
    }
   }
  }
 }
 inf<-do.call(rbind,rows)
 inf$benchmark_family<-as.character(inf[[eval_col]])
 inf$destination_family<-if('evaluation_profile'%in%names(inf))
   as.character(inf$evaluation_profile) else as.character(inf[[eval_col]])
 inf$destination_scenario_id<-as.character(inf$scenario_id)
 inf$destination_profile<-if('evaluation_profile'%in%names(inf))
   as.character(inf$evaluation_profile) else NA_character_
 inf$destination_type<-if('evaluation_profile'%in%names(inf))
   'empirical_profile_match' else 'synthetic_evaluation_family'
 inf$q_value_global<-NA_real_;valid<-is.finite(inf$p_value)
 inf$q_value_global[valid]<-stats::p.adjust(inf$p_value[valid],method='BH')
 inf$passes_bh<-is.finite(inf$q_value_global)&inf$q_value_global<=alpha
 ids<-c('stage','candidate_model','candidate_engine','benchmark','benchmark_role',group_cols,
  'independent_units','inference_unit')
 wide<-reshape(inf[,c(ids,'metric','difference','ci_lower','ci_upper','gain_pct',
  'gain_pct_lower','gain_pct_upper','p_value','q_value_global','passes_bh')],
  idvar=ids,timevar='metric',direction='wide')
 wm<-is.finite(wide$ci_upper.mse)&wide$ci_upper.mse<0
 wq<-is.finite(wide$ci_upper.q95)&wide$ci_upper.q95<0
 fm<-wm&wide$passes_bh.mse;fq<-wq&wide$passes_bh.q95
 wide$tier1_joint_mse_q95_bh_fdr<-fm&fq
 wide$tier2_joint_mse_q95_ci<-wm&wq
 wide$tier3_mse_only_bh_fdr<-fm&!wq&wide$difference.q95>=0
 wide$tier3_q95_only_bh_fdr<-fq&!wm&wide$difference.mse>=0
 wide$tier3_mse_only_ci<-wm&!wq&wide$difference.q95>=0
 wide$tier3_q95_only_ci<-wq&!wm&wide$difference.mse>=0
 wide$tier3_pareto_bh_fdr<-wide$tier3_mse_only_bh_fdr|wide$tier3_q95_only_bh_fdr
 wide$tier3_pareto_ci<-wide$tier3_mse_only_ci|wide$tier3_q95_only_ci
 wide$tier4_retained_candidate<-TRUE
 wide$highest_bh_supported_tier<-ifelse(wide$tier1_joint_mse_q95_bh_fdr,'tier1_joint_mse_q95_bh_fdr',
   ifelse(wide$tier3_pareto_bh_fdr,'tier3_pareto_single_metric_bh_fdr','tier4_retained_no_bh_win'))
 wide$highest_ci_supported_tier<-ifelse(wide$tier2_joint_mse_q95_ci,'tier2_joint_mse_q95_ci',
   ifelse(wide$tier3_pareto_ci,'tier3_pareto_single_metric_ci','tier4_retained_no_joint_ci_win'))
 wide$benchmark_family<-as.character(wide[[eval_col]])
 wide$destination_family<-if('evaluation_profile'%in%names(wide))
   as.character(wide$evaluation_profile) else as.character(wide[[eval_col]])
 wide$destination_scenario_id<-as.character(wide$scenario_id)
 wide$destination_profile<-if('evaluation_profile'%in%names(wide))
   as.character(wide$evaluation_profile) else NA_character_
 wide$destination_type<-if('evaluation_profile'%in%names(wide))
   'empirical_profile_match' else 'synthetic_evaluation_family'
 ck<-interaction(wide[c('stage','candidate_model',group_cols)],drop=TRUE,lex.order=TRUE)
 wide$benchmarks_evaluated<-ave(rep(1L,nrow(wide)),ck,FUN=sum)
 wide$beats_own_and_mean_tier1<-ave(as.integer(wide$tier1_joint_mse_q95_bh_fdr),ck,
   FUN=function(v)as.logical(all(v==1L)))
 wide$beats_own_and_mean_tier2<-ave(as.integer(wide$tier2_joint_mse_q95_ci),ck,
   FUN=function(v)as.logical(all(v==1L)))
 wide$practical_mse<-wide$gain_pct.mse>=ga_config$practical_gain_pct
 wide$practical_q95<-wide$gain_pct.q95>=ga_config$practical_gain_pct
 inf$inference_scope<-if(stage=='realworld'&&unit_col=='realworld_seed')
   'within_dataset_conditional_resampling' else if(stage=='realworld')
   'between_parent_dataset_generalization' else 'independent_evaluation_seed'
 inf$bh_panel_id<-if(stage=='realworld'&&unit_col=='realworld_seed')
   'realworld_within_dataset_conditional_panel' else paste0(stage,'_primary_tournament_panel')
 wide$inference_scope<-unique(inf$inference_scope)
 wide$bh_panel_id<-unique(inf$bh_panel_id)
 list(metrics=inf,taxonomy=wide,manifest=data.frame(stage=stage,unit=unit_col,
  inference_scope=unique(inf$inference_scope),bh_panel_id=unique(inf$bh_panel_id),
  own_benchmark_policy='best_classical_per_target_scenario_frozen_from_independent_data_plus_mean',
  primary_bh_family='candidate x own benchmark/mean x metric x scenario/transfer strata',
  alpha=alpha,ci_method='paired_evaluation_unit_t_interval',
  code_revision=Sys.getenv('GITHUB_SHA','unverified-local'),
  workflow_run_id=Sys.getenv('GITHUB_RUN_ID','local'),stringsAsFactors=FALSE))
}

# Stress scenarios are excluded from Discovery. Freeze the comparator on the
# first five reserved Stress seeds and evaluate W* only on the remaining five.
t3_stress_crossfit_benchmark_map<-function(unit_scores,unit_col='independent_unit'){
 req<-c('evaluation_family','scenario_id','sample_n',unit_col,'model','mse','q95')
 if(!all(req%in%names(unit_scores)))stop('Stress cross-fit benchmark inputs incomplete')
 base<-unit_scores[unit_scores$model%in%ESTIMATOR_NAMES,,drop=FALSE]
 # Cross-family files repeat the same baseline for each source family; collapse
 # those copies before selecting a comparator for the evaluation environment.
 keys<-c('evaluation_family','scenario_id','sample_n',unit_col,'model')
 base<-aggregate(base[c('mse','q95')],base[keys],mean)
 all_units<-sort(unique(as.integer(base[[unit_col]])))
 if(!identical(all_units,as.integer(t2_v3_indices('stress'))))stop('Stress seed set differs from its frozen role')
 calibration<-head(all_units,length(all_units)%/%2L)
 cells<-unique(base[c('evaluation_family','scenario_id','sample_n')]);out<-list();k<-0L
 for(i in seq_len(nrow(cells))){
  c<-cells[i,,drop=FALSE];z<-base[base$evaluation_family==c$evaluation_family &
    base$scenario_id==c$scenario_id & base$sample_n==c$sample_n,,drop=FALSE]
  tr<-z[z[[unit_col]]%in%calibration,,drop=FALSE]
  if(length(unique(tr[[unit_col]]))<3L)stop('Insufficient calibration Stress seeds')
  scales<-aggregate(tr[c('mse','q95')],tr[c(unit_col)],min)
   scale_mse<-mean(scales$mse);scale_q95<-mean(scales$q95)
   av<-aggregate(tr[c('mse','q95')],tr['model'],mean)
   av<-av[av$model!='mean',,drop=FALSE]
   av$score<-.5*(av$mse/scale_mse+av$q95/scale_q95)
   av<-av[order(av$score,match(av$model,ESTIMATOR_NAMES)),,drop=FALSE]
  k<-k+1L;out[[k]]<-data.frame(evaluation_family=c$evaluation_family,
   scenario_id=c$scenario_id,sample_n=c$sample_n,
   own_benchmark=av$model[1L],selection_units=paste(calibration,collapse=';'),
   selection_score=av$score[1L],stringsAsFactors=FALSE)
 }
 do.call(rbind,out)
}
