import requests

def get_turtle_nesting_weather(latitude: float, longitude: float):
    """
    Fetches temperature, humidity, and wind speed from Open-Meteo API.
    Does not require an API Key.
    """
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": ["temperature_2m", "relative_humidity_2m", "wind_speed_10m", "direct_normal_irradiance"],
        "hourly": ["temperature_2m", "soil_temperature_0cm"]
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching Open-Meteo data: {e}")
        return None

# Test call for Olive Ridley nesting beach coordinates (e.g., Rushikulya, Odisha: 19.3667, 85.0833)
if __name__ == "__main__":
    weather_data = get_turtle_nesting_weather(19.3667, 85.0833)
    print("Open-Meteo Data:", weather_data)
