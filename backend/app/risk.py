"""Read-only coastal fishing-effort risk from the bundled GFW snapshot."""

import json
import math
from datetime import date, datetime, timezone
from pathlib import Path

from fastapi import HTTPException


DAYS_IN_WINDOW = 30
ALERT_MULTIPLIER = 1.5
ZONE_COORDINATES = (
    (74.74, 13.10),
    (74.79, 13.10),
    (74.81, 12.92),
    (74.76, 12.90),
    (74.74, 13.10),
)
DATA_DIR = Path(__file__).with_name("data")


def _zone_area_km2() -> float:
    radius = 6371.0088
    average_latitude = math.radians(sum(point[1] for point in ZONE_COORDINATES) / len(ZONE_COORDINATES))
    points = [
        (radius * math.radians(lon) * math.cos(average_latitude), radius * math.radians(lat))
        for lon, lat in ZONE_COORDINATES
    ]
    return abs(sum(
        x1 * y2 - x2 * y1
        for (x1, y1), (x2, y2) in zip(points, points[1:])
    )) / 2


def _fishing_hours(value: object) -> tuple[float, list[date]]:
    total = 0.0
    dates: list[date] = []
    if isinstance(value, dict):
        hours = value.get("hours")
        if isinstance(hours, (int, float)) and not isinstance(hours, bool) and math.isfinite(hours):
            total += max(0.0, float(hours))
        raw_date = value.get("date")
        if isinstance(raw_date, str):
            try:
                dates.append(date.fromisoformat(raw_date))
            except ValueError:
                pass
        for key, item in value.items():
            if key not in {"hours", "date"}:
                child_total, child_dates = _fishing_hours(item)
                total += child_total
                dates.extend(child_dates)
    elif isinstance(value, list):
        for item in value:
            child_total, child_dates = _fishing_hours(item)
            total += child_total
            dates.extend(child_dates)
    return total, dates


def _load_snapshot(filename: str) -> tuple[float, list[date]]:
    path = DATA_DIR / filename
    try:
        content = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=503,
            detail={"code": "risk_data_unavailable", "message": "The coastal risk snapshot is unavailable."},
        ) from exc
    return _fishing_hours(content)


def get_fishing_risk() -> dict:
    current_hours, current_dates = _load_snapshot("fishing_data.json")
    reference_hours, _reference_dates = _load_snapshot("baseline_fishing_data.json")
    area = _zone_area_km2()
    current_density = current_hours / DAYS_IN_WINDOW / area
    reference_density = reference_hours / DAYS_IN_WINDOW / area
    latest_date = max(current_dates, default=None)

    if reference_density <= 0:
        status = "needs_more_reference_data"
        threshold = None
        ratio = None
        message = "Reference activity was zero, so a fair alert threshold is not available."
    else:
        threshold = reference_density * ALERT_MULTIPLIER
        ratio = current_density / reference_density
        if current_density >= threshold:
            status = "high"
            message = "Apparent fishing activity is elevated near the turtle zone. Notify coastal patrol."
        else:
            status = "low"
            message = "Recent apparent fishing activity is not unusually high against the reference period."

    today = datetime.now(timezone.utc).date()
    return {
        "zoneName": "TurtleGuard Dakshina Kannada Offshore Zone",
        "riskStatus": status,
        "message": message,
        "dataAsOf": latest_date.isoformat() if latest_date else None,
        "dataAgeDays": (today - latest_date).days if latest_date else None,
        "currentPeriodApparentFishingHours": round(current_hours, 2),
        "referencePeriodApparentFishingHours": round(reference_hours, 2),
        "currentDensityHoursPerKm2PerDay": round(current_density, 6),
        "referenceDensityHoursPerKm2PerDay": round(reference_density, 6),
        "alertThresholdDensityHoursPerKm2PerDay": round(threshold, 6) if threshold is not None else None,
        "activityRatio": round(ratio, 2) if ratio is not None else None,
        "alertMultiplier": ALERT_MULTIPLIER,
        "daysPerPeriod": DAYS_IN_WINDOW,
        "zoneAreaKm2": round(area, 2),
        "source": "Global Fishing Watch, saved AIS-derived snapshot",
        "limitations": "AIS-derived apparent fishing effort; small vessels without AIS may be missing. This is an indicator, not proof of illegal fishing.",
        "snapshotNote": "Snapshot inputs are bundled with this demo. Refresh them on the backend with an authorized Global Fishing Watch token before operational use.",
    }
