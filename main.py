import requests

# Get the temperature data from the API
url = "https://data.weather.gov.hk/weatherAPI/opendata/weather.php?dataType=rhrread&lang=en"
response = requests.get(url)
weather_data = response.json()

# Extract the temperature data of all stations
stations = weather_data["temperature"]["data"]

# Sort the stations by descending order of temperature
sorted_stations = sorted(stations, key=lambda x: x['value'], reverse=True)

# Display the temperature data of all stations
for station in sorted_stations:
    print(f"Station: {station['place']}, Temperature: {station['value']}°C")