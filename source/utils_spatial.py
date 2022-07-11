#!/usr/bin/python3
#!pip install backoff

import argparse
import backoff
import boto
import boto.s3
import boto3
import dotenv
import folium
import geojson
import geopandas as gpd
import io
import json
import mapclassify
import matplotlib.pyplot as plt
import numpy as np
import os 
import overpy
import pandas as pd
import requests
import shapely
import time
import zipfile

import branca.colormap as cm
from geojson import Feature, Point, FeatureCollection
from geopandas.tools import sjoin
from h3 import geo_to_h3, h3_to_geo_boundary
from shapely.geometry import Polygon
from collections import OrderedDict
from folium.plugins import MarkerCluster
from geopandas.tools import sjoin
from os import path
from OSMPythonTools.data import Data, dictRangeYears, ALL
from OSMPythonTools.nominatim import Nominatim
from OSMPythonTools.overpass import Overpass, overpassQueryBuilder
from pathlib import Path
from shapely.geometry import Point
from shapely.ops import unary_union
from wordcloud import WordCloud, STOPWORDS, ImageColorGenerator

import seaborn as sns


########
# ENV Load env variables
########
dotenv.load_dotenv()
sclbucket = os.environ.get("sclbucket")
scldatalake = os.environ.get("scldatalake")
access_token = os.environ.get("access_token_dp")
base_url = "https://api.mapbox.com/isochrone/v1/mapbox/"

########
# Countries
########
countries = pd.read_excel(scldatalake + 'Manuals and Standards/IADB country and area codes for statistical use/IADB_country_codes_admin_0.xlsx', engine='openpyxl')
countries = countries[~(countries.iadb_region_code.isna())]
countries = np.unique(countries.isoalpha3)

########
# API
########
overpass = Overpass()
api = overpy.Overpass()

s3 = boto3.resource('s3')
s3bucket = s3.Bucket(sclbucket)

########
# Coverage analysis
########

