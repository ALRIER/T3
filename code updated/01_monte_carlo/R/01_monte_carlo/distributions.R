# Extracted and retained original distribution functions and parameter grids.
rexwald <- function(n, mu = 1, lambda = 1, rate = 1) {
  stopifnot(length(n) == 1L, is.finite(n), n >= 0,
            is.finite(mu), is.finite(lambda), is.finite(rate))
  if (n == 0) return(numeric(0))
  if (lambda <= 0 || rate <= 0) stop("rexwald: 'lambda' and 'rate' must be > 0")
  T0 <- rexp(n, rate = rate)
  W  <- statmod::rinvgauss(n, mean = mu, shape = lambda)
  T0 + W
}

rexgaussian <- function(n, mu = 0, sigma = 1, tau = 1) {
  stopifnot(length(n) == 1L, is.finite(n), n >= 0,
            is.finite(mu), is.finite(sigma), is.finite(tau))
  if (n == 0) return(numeric(0))
  if (sigma <= 0 || tau <= 0) stop("rexgaussian: 'sigma' and 'tau' must be > 0")
  rnorm(n, mean = mu, sd = sigma) + rexp(n, rate = 1 / tau)
}

generate_population <- function(distribution, n, params = list()) {
  if (!is.character(distribution) || length(distribution) != 1L)
    stop("generate_population: 'distribution' must be a single string.")
  if (!is.numeric(n) || length(n) != 1L || n < 0)
    stop("generate_population: 'n' must be a non-negative scalar.")
  if (n == 0) return(numeric(0))
  
  distribution <- tolower(trimws(distribution))
  params <- as.list(params)
  # Local getter for parameters: supports defaults, explicit required fields, and consistent error messages
  # tied to the chosen distribution. This makes debugging failed grid rows much faster during large sweeps.
  getp <- function(name, default = NULL, required = FALSE) {
    if (!is.null(params[[name]])) return(params[[name]])
    if (required) stop(sprintf("generate_population(%s): missing '%s'.",
                               distribution, name))
    default
  }
  
  out <- switch(distribution,
                normal = {
                  mean <- getp("mean", 0); sd <- getp("sd", 1)
                  if (!is.finite(sd) || sd <= 0) stop("normal: 'sd' must be > 0.")
                  rnorm(n, mean = mean, sd = sd)
                },
                lognormal = {
                  meanlog <- getp("meanlog", 0); sdlog <- getp("sdlog", 1)
                  if (!is.finite(sdlog) || sdlog <= 0) stop("lognormal: 'sdlog' must be > 0.")
                  rlnorm(n, meanlog = meanlog, sdlog = sdlog)
                },
                weibull = {
                  shape <- getp("shape", required = TRUE); scale <- getp("scale", required = TRUE)
                  if (!is.finite(shape) || shape <= 0) stop("weibull: 'shape' must be > 0.")
                  if (!is.finite(scale) || scale <= 0) stop("weibull: 'scale' must be > 0.")
                  rweibull(n, shape = shape, scale = scale)
                },
                invgauss = {
                  mean <- getp("mean", required = TRUE); shape <- getp("shape", required = TRUE)
                  if (!is.finite(mean)  || mean  <= 0) stop("invgauss: 'mean' must be > 0.")
                  if (!is.finite(shape) || shape <= 0) stop("invgauss: 'shape' must be > 0.")
                  statmod::rinvgauss(n, mean = mean, shape = shape)
                },
                exgaussian = {
                  mu <- getp("mu", 0); sigma <- getp("sigma", 1); tau <- getp("tau", 1)
                  if (!is.finite(sigma) || sigma <= 0) stop("exgaussian: 'sigma' must be > 0.")
                  if (!is.finite(tau)   || tau   <= 0) stop("exgaussian: 'tau' must be > 0.")
                  rexgaussian(n, mu = mu, sigma = sigma, tau = tau)
                },
                exwald = {
                  mu <- getp("mu", 1); lambda <- getp("lambda", 1); rate <- getp("rate", 1)
                  if (!is.finite(lambda) || lambda <= 0) stop("exwald: 'lambda' must be > 0.")
                  if (!is.finite(rate)   || rate   <= 0) stop("exwald: 'rate' must be > 0.")
                  rexwald(n, mu = mu, lambda = lambda, rate = rate)
                },
                stop(sprintf("Unsupported distribution: %s", distribution))
  )
  
  # Remove any NA/Inf produced by extreme numeric conditions. If everything is filtered out, fail fast:
  # downstream code expects a non-empty finite population to sample from, and an empty result indicates
  # invalid parameters or a numerical pathology worth diagnosing immediately.
  out <- out[is.finite(out)]
  if (!length(out)) stop("generate_population: no finite sample generated.")
  out
}

