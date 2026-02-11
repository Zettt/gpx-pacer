import json
import tempfile
import os
import pytest

from src.model.data import SplitSegment, PacingPlan, TrackPoint
from src.services.pacer import generate_json, create_distance_splits


def _make_plan(splits=None, metadata=None):
    """Helper to create a PacingPlan with sensible defaults."""
    if splits is None:
        splits = [
            SplitSegment(
                start_distance=0, end_distance=5000, length=5000,
                elevation_gain=50, elevation_loss=30, name="Split 1"
            ),
            SplitSegment(
                start_distance=5000, end_distance=8000, length=3000,
                elevation_gain=10, elevation_loss=40, name="Split 2"
            ),
        ]
    if metadata is None:
        metadata = {"filename": "test.gpx", "total_dist": 8000}
    return PacingPlan(metadata=metadata, splits=splits)


def _generate_and_load(plan):
    """Write JSON to a temp file, read it back, and clean up."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        output_path = f.name
    try:
        generate_json(plan, output_path)
        with open(output_path, 'r') as f:
            return json.load(f)
    finally:
        os.unlink(output_path)


def test_json_output_structure():
    """Verify JSON output has top-level 'metadata' and 'splits' keys."""
    plan = _make_plan()
    data = _generate_and_load(plan)

    assert "metadata" in data
    assert "splits" in data
    assert isinstance(data["metadata"], dict)
    assert isinstance(data["splits"], list)


def test_json_metadata_matches_plan():
    """Verify metadata in JSON matches the PacingPlan metadata."""
    meta = {"filename": "course.gpx", "total_dist": 42195}
    plan = _make_plan(metadata=meta)
    data = _generate_and_load(plan)

    assert data["metadata"]["filename"] == "course.gpx"
    assert data["metadata"]["total_dist"] == 42195


def test_json_split_fields():
    """Verify each split in JSON has all expected fields with correct values."""
    plan = _make_plan()
    data = _generate_and_load(plan)

    assert len(data["splits"]) == 2

    split = data["splits"][0]
    assert split["segment_name"] == "Split 1"
    assert split["distance_km"] == 5.0
    assert split["split_length_km"] == 5.0
    assert split["gain_m"] == 50
    assert split["loss_m"] == 30
    assert split["net_change_m"] == 20
    assert "cumulative_elevation_m" in split
    assert "grade_pct" in split

    # Second split: net = 10 - 40 = -30
    split2 = data["splits"][1]
    assert split2["net_change_m"] == -30


def test_json_cumulative_elevation():
    """Verify cumulative elevation accumulates correctly across splits."""
    plan = _make_plan()
    data = _generate_and_load(plan)

    # Split 1: gain 50 - loss 30 = +20
    assert data["splits"][0]["cumulative_elevation_m"] == 20
    # Split 2: +20 + (10 - 40) = -10
    assert data["splits"][1]["cumulative_elevation_m"] == -10


def test_json_grade_values():
    """Verify grade is computed correctly in JSON output."""
    plan = _make_plan()
    data = _generate_and_load(plan)

    # Split 1: (50-30)/5000 * 100 = 0.4%
    assert data["splits"][0]["grade_pct"] == pytest.approx(0.4, abs=0.01)


def test_json_includes_surface_when_present():
    """Verify surface field appears in splits when surface data exists."""
    splits = [
        SplitSegment(
            start_distance=0, end_distance=5000, length=5000,
            elevation_gain=50, elevation_loss=0,
            name="Split 1", surface="Asphalt"
        ),
    ]
    plan = _make_plan(splits=splits)
    data = _generate_and_load(plan)

    assert data["splits"][0]["surface"] == "Asphalt"


def test_json_excludes_surface_when_absent():
    """Verify surface field is absent in splits when no surface data."""
    splits = [
        SplitSegment(
            start_distance=0, end_distance=5000, length=5000,
            elevation_gain=50, elevation_loss=0, name="Split 1"
        ),
    ]
    plan = _make_plan(splits=splits)
    data = _generate_and_load(plan)

    assert "surface" not in data["splits"][0]


def test_json_empty_splits():
    """Verify JSON handles empty splits list gracefully."""
    plan = _make_plan(splits=[])
    data = _generate_and_load(plan)

    assert data["splits"] == []
    assert "metadata" in data
