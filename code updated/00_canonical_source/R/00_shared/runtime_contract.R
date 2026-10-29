t2_runtime_requirements <- function(root = '.') {
  path <- file.path(root, 'config', 'runtime_requirements.csv')
  if (!file.exists(path)) stop('Missing runtime requirements: ', path)
  utils::read.csv(path, stringsAsFactors = FALSE, check.names = FALSE)
}

t2_set_rng_contract <- function() {
  if (getRversion() < '3.6.0') stop('R >= 3.6.0 is required for the declared RNG contract')
  RNGkind(kind = 'Mersenne-Twister', normal.kind = 'Inversion', sample.kind = 'Rejection')
  invisible(RNGkind())
}

t2_check_runtime <- function(root = '.', strict = TRUE) {
  req <- t2_runtime_requirements(root)
  problems <- character()
  declared_r <- req$version[req$component == 'R'][1]
  if (!identical(as.character(getRversion()), declared_r)) {
    problems <- c(problems, sprintf('R %s required; found %s', declared_r, getRversion()))
  }
  for (i in which(req$component == 'package' & req$required)) {
    pkg <- req$name[i]
    if (!requireNamespace(pkg, quietly = TRUE)) {
      problems <- c(problems, sprintf('Missing package %s %s', pkg, req$version[i]))
    } else {
      found <- as.character(utils::packageVersion(pkg))
      if (!identical(found, req$version[i])) {
        problems <- c(problems, sprintf('Package %s %s required; found %s', pkg, req$version[i], found))
      }
    }
  }
  rng_before <- RNGkind()
  t2_set_rng_contract()
  rng_after <- RNGkind()
  if (!identical(rng_after, c('Mersenne-Twister', 'Inversion', 'Rejection'))) {
    problems <- c(problems, paste('Unexpected RNG:', paste(rng_after, collapse = '/')))
  }
  if (length(problems) && strict) {
    stop('RUNTIME CONTRACT FAIL:\n- ', paste(problems, collapse = '\n- '))
  }
  list(status = if (length(problems)) 'FAIL' else 'PASS',
       problems = problems, R = as.character(getRversion()),
       rng = rng_after, previous_rng = rng_before,
       packages = stats::setNames(vapply(req$name[req$component == 'package'],
         function(x) as.character(utils::packageVersion(x)), character(1)),
         req$name[req$component == 'package']))
}
