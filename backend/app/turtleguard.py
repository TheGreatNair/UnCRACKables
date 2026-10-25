"""Offline TurtleGuard status and controlled Global Fishing Watch refresh."""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException


logger = logging.getLogger("turtleway.turtleguard")
router = APIRouter(prefix="/turtleguard", tags=["TurtleGuard"])
DATA_DIRECTORY = Path(os.getenv("TURTLEGUARD_DIR", Path(__file__).resolve().parents[1] / "turtleguard"))
REFRESH_SCRIPTS = ("fetch_baseline_data.py", "fetch_fishing_data.py", "calculate_turtle_risk.py")


def _error(code: str, message: str, status_code: int) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": message})


def _summary() -> dict:
    summary_file = DATA_DIRECTORY / "turtleguard_summary.json"
    if not summary_file.is_file():
        raise _error("turtleguard_summary_missing", "No saved TurtleGuard summary is available yet.", 404)
    try:
        summary = json.loads(summary_file.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        logger.error("Could not read the TurtleGuard summary")
        raise _error("turtleguard_summary_invalid", "The saved TurtleGuard summary cannot be read.", 500) from exc
    if not isinstance(summary, dict):
        raise _error("turtleguard_summary_invalid", "The saved TurtleGuard summary has an invalid format.", 500)
    return summary


def _run_refresh() -> None:
    for script_name in REFRESH_SCRIPTS:
        script = DATA_DIRECTORY / script_name
        if not script.is_file():
            raise _error("turtleguard_script_missing", "A required TurtleGuard refresh script is missing.", 503)
        try:
            result = subprocess.run(
                [sys.executable, str(script)], cwd=DATA_DIRECTORY, capture_output=True,
                text=True, timeout=300, check=False,
            )
        except subprocess.TimeoutExpired as exc:
            logger.warning("TurtleGuard refresh timed out in %s", script_name)
            raise _error("turtleguard_refresh_timeout", "TurtleGuard refresh timed out. Saved status is unchanged.", 502) from exc
        except OSError as exc:
            logger.error("TurtleGuard refresh could not start %s", script_name)
            raise _error("turtleguard_refresh_failed", "TurtleGuard refresh could not start.", 502) from exc
        if result.returncode != 0:
            # Do not return script output: upstream errors must not be exposed to clients.
            logger.warning("TurtleGuard refresh failed in %s with exit code %s", script_name, result.returncode)
            raise _error(
                "turtleguard_refresh_failed",
                "TurtleGuard could not fetch fresh Global Fishing Watch data. Saved status is unchanged.",
                502,
            )


@router.get("/status")
def status() -> dict:
    """Return the saved alert without making a network request."""
    return _summary()


@router.post("/refresh")
def refresh() -> dict:
    """Fetch baseline/current periods, calculate risk, and return the new saved result."""
    _run_refresh()
    return {"message": "TurtleGuard data refreshed successfully.", "summary": _summary()}
