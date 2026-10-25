t2_path <- function(shard,stage)file.path(t2_output_root(),shard,stage,'results',paste0(stage,'.rds'))
t2_seed <- function(shard,offset=0L) {
 a<-utf8ToInt(shard); as.integer((sum(a*seq_along(a))+offset)%%2000000000L+1L)
}
t2_families <- function()c('normal','lognormal','weibull','invgauss','exgaussian','exwald')
t2_training_seed_indices <- function() as.integer(ga_config$training_seed_indices)
t2_heldout_seed_index <- function() as.integer(ga_config$heldout_seed_index)
t2_mc_seed <- function(family, seed_index) {
  t2_seed(sprintf('mc_%s_seed%02d', family, as.integer(seed_index)), 100L)
}
t2_mc_scenario_seed <- function(family, seed_index, scenario_id, shard=NULL) {
  key <- if (is.null(shard)) sprintf('mc_%s_seed%02d_scenario%04d', family,
                                     as.integer(seed_index), as.integer(scenario_id)) else
    sprintf('mc_%s_scenario%04d', shard, as.integer(scenario_id))
  t2_seed(key, 200L)
}
t2_mc_version <- function() 'v2_shared_base_crn'
t2_mc_workers <- function() {
  x<-as.integer(Sys.getenv('T2_MC_WORKERS',unset='1'))
  if(!is.finite(x)||x<1L)stop('T2_MC_WORKERS must be a positive integer')
  if(.Platform$OS.type!='unix')1L else x
}
t2_mc_root <- function() Sys.getenv('T2_CANONICAL_MC_ROOT', unset='artifacts/mc_canonical')
t2_shared_shard <- function() {
  x <- Sys.getenv('T2_SHARED_SHARD', unset='')
  if (!nzchar(x)) NULL else x
}
t2_dependency_path <- function(shard, stage) {
  local <- t2_path(shard, stage)
  if (file.exists(local)) return(local)
  shared <- t2_shared_shard()
  if (!is.null(shared)) {
    candidate <- t2_path(shared, stage)
    if (file.exists(candidate)) return(candidate)
  }
  local
}
t2_mc_path <- function(mode, family, seed_index, n, replications) {
  file.path(t2_mc_root(), t2_mc_version(), mode, family, sprintf('seed%02d', as.integer(seed_index)),
            sprintf('n%s_r%s.rds', as.integer(n), as.integer(replications)))
}
t2_params <- function(family) switch(family,
 normal=list(mean=0,sd=1),lognormal=list(meanlog=0,sdlog=.65),
 weibull=list(shape=2,scale=1),invgauss=list(mean=1,shape=3),
 exgaussian=list(mu=0,sigma=1,tau=1),exwald=list(mu=1,lambda=3,rate=1),stop('family'))
