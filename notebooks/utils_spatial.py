#!/usr/bin/env python3
#!pip install geopandas
#!pip install wordcloud
#!pip install OSMPythonTools
#!pip install overpy
# !pip install folium
#!pip install pyshp
#!pip install folium

#!/usr/bin/python3

from pathlib import Path
import requests
import backoff
import geojson
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
import argparse

import overpy
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import folium
from OSMPythonTools.nominatim import Nominatim
from OSMPythonTools.overpass import Overpass, overpassQueryBuilder
from OSMPythonTools.data import Data, dictRangeYears, ALL
from collections import OrderedDict
from folium.plugins import MarkerCluster

overpass = Overpass()
api = overpy.Overpass()

import zipfile
import io
import io
#import shapefile
#import folium
import boto
import boto.s3
import os 
import numpy as np
import pandas as pd
from os import path
import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
#import utils_py as utils

from wordcloud import WordCloud, STOPWORDS, ImageColorGenerator
import matplotlib.pyplot as plt

# Data Lake path
import dotenv
dotenv.load_dotenv()

scldatalake = os.environ.get("scldatalake")
access_token = os.environ.get("access_token")
base_url = "https://api.mapbox.com/isochrone/v1/mapbox/"



def isochrone(x, y, profile, minutes, generalize, token, base_url):
    if not x or not y:
        print("Missing coordinates, skipping")
        return
    url = f'{base_url}{profile}/{x},{y}?contours_minutes={minutes}&generalize={generalize}&polygons=true&access_token={token}'
    response = request_isochrone(url).json()
    if 'features' in response:
        return response['features'][0]
    else:
        print("Issue creating isochrone, skipping", response)
        return


def request_isochrone(url):
    print(f'Getting isochrone {url}')
    r = requests.get(url)
    r.raise_for_status()
    return r


def create_isochrone_analysis(data, project_name=project_name,
                              output_folder='../data', token=token, 
                              profile=profile, time_profiles=time_profiles):
    """
    """
    result = pd.DataFrame({'profile': [profile] * len(time_profiles),'minutes': time_profiles})
    result['geometry'] = None
    for i in temp.index:
        print(time_profiles[i])
        result.at[i, 'geometry'] = create_isochrones(data, project=project_name, output_folder='../data', 
                                                   force=True, token=token, profile=profile, minutes=time_profiles[i])
    return result.sort_values('minutes',ascending=False).reset_index(drop=True)

def create_isochrones(df, project, output_folder, token,
                      profile='driving', minutes=30, limit=None, generalize=0, force=False):

    output = f'{output_folder}/{project}_isochrone_{profile}_{minutes}.json'
    
    print("Output: "+output)
    
    if (Path(output).exists()):
        if force:
            print("File already exists, overwriting!")
        else:
            print("File already exists, exiting. To overwrite, run with --force.")
            return

    with open(output, 'w') as output_file:
        features = []
        skipped = 0

        # Fix for NAN error when serializing to JSON
        df = df.fillna('')
        # TODO Support more default column names, or use args to define column name for each a la ogr2ogr
        if not ('lat' in df.columns and 'lon' in df.columns):
            print("Missing lat and lon columns")
            return
        gdf = gpd.GeoDataFrame(df.drop(['lon', 'lat'], axis=1),
                               crs={'init': 'epsg:4326'},
                               geometry=[Point(xy) for xy in zip(df.lon, df.lat)])

        for i, row in gdf.iterrows():
            if  limit == None or i <  limit:
                iso = isochrone(row.geometry.x, row.geometry.y,  profile,
                                 minutes,  generalize,  token, base_url)
                if iso:
                    iso['properties'] = row.drop('geometry').to_dict()
                    features.append(iso)
                else:
                    skipped = skipped + 1

        feature_collection = geojson.FeatureCollection(features)
        geometry = features.unary_union
        #output_file.write(geojson.dumps(feature_collection, sort_keys=True))
        return feature_collection, geometry

