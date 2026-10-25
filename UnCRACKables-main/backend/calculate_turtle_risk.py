# TurtleGuard: offline risk calculation using saved GFW data.
# It compares the current 30 days with the immediately previous 30 days.

import json
import math
from pathlib import Path


DAYS_IN_WINDOW = 30

# Change this later if conservation experts choose a different sensitivity.
# 1.5 means the current period must be 50% above the reference period.
ALERT_MULTIPLIER = 1.5

TURTLE_ZONE_COORDINATES = [
    [74.74, 13.10],
    [74.79, 13.10],
    [74.81, 12.92],
    [74.76, 12.90],
    [74.74, 13.10],
]


def calculate_polygon_area_km2(coordinates):
    """Estimate the area of the defined monitoring zone."""
    earth_radius_km = 6371.0088
    average_latitude = sum(point[1] for point in coordinates) / len(coordinates)
    average_latitude_radians = math.radians(average_latitude)

    points = []

    for longitude, latitude in coordinates:
        x = earth_radius_km * math.radians(longitude) * math.cos(average_latitude_radians)
        y = earth_radius_km * math.radians(latitude)
        points.append((x, y))

    area = 0

    for index in range(len(points) - 1):
        x1, y1 = points[index]
        x2, y2 = points[index + 1]
        area += x1 * y2
        area -= x2 * y1

    return abs(area) / 2


def find_fishing_hours(item):
    """Find every numeric 'hours' value in GFW's JSON response."""
    hours = []

    if isinstance(item, dict):
        for key, value in item.items():
            if key == "hours" and isinstance(value, (int, float)):
                hours.append(value)
            else:
                hours.extend(find_fishing_hours(value))

    elif isinstance(item, list):
        for value in item:
            hours.extend(find_fishing_hours(value))

    return hours


def get_density(data_file, zone_area_km2):
    """Return total fishing hours and average daily effort density."""
    data = json.loads(data_file.read_text(encoding="utf-8"))
    total_hours = sum(find_fishing_hours(data))
    density = total_hours / DAYS_IN_WINDOW / zone_area_km2
    return total_hours, density


def main():
    folder = Path(__file__).parent
    current_file = folder / "fishing_data.json"
    reference_file = folder / "baseline_fishing_data.json"

    if not current_file.exists() or not reference_file.exists():
        print("ERROR: Both saved GFW data files are required.")
        print("Run fetch_fishing_data.py and fetch_baseline_data.py first.")
        return

    zone_area_km2 = calculate_polygon_area_km2(TURTLE_ZONE_COORDINATES)

    current_hours, current_density = get_density(current_file, zone_area_km2)
    reference_hours, reference_density = get_density(reference_file, zone_area_km2)

    if reference_density <= 0:
        risk_status = "needs_more_reference_data"
        message = "Reference activity was zero, so TurtleGuard cannot set a fair alert threshold."
        threshold_density = None
        activity_ratio = None
    else:
        threshold_density = reference_density * ALERT_MULTIPLIER
        activity_ratio = current_density / reference_density

        if current_density >= threshold_density:
            risk_status = "high"
            message = "ALERT: High fishing activity near the turtle zone. Notify coastal patrol."
        else:
            risk_status = "low"
            message = "Low risk: recent fishing activity is not unusually high."

    summary = {
        "zone_name": "TurtleGuard Dakshina Kannada Offshore Zone",
        "days_per_period": DAYS_IN_WINDOW,
        "zone_area_km2": round(zone_area_km2, 2),
        "current_total_apparent_fishing_hours": round(current_hours, 2),
        "current_density_hours_per_km2_per_day": round(current_density, 6),
        "reference_total_apparent_fishing_hours": round(reference_hours, 2),
        "reference_density_hours_per_km2_per_day": round(reference_density, 6),
        "alert_multiplier": ALERT_MULTIPLIER,
        "threshold_density_hours_per_km2_per_day": (
            round(threshold_density, 6) if threshold_density is not None else None
        ),
        "activity_ratio": round(activity_ratio, 2) if activity_ratio is not None else None,
        "risk_status": risk_status,
        "message": message,
        "source": "Global Fishing Watch",
        "note": "AIS-derived apparent fishing effort; small vessels without AIS may be missing.",
    }

    summary_file = folder / "turtleguard_summary.json"
    summary_file.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print("TurtleGuard comparison complete")
    print(f"Zone area: {zone_area_km2:.2f} km²")
    print(f"Current 30-day density: {current_density:.6f} hours/km²/day")
    print(f"Reference 30-day density: {reference_density:.6f} hours/km²/day")

    if threshold_density is not None:
        print(f"Alert threshold: {threshold_density:.6f} hours/km²/day")
        print(f"Activity ratio: {activity_ratio:.2f}x reference")

    print(f"Risk status: {risk_status.upper()}")
    print(message)
    print(f"Saved summary: {summary_file}")


if __name__ == "__main__":
    main()