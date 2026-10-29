# Prueba T2 version 3 B3: shared memory/resource guard and provenance.
t2_b3_cgroup_value <- function(name) {
  paths<-c(file.path('/sys/fs/cgroup',name),file.path('/sys/fs/cgroup/memory',name))
  p<-paths[file.exists(paths)]
  if(!length(p))return(NA_real_)
  z<-tryCatch(readLines(p[1],warn=FALSE,n=1L),error=function(e)NA_character_)
  suppressWarnings(as.numeric(z))
}
t2_b3_memory_mb <- function(){
  val<-t2_b3_cgroup_value('memory.current')
  if(!is.finite(val))val<-t2_b3_cgroup_value('memory.usage_in_bytes')
  val/1024^2
}
t2_b3_memory_peak_mb <- function(){
  val<-t2_b3_cgroup_value('memory.peak')
  if(!is.finite(val))val<-t2_b3_cgroup_value('memory.max_usage_in_bytes')
  val/1024^2
}
t2_b3_ram_guard <- function(stage,output,step,limit_mb=as.numeric(Sys.getenv('T2_B3_RAM_LIMIT_MB','6000'))){
  dir.create(output,recursive=TRUE,showWarnings=FALSE)
  used<-t2_b3_memory_mb()
  if(is.finite(used)&&is.finite(limit_mb)&&used>limit_mb){
    invisible(gc(verbose=FALSE));used<-t2_b3_memory_mb()
    if(is.finite(used)&&used>limit_mb)stop('T2_V3_B3_RAM_LIMIT_EXCEEDED stage=',stage,
      ' step=',step,' MB=',round(used),' limit=',limit_mb)
  }
  row<-data.frame(version='T2_V3_B3',stage=stage,step=as.character(step),
    cgroup_used_mb=used,cgroup_peak_mb=t2_b3_memory_peak_mb(),
    r_ncells_mb=gc()[1L,2L],r_vcells_mb=gc()[2L,2L],
    stringsAsFactors=FALSE)
  p<-file.path(output,'memory_T2_V3_B3.csv')
  utils::write.table(row,p,append=file.exists(p),col.names=!file.exists(p),
     row.names=FALSE,sep=',',quote=TRUE)
  invisible(row)
}
t2_b3_inputs_manifest <- function(paths,output,role){
  paths<-unique(normalizePath(paths,mustWork=TRUE))
  d<-file.info(paths)
  if(any(d$isdir))stop('B3 manifest requires files')
  rows<-data.frame(version='T2_V3_B3',role=role,path=paths,
    bytes=as.numeric(d$size),md5=unname(tools::md5sum(paths)),
    stringsAsFactors=FALSE)
  dir.create(output,recursive=TRUE,showWarnings=FALSE)
  utils::write.csv(rows,file.path(output,'dependencies_T2_V3_B3.csv'),row.names=FALSE)
  invisible(rows)
}
