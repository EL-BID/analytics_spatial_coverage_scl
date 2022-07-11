source("utils.R")
source("source.R")

navbarPage( title = "SCL-Lab", 
            id="nav",
            theme = shinytheme("simplex"),
              tabPanel("Project Readme",
                       fluidRow(
                         absolutePanel(title = "Project Readme", class = "panel panel-default",
                                       fixed = FALSE,
                                       draggable = FALSE, 
                                       left = "5%",
                                       right = "5%", 
                                       bottom = "auto",
                                       width =  "auto",
                                       height = "auto",
                                       column(12, 
                                              div(
                                                style = "width: 80%;",
                                                htmlOutput("readme2")))
                         ))),
              tabPanel("Map",
                       fluidRow(class="outer",
                                tags$head(
                                  includeCSS("styles.css")
                                ),
                                
                                # If not using custom CSS, set height of leafletOutput to a number instead of percent
                                leafletOutput("map", width="100%", height="100%"),
                                
                                absolutePanel(id = "controls", class = "panel panel-default", fixed = TRUE,
                                              draggable = TRUE, top = 60, left = "5%",
                                              right = 20, bottom = "auto",
                                              width = 330, height = "auto",
                                              h2("Social infrastructure"),
                                              #htmlOutput('isocoords'),
                                              br(),
                                              br(),
                                              
                                              h4(""),
                                              selectInput("country",
                                                          "Select Country",
                                                          append(c('All'),sort(countrylist)),
                                                          selected = "All"
                                              ),                          
                                              selectInput("amenity",
                                                          "Select Amenity",
                                                          c(#"Schools" = "school",
                                                            "Hospitals" = "hospital"),
                                                          selected = "hospital"),
                                              # selectInput("isochrone", "Show Isochrones:",
                                              #             c("False",
                                              #               "True"),
                                              #             selected = "True"),
                                              # selectInput("coverage", "Show Coverage:",
                                              #             c("False",
                                              #               "True"),
                                              #             selected = "True"),
                                              selectInput("population",
                                                          "Select population (Consider that this may take a couple of minutes.)",
                                                          c("Total population"='total_population',
                                                            "Women of reproductive age (15-49)"="women_of_reproductive_age_15_49",
                                                            "Elderly 60 plus"="elderly_60_plus",
                                                            "Youth 15 24"="youth_15_24"
                                                          ),
                                                          selected = "total_population"
                                              ),
                                              # ToDo(rsanchezavalos) - Too slow
                                              selectInput("driveTime",
                                                          "Drive Time (Consider that this may take a couple of minutes.)",
                                                          seq(15, 45, 15),
                                                          selected = c(30),
                                                          multiple = FALSE),
                                              p("Show Coverage:"),
                                              switchInput(inputId = "coverage",
                                                          value = TRUE),
                                              p("Show population:"),
                                              switchInput(inputId = "population_rb",
                                                          value = FALSE),
                                              p("Show amenities:"),                                              
                                              switchInput(inputId = "amenities_rb",
                                                          value = FALSE),
                                              
                                ),
                                tags$div(id="SCLData + OpenStreetMap services"),
                       ),
                fluidRow(absolutePanel(id = "results", 
                                       class = "panel panel-default", fixed = TRUE,
                                       draggable = TRUE, 
                                       right = "4%",
                                       bottom = "auto",
                                       width = "40%", 
                                       height = "90%",
                                       br(),
                                       h2("Coverage Results"),
                                       #h4(HTML("<p style='color:red;'>Results may change - undergoing validation- </p>")),
                                       
                                       p("Total Population: "),
                                       
                                       textOutput("population_count"),
                                       br(),
                                       
                                       p("Amenity infrastructure sites: "),
                                       textOutput("amenity_count"),
                                       dataTableOutput('table'),
                                       downloadButton("downloadData", "Download coverage results"))
                ))
)