analytic_mean_from_params <- function(dist_name, params) {
  dist_name <- tolower(trimws(dist_name))
  params <- as.list(params)
  
  # Parameter getter mirrored from generate_population to keep error behavior consistent. This avoids
  # subtle mismatches where sampling uses one default/requirement and analytic mean uses another, which
  # would distort bias metrics and undermine interpretability of robustness comparisons.
  getp <- function(name, default = NULL, required = FALSE) {
    if (!is.null(params[[name]])) return(params[[name]])
    if (required) stop(sprintf("analytic_mean_from_params(%s): missing '%s'", dist_name, name))
    default
  }
  
  out <- switch(dist_name,
                normal = getp("mean", 0),
                lognormal = {
                  meanlog <- getp("meanlog", 0)
                  sdlog   <- getp("sdlog", 1, required = TRUE)
                  exp(meanlog + 0.5 * sdlog^2)
                },
                weibull = {
                  shape <- getp("shape", required = TRUE)
                  scale <- getp("scale", required = TRUE)
                  scale * gamma(1 + 1 / shape)
                },
                invgauss = getp("mean", required = TRUE),
                exgaussian = {
                  mu  <- getp("mu", 0)
                  tau <- getp("tau", 1, required = TRUE)
                  mu + tau
                },
                exwald = {
                  mu   <- getp("mu", 1, required = TRUE)
                  rate <- getp("rate", 1, required = TRUE)
                  (1 / rate) + mu
                },
                stop(sprintf("Unsupported distribution: %s", dist_name))
  )
  
  as.numeric(out)
}


.param_grids_default <- list(
  normal     = expand.grid(mean = c(1, 5),
                           sd   = c(1, sqrt(2), 2, 3),
                           KEEP.OUT.ATTRS = FALSE, stringsAsFactors = FALSE),
  lognormal  = expand.grid(meanlog = c(0.5, 1),
                           sdlog   = c(0.25, 0.5, 1),
                           KEEP.OUT.ATTRS = FALSE, stringsAsFactors = FALSE),
  weibull    = expand.grid(shape = c(0.5, 1, 2, 3),
                           scale = c(0.5, 1, 2),
                           KEEP.OUT.ATTRS = FALSE, stringsAsFactors = FALSE),
  invgauss   = expand.grid(mean  = c(0.5, 1, 2),
                           shape = c(0.5, 1, 2),
                           KEEP.OUT.ATTRS = FALSE, stringsAsFactors = FALSE),
  exgaussian = expand.grid(mu    = c(0, 1, 2),
                           sigma = c(0.5, 1, 1.5),
                           tau   = c(0.25, 0.5, 1),
                           KEEP.OUT.ATTRS = FALSE, stringsAsFactors = FALSE),
  exwald     = expand.grid(mu     = c(1, 1.5, 2),
                           lambda = c(0.5, 1, 2),
                           rate   = c(0.25, 0.5, 1),
                           KEEP.OUT.ATTRS = FALSE, stringsAsFactors = FALSE)
)



.validate_grid <- function(name, g) {
  if (!is.data.frame(g) || !nrow(g)) stop(sprintf("Invalid grid for '%s'.", name))
  g[] <- lapply(g, function(col) { col[!is.finite(col)] <- NA_real_; col })
  g <- stats::na.omit(g)
  if (name %in% c("weibull")) {
    g <- subset(g, shape > 0 & scale > 0)
  } else if (name %in% c("invgauss")) {
    g <- subset(g, mean > 0 & shape > 0)
  } else if (name %in% c("exgaussian")) {
    g <- subset(g, sigma > 0 & tau > 0)
  } else if (name %in% c("exwald")) {
    g <- subset(g, lambda > 0 & rate > 0)
  } else if (name %in% c("normal")) {
    g <- subset(g, sd > 0)
  } else if (name %in% c("lognormal")) {
    g <- subset(g, sdlog > 0)
  }
  if (!nrow(g)) stop(sprintf("After validation, grid '%s' became empty.", name))
  unique(g)
}

build_param_grids <- function(overrides = NULL, families = names(.param_grids_default)) {
  families <- intersect(tolower(families), names(.param_grids_default))
  if (!length(families)) stop("build_param_grids: no valid families selected.")
  res <- list()
  for (nm in families) {
    g <- if (!is.null(overrides) && !is.null(overrides[[nm]])) overrides[[nm]] else .param_grids_default[[nm]]
    res[[nm]] <- .validate_grid(nm, g)
  }
  res
}

