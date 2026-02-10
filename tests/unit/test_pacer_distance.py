import pytest
from src.model.data import TrackPoint, SplitSegment
# We will implement this in T012
from src.services.pacer import create_distance_splits 

def test_fixed_distance_splits_exact_match():
    # 3 points, total 2000m. Split every 1000m.
    points = [
        TrackPoint(lat=0, lon=0, ele=0, distance_from_start=0),
        TrackPoint(lat=0, lon=0, ele=10, distance_from_start=1000),
        TrackPoint(lat=0, lon=0, ele=20, distance_from_start=2000),
    ]
    
    splits = create_distance_splits(points, split_distance_meters=1000)
    
    assert len(splits) == 2
    assert splits[0].length == 1000
    assert splits[0].elevation_gain == 10
    assert splits[1].length == 1000
    assert splits[1].elevation_gain == 10

def test_fixed_distance_splits_remainder():
    # Total 1500m. Split every 1000m.
    points = [
        TrackPoint(lat=0, lon=0, ele=0, distance_from_start=0),
        TrackPoint(lat=0, lon=0, ele=10, distance_from_start=1000),
        TrackPoint(lat=0, lon=0, ele=15, distance_from_start=1500),
    ]
    
    splits = create_distance_splits(points, split_distance_meters=1000)
    
    assert len(splits) == 2
    assert splits[0].length == 1000
    assert splits[1].length == 500
    assert splits[1].elevation_gain == 5

def test_interpolation_logic():
    # Point at 0m and 2000m. Split at 1000m.
    # Should interpolate elevation.
    points = [
        TrackPoint(lat=0, lon=0, ele=0, distance_from_start=0),
        TrackPoint(lat=0, lon=0, ele=20, distance_from_start=2000),
    ]
    
    splits = create_distance_splits(points, split_distance_meters=1000)
    
    assert len(splits) == 2
    # First split 0-1000m. Gain should be 10m (half of 20).
    assert splits[0].length == 1000
    assert splits[0].elevation_gain == 10

def test_net_change_positive():
    """Net change is positive when gain exceeds loss."""
    segment = SplitSegment(
        start_distance=0, end_distance=1000, length=1000,
        elevation_gain=50, elevation_loss=30
    )
    assert segment.net_change == 20

def test_net_change_negative():
    """Net change is negative when loss exceeds gain."""
    segment = SplitSegment(
        start_distance=0, end_distance=1000, length=1000,
        elevation_gain=10, elevation_loss=40
    )
    assert segment.net_change == -30

def test_net_change_zero():
    """Net change is zero when gain equals loss."""
    segment = SplitSegment(
        start_distance=0, end_distance=1000, length=1000,
        elevation_gain=25, elevation_loss=25
    )
    assert segment.net_change == 0
