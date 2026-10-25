// utils/weather.ts
export interface WeatherData {
  temperature_2m: number;
  relative_humidity_2m: number;
  wind_speed_10m: number;
}

export async function fetchLiveWeather(lat: number = 19.3667, lon: number = 85.0833): Promise<WeatherData | null> {
  try {
    const res = await fetch(
      `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&current=temperature_2m,relative_humidity_2m,wind_speed_10m`
    );
    if (!res.ok) throw new Error("Failed to fetch weather");
    const data = await res.json();
    return data.current;
  } catch (err) {
    console.error("Open-Meteo fetch error:", err);
    return null;
  }
}
