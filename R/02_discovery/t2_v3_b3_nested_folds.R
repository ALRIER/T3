# Deterministic, scenario-level stratification for strict B3 nested validation.
# Read only immutable scenario metadata; no outcome or optimizer fitness used.
t2_b3_stratified_folds <- function(family, seed, ids=0:120, k=5L) {
 stopifnot(k>=2L,length(ids)>=k,anyDuplicated(ids)==0L)
 meta<-lapply(ids,function(id){
   p<-file.path(t2_v3_block_dir('discovery',family,seed,1000L),
                sprintf('scenario_%04d.rds',as.integer(id)))
   if(!file.exists(p))stop('Missing immutable scenario metadata: ',p)
   z<-readRDS(p)
   data.frame(scenario_id=as.integer(id),
     band=if(is.null(z$band))'unclassified' else as.character(z$band)[1L],
     mechanism=if(is.null(z$mechanism))'unclassified' else as.character(z$mechanism)[1L],
     mad=if(is.null(z$mad_scale)) NA_real_ else as.numeric(z$mad_scale)[1L],
     contamination=if(is.null(z$contamination)) NA_real_ else as.numeric(z$contamination)[1L],
     stringsAsFactors=FALSE)
 })
 tab<-do.call(rbind,meta)
 tab$mad_band<-ifelse(is.na(tab$mad),'unknown',ifelse(tab$mad<=4.5,'low',ifelse(tab$mad<=12,'mid','high')))
 tab$stratum<-paste(tab$band,tab$mechanism,tab$mad_band,sep='::')
 # Balanced assignment within observed strata, with global fold balance.
 tab$fold<-NA_integer_; totals<-integer(k)
 for(key in sort(unique(tab$stratum))){
   ix<-which(tab$stratum==key)
   ix<-ix[order(tab$scenario_id[ix])]
   counts<-integer(k)
   for(i in ix){
     eligible<-which(counts==min(counts))
     selected<-eligible[which.min(totals[eligible])]
     tab$fold[i]<-selected
     counts[selected]<-counts[selected]+1L
     totals[selected]<-totals[selected]+1L
   }
 }
 if(anyNA(tab$fold)||max(totals)-min(totals)>1L)
   stop('Unable to balance scenario strata; inspect B3 grid')
 tab
}
t2_b3_nested_partitions <- function(family,seed,outer,inner=NULL) {
 stopifnot(outer%in%1:5)
 ext<-t2_b3_stratified_folds(family,seed,0:120,5L)
 train<-ext$scenario_id[ext$fold!=outer]
 valid<-ext$scenario_id[ext$fold==outer]
 if(is.null(inner))return(list(training=train,validation=valid,outer=ext))
 stopifnot(inner%in%1:3)
 inside<-t2_b3_stratified_folds(family,seed,train,3L)
 list(training=inside$scenario_id[inside$fold!=inner],
      validation=inside$scenario_id[inside$fold==inner],
      outer_training=train,outer_validation=valid,outer=ext,inner=inside)
}
