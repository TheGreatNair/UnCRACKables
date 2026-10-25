import json
import math
from pathlib import Path


DAYS_IN_WINDOW = 30
ALERT_MULTIPLIER = 1.5  # Prototype calibration parameter; not expert-validated.
ZONE = [[74.74, 13.10], [74.79, 13.10], [74.81, 12.92], [74.76, 12.90], [74.74, 13.10]]


def _area_km2() -> float:
    radius = 6371.0088
    latitude = math.radians(sum(point[1] for point in ZONE) / len(ZONE))
    points = [(radius * math.radians(lon) * math.cos(latitude), radius * math.radians(lat)) for lon, lat in ZONE]
    return abs(sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(points, points[1:]))) / 2


def _hours(item) -> list[float]:
    if isinstance(item, dict):
        values = []
        for key, value in item.items():
            values.extend([value] if key == "hours" and isinstance(value, (int, float)) else _hours(value))
        return values
    if isinstance(item, list):
        return [number for value in item for number in _hours(value)]
    return []


def _density(path: Path, area: float) -> tuple[float, float]:
    total = sum(_hours(json.loads(path.read_text(encoding="utf-8"))))
    return total, total / DAYS_IN_WINDOW / area


def main() -> int:
    folder = Path(__file__).parent
    current_file, reference_file = folder / "fishing_data.json", folder / "baseline_fishing_data.json"
    if not current_file.exists() or not reference_file.exists():
        print("ERROR: Both saved GFW data files are required.")
        return 1
    area = _area_km2()
    current_hours, current_density = _density(current_file, area)
    reference_hours, reference_density = _density(reference_file, area)
    threshold = reference_density * ALERT_MULTIPLIER if reference_density > 0 else None
    ratio = current_density / reference_density if reference_density > 0 else None
    status = "needs_more_reference_data" if threshold is None else ("high" if current_density >= threshold else "low")
    message = "Reference activity was zero, so TurtleGuard cannot set a fair alert threshold." if threshold is None else ("ALERT: High fishing activity near the turtle zone. Notify coastal patrol." if status == "high" else "Low risk: recent fishing activity is not unusually high.")
    summary = {"zone_name": "TurtleGuard Dakshina Kannada Offshore Zone", "days_per_period": DAYS_IN_WINDOW, "zone_area_km2": round(area, 2), "current_total_apparent_fishing_hours": round(current_hours, 2), "current_density_hours_per_km2_per_day": round(current_density, 6), "reference_total_apparent_fishing_hours": round(reference_hours, 2), "reference_density_hours_per_km2_per_day": round(reference_density, 6), "alert_multiplier": ALERT_MULTIPLIER, "threshold_density_hours_per_km2_per_day": round(threshold, 6) if threshold is not None else None, "activity_ratio": round(ratio, 2) if ratio is not None else None, "risk_status": status, "message": message, "source": "Global Fishing Watch", "note": "AIS-derived apparent fishing effort; small vessels without AIS may be missing."}
    (folder / "turtleguard_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("TurtleGuard comparison complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
