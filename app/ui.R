source("utils.R")
source("source.R")


navbarPage("SCL-Lab", id="nav",
           tabPanel("Social infrastructure",
                    div(class="outer",
                        tags$head(
                          # Include our custom CSS
                          includeCSS("styles.css")
                        ),
                        
                        # If not using custom CSS, set height of leafletOutput to a number instead of percent
                        leafletOutput("map", width="100%", height="100%"),
                        
                        absolutePanel(id = "controls", class = "panel panel-default", fixed = TRUE,
                                      draggable = TRUE, top = 60, left = "5%",
                                      right = 20, bottom = "auto",
                                      width = 330, height = "auto",
                                      h2("Social infrastructure"),
                                      #h4("Pick a location in the map"),
                                      htmlOutput('isocoords'),
                                      br(),
                                      br(),
                                      
                                      h4("Download Results"),
                                      selectInput("country",
                                                  "Select Country",
                                                  countries$country_name_en,
                                                  selected = "Guyana"
                                      ),                          
                                      selectInput("amenity",
                                                  "Select Amenity",
                                                  c("school" = "school",
                                                    "hospital" = "hospital"),
                                                  selected = "school"
                                      ),                                                                
                                      selectInput("driveTime",
                                                  "Drive Time (min.)",
                                                  seq(15, 30, 15),
                                                  selected = c(15),
                                                  multiple = FALSE)

                        ),
                        
                        tags$div(id="SCLData + OpenStreetMap services"
                        )
                    )
           )
)