def create_coverage_dataset(world, amenity, population_, profile, minutes):
    """
    """
    
    # Load Population
    population = gpd.read_file(scldatalake + 
                               'Development Data Partnership/'+
                               'Facebook - High resolution population density map/'+
                               f'public-fb-data/geojson/LAC/{population_}_4'+
                               '.geojson')
    population = population[~(population.isoalpha3.isna()) & (population.isoalpha3.isin(countries))]
    population.population.sum()

    # Load isochrones
    # ToDo(rsanchezavalos) read from preprocess s3
    isochrones_data = pd.read_csv(f"../data/LAC_{amenity}_{profile}.csv")
    isochrones_data = isochrones_data[['isoalpha3', 'amenity', 'profile', 'minutes', 'multipolygon']]
    isochrones_data = isochrones_data[~(isochrones_data['multipolygon'].isna())]

    for minute in minutes:

        # Keep isochrones from selected time profile
        isochrone = isochrones_data[isochrones_data.minutes == int(minute)].reset_index()
        isochrone = isochrone[~(isochrone.multipolygon.isna())].reset_index()
        isochrone['geometry'] = gpd.GeoSeries.from_wkt(isochrone['multipolygon'])
        geom = gpd.GeoDataFrame(isochrone, geometry='geometry')
        geom = geom[['isoalpha3', 'amenity', 'profile', 'minutes', 'multipolygon', 'geometry']]

        # Quick Fix - some isochrones cover more than one country
        output = []
        for isoalpha3 in countries:
            gdf_match_iso = sjoin(population[population.isoalpha3==isoalpha3], geom[geom.isoalpha3==isoalpha3], how='left')
            output.append(gdf_match_iso)

            
        # ToDo(rsanchezavalos) Check population inconsistencies - gdf_match.population.sum()
        gdf_match = pd.concat(output)
        gdf_match.population.sum()
        del gdf_match['index_right']
        gdf_match.loc[(gdf_match.profile.isna()), 'profile'] = profile
        gdf_match.loc[(gdf_match.amenity.isna()), f'coverage_{minute}'] = 'uncovered'
        gdf_match.loc[~(gdf_match.amenity.isna()), f'coverage_{minute}'] = 'covered'
        gdf_match.loc[(gdf_match.population.isna()), 'population'] = 0
        gdf_match.loc[(gdf_match.minutes.isna()), 'minutes'] = minute
        gdf_match.loc[(gdf_match.amenity.isna()), 'amenity'] = amenity
        gdf_match['value'] = np.log(gdf_match.population)
        gdf_match.loc[(gdf_match['value']<0),'value']=0

        out = gdf_match.groupby(['amenity', f'coverage_{minute}'])['population'].sum().reset_index()
        out['pct'] = out.population/out.population.sum()*100

        # Spatial joinworld - state level
        # ToDo(rsanchezavalos)> calculate the spatial intersection to drop duplicates
        gdf_match = gdf_match.reset_index()
        gdf_match['index'] = gdf_match.index
        test = sjoin(gdf_match, world, how='left')
        test = test.drop_duplicates(['index'])
        
        # add national population
        level_1 = test.groupby(['isoalpha3','admin_name', f'coverage_{minute}'])['population'].sum().reset_index()
        t = level_1.groupby(['isoalpha3','admin_name'])['population'].sum().reset_index().rename(columns={'population':'poptot'})
        level_1 = level_1.merge(t, on=['isoalpha3','admin_name'], how='left')
        level_1['pct'] = level_1.population/level_1.poptot*100
        level_1 = level_1[level_1.isoalpha3.isin(list(geom.isoalpha3))]

        # fillna population for 100% coverage
        temp = (level_1.groupby(['isoalpha3', 'admin_name'])['poptot']
                .count().reset_index()
                .query('poptot == 1'))[['isoalpha3', 'admin_name']]
        temp[f'coverage_{minute}'] = 'uncovered'
        level_1 = level_1.merge(temp, on=['isoalpha3', 'admin_name', f'coverage_{minute}'], how='outer')
        level_1['poptot'] = level_1['poptot'].fillna(level_1.groupby(['isoalpha3', 'admin_name'])['poptot'].transform('max'))
        level_1['population'] = level_1['population'].fillna(0)
        level_1['pct'] = level_1['pct'].fillna(0)
        
        # filter only uncovered
        level_1 = level_1[level_1[f'coverage_{minute}']=='uncovered'].sort_values('population', ascending=False)

        country_result = world.merge(level_1, on=['isoalpha3','admin_name'], how='left')

        output_path = f"Geospatial infrastructure/Healthcare Facilities/coverage/coverage_{population_}_{minute}.csv"
        files = [object_ for object_ in s3bucket.objects.filter(Prefix=output_path)]

        if len(files) > 0:
            country_result.to_csv(scldatalake + output_path,index=False)
            print("File has been successfully uploaded to SCLData")

        else:
            country_result.to_csv(f'../data/coverage_{population_}_{minute}.csv',index=False)
            print('Please manually upload the file {0} in SCLData'.format(output_path))    
        return country_result


########
# Isochrone / Mapbox
########

def create_isochrone_analysis_countries(amenities_full, countrie0s, amenity, transport_profile, time_profiles):
    """
    Creates a table with concatenated lists of infrastructure for a list of countries in the dataset.
    Grouped by country, mode of transport and time profile
    """
    
    isochrones = []
    for isoalpha3 in countries:
        amenities_iso = amenities_full[amenities_full.isoalpha3 == isoalpha3].reset_index(drop=True)
        try:
            project_name = f'{isoalpha3}_{amenity}' 
            isochrones_data = create_isochrone_analysis(data = amenities_iso, project_name=project_name,
                                                        output_folder='../data', token=access_token, 
                                                        profile=transport_profile, time_profiles=time_profiles)    
            isochrones_data['isoalpha3'] = isoalpha3
            isochrones_data['amenity'] = amenity
            isochrones.append(isochrones_data)  
            print('success ' + isoalpha3)
        except Exception as e: 
            print('Error ' + isoalpha3)
            print(e)

    output = pd.concat(isochrones)
    
    return output


