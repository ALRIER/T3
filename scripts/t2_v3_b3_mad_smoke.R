#!/usr/bin/env Rscript
source('R/02_discovery/t2_v3_b3_mad_detection.R')
set.seed(20261025)
x<-c(stats::rnorm(300),10,-10)
z<-t2_b3_mad_flags(x)
stopifnot(z$status=='ok',z$n_flagged>=2L,
 z$flag[301],z$flag[302],abs(z$scaled_mad-1)<.3)
s<-t2_b3_mad_sensitivity(x)
stopifnot(identical(s$threshold,c(2,2.5,3)),
  s$n_flagged[1]>=s$n_flagged[2],
  s$n_flagged[2]>=s$n_flagged[3])
constant<-t2_b3_mad_flags(rep(3,20))
stopifnot(constant$status=='undefined_zero_mad',
 all(is.na(constant$flag)))
upper<-t2_b3_mad_flags(x,2.5,'upper')
stopifnot(upper$flag[301],!upper$flag[302])
cat('T2_B3_LEYS_MAD_CUTOFF_SENSITIVITY_PASS\n')
