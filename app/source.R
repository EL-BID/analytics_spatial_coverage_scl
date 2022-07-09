source("utils.R")
library(idbsocialdataR)
library(tidyverse)
library(dotenv)
library(aws.s3)
library(leaflet)
library(scales)

#install.packages("geojsonsf")
library(geojsonsf)
library(sf)
library(DT)

#install.packages("devtools")
#devtools::install_github("EL-BID/idbsocialdataR@main")

countries <- idbsocialdataR:::get_countries() %>% select(isoalpha3, country_name_en)


population <- idbsocialdataR:::query_indicator('population_un', year = 2022)


load_dot_env('.env')

Sys.setenv("AWS_ACCESS_KEY_ID" =Sys.getenv("AWS_ACCESS_KEY_ID"),
           "AWS_SECRET_ACCESS_KEY" =Sys.getenv("AWS_SECRET_ACCESS_KEY"),
           "AWS_DEFAULT_REGION" = Sys.getenv("AWS_DEFAULT_REGION"))

scldatalake = Sys.getenv("scldatalake")
# isochrones <- s3read_using(FUN = read_csv,
#                            object = paste0(scldatalake,
#                                            "/Geospatial infrastructure/Healthcare Facilities/isochrones/OSM_hospital_LAC_isochrones_simplify.csv")) %>% 
#   left_join(countries, how='left', on='isoalpha3')

skipcountries <- c('JAM', 'HTI', 'BRB', 'BHS', 'URY')
countrylist <- countries %>% 
  filter(!isoalpha3 %in% skipcountries) %>% 
  arrange(country_name_en) %>% 
  select(country_name_en) %>% pull()
