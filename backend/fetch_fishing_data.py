# TurtleGuard: download apparent fishing-effort data from Global Fishing Watch.
# The GFW token stays private in the GFW_TOKEN environment variable.

import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

import requests


# Official Global Fishing Watch 4Wings report endpoint.
API_URL = "https://gateway.api.globalfishingwatch.org/v3/4wings/report"

# Our approximate offshore monitoring zone near Dakshina Kannada.
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


def get_error_message(response):
    """Try to show GFW's useful error message."""
    try:
        return json.dumps(response.json(), indent=2)
    except ValueError:
        return response.text


def count_daily_records(data):
    """Count the daily records returned inside GFW's response."""
    count = 0

    for entry in data.get("entries", []):
        # GFW usually stores records inside the dataset name.
        for value in entry.values():
            if isinstance(value, list):
                count += len(value)

    return count


def main():
    # Read the private token set in the PowerShell terminal.
    token = os.getenv("GFW_TOKEN")

    if not token:
        print("ERROR: GFW_TOKEN was not found.")
        print('Run: $env:GFW_TOKEN="your_token"')
        sys.exit(1)

    # Ask for the latest 30 calendar days.
    end_date = date.today()
    start_date = end_date - timedelta(days=30)

    params = {
        "format": "JSON",
        "datasets[0]": "public-global-fishing-effort:latest",
        "group-by": "FLAG",
        "temporal-resolution": "DAILY",
        "spatial-aggregation": "true",
        "date-range": f"{start_date},{end_date}",
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
        print(f"ERROR: Could not connect to Global Fishing Watch.\n{error}")
        sys.exit(1)

    if not response.ok:
        print(f"ERROR: GFW returned status code {response.status_code}")
        print(get_error_message(response))
        sys.exit(1)

    try:
        fishing_data = response.json()
    except ValueError:
        print("ERROR: GFW returned a response that was not JSON.")
        print(response.text)
        sys.exit(1)

    # Save beside this Python file, so offline mode can use it later.
    output_file = Path(__file__).with_name("fishing_data.json")
    output_file.write_text(json.dumps(fishing_data, indent=2), encoding="utf-8")

    record_count = count_daily_records(fishing_data)
    print("SUCCESS: Fishing data saved.")
    print(f"Date range: {start_date} to {end_date}")
    print(f"Daily records returned: {record_count}")
    print(f"Saved file: {output_file}")


if __name__ == "__main__":
    main()
