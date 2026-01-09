field <- commandArgs(trailingOnly = TRUE)

library(httr)
library(jsonlite)

source("fun.R")
source("credentials.R")
source("./parameters/prompts.R")

now <- Sys.time()
crawl_start_date <- as.Date(now) - 14
crawl_end_date <- as.Date(now) - 1

journals <- read.csv(paste0("./parameters/", field, "_journals.csv"))
past_urls <- read.csv(paste0("./memory/", field, "_urls.csv"))

use_polite <- crossref_endpoint_polite_faster(crawl_start_date,crawl_end_date)

# Crawl Crossref API 
out <- retrieve_crossref_issn_data(
    issn_list=journals$issn, 
    start_date=crawl_start_date, 
    end_date=crawl_end_date, 
    verbose=TRUE, polite_endpoint=use_polite)

# Remove duplicates
out <- out[!duplicated(out$url),] 
# Remove past paers
out <- out[!(out$url %in% past_urls$url), ]
if(is.null(out) | nrow(out)==0) {
    json <- toJSON(list("update"=as.Date(now), "content"=list()), 
        pretty=TRUE, auto_unbox=TRUE)
    write(json, paste0("./output/", field, ".json"))
    quit(save="no")
    } 

# Cleanup data
out$abstract <- strip_html(out$abstract)
out$abstract <- gsub("^(Abstract|ABSTRACT) ", "", out$abstract)
out$title <- strip_html(out$title)
out$doi <- extract_doi_id(out$url)

# Merge in journal information 
out <- merge(out, journals, by="issn")

# Apply standard filter flags 
out <- add_standard_filter(out) 

# Filter flags: Multidisciplinary journals 
if(field %in% c("multidisciplinary", "environmental_and_climate_politics_studies") ){
    out_lst <- split(out, out$filter_function) 
    out_lst <- lapply(out_lst, dispatch_special_filter ) 
    out <- do.call(rbind, out_lst)
    out$filter <- apply(out, 1, function(x){
        tryCatch(
            {add_multidisciplinary_filter(x)
            }, error = function(msg){
                return(-1)
            })
        })
    rownames(out) <- NULL
    } 

# Output JSON
out_json <- render_json(out, date=as.Date(now)) 
write(out_json, paste0("./output/", field, ".json"))

# Update past urls
write.table(out[,"url"], 
    file=paste0("./memory/", field, "_urls.csv"), 
    na="", 
    sep=";", 
    append=TRUE, 
    quote=FALSE, 
    col.names=FALSE,
    row.names=FALSE)

# Write journal short list
journals_out <- unique(journals[,c("journal_full","journal_short")])
journals_out <- journals_out[order(journals_out$journal_full),]
journals_out <- toJSON(journals_out, pretty=TRUE, auto_unbox=TRUE) 
write(journals_out, paste0("./output/", field, "_journals.json"))


