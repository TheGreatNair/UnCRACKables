import urllib.request
import json

LATITUDE = 13.0827
LONGITUDE = 74.7797

url = (
    f"https://api.open-meteo.com/v1/forecast"
    f"?latitude={LATITUDE}"
    f"&longitude={LONGITUDE}"
    f"&current=temperature_2m,relative_humidity_2m,wind_speed_10m"
)

try:
    # Fetch data using Python's built-in urllib
    with urllib.request.urlopen(url) as response:
        raw_data = response.read().decode('utf-8')
        data = json.loads(raw_data)

    current = data["current"]
    units = data["current_units"]

    temp = current["temperature_2m"]
    temp_unit = units["temperature_2m"]
    humidity = current["relative_humidity_2m"]
    wind = current["wind_speed_10m"]
    wind_unit = units["wind_speed_10m"]

    print("=" * 30)
    print("      LIVE WEATHER REPORT     ")
    print("=" * 30)
    print(f"Location    : {LATITUDE}, {LONGITUDE}")
    print(f"Temperature : {temp} {temp_unit}")
    print(f"Humidity    : {humidity}%")
    print(f"Wind Speed  : {wind} {wind_unit}")
    print("=" * 30)

except Exception as error:
    print(f"Error fetching data: {error}")