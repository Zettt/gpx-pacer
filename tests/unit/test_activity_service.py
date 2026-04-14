from pathlib import Path

from src.services.activity_service import parse_activity


def test_parse_activity_dispatches_fit_and_extracts_rich_metrics():
    fit_path = Path("data/Freiburg_Marathon_2026_Recording.fit")

    track_points, waypoints, metadata = parse_activity(str(fit_path))

    assert len(track_points) > 10000
    assert any(point.power_w is not None for point in track_points)
    assert any(point.respiration_rate_brpm is not None for point in track_points)
    assert any(point.vertical_oscillation_mm is not None for point in track_points)
    assert any(point.step_length_mm is not None for point in track_points)

    assert any(waypoint.name == "Aid Station" for waypoint in waypoints)
    assert any(waypoint.name == "Water" for waypoint in waypoints)

    assert metadata["fit_session"]["avg_power"] == 289
    assert metadata["fit_session"]["avg_heart_rate"] == 141
    assert len(metadata["fit_laps"]) == 6
    assert len(metadata["fit_time_in_zone"]) >= 1
    assert metadata["fit_workout"]["wkt_name"] == "Freiburg Marathon (Pace)"
    assert len(metadata["fit_workout_steps"]) == 5
    assert len(metadata["fit_course_points"]) >= 1


def test_parse_activity_dispatches_gpx_without_fit_metadata():
    track_points, waypoints, metadata = parse_activity("tests/data/sample_recording.gpx")

    assert len(track_points) == 3
    assert waypoints == []
    assert metadata == {}
