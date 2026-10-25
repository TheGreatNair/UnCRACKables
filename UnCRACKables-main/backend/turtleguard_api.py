# TurtleGuard FastAPI backend.
# The React Native TurtleWay app will call these endpoints.

import json
import subprocess
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(
    title="TurtleGuard API",
    description="Offshore fishing-threat alerts for TurtleWay.",
    version="1.0.0",
)

# Allows the Expo/React Native app to call this local API during development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PROJECT_FOLDER = Path(__file__).parent
SUMMARY_FILE = PROJECT_FOLDER / "turtleguard_summary.json"


def load_summary():
    """Read the saved offline TurtleGuard result."""
    if not SUMMARY_FILE.exists():
        raise HTTPException(
            status_code=404,
            detail="No TurtleGuard summary exists yet. Run the calculator first.",
        )

    try:
        return json.loads(SUMMARY_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500,
            detail="TurtleGuard summary file is invalid.",
        )


def run_script(script_name):
    """Run one local TurtleGuard script and return its terminal output."""
    script_path = PROJECT_FOLDER / script_name

    result = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=PROJECT_FOLDER,
        capture_output=True,
        text=True,
        timeout=300,
    )

    if result.returncode != 0:
        error_text = result.stderr or result.stdout or "Unknown script error."
        raise HTTPException(status_code=502, detail=error_text)

    return result.stdout


@app.get("/")
def home():
    return {
        "service": "TurtleGuard API",
        "message": "TurtleGuard is running.",
        "endpoints": {
            "status": "GET /turtleguard/status",
            "refresh": "POST /turtleguard/refresh",
        },
    }


@app.get("/turtleguard/status")
def get_status():
    """
    Return the saved alert result.
    This endpoint works offline because it only reads turtleguard_summary.json.
    """
    return load_summary()


@app.post("/turtleguard/refresh")
def refresh_data():
    """
    Manually download fresh GFW data, rebuild the baseline,
    recalculate the alert, then return the new saved result.
    """
    baseline_output = run_script("fetch_baseline_data.py")
    current_output = run_script("fetch_fishing_data.py")
    calculation_output = run_script("calculate_turtle_risk.py")

    return {
        "message": "TurtleGuard data refreshed successfully.",
        "summary": load_summary(),
        "logs": {
            "baseline_fetch": baseline_output,
            "current_fetch": current_output,
            "calculation": calculation_output,
        },
    }