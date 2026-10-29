# Frozen T2 evaluation on the historical external-battery structure.
# Profiles, parent units and comparators are fixed before any W* score.

t2_legacy_rw_manifest <- function(path = Sys.getenv('T2_LEGACY_RW_MANIFEST', unset = file.path('config', 'legacy_realworld_t2_manifest.csv'))) {
  if (!file.exists(path)) stop('Legacy real-world manifest is missing: ', path)
  x <- read.csv(path, stringsAsFactors = FALSE, check.names = FALSE)
  req <- c('dataset_id','parent_dataset_id','path','sha256','license','variable','transform','source_url','domain','family_hint')
  if (!all(req %in% names(x)) || !nrow(x) || anyDuplicated(x$dataset_id)) stop('Legacy real-world manifest is incomplete')
  x$path <- file.path('.', x$path)
  if (any(!file.exists(x$path))) stop('Legacy real-world processed input is missing')
  got <- vapply(x$path, t2_sha256, character(1))
  if (any(tolower(got) != tolower(x$sha256))) stop('Legacy real-world checksum mismatch')
  x
}

t2_legacy_rw_profile <- function(x, hint='', domain='') {
  sk <- mean((x - mean(x))^3) / max(stats::sd(x)^3, 1e-12)
  ku <- mean((x - mean(x))^4) / max(stats::sd(x)^4, 1e-12) - 3
  h <- tolower(paste(hint, domain))
  if (grepl('bounded|proportion|percent|rate',h)) 'bounded_or_proportion'
  else if (grepl('zero|count|poisson',h)) 'zero_inflated_count'
  else if (grepl('lognormal',h) || (sk >= 1.25 && min(x) >= 0)) 'lognormal_like'
  else if (grepl('weibull|duration|survival',h) || (sk > .25 && sk < 2.5 && ku < 8 && min(x)>=0)) 'weibull_like'
  else if (grepl('normal',h) || (abs(sk) <= .6 && ku <= 4)) 'normal_like'
  else if (grepl('return|market',h)) 'heavy_tail_symmetric' else 'empirical_unknown'
}

t2_legacy_rw_in_profile <- function(family, profile) switch(family,
 normal=profile %in% c('normal_like','heavy_tail_symmetric'), lognormal=identical(profile,'lognormal_like'),
 weibull=identical(profile,'weibull_like'), invgauss=profile %in% c('lognormal_like','weibull_like'),
 exgaussian=profile %in% c('normal_like','heavy_tail_symmetric','lognormal_like'),
 exwald=profile %in% c('weibull_like','lognormal_like'), FALSE)

t2_legacy_rw_benchmark <- function(profile) if (profile == 'normal_like') 'mean' else if (profile %in% c('heavy_tail_symmetric','bounded_or_proportion')) 'huber' else 'trimmed20'

t2_legacy_rw_score <- function(mode='smoke', families=t2_families()) {
  tab <- t2_legacy_rw_manifest(); root <- file.path(t2_confirmatory_root(),'legacy_realworld')
  only_id <- Sys.getenv('T2_LEGACY_RW_DATASET_ID', '')
  if (nzchar(only_id)) {
    tab <- tab[tab$dataset_id == only_id,,drop=FALSE]
    if (!nrow(tab)) stop('Requested legacy dataset is absent from the manifest: ', only_id)
  }
  max_datasets <- suppressWarnings(as.integer(Sys.getenv('T2_LEGACY_RW_MAX_DATASETS', '0')))
  if (is.finite(max_datasets) && max_datasets > 0L) tab <- tab[seq_len(min(nrow(tab), max_datasets)),,drop=FALSE]
  dir.create(file.path(root,'raw'),recursive=TRUE,showWarnings=FALSE); summary <- list()
  for (i in seq_len(nrow(tab))) {
    row <- tab[i,,drop=FALSE]; d <- t2_realworld_load_vector(row); profile <- t2_legacy_rw_profile(d$x,row$family_hint,row$domain)
    ns <- if(mode=='smoke') 200L else as.integer(strsplit(Sys.getenv('T2_LEGACY_RW_SAMPLE_SIZES','200|1000'),'|',fixed=TRUE)[[1]])
    reps <- if(mode=='smoke') 20L else as.integer(Sys.getenv('T2_LEGACY_RW_REPS','500'))
    prepared <- lapply(ns,function(n) realworld_prepare(d$x,n,R=reps,seed=t2_seed(paste('legacy_rw',row$dataset_id,n),8101L))[[1]])
    entries <- list()
    for (fam in families) {
      mods <- t2_confirmatory_load_models(fam); bench <- t2_legacy_rw_benchmark(profile)
      for (z in prepared) {
        # reference_model_set() is intentionally an unnamed list; select its
        # frozen component rather than relying on an incidental list name.
        ref_i <- which(vapply(mods$reference, function(m) identical(m$component, bench), logical(1)))
        if (length(ref_i) != 1L) stop('Profile comparator is unavailable: ', bench)
        b <- (model_predict(z$T,mods$reference[[ref_i]])-z$target)^2
        cse <- do.call(cbind,lapply(mods$candidates,function(m)(model_predict(z$T,m)-z$target)^2)); colnames(cse) <- names(mods$candidates)
        entries[[length(entries)+1L]] <- list(family=fam,profile=profile,benchmark_id=bench,sample_n=z$sample_n,benchmark_se=b,candidate_ids=colnames(cse),candidate_se=cse)
      }
    }
    f <- file.path(root,'raw',paste0(row$dataset_id,'.rds')); t2_atomic_save(entries,f)
    summary[[i]] <- data.frame(dataset_id=row$dataset_id,parent_dataset_id=row$parent_dataset_id,empirical_profile=profile,source_group=row$source_group,raw_path=f,raw_sha256=t2_sha256(f))
  }
  t2_write_csv(do.call(rbind,summary),file.path(root,'raw_manifest.csv')); t2_write_csv(tab,file.path(root,'manifest_verified.csv'))
  writeLines('legacy_realworld_score COMPLETE',file.path(root,'score.status'))
}

