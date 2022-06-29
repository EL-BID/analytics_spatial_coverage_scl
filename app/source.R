source("utils.R")
#install.packages("devtools")
#devtools::install_github("EL-BID/idbsocialdataR@main") 

library(idbsocialdataR)

countries <- idbsocialdataR:::get_countries() %>% select(isoalpha3, country_name_en) 
# %>% rev() %>% unstack() %>% as.list()

load_dot_env('.env')

Sys.setenv(
  "AWS_ACCESS_KEY_ID" =Sys.getenv("AWS_ACCESS_KEY_ID"),
  "AWS_SECRET_ACCESS_KEY" =Sys.getenv("AWS_SECRET_ACCESS_KEY"),
  "AWS_DEFAULT_REGION" = Sys.getenv("AWS_DEFAULT_REGION")
)


scldatalake = Sys.getenv("scldatalake")

schools <- s3read_using(FUN = read.csv,
                          object = paste0(scldatalake,"/Geospatial infrastructure/Education Facilities/education_facilities.csv"),
                          encoding = 'UTF-8')

hospitals <- s3read_using(FUN = read.csv,
                         object = paste0(scldatalake,"/Geospatial infrastructure/Healthcare Facilities/HOTOSM/OSM_hospital_LAC.csv"),
                         encoding = 'UTF-8')
