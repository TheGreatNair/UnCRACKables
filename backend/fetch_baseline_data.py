# TurtleGuard: download the previous 30-day reference period from GFW.
# This is used only to calculate the alert threshold.

import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

import requests


API_URL = "https://gateway.api.globalfishingwatch.org/v3/4wings/report"

# The same final TurtleGuard monitoring zone.
TURTLE_ZONE = {
    "type": "Polygon",
    "coordinates": [
        [
            [74.74, 13.10],
            [74.79, 13.10],
            [74.81, 12.92],
            [74.76, 12.90],
            [74.74, 13.10],
        ]
    ],
}


def count_records(data):
    """Count records inside GFW's response."""
    count = 0

    for entry in data.get("entries", []):
        for value in entry.values():
            if isinstance(value, list):
                count += len(value)

    return count


def main():
    token = os.getenv("GFW_TOKEN")

    if not token:
        print("ERROR: GFW_TOKEN was not found.")
        print('Run: $env:GFW_TOKEN="your_token"')
        sys.exit(1)

    # Current file used: today minus 30 days to today.
    # Baseline: the 30 days immediately before that current window.
    baseline_end = date.today() - timedelta(days=30)
    baseline_start = baseline_end - timedelta(days=30)

    params = {
        "format": "JSON",
        "datasets[0]": "public-global-fishing-effort:latest",
        "group-by": "FLAG",
        "temporal-resolution": "DAILY",
        "spatial-aggregation": "true",
        "date-range": f"{baseline_start},{baseline_end}",
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Content-Language": "en-EN",
    }

    try:
        response = requests.post(
            API_URL,
            params=params,
            headers=headers,
            json={"geojson": TURTLE_ZONE},
            timeout=120,
        )
    except requests.RequestException as error:
        print("ERROR: Could not connect to Global Fishing Watch.")
        print(error)
        sys.exit(1)

    if not response.ok:
        print(f"ERROR: GFW returned status code {response.status_code}")
        print(response.text)
        sys.exit(1)

    try:
        baseline_data = response.json()
    except ValueError:
        print("ERROR: GFW returned a response that was not JSON.")
        print(response.text)
        sys.exit(1)

    output_file = Path(__file__).with_name("baseline_fishing_data.json")
    output_file.write_text(json.dumps(baseline_data, indent=2), encoding="utf-8")

    print("SUCCESS: Baseline fishing data saved.")
    print(f"Reference date range: {baseline_start} to {baseline_end}")
    print(f"Daily records returned: {count_records(baseline_data)}")
    print(f"Saved file: {output_file}")


if __name__ == "__main__":
    main()
