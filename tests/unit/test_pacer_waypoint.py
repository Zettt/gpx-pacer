import pytest
from src.model.data import TrackPoint, Waypoint, SplitSegment

def test_waypoint_splits_basic():
    """Test that waypoint splits create segments between waypoints."""
    # Import here to allow test collection even if function doesn't exist yet
    from src.services.pacer import create_waypoint_splits
    
    # Create a simple track with 3 points
    points = [
        TrackPoint(lat=0.0, lon=0.0, ele=100, distance_from_start=0),
        TrackPoint(lat=0.1, lon=0.0, ele=150, distance_from_start=5000),
        TrackPoint(lat=0.2, lon=0.0, ele=200, distance_from_start=10000),
        TrackPoint(lat=0.3, lon=0.0, ele=180, distance_from_start=15000),
    ]
    
    # Waypoints matching some track points
    waypoints = [
        Waypoint(name="Aid Station 1", lat=0.1, lon=0.0, distance_from_start=5000),
        Waypoint(name="Aid Station 2", lat=0.2, lon=0.0, distance_from_start=10000),
    ]
    
    splits = create_waypoint_splits(points, waypoints)
    
    # Should create 3 splits: Start->Aid1, Aid1->Aid2, Aid2->Finish
    assert len(splits) == 3
    assert splits[0].name == "Start to Aid Station 1"
    assert splits[0].length == 5000
    assert splits[1].name == "Aid Station 1 to Aid Station 2"
    assert splits[1].length == 5000
    assert splits[2].name == "Aid Station 2 to Finish"
    assert splits[2].length == 5000


def test_waypoint_splits_no_waypoints():
    """Test behavior when no waypoints are provided."""
    from src.services.pacer import create_waypoint_splits
    
    points = [
        TrackPoint(lat=0.0, lon=0.0, ele=100, distance_from_start=0),
        TrackPoint(lat=0.1, lon=0.0, ele=150, distance_from_start=5000),
    ]
    
    splits = create_waypoint_splits(points, [])
    
    # Should create single split from start to finish
    assert len(splits) == 1
    assert splits[0].name == "Start to Finish"
    assert splits[0].length == 5000


def test_waypoint_elevation_calculation():
    """Test that elevation gain/loss is correctly calculated for waypoint splits."""
    from src.services.pacer import create_waypoint_splits
    
    points = [
        TrackPoint(lat=0.0, lon=0.0, ele=100, distance_from_start=0),
        TrackPoint(lat=0.05, lon=0.0, ele=150, distance_from_start=2500),  # +50m
        TrackPoint(lat=0.1, lon=0.0, ele=120, distance_from_start=5000),   # -30m
        TrackPoint(lat=0.15, lon=0.0, ele=200, distance_from_start=7500),  # +80m
        TrackPoint(lat=0.2, lon=0.0, ele=180, distance_from_start=10000),  # -20m
    ]
    
    waypoints = [
        Waypoint(name="Mid", lat=0.1, lon=0.0, distance_from_start=5000),
    ]
    
    splits = create_waypoint_splits(points, waypoints)
    
    assert len(splits) == 2
    # First split: 100 -> 150 -> 120 = +50 gain, -30 loss
    assert splits[0].elevation_gain == 50
    assert splits[0].elevation_loss == 30
    # Second split: 120 -> 200 -> 180 = +80 gain, -20 loss
    assert splits[1].elevation_gain == 80
    assert splits[1].elevation_loss == 20
