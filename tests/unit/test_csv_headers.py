import pytest


def test_csv_includes_planning_columns():
    """Verify CSV output includes all required planning columns (US3)."""
    from src.services.pacer import create_distance_splits, generate_csv
    from src.model.data import TrackPoint, PacingPlan
    import tempfile
    import os
    
    points = [
        TrackPoint(lat=0, lon=0, ele=100, distance_from_start=0),
        TrackPoint(lat=0.1, lon=0, ele=150, distance_from_start=5000),
    ]
    
    splits = create_distance_splits(points, split_distance_meters=5000)
    plan = PacingPlan(metadata={"test": True}, splits=splits)
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        output_path = f.name
    
    try:
        generate_csv(plan, output_path)
        
        with open(output_path, 'r') as f:
            header = f.readline()
        
        # Verify all required columns from spec are present
        assert "Segment Name" in header
        assert "Distance (km)" in header
        assert "Split Length (km)" in header
        assert "Gain (m)" in header
        assert "Loss (m)" in header
        assert "Net Change (m)" in header
        assert "Grade (%)" in header
        # Planning columns (FR-009)
        assert "Target Pace" in header
        assert "Split Time" in header
        assert "Arrival Time" in header
        assert "Station Delay" in header
        
        # Verify Net Change position: after Loss, before Cumulative Elevation
        headers = header.strip().split(",")
        loss_idx = headers.index("Loss (m)")
        net_idx = headers.index("Net Change (m)")
        cum_idx = headers.index("Cumulative Elevation (m)")
        assert loss_idx < net_idx < cum_idx
    finally:
        os.unlink(output_path)


def test_planning_columns_are_empty_by_default():
    """Verify planning columns are empty/default for user to fill in."""
    from src.services.pacer import create_distance_splits, generate_csv
    from src.model.data import TrackPoint, PacingPlan
    import tempfile
    import os
    import csv
    
    points = [
        TrackPoint(lat=0, lon=0, ele=100, distance_from_start=0),
        TrackPoint(lat=0.1, lon=0, ele=150, distance_from_start=5000),
    ]
    
    splits = create_distance_splits(points, split_distance_meters=5000)
    plan = PacingPlan(metadata={"test": True}, splits=splits)
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        output_path = f.name
    
    try:
        generate_csv(plan, output_path)
        
        with open(output_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Planning columns should be empty
                assert row["Target Pace (min/km)"] == ""
                assert row["Split Time (min)"] == ""
                assert row["Arrival Time"] == ""
                assert row["Station Delay (min)"] == ""
    finally:
        os.unlink(output_path)


def test_csv_surface_column_present_when_data_exists():
    """Verify Surface column appears in CSV when splits have surface data."""
    from src.services.pacer import generate_csv
    from src.model.data import SplitSegment, PacingPlan
    import tempfile
    import os

    splits = [
        SplitSegment(
            start_distance=0, end_distance=5000, length=5000,
            elevation_gain=50, elevation_loss=0,
            name="Split 1", surface="Asphalt"
        ),
    ]
    plan = PacingPlan(metadata={"test": True}, splits=splits)

    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        output_path = f.name

    try:
        generate_csv(plan, output_path)

        with open(output_path, 'r') as f:
            header = f.readline()

        assert "Surface" in header
    finally:
        os.unlink(output_path)


def test_csv_surface_column_absent_when_no_data():
    """Verify Surface column does NOT appear in CSV when no surface data."""
    from src.services.pacer import generate_csv
    from src.model.data import SplitSegment, PacingPlan
    import tempfile
    import os

    splits = [
        SplitSegment(
            start_distance=0, end_distance=5000, length=5000,
            elevation_gain=50, elevation_loss=0,
            name="Split 1",
            # surface is None (default)
        ),
    ]
    plan = PacingPlan(metadata={"test": True}, splits=splits)

    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        output_path = f.name

    try:
        generate_csv(plan, output_path)

        with open(output_path, 'r') as f:
            header = f.readline()

        assert "Surface" not in header
    finally:
        os.unlink(output_path)

