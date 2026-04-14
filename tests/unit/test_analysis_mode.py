from datetime import datetime, timedelta, timezone
import csv
import json
import os
import tempfile

from src.model.data import AnalysisSplitSegment, PacingPlan, TrackPoint
from src.services.pacer import create_analysis_splits, generate_analysis_csv, generate_analysis_json


def _point(distance_from_start, seconds, ele, hr=None, cad=None, temp=None):
    return TrackPoint(
        lat=0.0,
        lon=0.0,
        ele=ele,
        distance_from_start=distance_from_start,
        timestamp=datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        + timedelta(seconds=seconds),
        heart_rate_bpm=hr,
        cadence=cad,
        temperature_c=temp,
    )


def test_analysis_splits_exact_boundary():
    points = [
        _point(0, 0, 100, hr=120, cad=80, temp=12.0),
        _point(500, 120, 110, hr=130, cad=82, temp=13.0),
        _point(1000, 240, 105, hr=140, cad=84, temp=14.0),
    ]

    splits = create_analysis_splits(points, 500)

    assert len(splits) == 2
    assert splits[0].elapsed_seconds == 120.0
    assert splits[0].pace_seconds_per_km == 240.0
    assert splits[0].average_heart_rate_bpm == 125.0
    assert splits[0].max_heart_rate_bpm == 130
    assert splits[0].average_cadence == 81.0
    assert splits[0].average_temperature_c == 12.5
    assert splits[0].point_count == 2
    assert splits[0].elevation_gain == 10
    assert splits[0].elevation_loss == 0


def test_analysis_splits_interpolate_mid_segment_boundary():
    points = [
        _point(0, 0, 100, hr=100, cad=80, temp=10.0),
        _point(1000, 100, 120, hr=150, cad=90, temp=14.0),
    ]

    splits = create_analysis_splits(points, 500)

    assert len(splits) == 2
    assert splits[0].end_time == datetime(2026, 1, 1, 10, 0, 50, tzinfo=timezone.utc)
    assert splits[0].elapsed_seconds == 50.0
    assert splits[0].elevation_gain == 10.0
    assert splits[0].average_heart_rate_bpm == 112.5
    assert splits[0].max_heart_rate_bpm == 125


def test_analysis_splits_missing_optional_metrics():
    points = [
        _point(0, 0, 100),
        _point(500, 60, 95),
    ]

    splits = create_analysis_splits(points, 500)

    assert len(splits) == 1
    assert splits[0].average_heart_rate_bpm is None
    assert splits[0].max_heart_rate_bpm is None
    assert splits[0].average_cadence is None
    assert splits[0].average_temperature_c is None


def test_analysis_json_output_uses_analysis_fields():
    plan = PacingPlan(
        metadata={"filename": "recording.gpx", "total_dist": 1000, "mode": "analysis"},
        splits=[
            AnalysisSplitSegment(
                start_distance=0,
                end_distance=1000,
                length=1000,
                elevation_gain=20,
                elevation_loss=5,
                name="1.0 km",
                start_time=datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
                end_time=datetime(2026, 1, 1, 10, 5, 0, tzinfo=timezone.utc),
                elapsed_seconds=300.0,
                pace_seconds_per_km=300.0,
                average_heart_rate_bpm=None,
                max_heart_rate_bpm=None,
                average_cadence=88.5,
                average_temperature_c=None,
                point_count=12,
            )
        ],
    )

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        output_path = f.name

    try:
        generate_analysis_json(plan, output_path)
        with open(output_path, "r") as f:
            data = json.load(f)
    finally:
        os.unlink(output_path)

    split = data["splits"][0]
    assert split["elapsed_s"] == 300.0
    assert split["pace_s_per_km"] == 300.0
    assert split["avg_hr_bpm"] is None
    assert split["avg_cadence"] == 88.5
    assert split["point_count"] == 12
    assert split["start_time"] == "2026-01-01T10:00:00+00:00"


def test_analysis_csv_output_has_analysis_headers_and_blank_optional_metrics():
    plan = PacingPlan(
        metadata={"filename": "recording.gpx", "total_dist": 1000, "mode": "analysis"},
        splits=[
            AnalysisSplitSegment(
                start_distance=0,
                end_distance=1000,
                length=1000,
                elevation_gain=20,
                elevation_loss=5,
                name="1.0 km",
                start_time=datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
                end_time=datetime(2026, 1, 1, 10, 5, 0, tzinfo=timezone.utc),
                elapsed_seconds=300.0,
                pace_seconds_per_km=300.0,
                average_heart_rate_bpm=None,
                max_heart_rate_bpm=None,
                average_cadence=None,
                average_temperature_c=None,
                point_count=12,
            )
        ],
    )

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        output_path = f.name

    try:
        generate_analysis_csv(plan, output_path)
        with open(output_path, "r") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames
            row = next(reader)
    finally:
        os.unlink(output_path)

    assert "Elapsed (s)" in headers
    assert "Avg HR (bpm)" in headers
    assert "Target Pace (min/km)" not in headers
    assert row["Avg HR (bpm)"] == ""
    assert row["Avg Cadence"] == ""
    assert row["Avg Temp (C)"] == ""
