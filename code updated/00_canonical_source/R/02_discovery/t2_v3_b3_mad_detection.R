# Prospective B3 outlier-detection contract. No observations are deleted.
# Leys et al. (2013), JESP 49:764-766, DOI 10.1016/j.jesp.2013.03.013
t2_b3_mad_flags <- function(x,threshold=2.5,side='two_sided') {
 stopifnot(is.numeric(x),length(x)>=5L,all(is.finite(x)),
   length(threshold)==1L,is.finite(threshold),threshold>0,
   side%in%c('two_sided','upper','lower'))
 med<-stats::median(x)
 raw_mad<-stats::median(abs(x-med))
 scaled_mad<-raw_mad*1.4826
 if(scaled_mad==0) {
   # For discrete or degenerate samples, report undefined scale rather
   # than silently calling every off-median value an outlier.
   return(list(flag=rep(NA,length(x)),n_flagged=NA_integer_,
     median=med,raw_mad=raw_mad,scaled_mad=scaled_mad,
     threshold=threshold,side=side,status='undefined_zero_mad'))
 }
 z<-(x-med)/scaled_mad
 flag<-switch(side,two_sided=abs(z)>threshold,
   upper=z>threshold,lower=z< -threshold)
 list(flag=flag,n_flagged=sum(flag),median=med,
   raw_mad=raw_mad,scaled_mad=scaled_mad,threshold=threshold,
   side=side,status='ok')
}
t2_b3_mad_sensitivity <- function(x,thresholds=c(2,2.5,3),
                                    side='two_sided') {
 out<-lapply(thresholds,function(t)t2_b3_mad_flags(x,t,side))
 data.frame(threshold=thresholds,
   n_flagged=vapply(out,function(z)z$n_flagged,integer(1)),
   flagged_fraction=vapply(out,function(z)
     if(is.na(z$n_flagged))NA_real_ else z$n_flagged/length(x),numeric(1)),
   status=vapply(out,function(z)z$status,character(1)))
}