t2_make_scenarios <- function(mode,shard,n,replications,family='normal',seed_index=NULL) {
 cfg<-ga_config; grid<-build_contamination_grid(cfg)
 if(mode=='smoke')grid<-grid[c(1L,2L,which(grid$rate==.1)[1],which(grid$rate==.2)[1]),]
 bands<-ifelse(grid$rate==0,'clean',ifelse(grid$rate<=.05,'low',ifelse(grid$rate<=.1,'intermediate','high')))
  seed<-if(is.null(seed_index)) t2_seed(shard,100L) else t2_mc_seed(family, seed_index)
  params<-t2_params(family);target<-analytic_mean_from_params(family,params)
  set.seed(seed)
  base_samples<-vapply(seq_len(replications),function(k)generate_population(family,n,params),numeric(n))
  sc<-lapply(seq_len(nrow(grid)),function(j)
    t2_mc_generate_one(family,n,replications,grid[j,,drop=FALSE],target,base_samples,
                       if(is.null(seed_index))NULL else seed_index,shard))
 list(scenarios=sc,grid=grid,seed=seed,family=family,n=n,replications=replications,
      seed_index=if(is.null(seed_index)) NA_integer_ else as.integer(seed_index),
      role=if(is.null(seed_index)) 'legacy_local' else
        if(as.integer(seed_index)==t2_heldout_seed_index()) 'heldout' else 'training')
}
t2_mc_checkpoint_paths <- function(path) {
  list(root=paste0(path, '.parts'), progress=paste0(path, '.progress.rds'))
}
t2_mc_generate_one <- function(family, n, replications, row, target, base_samples,
                                seed_index=NULL, shard=NULL) {
  if (!is.matrix(base_samples) || nrow(base_samples)!=n || ncol(base_samples)!=replications)
    stop('Invalid canonical Monte Carlo base sample pool')
  if (row$rate > 0) set.seed(t2_mc_scenario_seed(family, seed_index, row$scenario_id, shard))
  samples<-vector('list',replications)
  for(k in seq_len(replications)) {
    x<-base_samples[,k]
    if(row$rate>0)x<-inject_outliers_realistic(x,contamination_rate=row$rate,
                                                outlier_scale_mad=row$scale,type=row$mechanism)
    samples[[k]]<-x
  }
  Tmat<-component_matrix(samples);eligible<-rep(TRUE,26L)
  list(T=Tmat,target=target,benchmark=precompute_benchmarks(Tmat,target,eligible),
       band=ifelse(row$rate==0,'clean',
       ifelse(row$rate<=.05,'low',ifelse(row$rate<=.1,'intermediate','high'))),
       eligible=eligible,scenario_id=row$scenario_id,rate=row$rate,mechanism=row$mechanism)
}
t2_canonical_mc <- function(mode, family, seed_index, n, replications) {
  if (!family %in% t2_families()) stop('Unknown Monte Carlo family')
  path <- t2_mc_path(mode, family, seed_index, n, replications)
  if (file.exists(path)) {
    out <- t2_read_rds(path)
    expected <- c(family=family, n=as.character(n), replications=as.character(replications),
                  seed_index=as.character(seed_index))
    got <- c(family=out$family, n=as.character(out$n), replications=as.character(out$replications),
             seed_index=as.character(out$seed_index))
    if (!identical(unname(got), unname(expected))) stop('Canonical Monte Carlo provenance mismatch')
    return(out)
  }
  cfg<-ga_config; grid<-build_contamination_grid(cfg)
  if(mode=='smoke')grid<-grid[c(1L,2L,which(grid$rate==.1)[1],which(grid$rate==.2)[1]),]
  cp<-t2_mc_checkpoint_paths(path)
  dir.create(cp$root, recursive=TRUE, showWarnings=FALSE)
  target<-analytic_mean_from_params(family,t2_params(family))
  base_path<-file.path(cp$root,'base_samples.rds')
  if (file.exists(base_path)) {
    base_samples<-t2_read_rds(base_path)
  } else {
    set.seed(t2_mc_seed(family,seed_index))
    params<-t2_params(family)
    base_samples<-vapply(seq_len(replications),function(k)generate_population(family,n,params),numeric(n))
    t2_atomic_save(base_samples,base_path)
  }
  progress<-NULL
  if(file.exists(cp$progress)) {
    progress<-t2_read_rds(cp$progress)
    expected<-list(mode=mode,family=family,seed_index=as.integer(seed_index),n=as.integer(n),
                   replications=as.integer(replications),grid=grid,
                   mc_version=t2_mc_version(),base_seed=t2_mc_seed(family,seed_index))
    if(!identical(progress[c('mode','family','seed_index','n','replications','grid',
                             'mc_version','base_seed')],expected))
      stop('Canonical Monte Carlo checkpoint provenance mismatch')
  } else {
    progress<-list(mode=mode,family=family,seed_index=as.integer(seed_index),n=as.integer(n),
                   replications=as.integer(replications),grid=grid,completed=integer(),
                   mc_version=t2_mc_version(),base_seed=t2_mc_seed(family,seed_index))
    t2_atomic_save(progress,cp$progress)
  }
  completed<-sort(unique(as.integer(progress$completed)))
  if (length(completed)) {
    part_paths<-file.path(cp$root,sprintf('scenario_%04d.rds',completed))
    if (any(!file.exists(part_paths))) stop('Canonical Monte Carlo checkpoint is incomplete')
  }
  todo<-setdiff(seq_len(nrow(grid)),completed)
  workers<-min(t2_mc_workers(),length(todo))
  batches<-if(!length(todo))list() else split(todo,ceiling(seq_along(todo)/workers))
  for(batch in batches) {
    parts<-if(workers>1L) parallel::mclapply(batch,function(j)
      t2_mc_generate_one(family,n,replications,grid[j,,drop=FALSE],target,base_samples,seed_index),
      mc.cores=length(batch),mc.preschedule=FALSE) else
      lapply(batch,function(j)t2_mc_generate_one(family,n,replications,grid[j,,drop=FALSE],
                                                  target,base_samples,seed_index))
    for(i in seq_along(batch)) {
      j<-batch[i];t2_atomic_save(parts[[i]],file.path(cp$root,sprintf('scenario_%04d.rds',j)))
      completed<-sort(c(completed,j));progress$completed<-completed
      t2_atomic_save(progress,cp$progress)
    }
  }
  sc<-lapply(seq_len(nrow(grid)),function(j)
    t2_read_rds(file.path(cp$root,sprintf('scenario_%04d.rds',j))))
  out <- list(scenarios=sc,grid=grid,seed=t2_mc_seed(family,seed_index),family=family,
              n=n,replications=replications,seed_index=as.integer(seed_index),
              role=if(as.integer(seed_index)==t2_heldout_seed_index()) 'heldout' else 'training',
              mc_version=t2_mc_version(),base_pool_reused=TRUE,
              scenario_seed_scheme='family_seed_scenario_id')
  out$canonical_id <- sprintf('%s_seed%02d_n%s_r%s', family, as.integer(seed_index), n, replications)
  out$generated_once <- TRUE
  t2_atomic_save(out, path)
  out
}
t2_models <- function(d) {
 mods<-reference_model_set()
 for(engine in names(d)) {
  result<-d[[engine]]; ix<-which.min(rowSums(sweep(result$objectives,2,pmax(colMeans(abs(result$objectives)),1e-12),'/')))
  mods[[length(mods)+1L]]<-new_frozen_model(engine,weights=result$weights[,ix],family=engine)
 }
 mods
}
t2_require <- function(shard,stage) {
 path<-t2_dependency_path(shard,stage)
 if(!file.exists(path))stop(paste('Required stage missing:',stage,'for',shard))
 t2_read_rds(path)
}
t2_inference <- function(T,models,target,stage,seed) {
 model_comparison_table(T,models,target,benchmark_id='mean',stage=stage,B=ga_config$bootstrap_B,seed=seed)
}
t2_precheck <- function(shard, stage, mode) {
 required <- switch(stage, montecarlo=c('datasets','mc_validation'),
   discovery=c('datasets','mc_validation','montecarlo'),
   heldout=c('discovery'),realworld=c('datasets','discovery'),
   stress=c('discovery'),aggregate=c('mc_validation','heldout','realworld','stress'), character())
 for (name in required) {
  previous <- t2_require(shard,name)
  if (!identical(previous$provenance$mode,mode)) stop(paste('Mode mismatch for dependency',name))
  if (name %in% c('datasets','mc_validation') && !identical(previous$status,'PASS'))
   stop(paste('Hard gate not passed:',name))
 }
 invisible(TRUE)
}
t2_run_datasets <- function(mode,shard) {
 manifest <- file.path('config','public_datasets.csv')
 if (!file.exists(manifest)) stop('Frozen public dataset manifest is missing')
 tab <- read.csv(manifest,stringsAsFactors=FALSE)
 if (!all(c('dataset_id','path','sha256','license') %in% names(tab))) stop('Incomplete dataset manifest')
 if (!nrow(tab)) stop('No datasets registered; cannot pass')
 if (mode=='full' && any(grepl('fixture|nonredistributable|review|pending|unknown',tab$license,ignore.case=TRUE)))
   stop('Full runs require reviewed redistributable public inputs')
 if (any(!nzchar(tab$license))) stop('Dataset license not documented')
 if (any(!file.exists(tab$path))) stop('Dataset cache is incomplete')
 hashes <- unname(tools::md5sum(tab$path))
 if (anyNA(hashes)) stop('Cannot calculate dataset digests')
 if (requireNamespace('digest',quietly=TRUE)) {
  actual <- vapply(tab$path,digest::digest,character(1),algo='sha256',file=TRUE)
 } else {
  actual <- vapply(tab$path,function(f) {
   z<-suppressWarnings(system2('sha256sum',shQuote(f),stdout=TRUE))
   if(length(z)!=1L)stop('SHA256 unavailable');strsplit(z,' ')[[1]][1]
  },character(1))
 }
 if (any(tolower(actual)!=tolower(tab$sha256))) stop('Dataset integrity mismatch')
 list(status='PASS',manifest=tab,sha256=actual,fixture=identical(mode,'smoke'))
}
t2_run_mc_validation <- function(mode,shard) {
 d<-t2_require(shard,'datasets')
 if(!identical(d$status,'PASS'))stop('Datasets did not pass')
 seed<-t2_seed(shard,730L);set.seed(seed)
 n <- if(mode=='smoke') 1500L else 20000L
 x<-generate_population('normal',n,t2_params('normal'))
 l1 <- is.finite(mean(x)) && abs(mean(x)) < 5/sqrt(n) &&
       abs(sd(x)-1) < 5/sqrt(2*n)
 contaminated<-inject_outliers_realistic(x,contamination_rate=.2,outlier_scale_mad=9,type='upper_tail')
 l2 <- length(contaminated)==n && all(is.finite(contaminated)) &&
       abs(mean(contaminated)-mean(x))>1e-3
 m <- if(mode=='smoke') 120L else 1500L
 z<-replicate(m,{a<-rnorm(200);c(mean(a)^2,median(a)^2)})
 l3 <- mean(z[1,]) < mean(z[2,])
 l4 <- nrow(d$manifest)>=1L && all(file.exists(d$manifest$path))
 results<-data.frame(layer=c('L1_interface','L2_interface','L3_interface','L4_manifest'),
                    status=ifelse(c(l1,l2,l3,l4),'PASS','FAIL'),
                    stringsAsFactors=FALSE)
 audits <- t2_run_integrated_mc_audits(mode, shard)
 results <- rbind(results, audits$summary)
 overall<-if(all(results$status=='PASS')) 'PASS' else 'FAIL'
  anchor <- t2_run_mc_empirical_anchoring(mode, shard)
  if (mode == 'full' && !identical(anchor$status, 'PASS')) overall <- 'FAIL'
  if (mode == 'smoke' && identical(anchor$status, 'SKIPPED')) overall <-
    if (audits$status == 'PASS' && all(results$status == 'PASS')) 'PASS' else 'FAIL'
  list(status=overall, layers=results, empirical_anchor=anchor$status,
       empirical_manifest=anchor$manifest,
       results=c(audits$results, list(empirical_anchor=if (!is.null(anchor$results)) anchor$results else
                      data.frame(status=anchor$status, reason=anchor$reason))),
       seed=seed, scientific_scope=if(mode=='smoke')
   'Integrated historical audit smoke plus interface checks; empirical anchoring is not executed in smoke' else
   'Integrated historical audits plus empirical shape anchoring; final real-world validation remains separate',
   integrated_historical_audits=audits$status,
   legacy_four_layer_certified=isTRUE(mode == 'full' && audits$status == 'PASS' && anchor$status == 'PASS'))
}
t2_run_discovery <- function(data,mode,shard,engine='all'){
 if(is.null(data$scenarios)) {
   if(is.null(data$family)||is.null(data$seed_index)||is.null(data$n)||is.null(data$replications))
     stop('Monte Carlo reference is incomplete')
   data<-t2_canonical_mc(mode,data$family,data$seed_index,data$n,data$replications)
 }
 cfg<-ga_config
 if(mode=='smoke'){cfg$population<-8L;cfg$generations<-2L;cfg$patience<-2L;cfg$bootstrap_B<-100L}
 s<-data$scenarios
 dispatch <- list(
   ga=function() ga_discover(s,cfg,t2_seed(shard,201),shard=shard),
   nsga2=function() nsga_discover(s,cfg,t2_seed(shard,202),shard=shard),
   de=function() de_discover(s,cfg,t2_seed(shard,203),shard=shard),
   dirichlet=function() dirichlet_discover(s,cfg,t2_seed(shard,204),n_draws=cfg$population*(cfg$generations+1L),shard=shard)
 )
 selected <- if (engine == 'all') names(dispatch) else engine
 if (!all(selected %in% names(dispatch))) stop('Unknown discovery engine')
 engines <- setNames(lapply(selected, function(name) dispatch[[name]]()), selected)
 list(engines=engines,models=t2_models(engines),config=cfg,
      budget_registry=t2_discovery_budget_registry(cfg),seed=t2_seed(shard,200),
      training_seed_index=if (length(data$seed_index)) as.integer(data$seed_index) else 0L,
      mc_canonical_id=if(is.null(data$canonical_id)) NA_character_ else data$canonical_id)
}
t2_run_heldout <- function(discovery,mode,shard,family='normal') {
 cfg<-discovery$config; replications<-if(mode=='smoke')30L else cfg$evaluation_replicates
 n_values<-if(mode=='smoke')c(200L,1000L,3000L) else cfg$heldout_n
 by_n<-lapply(seq_along(n_values),function(i){
  n<-n_values[i];s<-t2_canonical_mc(mode, family, t2_heldout_seed_index(), n, replications)$scenarios
  per_sc<-lapply(s,function(z){scores<-score_model_set(z$T,discovery$models,z$target);scores$scenario_id<-z$scenario_id;scores$sample_n<-n;scores})
  do.call(rbind,per_sc)
 })
 audit <- t2_heldout_independence_audit(discovery, mode, shard, family, n_values)
 list(scores=do.call(rbind,by_n),models=discovery$models,stage='heldout',fresh_rng=TRUE,
      independence_audit=audit, budget_parity=t2_budget_parity_audit(discovery))
}
t2_run_realworld <- function(discovery,mode,shard) {
 t2_run_realworld_public(discovery, mode, shard)
}
t2_run_stress <- function(discovery,mode,shard,family='normal') {
 stress_mode <- if (mode == 'full') 'full' else 'smoke'
 stress_n <- as.integer(Sys.getenv('T2_STRESS_SAMPLE_N', unset=if(mode=='full') '1000' else '200'))
 stress_R <- as.integer(Sys.getenv('T2_STRESS_REPS', unset=if(mode=='full') '250' else '30'))
 if (!is.finite(stress_n) || stress_n < 20L || !is.finite(stress_R) || stress_R < 5L)
   stop('Invalid stress runtime configuration')
 stress_path <- t2_mc_path(stress_mode, family, t2_heldout_seed_index(), stress_n, stress_R)
 if (mode == 'full' && identical(Sys.getenv('T2_REQUIRE_CANONICAL_STRESS', '0'), '1') &&
     !file.exists(stress_path)) {
   stop('Canonical stress block is missing: ', stress_path,
        '; refusing to regenerate it inside every model shard')
 }
 x<-t2_canonical_mc(stress_mode, family, t2_heldout_seed_index(), stress_n, stress_R)
 result<-do.call(rbind,lapply(x$scenarios,function(s){z<-score_model_set(s$T,discovery$models,s$target);z$scenario_id<-s$scenario_id;z}))
 list(scores=result,stage='stress',fixture=identical(mode, 'smoke'),stress_config=list(sample_n=stress_n,
      replications=stress_R,scenario_count=length(x$scenarios),family=family))
}
t2_run_aggregate <- function(shard){
 d<-t2_require(shard,'discovery');h<-t2_require(shard,'heldout');r<-t2_require(shard,'realworld');s<-t2_require(shard,'stress')
 stopifnot(length(d$models)>4L,nrow(h$scores)>0L,nrow(r$scores)>0L,nrow(s$scores)>0L)
 lapply(list(heldout=h,realworld=r,stress=s),function(z)stopifnot(all(c('model','mse','q95')%in%names(z$scores))))
 list(stage='aggregate',results=list(heldout=h$scores,realworld=r$scores,stress=s$scores),fixture_realworld=isTRUE(r$fixture),fixture_stress=isTRUE(s$fixture))
}
run_t2_stage <- function(stage,shard,mode='smoke',family='normal',seed_index=0L,engine='all'){
 started<-Sys.time()
 base<-t2_stage_dirs(shard,stage)$base
 t2_precheck(shard,stage,mode)
 if(stage=='preflight'){
  scripts<-list.files('tests',pattern='\\.R$',full.names=TRUE)
  for(f in scripts){status<-system2('Rscript',f);if(status!=0L)stop(paste('Test failed:',f))}
  out<-list(status='pass',tests=basename(scripts))
 } else if(stage=='datasets'){
  out<-t2_run_datasets(mode,shard)
 } else if(stage=='mc_validation'){
  out<-t2_run_mc_validation(mode,shard)
  if(!identical(out$status,'PASS'))stop('Monte Carlo validation failed')
  if(mode=='full' && !isTRUE(out$legacy_four_layer_certified))stop('Full historical four-layer certification unavailable')
 } else if(stage=='montecarlo'){
  n_mc <- if(mode=='smoke') 30L else ga_config$train_n
  r_mc <- if(mode=='smoke') 30L else ga_config$evaluation_replicates
  mc<-t2_canonical_mc(mode, family, seed_index, n_mc, r_mc)
  out<-list(stage='montecarlo',canonical_id=mc$canonical_id,family=family,
            seed_index=as.integer(seed_index),n=as.integer(n_mc),replications=as.integer(r_mc),
            mc_version=mc$mc_version,base_pool_reused=mc$base_pool_reused,
            scenario_seed_scheme=mc$scenario_seed_scheme,
            canonical_reference=data.frame(canonical_id=mc$canonical_id,version=mc$mc_version,
              family=family,seed_index=as.integer(seed_index),sample_n=as.integer(n_mc),
              replications=as.integer(r_mc),storage_root=t2_mc_root(),stringsAsFactors=FALSE))
 } else if(stage=='discovery'){
  out<-t2_run_discovery(t2_require(shard,'montecarlo'),mode,shard,engine)
 } else if(stage=='heldout'){
  out<-t2_run_heldout(t2_require(shard,'discovery'),mode,shard,family)
 } else if(stage=='realworld'){
  out<-t2_run_realworld(t2_require(shard,'discovery'),mode,shard)
 } else if(stage=='stress'){
  out<-t2_run_stress(t2_require(shard,'discovery'),mode,shard,family)
 } else if(stage=='aggregate'){
  out<-t2_run_aggregate(shard)
 }
 out$provenance<-list(shard=shard,stage=stage,mode=mode,family=family,seed_index=seed_index,engine=engine,
                      commit=Sys.getenv('GITHUB_SHA','local'),timestamp=as.character(Sys.time()))
 t2_emit_stage_artifacts(out,shard,stage,mode,family,t2_seed(shard,seed_index),started)
 invisible(out)
}
