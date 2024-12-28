rm(list=ls())
library(jsonlite)

# Count number of articles by journal 
files <- list.files("./output/", pattern='.json', full.names=TRUE)
files <- files[!grepl("_journals", files)]

lst <- list()

for(file in files){

    data <- fromJSON(file)

    update <- data$update
    journals <- data$content$journal_full
    N_articles <- sapply(data$content$articles, nrow)

    lst[[file]] <- data.frame(journal=journals, N=N_articles)

    }

df <- do.call(rbind, lst)
rownames(df) <- NULL
colnames(df) <- c("journal", update)

# Load existing data
data <- read.csv("./output/stats.csv", check.names=FALSE)

if(!(update %in% colnames(data))){

    # Merge with existing data 
    df <- merge(
        x=data,
        y=df, 
        by.x="Journal Name", 
        by.y="journal", 
        sort=FALSE, all=TRUE)

    # Set missings to zero
    df[[update]] <- ifelse(is.na(df[[update]]), 0, df[[update]])

    # Sort: Rows 
    df <- df[order(df$Sort), ]

    # Sort: Cols 
    labs <- as.Date(colnames(df)[-c(1:3)])
    labs <- labs[order(labs, decreasing = TRUE)]
    labs <- c("Sort", "Field", "Journal Name", as.character(labs))
    df <- df[,labs]

    write.csv(df, file="./output/stats.csv", na="", row.names=FALSE)

    }