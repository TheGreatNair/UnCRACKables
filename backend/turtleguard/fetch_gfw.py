"""Shared Global Fishing Watch fetch helper. GFW_TOKEN stays in the environment."""

import json
import os
from datetime import date, timedelta
from pathlib import Path

import requests


API_URL = "https://gateway.api.globalfishingwatch.org/v3/4wings/report"
TURTLE_ZONE = {"type": "Polygon", "coordinates": [[[74.74, 13.10], [74.79, 13.10], [74.81, 12.92], [74.76, 12.90], [74.74, 13.10]]]}


def fetch(output_name: str, start: date, end: date) -> int:
    token = os.getenv("GFW_TOKEN")
    if not token:
        print("ERROR: GFW_TOKEN was not found.")
        return 1
    try:
        response = requests.post(
            API_URL,
            params={"format": "JSON", "datasets[0]": "public-global-fishing-effort:latest", "group-by": "FLAG", "temporal-resolution": "DAILY", "spatial-aggregation": "true", "date-range": f"{start},{end}"},
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json", "Content-Language": "en-EN"},
            json={"geojson": TURTLE_ZONE}, timeout=120,
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as error:
        print(f"ERROR: Could not fetch valid Global Fishing Watch data: {error}")
        return 1
    (Path(__file__).parent / output_name).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"SUCCESS: {output_name} saved for {start} to {end}.")
    return 0


def fetch_current() -> int:
    end = date.today()
    return fetch("fishing_data.json", end - timedelta(days=30), end)


def fetch_baseline() -> int:
    end = date.today() - timedelta(days=30)
    return fetch("baseline_fishing_data.json", end - timedelta(days=30), end)
