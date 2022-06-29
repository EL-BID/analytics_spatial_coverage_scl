list.of.packages <- c('shiny', 'leaflet', 'osrm', 'rgdal',
                      'sp', 'sf', 'viridis', 'shiny',
                      'leaflet', 'shinythemes')
new.packages <- list.of.packages[!(list.of.packages %in% installed.packages()[,"Package"])]
if(length(new.packages)) install.packages(new.packages)
