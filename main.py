import json
import folium
import requests

with open('HKONWS.json') as f:
    data = json.load(f)

m = folium.Map(location=[22.3193, 114.1694], zoom_start=11)

for feature in data['features']:
    if feature['properties']['TypesofWeatherStation_en'] == 'AUTOMATIC WEATHER STATION':
        latitude = feature['properties']['Latitude']
        longitude = feature['properties']['Longitude']
        temperature_data = data['temperature']['data']
        for temp in temperature_data:
            folium.Marker(location=[latitude, longitude],
                          popup=f"The current temperature in {temp['place']} is {temp['value']} degrees Celsius.").add_to(
                m)
