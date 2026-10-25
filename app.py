from flask import Flask, jsonify, request  # Or FastAPI equivalent
from weather import get_turtle_nesting_weather

app = Flask(__name__)

@app.route('/api/weather', methods=['GET'])
def weather_endpoint():
    # Read lat/lon from query parameters or default to nesting site coordinates
    lat = request.args.get('lat', default=19.3667, type=float)
    lon = request.args.get('lon', default=85.0833, type=float)
    
    weather_data = get_turtle_nesting_weather(lat, lon)
    if weather_data:
        return jsonify(weather_data), 200
    return jsonify({"error": "Failed to fetch weather data"}), 500

if __name__ == '__main__':
    app.run(port=5000, debug=True)
