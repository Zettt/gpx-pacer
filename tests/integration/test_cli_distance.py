import pytest
import os
import subprocess
import sys

def test_cli_distance_mode_basic(tmp_path, sample_gpx_path):
    """
    Test that the CLI runs successfully with default distance mode
    and produces an output file.
    """
    output_file = tmp_path / "output.csv"
    
    # Construct command: python -m src.cli.main INPUT -o OUTPUT
    cmd = [
        sys.executable, "-m", "src.cli.main",
        str(sample_gpx_path),
        "--output", str(output_file),
        "--split-mode", "distance",
        "--split-dist", "0.1", # Small split for the sample file
        "--unit", "km"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    # Check execution
    assert result.returncode == 0, f"CLI failed: {result.stderr}"
    assert os.path.exists(output_file), "Output CSV was not created"
    
    # Basic content check
    with open(output_file, 'r') as f:
        content = f.read()
        assert "Distance" in content
        assert "Gain" in content
