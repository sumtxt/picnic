# Main 
########

retrieve_crossref_issn_data <- function(issn_list, start_date, end_date, verbose=FALSE){

    K <- length(issn_list)
    out <- list()

    for(i in 1:K){
        issn <- issn_list[i]
        if(verbose) cat(issn, "\n")
        j <- 0
        tmp <- list()
        for(type in c("created", "published")){
            j <- j + 1
            tmp[[j]] <- call_crossref_api(
                id=issn, 
                type="issn", 
                start=start_date, 
                end=end_date, 
                date_type=type)
        }
        tmp <- rbind(
                get_crossref_articles(tmp[[1]]), 
                get_crossref_articles(tmp[[2]])
            )
        if(!is.null(tmp)) tmp$issn <- issn
        out[[i]] <- tmp[!duplicated(tmp$url),]
        }

    if(is.null(out)) return(NULL)

    out <- do.call(rbind, out)
    return(out)
    }


# Filter 
#########

add_multidisciplinary_filter <- function(row){
    row_nam <- names(row)
        cat(row[row_nam=="url"], "\n")
    row[row_nam=="filter"] <- as.integer(row[row_nam=="filter"])
    if(row[row_nam=="filter"]!=0) return(row[row_nam=="filter"])
    else{
        res <- call_openai_api(
            system_prompt=prompt_socsci_classifier, 
            user_prompt=paste(
                "Journal Name:", row[row_nam=="journal_full"], "\n",
                "Title:", row[row_nam=="title"], "\n",
                row[row_nam=="abstract"]
            ),
            model="gpt-4o-mini")
        if( get_openai_finish_reason(res)!="stop" ) return(-1)
        if( tolower(get_openai_response(res))=="no" ) return(2)
        return(0)
    }
}

dispatch_special_filter <- function(data){
    FUN <- unique(data$filter_function)
    if(FUN=="") return(data)
    else {
        filter_fun <- match.fun(FUN)
        return(filter_fun(data))
    }
    }

add_science_filter <- function(data){
    flag <- as.numeric(is.na(data$abstract)) 
    flag <- ifelse(flag==0, as.numeric(nchar(data$abstract)<200), flag) 
    data$filter <- flag*3
    return(data)
    }

add_nature_filter <- function(data){
    data$filter <- as.numeric(!grepl("/s", data$url))*4
    return(data)
    }

add_standard_filter <- function(data){
    str <- data$title
    flag <- rep(0, length(str))
    flag <- ifelse(is.na(str),1, flag) # ToCs have no title 
    flag <- ifelse(str=="Editorial Board",1, flag)
    flag <- ifelse(str=="Issue Information",1, flag)
    flag <- ifelse(str=="Forthcoming Papers",1, flag)
    flag <- ifelse(grepl("ERRATUM|ERRATA|Frontmatter|Front matter|Backmatter|Back matter", str, ignore.case = TRUE),1, flag)
    data$filter <- flag
    return(data)
    }


# Helpers 
##########

render_json <- function(df,date){

    df <- split(df, df$journal_full)
    to_json <- list()
    for(i in 1:length(df)){
        articles <- df[[i]]
        journal_full <- unique(articles$journal_full)
        journal_short <- unique(articles$journal_short)
        articles <- articles[c("title", "authors", "abstract", "url", "doi", "filter")]
        articles_hidden <- subset(articles, !(filter==0 | filter==-1) )
        articles_hidden <- sort_by(articles_hidden, articles_hidden$filter) 
        articles <- subset(articles, (filter==0 | filter==-1) )
        to_json[[i]] <- list(
            "journal_full"=journal_full, 
            "journal_short"=journal_short,
            "articles"=articles, 
            "articles_hidden"=articles_hidden)
    }
    to_json <- list("update"=date, "content"=to_json)
    json <- toJSON(to_json, pretty=TRUE, auto_unbox=TRUE) 
    return(json)
    }

extract_doi_id <- function(url){
    return(gsub("http(|s)://dx.doi.org/", "", url))
    }

