import json
import os
import subprocess
import sys

import pytest

from src.model.data import AnalysisSplitSegment, TrackPoint


def test_cli_analysis_mode_json(tmp_path):
    input_file = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "data",
        "sample_recording.gpx",
    )
    output_file = tmp_path / "analysis.json"

    cmd = [
        sys.executable,
        "-m",
        "src.cli.main",
        input_file,
        "--output",
        str(output_file),
        "--split-mode",
        "analysis",
        "--split-dist",
        "0.05",
        "--format",
        "json",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    assert result.returncode == 0, f"CLI failed: {result.stderr}"
    assert os.path.exists(output_file)

    with open(output_file, "r") as f:
        data = json.load(f)

    assert data["metadata"]["mode"] == "analysis"
    assert len(data["splits"]) >= 1
    assert "elapsed_s" in data["splits"][0]
    assert "pace_s_per_km" in data["splits"][0]


def test_cli_analysis_mode_csv(tmp_path):
    input_file = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "data",
        "sample_recording.gpx",
    )
    output_file = tmp_path / "analysis.csv"

    cmd = [
        sys.executable,
        "-m",
        "src.cli.main",
        input_file,
        "--output",
        str(output_file),
        "--split-mode",
        "analysis",
        "--split-dist",
        "0.05",
        "--format",
        "csv",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    assert result.returncode == 0, f"CLI failed: {result.stderr}"
    assert os.path.exists(output_file)

    with open(output_file, "r") as f:
        content = f.read()

    assert "Elapsed (s)" in content
    assert "Avg HR (bpm)" in content
    assert "Target Pace (min/km)" not in content


def test_cli_analysis_mode_json_fit(tmp_path):
    input_file = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "data",
        "Freiburg_Marathon_2026_Recording.fit",
    )
    output_file = tmp_path / "analysis-fit.json"

    cmd = [
        sys.executable,
        "-m",
        "src.cli.main",
        input_file,
        "--output",
        str(output_file),
        "--split-mode",
        "analysis",
        "--split-dist",
        "1",
        "--format",
        "json",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    assert result.returncode == 0, f"CLI failed: {result.stderr}"
    with open(output_file, "r") as f:
        data = json.load(f)

    assert data["metadata"]["filename"].endswith(".fit")
    assert "fit_session" in data["metadata"]
    assert "fit_workout" in data["metadata"]
    assert "avg_power_w" in data["splits"][0]
    assert "avg_respiration_rate_brpm" in data["splits"][0]


def test_cli_distance_mode_json_fit(tmp_path):
    input_file = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "data",
        "Freiburg_Marathon_2026_Recording.fit",
    )
    output_file = tmp_path / "distance-fit.json"

    cmd = [
        sys.executable,
        "-m",
        "src.cli.main",
        input_file,
        "--output",
        str(output_file),
        "--split-mode",
        "distance",
        "--split-dist",
        "5",
        "--format",
        "json",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    assert result.returncode == 0, f"CLI failed: {result.stderr}"
    with open(output_file, "r") as f:
        data = json.load(f)

    assert data["metadata"]["filename"].endswith(".fit")
    assert len(data["splits"]) >= 8


def test_cli_waypoint_mode_json_fit(tmp_path):
    input_file = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "data",
        "Freiburg_Marathon_2026_Recording.fit",
    )
    output_file = tmp_path / "waypoints-fit.json"

    cmd = [
        sys.executable,
        "-m",
        "src.cli.main",
        input_file,
        "--output",
        str(output_file),
        "--split-mode",
        "waypoint",
        "--format",
        "json",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    assert result.returncode == 0, f"CLI failed: {result.stderr}"
    with open(output_file, "r") as f:
        data = json.load(f)

    assert data["metadata"]["filename"].endswith(".fit")
    assert len(data["splits"]) >= 2
    assert data["splits"][0]["segment_name"].startswith("Start to ")


def test_cli_surface_endpoint_flag_passed_to_detect_surfaces(tmp_path, monkeypatch):
    from src.cli.main import main

    output_file = tmp_path / "analysis.json"
    endpoint_calls = []

    points = [
        TrackPoint(lat=48.0, lon=11.0, ele=500, distance_from_start=0),
        TrackPoint(lat=48.01, lon=11.01, ele=505, distance_from_start=50),
        TrackPoint(lat=48.02, lon=11.02, ele=510, distance_from_start=100),
    ]
    splits = [
        AnalysisSplitSegment(
            start_distance=0,
            end_distance=100,
            length=100,
            elevation_gain=10,
            elevation_loss=0,
            name="0.1 km",
            point_count=3,
        )
    ]

    def fake_parse_activity(_input_file):
        return points, [], {}

    def fake_create_analysis_splits(_points, _distance):
        return splits

    def fake_detect_surfaces(_splits, _points, endpoint=None):
        endpoint_calls.append(endpoint)
        return _splits

    monkeypatch.setattr("src.cli.main.parse_activity", fake_parse_activity)
    monkeypatch.setattr("src.cli.main.create_analysis_splits", fake_create_analysis_splits)
    monkeypatch.setattr("src.services.surface_service.detect_surfaces", fake_detect_surfaces)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "gpx-pacer",
            __file__,
            "--output",
            str(output_file),
            "--split-mode",
            "analysis",
            "--format",
            "json",
            "--surface",
            "--surface-endpoint",
            "https://example.test/api/interpreter",
        ],
    )

    main()

    assert endpoint_calls == ["https://example.test/api/interpreter"]
    assert output_file.exists()