def create_isochrone_analysis(data, project_name, token,
                              profile, time_profiles,
                              output_folder='../data'):
    """
    """
    result = pd.DataFrame({'profile': [profile] * len(time_profiles),'minutes': time_profiles})
    result['geometry'] = None
    result['FeatureCollection'] = None
    result['multipolygon'] = None
    
    # Run for each profile * time_profiles
    for i in result.index:
        try:
            geom_ = create_isochrones(data, project=project_name, output_folder='../data', 
                                      force=True, token=token, profile=profile, minutes=time_profiles[i])
            result.at[i, 'geometry'] = geom_
            result.at[i, 'FeatureCollection'] = geojson.FeatureCollection(geom_)
            geom_ = gpd.GeoDataFrame.from_features(geom_)
            union_ = shapely.ops.unary_union(geom_['geometry'].tolist())
            result.at[i, 'multipolygon'] = union_
        except Exception as e: 
            print(e)
            try:
                geom_ = create_isochrones(data, project=project_name, output_folder='../data', 
                                          force=True, token=token, profile=profile, minutes=time_profiles[i])
                result.at[i, 'geometry'] = geom_
                result.at[i, 'FeatureCollection'] = geojson.FeatureCollection(geom_)
                geom_ = gpd.GeoDataFrame.from_features(geom_)
                union_ = shapely.ops.unary_union(geom_['geometry'].tolist())
                result.at[i, 'multipolygon'] = union_
            except:                
                pass

    return result.sort_values('minutes',ascending=False).reset_index(drop=True)

def create_isochrones(df, project, output_folder, token,
                      profile='driving', minutes=30, limit=None, generalize=0, force=False):
    """
    """    

    output = f'{project}_isochrone_{profile}_{minutes}'
    
    print("Output: "+ output)

    features = []
    skipped = 0

    # Fix for NAN error when serializing to JSON
    df = df.fillna('')
    
    if not ('lat' in df.columns and 'lon' in df.columns):
        print("Missing lat and lon columns")
        return
    
    gdf = gpd.GeoDataFrame(df.drop(['lon', 'lat'], axis=1),
                            crs={'init': 'epsg:4326'},
                            geometry=[Point(xy) for xy in zip(df.lon, df.lat)])

    for i, row in gdf.iterrows():
        if  limit == None or i <  limit:
            try:
                iso = isochrone(row.geometry.x, row.geometry.y,  profile,
                                    minutes,  generalize,  token, base_url)
                if iso:
                    iso['properties'] = row.drop('geometry').to_dict()
                    features.append(iso)
                else:
                    skipped = skipped + 1
                    
            except Exception as e: 
                # Catch query exceeds time limit sleep and retry
                print(e)
                time.sleep(5)
                try:
                    iso = isochrone(row.geometry.x, row.geometry.y,  profile,
                                        minutes,  generalize,  token, base_url)
                    if iso:
                        iso['properties'] = row.drop('geometry').to_dict()
                        features.append(iso)
                    else:
                        skipped = skipped + 1
                except:
                    pass

    return features

def isochrone(x, y, profile, minutes, generalize, token, base_url):
    """
    """
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
    """
    """
    print(f'Getting isochrone {url}')
    r = requests.get(url)
    r.raise_for_status()
    return r

########
# Population / Facebook
########

def get_hex_isoalpha(scldatalake, population, resolution, isoalpha3):
    """
    """
    
    population = pd.read_csv(scldatalake + 
                             f'Development Data Partnership/Facebook - High resolution population density map/public-fb-data/csv/{isoalpha3}/{isoalpha3}_{population_}.csv.gz',
                            sep='\t').rename(columns={'latitude':'lat', 'longitude':'lon'})
    population["hex_id"] = population.apply(lambda x: geo_to_h3(x["lat"], x["lon"], resolution), axis=1)
    population = population.groupby('hex_id').agg({'population':sum}).reset_index()
    population['hex'] = population['hex_id'].apply(lambda x: h3_to_geo_boundary(x, geo_json=True))
    population['hex_poly'] = population['hex'].apply(lambda x: Polygon(x))
    population['isoalpha3'] = isoalpha3
    population['population_type'] = population_
    gs = gpd.GeoSeries(population['hex_poly'])
    gdf = gpd.GeoDataFrame(population, geometry=gs, crs="EPSG:4326")
    gdf = gdf[['hex_id', 'population', 'isoalpha3', 'population_type', 'geometry']]
    
    return gdf

