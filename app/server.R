source("utils.R")
source("source.R")

scldatalake = Sys.getenv("scldatalake")


shinyServer(function(input, output) {

  # Data
  population_map <- eventReactive({input$population 
                                   input$population_rb 
                                   }, {
                                     
                                     
    if (input$population=='total_population') {
      path <- "./data/total_population_4.geojson"
      geo <- geojson_sf(path) %>%
        left_join(countries, how='left', on='isoalpha3') %>% 
        filter(country_name_en==input$country) 
      
    } else {
      path <- str_c(scldatalake,"/Development Data Partnership/",
                    "Facebook - High resolution population density map/",
                    "public-fb-data/geojson/LAC/",input$population,"_4.geojson")
      geo <- s3read_using(FUN = geojson_sf,
                          object = path) %>%
        left_join(countries, how='left', on='isoalpha3') %>% 
        filter(country_name_en==input$country) 
      
      
    }
    
    return(geo)
  })  
  
  
  amenity <- eventReactive({input$amenity}, {
    if (input$amenity=='school') {
      data <- s3read_using(FUN = read.csv,
                           object = paste0(scldatalake,"/Geospatial infrastructure/Education Facilities/education_facilities.csv"),
                           encoding = 'UTF-8') %>% 
        filter(!is.na(lat) & !is.na(lon) )%>%
        left_join(countries, how='left', on='isoalpha3') %>% 
        filter(!isoalpha3 %in% skipcountries)
      
      
    } else if (input$amenity=='hospital'){
      
      data <- s3read_using(FUN = read.csv,
                           object = paste0(scldatalake,"/Geospatial infrastructure/Healthcare Facilities/healthcare_facilities.csv"),
                           encoding = 'UTF-8')%>% 
        filter(!is.na(lat) & !is.na(lon) )%>%
        left_join(countries, how='left', on='isoalpha3')%>% 
        filter(!isoalpha3 %in% skipcountries)
    }
    
  })
  
  country <- eventReactive({input$country
    input$amenity
    }, {
      
      if (input$country!='All') {
        data <- amenity() %>% 
          filter(country_name_en==input$country) 
        
      } else {
        data <- amenity() 
      }
      
    })
  
  
  # isochrone <- eventReactive({input$driveTime 
  #   input$amenity 
  #   input$country}, {
  #     db <- isochrones %>%
  #       filter((country_name_en==input$country) &
  #                (amenity==input$amenity))
  #     # (minutes==input$driveTime)
  #     if (!is_empty(db)) {
  #       return(db)
  #     }  else {
  #       return(NULL)
  #     }      
  #   })
  
  coverage_data <- eventReactive({input$population
    #input$driveTime
    }, {
      if (input$population=='total_population' #& input$driveTime=='30'
          ) {
        
        db <- read_csv(str_c('./data/coverage_total_population_', #input$driveTime,
                             '30', '.csv')) %>%
          left_join(countries, how='left', on='isoalpha3') %>% 
          filter(!isoalpha3 %in% skipcountries) %>%
          mutate(pct = pct/100)

      } else {
        path <- str_c(scldatalake,
                      "/Geospatial infrastructure/Healthcare Facilities/",
                      "coverage/coverage_",input$population,"_", # input$driveTime
                      '30','.csv')
        print(path)
        db <- s3read_using(FUN = read_csv,
                                      object = path) %>%
          left_join(countries, how='left', on='isoalpha3') %>% 
          filter(!isoalpha3 %in% skipcountries) %>%
          mutate(pct = pct/100)
        
      }
      
      
      if (!is_empty(db)) {
        return(db)
      }  else {
        return(NULL)
      }
    })
  
  coverage <- eventReactive({input$population 
    #input$driveTime
    input$amenity 
    input$country}, {
      
      
      if (input$country=='All') {
        level_0 <- idbsocialdataR:::get_map() %>% select(isoalpha3, geometry)
        db <-  coverage_data() %>% 
          mutate(uncov_pop = poptot*pct) %>% 
          group_by(isoalpha3, country_name_en) %>% 
          summarize(poptot = sum(poptot, na.rm = T),
                    uncov_pop = sum(uncov_pop, na.rm = T)) %>% 
          mutate(pct = round(uncov_pop/poptot,4),
                 admin_name=country_name_en) %>% 
          left_join(level_0) %>% 
          select(admin_name, isoalpha3, poptot, uncov_pop , pct, geometry) %>% 
          ungroup()
        db <- st_as_sf(db, sf_column_name = "geometry")

      } else {
        db <-  coverage_data() %>%
          filter((country_name_en==input$country))
        
        db <- st_as_sf(db, wkt = "geometry")  
      }
      
      
      
      if (!is_empty(db)) {
        return(db)
      }  else {
        return(NULL)
      }
    })
  
 
  
  output$map <- renderLeaflet({
    
    amenity<-country()
    lat_m <- mean(amenity$lat)
    lon_m <- mean(amenity$lon)
    
    #if (input$population_rb=='True') {
    if (FALSE) {
      population_ <- population_map()
      bins <- quantile(population_$population, probs = seq(0, 1, 0.25), 
                       na.rm = T,names = FALSE)
      pal <- colorBin("YlOrRd", domain = population_$population, bins = bins)
      
      labels <- sprintf("<br/>Total Population: %s",
                              scales::comma(population_$population)) %>% 
        lapply(htmltools::HTML)
      
      m<-leaflet(population_)  %>% addProviderTiles(providers$CartoDB.Positron) %>% 
        addPolygons(fillColor = ~pal(population_$population),
                    weight = 2,
                    opacity = 1,
                    color = "white",
                    label = labels,
                    labelOptions = labelOptions(
                      style = list("font-weight" = "normal", padding = "3px 8px"),
                      textsize = "15px",
                      direction = "auto"),
                    dashArray = "3",
                    fillOpacity = 0.7)
    } else {
      m<-leaflet(country())  %>% addProviderTiles(providers$CartoDB.Positron)
    }
    
    m %>%
      clearMarkers() %>%
      clearShapes()
    
    # if ( isTruthy(iso) & input$isochrone=="True") {
    #iso <-isochrone()
    # colors <- list('15' = '#ef8a62', 
    #                '30' = '#f7f7f7',
    #                '45' = '#67a9cf'
    # )
    #   geom <-  iso # %>% filter(minutes==minute)
    #   geom <- st_as_sf(iso, wkt = "multipolygon")  
    #   #print(minute)
    #   #print(colors[as.character(minute)][[1]])
    #   m <- m %>% 
    #     addMapPane("15", zIndex = 450) %>%
    #     addMapPane("30", zIndex = 420) %>%
    #     addMapPane("45", zIndex = 410) %>% 
    #     addPolygons(data = geom %>% filter(minutes==15), 
    #                 stroke = FALSE, 
    #                 smoothFactor = 0.3,
    #                 color = '#ef8a62',
    #                 fillOpacity = 0.8,
    #                 options = pathOptions(pane = '15')) %>% 
    #     addPolygons(data = geom %>% filter(minutes==30), 
    #                 stroke = FALSE, 
    #                 smoothFactor = 0.3,
    #                 color = '#f7f7f7',
    #                 fillOpacity = 0.8,
    #                 options = pathOptions(pane = '30')) %>% 
    #     addPolygons(data = geom %>% filter(minutes==45), 
    #                 stroke = FALSE, 
    #                 smoothFactor = 0.3,
    #                 color = '#67a9cf',
    #                 fillOpacity = 0.8,
    #                 options = pathOptions(pane = '45'))
    # }
    
    if (input$coverage=="True") {
      geom <-coverage()

      bins <- quantile(geom$pct, probs = seq(0, 1, 0.25), 
                       na.rm = T,names = FALSE)
      pal <- colorBin("YlOrRd", domain = geom$pct, bins = bins)
      
      labels <- str_c(sprintf("Admin_name: <strong>%s</strong>
                              <br/>Total Population: %s
                              <br/>Pct of population without coverage: %g",
                              geom$admin_name, 
                              scales:::comma(geom$poptot), 
                              round(geom$pct*100,2)), '%') %>% 
        lapply(htmltools::HTML)
      
      
      m <- m %>% addProviderTiles(providers$CartoDB.Positron) %>% 
        addPolygons(data = geom,
                    fillColor = ~pal(geom$pct),
                    weight = 2,
                    opacity = 1,
                    color = "white",
                    dashArray = "3",
                    fillOpacity = 0.7,
                    highlightOptions = highlightOptions(
                      weight = 5,
                      color = "#666",
                      dashArray = "",
                      fillOpacity = 0.7,
                      bringToFront = TRUE),
                    label = labels,
                    labelOptions = labelOptions(
                      style = list("font-weight" = "normal", padding = "3px 8px"),
                      textsize = "15px",
                      direction = "auto")) %>%
        addLegend(pal = pal, values = ~geom$pct, opacity = 0.9, title = NULL,
                  position = "bottomleft")
      
      
    }
    

    labels <- sprintf("<br/>Country (Isoalpha3): %s
                      <br/>Source: %s
                      <br/>Name: %s",
                      amenity$isoalpha3,
                      amenity$source,
                      amenity$name) %>% 
      lapply(htmltools::HTML)
    
    if (input$amenities_rb=='True') {
      m <- m %>%
        addCircleMarkers(data = amenity, ~lon, ~lat,
                         label = labels,
                         radius = 3,
                         color = 'blue',
                         stroke = FALSE,
                         fillOpacity = 0.5,
                         clusterOptions = markerClusterOptions())
    }
    
    return(m)
  })
  
  observe({
    m <- leafletProxy("map") 
    return(m)
    
  })
  
  output$amenity_count<-renderText({
    count<-country() %>% nrow()
    return(as.character(comma(count))) 
    })
  
  output$population_count <-renderText({
    #population_ <- population_map()
    population_ <- coverage() 
    count<- sum(population_$poptot, na.rm = T)
    return(as.character(comma(count))) 
  })
  
  coverage_out <- eventReactive({input$population
                                 input$country
                                 input$amenity}, {
      out <- coverage() %>% 
        select(-geometry) %>% 
        mutate(uncov_pop = scales:::comma(poptot*pct),
               pct = round(pct, 4),
               poptot = scales:::comma(poptot)) %>% 
        arrange(desc(pct)) %>% 
        as_tibble() %>% 
        select(isoalpha3, admin_name, poptot, uncov_pop, pct) 
      
    })
  output$downloadData <- downloadHandler(
    filename = function() {
      str_c('coverage_',input$population,'_',input$amenity, ".csv")
    },
    content = function(file) {
      write.csv(coverage_out(),
                file, row.names = FALSE)
    }
  )  
  output$table <- renderDataTable({
    DT::datatable(coverage_out(),
                  filter='none',
                  options = list(
                    pageLength = 10, 
                    autoWidth = TRUE,
                    dom = 'tp',
                    ordering=T)) %>% 
      formatPercentage(c("pct"), 2)
    })
  
  output$readme2 <- renderUI({
    HTML(markdown::markdownToHTML('README.md',
                                  style=list(html.output='diff.w.style')))
  })
  
})