strip_html <- function(str) {
   if(is.null(str)) return(NA)
   else {
    str <- gsub("<.*?>", " ", str)
    str <- gsub("\\s+", " ", str)
    str <- trimws(str)
    return(str)
   }
}

strip_whitespace <- function(str) {
   if(is.null(str)) return(NA)
   else {
    str <- gsub("\\s+", " ", str)
    return(trimws(str))
   }
}

file_empty <- function(file){
    length(readLines(file))==0
    }

read.csv2_check <- function(file, ...){
    if(!file_empty(file)){ 
        return(read.csv2(file, ...))
    } else { 
        return(NULL)
    }
}

# Crossref 
call_crossref_api <- function(id,type="issn",start,end,date_type="created", rows=1000){
    if( sum(type %in% c("issn", "doi"))!=1 ) stop("type must be either 'issn' or 'doi'")
    if( sum(date_type %in% c("created", "published"))!=1 ) stop("date_type must be either 'created' or 'published'")
    if(type=="issn"){
        endpoint <- paste0("https://api.crossref.org/journals/", id, "/works")
    }
    if(type=="doi"){
        endpoint <- paste0("https://api.crossref.org/prefixes/", id, "/works")
    }
    if(date_type=="created") {
        filter <- paste0("from-created-date:", start, ",until-created-date:", end)
    }
    if(date_type=="published") {
        filter <- paste0("from-pub-date:", start, ",until-pub-date:", end)
    }
    param = list(
        "filter"=filter, 
        "select"="title,author,abstract,URL,created", 
        "mailto"=crossref_email, 
        rows=rows)
    res = GET(endpoint,query=param)
    return(content(res))
    }

get_crossref_articles <- function(items){
    ll <- lapply(items$message$items, get_crossref_article_info)
    ll <- do.call(rbind, lapply(ll, function(x) as.data.frame(t(x))))
    return(ll)
}

get_crossref_article_info <- function(item){

    return((c(
        title=get_crossref_title(item),
        authors=get_crossref_authors(item),
        created=get_crossref_date(item, "created"),
        abstract=get_crossref_abstract(item), 
        url = get_crossref_url(item)
    )))
}

get_crossref_abstract <- function(item){
    if(is.null(item$abstract)) return(NA)
    else return(item$abstract)
}

get_crossref_authors <- function(item){
    if(is.null(item$author)) return(NA)
    else return(paste(lapply(item$author, get_crossref_author), collapse=", "))
}

get_crossref_author <- function(item){
    paste(item$given, item$family)
}

get_crossref_date <- function(item, name){
    if(is.null(item[[name]])) return(NA)
    else paste(unlist(item[[name]][["date-parts"]]), collapse="-")
}

get_crossref_title <- function(item){
    if(is.null(item$title)) return(NA)
    else unlist(item$title)
}

get_crossref_journal <- function(item){
    if(is.null(item$`container-title`)) return(NA)
    else unlist(item$`container-title`)
}

get_crossref_url <- function(item){
    if(is.null(item$URL)) return(NA)
    else unlist(item$URL)
}

get_crossref_api_limits <- function(response){
    out <- headers(response)
    limit <- out$`x-ratelimit-limit`
    interval <- out$`x-ratelimit-interval`
    return(c("limit"=limit, "interval"=interval))
    }



# Open AI 
call_openai_api <- function(system_prompt, user_prompt, model){
    endpoint <- "https://api.openai.com/v1/chat/completions"
    body <- list(
        model = model,
        messages = list(
            list(role="system", content=system_prompt),
            list(role="user", content=user_prompt)
            )
        )
    body <- toJSON(body, auto_unbox=TRUE)
    res <- POST(endpoint, 
        body=body, 
        encode='raw', 
        content_type_json(), 
        add_headers(Authorization = paste("Bearer", openai_apikey, sep = " ")))
    
    return(content(res))
    }

get_openai_response <- function(response){
    return(response$choices[[1]]$message$content)
}

get_openai_finish_reason <- function(response){
    return(response$choices[[1]]$finish_reason)
}

get_openai_usage <- function(response){
    return(unlist(response$usage$total_tokens))
}