def test_cli_surface_endpoint_env_used_when_flag_absent(tmp_path, monkeypatch):
    from src.cli.main import main

    output_file = tmp_path / "analysis.json"
    endpoint_calls = []

    points = [
        TrackPoint(lat=48.0, lon=11.0, ele=500, distance_from_start=0),
        TrackPoint(lat=48.01, lon=11.01, ele=505, distance_from_start=50),
        TrackPoint(lat=48.02, lon=11.02, ele=510, distance_from_start=100),
    ]
    splits = [
        AnalysisSplitSegment(
            start_distance=0,
            end_distance=100,
            length=100,
            elevation_gain=10,
            elevation_loss=0,
            name="0.1 km",
            point_count=3,
        )
    ]

    def fake_parse_activity(_input_file):
        return points, [], {}

    def fake_create_analysis_splits(_points, _distance):
        return splits

    def fake_detect_surfaces(_splits, _points, endpoint=None):
        endpoint_calls.append(endpoint)
        return _splits

    monkeypatch.setattr("src.cli.main.parse_activity", fake_parse_activity)
    monkeypatch.setattr("src.cli.main.create_analysis_splits", fake_create_analysis_splits)
    monkeypatch.setattr("src.services.surface_service.detect_surfaces", fake_detect_surfaces)
    monkeypatch.setenv(
        "GPX_PACER_SURFACE_ENDPOINT",
        "https://env.test/api/interpreter",
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "gpx-pacer",
            __file__,
            "--output",
            str(output_file),
            "--split-mode",
            "analysis",
            "--format",
            "json",
            "--surface",
        ],
    )

    main()

    assert endpoint_calls == ["https://env.test/api/interpreter"]
    assert output_file.exists()


def test_cli_surface_endpoint_flag_overrides_env(tmp_path, monkeypatch):
    from src.cli.main import main

    output_file = tmp_path / "analysis.json"
    endpoint_calls = []

    points = [
        TrackPoint(lat=48.0, lon=11.0, ele=500, distance_from_start=0),
        TrackPoint(lat=48.01, lon=11.01, ele=505, distance_from_start=50),
        TrackPoint(lat=48.02, lon=11.02, ele=510, distance_from_start=100),
    ]
    splits = [
        AnalysisSplitSegment(
            start_distance=0,
            end_distance=100,
            length=100,
            elevation_gain=10,
            elevation_loss=0,
            name="0.1 km",
            point_count=3,
        )
    ]

    def fake_parse_activity(_input_file):
        return points, [], {}

    def fake_create_analysis_splits(_points, _distance):
        return splits

    def fake_detect_surfaces(_splits, _points, endpoint=None):
        endpoint_calls.append(endpoint)
        return _splits

    monkeypatch.setattr("src.cli.main.parse_activity", fake_parse_activity)
    monkeypatch.setattr("src.cli.main.create_analysis_splits", fake_create_analysis_splits)
    monkeypatch.setattr("src.services.surface_service.detect_surfaces", fake_detect_surfaces)
    monkeypatch.setenv(
        "GPX_PACER_SURFACE_ENDPOINT",
        "https://env.test/api/interpreter",
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "gpx-pacer",
            __file__,
            "--output",
            str(output_file),
            "--split-mode",
            "analysis",
            "--format",
            "json",
            "--surface",
            "--surface-endpoint",
            "https://flag.test/api/interpreter",
        ],
    )

    main()

    assert endpoint_calls == ["https://flag.test/api/interpreter"]
    assert output_file.exists()


def test_cli_surface_query_failure_exits_with_actionable_stderr(tmp_path, monkeypatch, capsys):
    from src.cli.main import main
    from src.services.surface_service import SurfaceQueryError

    output_file = tmp_path / "analysis.json"

    points = [
        TrackPoint(lat=48.0, lon=11.0, ele=500, distance_from_start=0),
        TrackPoint(lat=48.01, lon=11.01, ele=505, distance_from_start=50),
        TrackPoint(lat=48.02, lon=11.02, ele=510, distance_from_start=100),
    ]
    splits = [
        AnalysisSplitSegment(
            start_distance=0,
            end_distance=100,
            length=100,
            elevation_gain=10,
            elevation_loss=0,
            name="0.1 km",
            point_count=3,
        )
    ]

    def fake_parse_activity(_input_file):
        return points, [], {}

    def fake_create_analysis_splits(_points, _distance):
        return splits

    def fake_detect_surfaces(_splits, _points, endpoint=None):
        raise SurfaceQueryError("default", 48.0, 11.0, "HTTP 406")

    monkeypatch.setattr("src.cli.main.parse_activity", fake_parse_activity)
    monkeypatch.setattr("src.cli.main.create_analysis_splits", fake_create_analysis_splits)
    monkeypatch.setattr("src.services.surface_service.detect_surfaces", fake_detect_surfaces)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "gpx-pacer",
            __file__,
            "--output",
            str(output_file),
            "--split-mode",
            "analysis",
            "--format",
            "json",
            "--surface",
        ],
    )

    with pytest.raises(SystemExit) as exc_info:
        main()

    captured = capsys.readouterr()
    assert exc_info.value.code == 1
    assert "Surface lookup failed" in captured.err
    assert "default" in captured.err
    assert "HTTP 406" in captured.err
    assert "--surface-endpoint" in captured.err
    assert "attempt 1/1" in captured.err
    assert "Successfully generated pacing plan" not in captured.out
    assert not output_file.exists()
