# T2 V3 B3 unified artifact naming. Never mutate immutable source outputs.
t2_b3_publish <- function(directory) {
  stopifnot(dir.exists(directory))
  originals <- list.files(directory,full.names=TRUE,recursive=FALSE)
  originals <- originals[file.info(originals)$isdir %in% FALSE]
  originals <- originals[!grepl('_T2_V3_B3\\.',basename(originals))]
  rows <- lapply(originals,function(p) {
    ext <- tools::file_ext(p)
    stem <- if(nzchar(ext)) substr(basename(p),1,nchar(basename(p))-nchar(ext)-1L) else basename(p)
    alias <- file.path(dirname(p),paste0(stem,'_T2_V3_B3',if(nzchar(ext))paste0('.',ext) else ''))
    if(!file.copy(p,alias,overwrite=TRUE))stop('Cannot create versioned copy: ',alias)
    data.frame(source=basename(p),published=basename(alias),
               md5=unname(tools::md5sum(alias)),stringsAsFactors=FALSE)
  })
  if(length(rows))utils::write.csv(do.call(rbind,rows),
      file.path(directory,'T2_V3_B3_file_map.csv'),row.names=FALSE)
  invisible(TRUE)
}
