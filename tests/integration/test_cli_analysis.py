import json
import os
import subprocess
import sys


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
