import json

import pytest
from fastapi import HTTPException

from app import turtleguard


def test_status_reads_saved_summary_without_network(tmp_path, monkeypatch):
    expected = {"risk_status": "high", "source": "Global Fishing Watch"}
    (tmp_path / "turtleguard_summary.json").write_text(json.dumps(expected), encoding="utf-8")
    monkeypatch.setattr(turtleguard, "DATA_DIRECTORY", tmp_path)

    assert turtleguard.status() == expected


def test_refresh_stops_after_first_script_failure(tmp_path, monkeypatch):
    for name in turtleguard.REFRESH_SCRIPTS:
        (tmp_path / name).write_text("# test script", encoding="utf-8")
    monkeypatch.setattr(turtleguard, "DATA_DIRECTORY", tmp_path)

    called = []

    class FailedResult:
        returncode = 1

    def fake_run(command, **_kwargs):
        called.append(command[-1])
        return FailedResult()

    monkeypatch.setattr(turtleguard.subprocess, "run", fake_run)

    with pytest.raises(HTTPException) as raised:
        turtleguard.refresh()

    assert raised.value.status_code == 502
    assert called == [str(tmp_path / "fetch_baseline_data.py")]