t2_legacy_rw_inference <- function(mode='smoke') {
  root <- file.path(t2_confirmatory_root(),'legacy_realworld'); if(!file.exists(file.path(root,'score.status'))) stop('Legacy real-world score is missing')
  ix <- read.csv(file.path(root,'raw_manifest.csv'),stringsAsFactors=FALSE); B <- t2_confirmatory_bootstrap_B(mode); blocks <- list(); k <- 0L
  for(i in seq_len(nrow(ix))) for(e in t2_read_rds(file.path(root,'raw',paste0(ix$dataset_id[i],'.rds')))) for(engine in c('ga','nsga2','de','dirichlet')) {
    j <- grep(sprintf('^%s_%s_train',e$family,engine),e$candidate_ids); cse <- rowMeans(e$candidate_se[,j,drop=FALSE]); b <- e$benchmark_se; k <- k+1L
    blocks[[k]] <- data.frame(dataset_id=ix$dataset_id[i],parent_dataset_id=ix$parent_dataset_id[i],profile=e$profile,family=e$family,engine=engine,benchmark_id=e$benchmark_id,in_profile=t2_legacy_rw_in_profile(e$family,e$profile),sample_n=e$sample_n,mse_difference=mean(cse)-mean(b),q95_difference=unname(quantile(cse,.95,type=8)-quantile(b,.95,type=8)),benchmark_mse=mean(b),benchmark_q95=unname(quantile(b,.95,type=8)))
  }
  block <- do.call(rbind,blocks); parent <- aggregate(cbind(mse_difference,q95_difference,benchmark_mse,benchmark_q95) ~ parent_dataset_id + profile + family + engine + benchmark_id + in_profile,block,mean)
  tests <- lapply(split(parent,interaction(parent$family,parent$engine,parent$profile,drop=TRUE)),function(z) {
    a <- t2_confirmatory_block_test(z$mse_difference,B,t2_seed(paste('legacy',z$family[1],z$engine[1],z$profile[1],'mse'),8201L)); b <- t2_confirmatory_block_test(z$q95_difference,B,t2_seed(paste('legacy',z$family[1],z$engine[1],z$profile[1],'q95'),8202L))
    data.frame(family=z$family[1],engine=z$engine[1],empirical_profile=z$profile[1],benchmark_id=z$benchmark_id[1],n_parent_datasets=nrow(z),mse_difference=a['difference'],mse_ci_low=a['ci_low'],mse_ci_high=a['ci_high'],mse_p_value=a['p_value'],q95_difference=b['difference'],q95_ci_low=b['ci_low'],q95_ci_high=b['ci_high'],q95_p_value=b['p_value'],benchmark_mse=mean(z$benchmark_mse),benchmark_q95=mean(z$benchmark_q95))
  })
  out <- do.call(rbind,tests); out$mse_q_value <- p.adjust(out$mse_p_value,'BH'); out$q95_q_value <- p.adjust(out$q95_p_value,'BH')
  alpha <- as.numeric(t2_confirmatory_value('fdr_alpha')); out$mse_supported <- out$mse_difference<0 & out$mse_ci_high<0 & out$mse_q_value<=alpha; out$q95_supported <- out$q95_difference<0 & out$q95_ci_high<0 & out$q95_q_value<=alpha
  out$pareto_supported <- out$mse_supported & out$q95_supported; out$mse_gain_pct <- -100*out$mse_difference/pmax(out$benchmark_mse,1e-12); out$q95_gain_pct <- -100*out$q95_difference/pmax(out$benchmark_q95,1e-12); out$evidence_role <- 'descriptive_external_profile_taxonomy'
  t2_write_csv(block,file.path(root,'derived_rows_not_independent.csv')); t2_write_csv(parent,file.path(root,'parent_dataset_blocks.csv')); t2_write_csv(out,file.path(root,'profile_taxonomy_inference.csv')); writeLines('legacy_realworld_inference COMPLETE',file.path(root,'inference.status')); invisible(out)
}
