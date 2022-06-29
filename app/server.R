source("utils.R")
source("source.R")

scldatalake = Sys.getenv("scldatalake")

shinyServer(function(input, output) {
  
  # Data
  country <- eventReactive({input$country
                            input$amenity}, {
                              if (input$amenity=='school') {
                                #data <- read_csv('./data/education_facilities.csv') 
                                data <- schools
                                
                              } else if (input$amenity=='hospital'){
                                #data <- read_csv('./data/OSM_hospital_LAC.csv')
                                data <- hospitals
                              }
                              data %>% 
                                left_join(countries, how='left', on='isoalpha3') %>% 
                                filter(country_name_en==input$country) %>% 
                                #filter(amenity==input$amenity) %>% 
                                filter(!is.na(lat) & !is.na(lon) )
    })
  
  
  
  observeEvent(input$map_click, {
    click = input$map_click
    leafletProxy('map') %>%
      clearMarkers() %>%
      addMarkers(lng = Lng(), lat = Lat())
  })
  
  Lat <- eventReactive(input$map_click, {
    click = input$map_click
    out <- click$lat
    
  })
  
  Lng <- eventReactive(input$map_click, {
    click <- input$map_click
    out <- click$lng
  })
  
  output$isocoords <- renderText({
    str_c('<h4>Lon: ',
          round(isoCoords()[['lon']],4),' <br> ',
          'Lat: ',
          round(isoCoords()[['lat']],4), '</h4>')
  })
  
  isoCoords <- reactive({
    coords <- c(lat = Lat(),
                lon = Lng())
    print(coords)
    coords
  })
  
  isochrone <- eventReactive(input$submit, {
    withProgress(message = 'Sending Request',
                 isochrone <- osrmIsochrone(loc = c(isoCoords()[['lon']],
                                                    isoCoords()[['lat']]),
                                            breaks = as.numeric(input$driveTime),
                                            res = 40) %>%
                   st_as_sf()
    )
    isochrone
  })
  
  output$map <- renderLeaflet({

    leaflet(country())  %>%
      #addTiles('http://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png') 
      addTiles()
      
  })
  
  
  observeEvent(input$submit , {
    
    steps <- sort(as.numeric(input$driveTime))
    print(steps)
    isochrone <- cbind(steps = steps[isochrone()[['id']]], isochrone())
    pal <- colorFactor(viridis::plasma(nrow(isochrone), direction = -1),
                       isochrone$steps)
    
    # leafletProxy("map") %>%
    #   clearShapes() %>%
    #   clearMarkers() %>%
    #   clearControls() %>%
    #   addPolygons(data = isochrone,
    #               weight = .5,
    #               color = ~pal(steps)) %>%
    #   addLegend(data = isochrone,
    #             pal = pal,
    #             values = ~steps,
    #             title = 'Drive Time (min.)',
    #             opacity = 1) %>%
    #   addMarkers(lng = isoCoords()[['lon']], isoCoords()[['lat']]) %>%
    #   setView(isoCoords()[['lon']], isoCoords()[['lat']], zoom = 9)
  })

  observe({
    
    amenity<-country()
    lat_m <- mean(amenity$lat)
    lon_m <- mean(amenity$lon)
    leafletProxy("map") %>%
      #clearTiles() %>% 
      clearMarkers() %>%
      #addTiles('http://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png') %>% 
      #addProviderTiles(providers[[leaflet::providers$OpenStreetMap]]) %>% 
      setView(lon_m, lat_m, zoom = 6) %>% 
      addCircleMarkers(data = amenity, ~lon, ~lat,
                       popup = ~as.character(name), label = ~as.character(name),
                       clusterOptions = markerClusterOptions()
                       ) 

  })
  
  output$dlIsochrone <- downloadHandler(
    filename = function() {
      paste0("drivetime_isochrone", input$shapeOutput)
    },
    content = function(file) {
      st_write(isochrone(), file)
    }
  )
  
})