def get_country_amenity(isoalpha3, amenity):   
    """
    """
    query = f'''
            area["ISO3166-1:alpha3"="{isoalpha3}"]->.a;
            ( node(area.a)[amenity={amenity}];
              way(area.a)[amenity={amenity}];
              rel(area.a)[amenity={amenity}];);
            out center;
            '''
    r = api.query(query)
    
    coords_node = pd.DataFrame([{'id': node.id, 
                                 'lon': node.lon, 'lat': node.lat} 
                           for node in r.nodes]).reset_index()
    coords_way = pd.DataFrame([{'id': way.id, 'lon': way.center_lon, 'lat': way.center_lat}
                              for way in r.ways]).reset_index()
    coords_relation = pd.DataFrame([{'id': relation.id, 'lon': relation.center_lon, 'lat': relation.center_lat}
                              for relation in r.relations]).reset_index()

    metadata_node =  pd.DataFrame([node.tags
                              for node in r.nodes]).reset_index()
    metadata_way = pd.DataFrame([way.tags
                              for way in r.ways]).reset_index()
    metadata_relation = pd.DataFrame([way.tags
                              for way in r.relations]).reset_index()

    output_node = coords_node.merge(metadata_node, on='index').drop('index', axis=1)
    output_way = coords_way.merge(metadata_way, on='index').drop('index', axis=1)
    output_relation = coords_relation.merge(metadata_relation, on='index').drop('index', axis=1)
    output_tot = pd.concat([output_node, output_way, output_relation])
    
    return output_tot

def get_country_amenities(isoalpha3, amenities):
    results = []
    for amenity in amenities:
        try:
            results.append(get_country_amenity(isoalpha3, amenity))
        except:
            print(f'Error for {isoalpha3} - amenity {amenity}')
    result = pd.concat(results).reset_index(drop=True)
    return result
        
        
    
def get_dictionary(collection='census'):
    if collection=='census':
        dictionary = pd.read_csv(scldatalake +
                                         'Population and Housing Censuses/Population and Housing Censuses Indicators/D.7.2.1 Diccionario - indicadores de censos de población.csv')
        return dictionary
    
    
def get_indicators(collection, level):
    """
    """
    if collection=='census':
        if level=='0':
            # Read indicators
            indicators = pd.read_csv(scldatalake +
                                     'Population and Housing Censuses/Population and Housing Censuses Indicators/indicadores_censos.csv', encoding='latin1')
            return indicators
        
        elif level=='1':
            indicators = pd.read_csv(scldatalake +
                                     'Population and Housing Censuses/Population and Housing Censuses Indicators/indicadores_censos-level-01.csv', encoding='latin1')
            indicators['geolevel1'] = indicators['geolev1'].astype(str)

            return indicators
        
        elif level=='2':
            indicators = pd.read_csv(scldatalake +
                                     'Population and Housing Censuses/Population and Housing Censuses Indicators/indicadores_censos-level-02.csv', encoding='latin1')
            indicators['geolevel2'] = indicators['geolev2'].astype(str)
            
            return indicators
    

def get_basemap(level='0'):

    if level == '0':
        world = gpd.read_file(scldatalake +
                              'Geospatial Basemaps/Cartographic Boundary Files/world/level-0/world-level-0.zip')
        world = world.rename(columns={"iso3":"isoalpha3"})
        return world
    
    elif level == '1':
        world = gpd.read_file(scldatalake +
                              'Geospatial Basemaps/Cartographic Boundary Files/LAC/level-1/IPUMS/world_geolev1_2021.zip')
        world = world.rename(columns={"iso3":"isoalpha3"})
        world.columns = [x.lower() for x in world.columns]        
        return world
    
    elif level == '2':
        world = gpd.read_file(scldatalake +
                              'Geospatial Basemaps/Cartographic Boundary Files/LAC/level-2/IPUMS/world_geolev2_2021.zip')
        world = world.rename(columns={"iso3":"isoalpha3"})
        world.columns = [x.lower() for x in world.columns]        
        return world

def read_shapefile(shp_path):
    """
    """

    blocks = sc.binaryFiles(shp_path)
    block_dict = dict(blocks.collect())

    sf = shapefile.Reader(shp=io.BytesIO(block_dict[[i for i in block_dict.keys() if i.endswith(".shp")][0]]),
                              shx=io.BytesIO(block_dict[[i for i in block_dict.keys() if i.endswith(".shx")][0]]),
                              dbf=io.BytesIO(block_dict[[i for i in block_dict.keys() if i.endswith(".dbf")][0]]))

    fields = [x[0] for x in sf.fields][1:]
    records = sf.records()
    shps = [s.points for s in sf.shapes()]
    center = [shape(s).centroid.coords[0] for s in sf.shapes()]

    #write into a dataframe
    df = pd.DataFrame(columns=fields, data=records)
    df = df.assign(coords=shps, centroid=center)

    return df


