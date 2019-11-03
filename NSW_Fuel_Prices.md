NSW\_Fuel\_Prices\_Dataset
================
Sam Oranyeli
04/11/2019

``` r
library(tidyverse)
library(roomba)
library(rvest)
library(jsonlite)
library(glue)
library(httr)
library(readxl)
library(fs)
library(DBI)
library(config)


url <- 'https://data.nsw.gov.au/data/dataset/fuel-check'

json_content <- read_html(url)%>%
  html_nodes("ul.au-tags.homepage-search-tags")%>%
  html_nodes("a")%>%
  first()%>%
  html_attr("href")%>%
  glue("https://data.nsw.gov.au", .) %>%
  fromJSON(simplifyVector = FALSE) %>%
  roomba(cols = c("name","format","url"))%>%
  filter(str_detect(str_to_lower(format),"xlsx"))

json_content

#create temp file paths
file_paths <- str_replace_all(json_content$name, " ","_") %>%
  str_remove_all(".xlsx")%>%
  map(., ~glue(.,'.xlsx'))

paths <- file_temp() %>%
  dir_create() %>%
  path(file_paths) %>%
  file_create()


#read in file and
#write to temp files
downloads <- map(json_content$url, GET)%>%
  map(., content, as="raw") %>%
  map2(.,paths,writeBin)

#read in all the excel files
#purrr library in action here
files_loaded <- map(paths, read_excel,
                    col_names = FALSE, 
                    col_types = c("text","text","text","numeric","text","text","date","numeric"),
                    .name_repair = ~ c("servicestationname","address",
                                       "suburb","postcode",
                                       "brand","fuelcode",
                                       "priceupdateddate","price"))


#attach file_names to each tibble
#for future identification
#and bind rows to form one tibble
files_loaded <- files_loaded %>%
  map2_dfr(.x = files_loaded,
           .y = json_content$name,
           .f = ~ mutate(.x, file_header = .y)
           )

#some cleaning
#remove empty rows
#remove the header rows
#remove duplicates
files_loaded <- files_loaded %>%
  filter(!is.na(price))%>%
  fill(-price)%>%
  distinct_at(vars("servicestationname","address",
                   "suburb","postcode","brand",
                   "fuelcode","priceupdateddate"))


#get configuration details for database
dw <- config::get("datawarehouse")

#set connection to database
con <- dbConnect(RPostgres::Postgres(),
                 dbname = dw$database,
                 port = dw$port,
                 user = dw$uid,
                 password = dw$pwd)

dbWriteTable(con,"fuel_prices_nsw",files_loaded, append=TRUE)
```
