from datetime import datetime, timedelta, timezone
import csv
import json
import os
import tempfile

from src.model.data import AnalysisSplitSegment, PacingPlan, TrackPoint
from src.services.pacer import create_analysis_splits, generate_analysis_csv, generate_analysis_json


def _point(
    distance_from_start,
    seconds,
    ele,
    hr=None,
    cad=None,
    temp=None,
    speed=None,
    power=None,
    respiration=None,
    vertical_oscillation=None,
    stance_time=None,
    stance_time_percent=None,
    vertical_ratio=None,
    stance_time_balance=None,
    step_length=None,
):
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
        speed_mps=speed,
        power_w=power,
        respiration_rate_brpm=respiration,
        vertical_oscillation_mm=vertical_oscillation,
        stance_time_ms=stance_time,
        stance_time_percent=stance_time_percent,
        vertical_ratio_pct=vertical_ratio,
        stance_time_balance_pct=stance_time_balance,
        step_length_mm=step_length,
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


def test_analysis_splits_aggregate_fit_metrics():
    points = [
        _point(
            0,
            0,
            100,
            speed=2.5,
            power=250,
            respiration=30.0,
            vertical_oscillation=80.0,
            stance_time=240.0,
            stance_time_percent=34.0,
            vertical_ratio=9.0,
            stance_time_balance=50.0,
            step_length=900.0,
        ),
        _point(
            500,
            100,
            102,
            speed=3.0,
            power=300,
            respiration=35.0,
            vertical_oscillation=90.0,
            stance_time=230.0,
            stance_time_percent=33.0,
            vertical_ratio=8.5,
            stance_time_balance=50.5,
            step_length=950.0,
        ),
    ]

    splits = create_analysis_splits(points, 500)

    assert len(splits) == 1
    assert splits[0].average_speed_mps == 2.75
    assert splits[0].average_power_w == 275.0
    assert splits[0].max_power_w == 300
    assert splits[0].average_respiration_rate_brpm == 32.5
    assert splits[0].max_respiration_rate_brpm == 35.0
    assert splits[0].average_vertical_oscillation_mm == 85.0
    assert splits[0].average_stance_time_ms == 235.0
    assert splits[0].average_stance_time_percent == 33.5
    assert splits[0].average_vertical_ratio_pct == 8.75
    assert splits[0].average_stance_time_balance_pct == 50.25
    assert splits[0].average_step_length_mm == 925.0


def test_analysis_json_output_uses_analysis_fields():
    plan = PacingPlan(
        metadata={
            "filename": "recording.fit",
            "total_dist": 1000,
            "mode": "analysis",
            "fit_session": {"avg_power": 289},
            "fit_laps": [{"total_distance": 1000}],
            "fit_time_in_zone": [{"reference_mesg": "session"}],
            "fit_workout": {"wkt_name": "Example"},
            "fit_workout_steps": [{"message_index": 0}],
            "fit_course_points": [{"name": "Aid Station"}],
        },
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
                average_speed_mps=2.8,
                average_power_w=280.0,
                max_power_w=310,
                average_respiration_rate_brpm=32.5,
                max_respiration_rate_brpm=36.0,
                average_vertical_oscillation_mm=88.0,
                average_stance_time_ms=234.0,
                average_stance_time_percent=34.0,
                average_vertical_ratio_pct=9.2,
                average_stance_time_balance_pct=50.5,
                average_step_length_mm=930.0,
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
    assert split["avg_speed_mps"] == 2.8
    assert split["avg_power_w"] == 280.0
    assert split["max_power_w"] == 310
    assert split["avg_respiration_rate_brpm"] == 32.5
    assert split["avg_vertical_oscillation_mm"] == 88.0
    assert split["point_count"] == 12
    assert split["start_time"] == "2026-01-01T10:00:00+00:00"
    assert data["metadata"]["fit_session"]["avg_power"] == 289
    assert data["metadata"]["fit_workout"]["wkt_name"] == "Example"


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
                average_speed_mps=None,
                average_power_w=None,
                max_power_w=None,
                average_respiration_rate_brpm=None,
                max_respiration_rate_brpm=None,
                average_vertical_oscillation_mm=None,
                average_stance_time_ms=None,
                average_stance_time_percent=None,
                average_vertical_ratio_pct=None,
                average_stance_time_balance_pct=None,
                average_step_length_mm=None,
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
    assert "Avg Power (W)" in headers
    assert "Avg Respiration (brpm)" in headers
    assert "Target Pace (min/km)" not in headers
    assert row["Avg HR (bpm)"] == ""
    assert row["Avg Cadence"] == ""
    assert row["Avg Temp (C)"] == ""
    assert row["Avg Power (W)"] == ""
    assert row["Avg Respiration (brpm)"] == ""
