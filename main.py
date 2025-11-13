import json
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import requests

API_URL = "https://data.weather.gov.hk/weatherAPI/opendata/weather.php?dataType=rhrread&lang=en"
STATIONS_FILE = Path(__file__).with_name("HKONWS.json")
MAP_OUTPUT_FILE = Path(__file__).with_name("weather_map.html")
REQUEST_TIMEOUT = 10

COOL_RGB = (44, 123, 182)
HOT_RGB = (215, 25, 28)

STATION_NAME_ALIASES: Dict[str, str] = {
    "Chek Lap Kok": "Hong Kong International Airport",
}


def fetch_temperature_readings() -> List[Dict[str, float]]:
    """Fetch temperature readings from the Hong Kong Observatory API."""
    response = requests.get(API_URL, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    payload = response.json()
    stations = payload.get("temperature", {}).get("data", [])

    readings: List[Dict[str, float]] = []
    for station in stations:
        name = station.get("place")
        value = station.get("value")
        if name is None or value is None:
            continue
        try:
            temperature = float(value)
        except (TypeError, ValueError):
            continue
        readings.append({"name": name, "temperature": temperature})

    return readings


def load_station_coordinates() -> Dict[str, Tuple[float, float]]:
    """Load station coordinates from the local GeoJSON dataset."""
    if not STATIONS_FILE.exists():
        raise FileNotFoundError(f"Station metadata file not found: {STATIONS_FILE}")

    with STATIONS_FILE.open(encoding="utf-8") as source:
        data = json.load(source)

    coordinates: Dict[str, Tuple[float, float]] = {}
    for feature in data.get("features", []):
        properties = feature.get("properties", {})
        name = properties.get("Name_en")
        latitude = properties.get("Latitude")
        longitude = properties.get("Longitude")
        if name is None or latitude is None or longitude is None:
            continue
        try:
            coordinates[name] = (float(latitude), float(longitude))
        except (TypeError, ValueError):
            continue

    return coordinates


def merge_station_data(
    readings: Sequence[Dict[str, float]],
    coordinates: Dict[str, Tuple[float, float]],
) -> Tuple[List[Dict[str, float]], List[str]]:
    """Combine temperature readings with coordinate metadata."""
    merged: List[Dict[str, float]] = []
    missing: List[str] = []

    for entry in readings:
        name = entry["name"]
        lookup_name = STATION_NAME_ALIASES.get(name, name)
        coords = coordinates.get(lookup_name)
        if not coords:
            missing.append(name)
            continue
        latitude, longitude = coords
        merged.append(
            {
                "name": name,
                "temperature": entry["temperature"],
                "latitude": latitude,
                "longitude": longitude,
            }
        )

    return merged, missing


def format_temperature(value: float) -> str:
    """Format a temperature value for display."""
    if float(value).is_integer():
        return f"{int(value)}"
    return f"{value:.1f}"


def color_for_temperature(value: float, min_value: float, max_value: float) -> str:
    """Map a temperature value to a hex color string."""
    if max_value == min_value:
        ratio = 0.5
    else:
        ratio = (value - min_value) / (max_value - min_value)
    ratio = max(0.0, min(1.0, ratio))

    r = int(COOL_RGB[0] + (HOT_RGB[0] - COOL_RGB[0]) * ratio)
    g = int(COOL_RGB[1] + (HOT_RGB[1] - COOL_RGB[1]) * ratio)
    b = int(COOL_RGB[2] + (HOT_RGB[2] - COOL_RGB[2]) * ratio)
    return f"#{r:02x}{g:02x}{b:02x}"


def rgb_to_hex(rgb: Tuple[int, int, int]) -> str:
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"


def build_map_html(stations: Sequence[Dict[str, object]], min_temp: float, max_temp: float) -> str:
    """Generate an interactive Leaflet map as an HTML string."""
    stations_json = json.dumps(stations, ensure_ascii=False)
    min_label = format_temperature(min_temp)
    max_label = format_temperature(max_temp)
    cool_hex = rgb_to_hex(COOL_RGB)
    hot_hex = rgb_to_hex(HOT_RGB)

    return f"""<!DOCTYPE html>
<html lang=\"en\">
<head>
    <meta charset=\"utf-8\" />
    <title>Hong Kong Observatory Weather Map</title>
    <link rel=\"stylesheet\" href=\"https://unpkg.com/leaflet@1.9.4/dist/leaflet.css\" integrity=\"sha256-sA+sx2GddOBI1p5MNDoAuCEr0aKBslrG2WZ8wPz0iEk=\" crossorigin=\"\" />
    <style>
        html, body {{
            height: 100%;
            margin: 0;
        }}
        #map {{
            width: 100%;
            height: 100%;
        }}
        .legend {{
            position: absolute;
            bottom: 16px;
            left: 16px;
            background-color: rgba(255, 255, 255, 0.9);
            padding: 12px 16px;
            border-radius: 8px;
            box-shadow: 0 2px 6px rgba(0, 0, 0, 0.15);
            font-family: system-ui, -apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif;
        }}
        .legend .title {{
            font-size: 14px;
            font-weight: 600;
        }}
        .legend .gradient {{
            height: 10px;
            margin: 8px 0;
            background: linear-gradient(90deg, {cool_hex}, {hot_hex});
            border-radius: 4px;
        }}
        .legend .labels {{
            display: flex;
            justify-content: space-between;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div id=\"map\"></div>
    <div class=\"legend\">
        <div class=\"title\">Temperature (°C)</div>
        <div class=\"gradient\"></div>
        <div class=\"labels\">
            <span>{min_label}</span>
            <span>{max_label}</span>
        </div>
    </div>
    <script src=\"https://unpkg.com/leaflet@1.9.4/dist/leaflet.js\" integrity=\"sha256-o9N1j7kCqeHLf5gWFlNClUTKF5ki38qBC38yp3r1m08=\" crossorigin=\"\"></script>
    <script>
        const stations = {stations_json};
        const map = L.map('map');

        if (stations.length) {{
            const bounds = L.latLngBounds(stations.map((station) => [station.latitude, station.longitude]));
            map.fitBounds(bounds.pad(0.05));
        }} else {{
            map.setView([22.3193, 114.1694], 11);
        }}

        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            maxZoom: 18,
            attribution: '&copy; <a href=\"https://www.openstreetmap.org/\">OpenStreetMap</a> contributors'
        }}).addTo(map);

        stations.forEach((station) => {{
            const marker = L.circleMarker([station.latitude, station.longitude], {{
                radius: 8,
                fillColor: station.color,
                color: station.color,
                weight: 1,
                fillOpacity: 0.85
            }}).addTo(map);

            const popupContent = `<strong>${{station.name}}</strong><br/>Temperature: ${{station.displayTemperature}}&deg;C`;
            marker.bindPopup(popupContent);
            marker.bindTooltip(`${{station.name}}: ${{station.displayTemperature}}°C`);
        }});
    </script>
</body>
</html>
"""


def main() -> None:
    readings = fetch_temperature_readings()
    sorted_readings = sorted(readings, key=lambda entry: entry["temperature"], reverse=True)

    if not sorted_readings:
        print("No temperature readings were returned by the API.")
        return

    for entry in sorted_readings:
        print(f"Station: {entry['name']}, Temperature: {format_temperature(entry['temperature'])}°C")

    coordinates = load_station_coordinates()
    mapped_stations, missing = merge_station_data(sorted_readings, coordinates)

    if not mapped_stations:
        print("\nNo coordinate data available for the fetched stations. Map not generated.")
        if missing:
            print("Missing coordinates for: " + ", ".join(sorted(set(missing))))
        return

    min_temp = min(station["temperature"] for station in mapped_stations)
    max_temp = max(station["temperature"] for station in mapped_stations)

    for station in mapped_stations:
        station["color"] = color_for_temperature(station["temperature"], min_temp, max_temp)
        station["displayTemperature"] = format_temperature(station["temperature"])

    map_html = build_map_html(mapped_stations, min_temp, max_temp)
    MAP_OUTPUT_FILE.write_text(map_html, encoding="utf-8")
    print(f"\nInteractive map saved to {MAP_OUTPUT_FILE.resolve()}")

    if missing:
        print("\nStations without coordinate data: " + ", ".join(sorted(set(missing))))


if __name__ == "__main__":
    main()
