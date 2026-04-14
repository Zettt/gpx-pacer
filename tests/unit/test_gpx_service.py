from datetime import datetime, timezone

from src.services.gpx_service import parse_gpx


def test_parse_gpx_extracts_recording_metrics():
    track_points, waypoints = parse_gpx("tests/data/sample_recording.gpx")

    assert waypoints == []
    assert len(track_points) == 3

    first = track_points[0]
    assert first.timestamp == datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    assert first.heart_rate_bpm == 120
    assert first.cadence == 80
    assert first.temperature_c == 12.5

    third = track_points[2]
    assert third.heart_rate_bpm == 140
    assert third.cadence == 84
    assert third.temperature_c == 13.5
