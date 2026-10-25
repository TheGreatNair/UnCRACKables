# TurtleGuard backend handoff

## Base URL

During local development, the backend is `http://127.0.0.1:8000` on the computer running FastAPI.

`127.0.0.1` works only when the Expo app runs on that same computer. A physical phone must use the computer's LAN IP address after the backend is intentionally exposed to the local network.

## Endpoints

### `GET /turtleguard/status`

Returns the latest saved TurtleGuard result. It reads the local `turtleguard_summary.json` file, so it works without internet access and does not call Global Fishing Watch.

Success: `200 OK`

```json
{
  "zone_name": "TurtleGuard Dakshina Kannada Offshore Zone",
  "days_per_period": 30,
  "zone_area_km2": 116.85,
  "current_total_apparent_fishing_hours": 35.72,
  "current_density_hours_per_km2_per_day": 0.010189,
  "reference_total_apparent_fishing_hours": 4.77,
  "reference_density_hours_per_km2_per_day": 0.001359,
  "alert_multiplier": 1.5,
  "threshold_density_hours_per_km2_per_day": 0.002039,
  "activity_ratio": 7.5,
  "risk_status": "high",
  "message": "ALERT: High fishing activity near the turtle zone. Notify coastal patrol.",
  "source": "Global Fishing Watch",
  "note": "AIS-derived apparent fishing effort; small vessels without AIS may be missing."
}
```

Possible error: `404 Not Found` when no saved summary exists yet.

### `POST /turtleguard/refresh`

No request body. Downloads the current and previous 30-day GFW data, recalculates the risk, saves the summary, then returns it. This endpoint needs internet access and a valid private `GFW_TOKEN` environment variable on the backend computer.

Success: `200 OK`

```json
{
  "message": "TurtleGuard data refreshed successfully.",
  "summary": { "risk_status": "high" },
  "logs": {
    "baseline_fetch": "...",
    "current_fetch": "...",
    "calculation": "..."
  }
}
```

Failure: `502 Bad Gateway` if GFW cannot be contacted, rejects the request, returns invalid data, or the backend has no token. The app must keep showing the last successful `GET /status` result and state that refresh failed.

## App behavior

1. On launch, call `GET /turtleguard/status` and show the saved alert.
2. The Refresh button calls `POST /turtleguard/refresh`.
3. While refreshing, disable the button and show a loading state.
4. On a `200`, replace the displayed result with `response.summary`.
5. On a refresh error, retain the previous result and show a short connection/data-update error.

## Meaning and limitations

* `risk_status` may be `high`, `low`, or `needs_more_reference_data`.
* `alert_multiplier` is a **prototype calibration parameter**. Its current value of `1.5` means current apparent fishing-effort density must be at least 1.5 times the previous 30-day density to mark the risk as high.
* Global Fishing Watch data is AIS-derived apparent fishing effort. It is not proof of illegal fishing.
* Small vessels without AIS can be absent from the data.
* Data is updated regularly, not in real time.
* Credit **Global Fishing Watch** in the app's data/source text.

## Security

The mobile app must never contain `GFW_TOKEN`. Only the Python backend reads it from its environment.
