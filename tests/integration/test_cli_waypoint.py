import pytest
import os
import subprocess
import sys


def test_cli_waypoint_mode_basic(tmp_path):
    """
    Test that the CLI runs successfully with waypoint mode
    using the real Rennsteiglauf GPX file with waypoints.
    """
    # Path to the test GPX file with waypoints
    gpx_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "data",
        "Rennsteiglauf2026_from_garmin.gpx"
    )
    
    output_file = tmp_path / "waypoint_output.csv"
    
    cmd = [
        sys.executable, "-m", "src.cli.main",
        gpx_path,
        "--output", str(output_file),
        "--split-mode", "waypoint",
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    assert result.returncode == 0, f"CLI failed: {result.stderr}"
    assert os.path.exists(output_file), "Output CSV was not created"
    
    # Check content includes waypoint names
    with open(output_file, 'r') as f:
        content = f.read()
        assert "Distance" in content
        # Should include waypoint names from the GPX file
        assert "Aid Station" in content or "turmhut" in content or "Water" in content


def test_cli_waypoint_mode_no_waypoints(tmp_path, sample_gpx_path):
    """
    Test waypoint mode with a GPX file that has no waypoints.
    Should fall back to a single start-to-finish split.
    """
    output_file = tmp_path / "no_waypoint_output.csv"
    
    cmd = [
        sys.executable, "-m", "src.cli.main",
        sample_gpx_path,
        "--output", str(output_file),
        "--split-mode", "waypoint",
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    assert result.returncode == 0, f"CLI failed: {result.stderr}"
    assert os.path.exists(output_file), "Output CSV was not created"
    
    with open(output_file, 'r') as f:
        content = f.read()
        # Should contain start to finish
        assert "Start to Finish" in content or "Finish" in content
