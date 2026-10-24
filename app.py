from datetime import datetime, timedelta, timezone
import folium

print("Generating night lights map...")

# 1. Initialize map centered over India / Global view
# [latitude, longitude], zoom_start controls initial zoom level
m = folium.Map(
    location=[20.5937, 78.9629],
    zoom_start=5,
    tiles=None,  # Disable default bright OpenStreetMap layer
    max_zoom=8,
)

# 2. Add NASA Black Marble (Processed composite night lights)
black_marble_url = (
    "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/"
    "VIIRS_Black_Marble/default/2016-01-01/GoogleMapsCompatible_Level8/{z}/{y}/{x}.png"
)

folium.TileLayer(
    tiles=black_marble_url,
    name="NASA Black Marble (Clear Composite)",
    attr="NASA EOSDIS GIBS",
    max_zoom=8,
    overlay=False,
    control=True,
).add_to(m)

# 3. Add Near Real-Time Daily VIIRS Night Lights (Yesterday's scan)
yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
daily_dnb_url = (
    f"https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/"
    f"VIIRS_SNPP_DayNightBand_ENCC/default/{yesterday}/GoogleMapsCompatible_Level8/{{z}}/{{y}}/{{x}}.jpg"
)

folium.TileLayer(
    tiles=daily_dnb_url,
    name=f"Daily VIIRS Night Scan ({yesterday})",
    attr="NASA EOSDIS GIBS",
    max_zoom=8,
    overlay=False,
    control=True,
).add_to(m)

# 4. Add city/country boundary reference labels (so you can identify places)
folium.TileLayer(
    tiles="https://{s}.basemaps.cartocdn.com/dark_only_labels/{z}/{x}/{y}{r}.png",
    name="City & Border Labels",
    attr="CartoDB",
    overlay=True,
    control=True,
).add_to(m)

# 5. Add layer toggle control in the top-right corner
folium.LayerControl().add_to(m)

# 6. Save the output as an HTML file
output_file = "night_lights_map.html"
m.save(output_file)

print(f"Success! Map saved as '{output_file}'.")
print("Open this file in your browser to view the interactive night map.")