########
# Amenities / OSM
########

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
    """
    """    
    results = []
    for amenity in amenities:
        try:
            results.append(get_country_amenity(isoalpha3, amenity))
        except:
            try:
                time.sleep(5)
                results.append(get_country_amenity(isoalpha3, amenity))
            except:
                print(f'Error for {isoalpha3} - amenity {amenity}')

    result = pd.concat(results).reset_index(drop=True)
    return result


def get_countries_amenities(amenities, countries, output_path):
    """
    """
    s3 = boto3.resource('s3')
    s3bucket = s3.Bucket(sclbucket)
    
    db = {}
    for isoalpha3 in countries:
        if isoalpha3 not in [*db.keys()]:
            try:
                db[isoalpha3] = get_country_amenities(isoalpha3, amenities) 
            except:
                time.sleep(5)
                db[isoalpha3] = get_country_amenities(isoalpha3, amenities) 
                pass

    temp = pd.concat(db)
    temp = temp.reset_index().rename(columns={'level_0':'isoalpha3'})

    path = '_'.join(amenities)
    files = [object_ for object_ in s3bucket.objects.filter(Prefix=output_path )]

    if len(files) > 0:
        temp.to_csv(scldatalake + output_path,
                    index=False)
        print("File has been successfully uploaded to SCLData")

    else:
        print('Please upload *manually* the file {0} to SCLData'.format(output_path))
        temp.to_csv(f'../data/OSM_{path}_LAC.csv',
                    index=False)   
    return temp
        

########
# Maps and readers
########
   

def get_basemap(level='0'):
    """
    """
    if level == '0':
        world = gpd.read_file(scldatalake +
                              'Geospatial Basemaps/Cartographic Boundary Files/world/level-0/world-level-0.zip')
        world = world.rename(columns={"iso3":"isoalpha3"})
        return world
    
    elif level == '1':
        world = gpd.read_file(scldatalake +
                              'Geospatial Basemaps/Cartographic Boundary Files/world/level-1/world-level-1.zip')
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


########
# Utilities
########
def get_dictionary(collection='census'):
    """
    """    
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
        
########
# Plots
########

def plot_lat_lon(data, method='plt', zoom_start=7):
    """
    """    
    if method=='plt':
        coords  = []
        coords += [(float(data.lon[node]), float(data.lat[node])) for node in range(len(data))]
        print(len(coords))
        X = np.array(coords)
        plt.plot(X[:, 0], X[:, 1], 'o')
        plt.xlabel('Longitude')
        plt.ylabel('Latitude')
        plt.axis('equal')

        return plt.show()
    
    elif method=='folium':
        lat_mean = np.mean(data['lat'])
        lon_mean = np.mean(data['lon'])

        m = folium.Map(location=[lat_mean,lon_mean], zoom_start=zoom_start, tiles='CartoDB positron')
        marker_cluster = MarkerCluster().add_to(m)        
        for index, x in data.iterrows():
            
            folium.Marker([x["lat"], x["lon"]]).add_to(marker_cluster)
            
        return m

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

def plot_isochone_points(facility_data, isochrones_data, zoom_start, geom='FeatureCollection'):
    """
    """
    lat_mean = np.mean(facility_data['lat'])
    lon_mean = np.mean(facility_data['lon'])

    m = folium.Map(location=[lat_mean,lon_mean], zoom_start=zoom_start, tiles='CartoDB positron')
    marker_cluster = MarkerCluster().add_to(m)
    color = ['#999999', '#bcbddc', '#ef8a62']
    for i, x in isochrones_data.iterrows():
        fillColor = color[i]
        folium.GeoJson(data=x[geom], name=x['profile'],
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