def get_indicator(indicators, indicador, tema, tiempo_id,
                  nivel_id, geografia_id, clase, clase_id):
    """
    """
    
    indicators = indicators.loc[(indicators.tema==tema) & 
                            (indicators.tiempo_id==tiempo_id) &
                            (indicators.nivel_id == nivel_id) &
                           (indicators.geografia_id == geografia_id) & 
                           (indicators.clase == clase) &                                 
                           (indicators.clase_id== clase_id)]
    
    indicators = indicators.loc[(indicators.indicador == indicador)]
    indicators = indicators[["pais_id", "valor"]].drop_duplicates()
    
    indicators =indicators.rename(columns={"pais_id":"isoalpha3",
                                          "valor":"value"})
    return indicators

#############################

def plot_lat_lon(data):
    coords  = []
    coords += [(float(data.lon[node]), float(data.lat[node])) for node in range(len(data))]
    print(len(coords))
    X = np.array(coords)
    plt.plot(X[:, 0], X[:, 1], 'o')
    plt.xlabel('Longitude')
    plt.ylabel('Latitude')
    plt.axis('equal')
    
    return plt.show()

def geo_plot(world, data, indicator):
    """
    """
    
    world = world.merge(data, on='isoalpha3', how="left")
    world = world.loc[~(world.value.isna())]
    
    world["tooltip"] = world["isoalpha3"] +': \n'+ world["value"].astype(str)
    bins = (world['value'].quantile([0, 0.25, 0.5, 0.75, 1])).tolist()

    m = folium.Map(location=[-6.3773968,-82.3965406], 
                   zoom_start=3)

    choropleth = folium.Choropleth(
        geo_data=world.to_json(),
        name="choropleth",
        data=world,
        columns=["isoalpha3", "value"],
        key_on="feature.properties.isoalpha3",
        fill_color="BuPu",
        bins=bins,
        reset=True,
        fill_opacity=0.7,
        line_opacity=0.2,
        legend_name=indicator).add_to(m)
    
    folium.LayerControl().add_to(m)
    choropleth.geojson.add_child(folium.features.GeoJsonTooltip(['tooltip'], labels=False))

    return m




def geo_simple_plot(world):
    """
    """
    
    m = folium.Map(location=[-6.3773968,-82.3965406], 
                   zoom_start=3)

    choropleth = folium.Choropleth(
        geo_data=world.to_json(),
        name="choropleth",
        data=world,
        columns=["LocationNa", "value"],
        key_on="feature.properties.isoalpha3",
        fill_color="BuPu",
        bins=bins,
        reset=True,
        fill_opacity=0.7,
        line_opacity=0.2,
        legend_name=indicator).add_to(m)
    
    folium.LayerControl().add_to(m)
    choropleth.geojson.add_child(folium.features.GeoJsonTooltip(['tooltip'], labels=False))

    return m


def geo_simple_plot_old(world):
    """
    """
    
    m = folium.Map(location=[-6.3773968,-82.3965406], 
                   zoom_start=3)

    choropleth = folium.Choropleth(
        geo_data=world.to_json(),
        name="choropleth",
        data=world,
        columns=["LocationNa", "value"],
        key_on="feature.properties.isoalpha3",
        fill_color="BuPu",
        bins=bins,
        reset=True,
        fill_opacity=0.7,
        line_opacity=0.2,
        legend_name=indicator).add_to(m)
    
    folium.LayerControl().add_to(m)
    choropleth.geojson.add_child(folium.features.GeoJsonTooltip(['tooltip'], labels=False))

    return m

def plot_isochone_points(facility_data, isochrones_data, zoom_start):
    """
    """
    lat_mean = np.mean(facility_data['lat'])
    lon_mean = np.mean(facility_data['lon'])

    m = folium.Map(location=[lat_mean,lon_mean], zoom_start=zoom_start, tiles='CartoDB positron')
    marker_cluster = MarkerCluster().add_to(m)
    color = ['#999999', '#bcbddc', '#ef8a62']
    for i, x in isochrones_data.iterrows():
        fillColor = color[i]
        folium.GeoJson(data=x['geometry'], name=x['profile'],
                       style_function=lambda x,
                       fillColor=fillColor, color=fillColor: {
                           "fillColor": fillColor,
                            'weight': 2,
                            'opacity': 1,
                            'color': 'white',
                            'fillOpacity': 0.7
                       }).add_to(marker_cluster)


    for index, x in facility_data.iterrows():
        folium.Marker([x["lat"], x["lon"]], popup=x["name"]).add_to(marker_cluster)
    return m

#aws s3api put-object-tagging --bucket cf-p-scldata-prod-s3-p-scldata-app --key 'Labour Force Surveys/MEX-ENOE/2018/t1/data_orig/VIVT118.dta' --tagging 'TagSet=[{Key=riskType,Value=myValue}]'

#s3://cf-p-scldata-prod-s3-p-scldata-app/
    
    
    