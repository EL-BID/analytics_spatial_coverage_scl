**SCL Data - Data Ecosystem Working Group**


<center>
<p float="left">
  <img src="https://scldata.iadb.org/assets/iadb-7779368a000004449beca0d4fc6f116cc0617572d549edf2ae491e9a17f63778.png" width="17%" style="margin:50px 50px">
  <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/1/1f/Mapbox_logo_2019.svg/1200px-Mapbox_logo_2019.svg.png" width="20%" style="margin:50px 50px">
</p>
</center>

<h1 align="center"> Spatial coverage of social infrastructure  </h1>


## Index:
--- 
- [Description and Context](#description-and-context)
- [Structure](#structure)
- [Methodology](#methodology)
- [Author(s)](#authors)

## Description and Context
---

The objective of this project is to create a tool to visualize the status of social infrastructure coverage in different countries of Latin America and the Caribbean region. We say that the population is not covered when, given its geographic location and a certain driving time, it cannot access the selected service.

This tool will be beneficial to give an initial assessment of infrastructure availability in the region, guide research, and the possible orientation of public policy decisions.

This analysis focuses on the coverage of education and health facilities. For each country and region we show the percentage of uncovered people for each type of infrastructure. 

The data from facilities is obtained from official sources when available, and from Open Street Maps (OSM) in case public information is not found.  
The information from the population of interest is obtained from the Facebook project - High-resolution population density maps. 
Finally, we use the Mapbox API to calculate the isochrones and determine the percentage of the population that is not covered using a driving time of 15,30 and 45 minutes.

Combining said sources we perform spatial join to identify the population without access to the service with the defined profile.


## Structure
---

This repository contains the code of the *Spatial coverage of social infrastructure tool.* 

- [Shiny app](https://bid-data.shinyapps.io/infrastructure_coverage/)

- [Code](https://github.com/BID-DATA/analytics_spatial_coverage_scl)


## Methodology
---

-	We created a database of amenities for each social infrastructure.

- For this study we defined *coverage* with three driving profiles *15,30 and 45 minutes* by private transport from at least one social service infrastructure. 

-	We used the Mapbox API to calculate distance measurements to each georeference using the desired profile and time. 

- We used the High-Resolution Population Density Map to obtain a location layer of the population of interest in order to perform the coverage analysis.

- The population outside the proximity polygons were identified. 

-	Outcome metrics were created at the national level and state level to identify the population without coverage.


### Authors
- [Roberto Sánchez A.](https://github.com/rsanchezavalos)
- [Luis Tejerina.](https://github.com/luistejerina)
- [María Reyes Retana](https://github.com/mariarrt94)
