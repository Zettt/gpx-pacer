import pytest

from src.model.data import SplitSegment, TrackPoint


def test_calculate_track_bbox_applies_default_buffer():
    from src.services.surface_geometry import calculate_track_bbox

    points = [
        TrackPoint(lat=48.0000, lon=11.0000, distance_from_start=0),
        TrackPoint(lat=48.0010, lon=11.0020, distance_from_start=1000),
    ]

    bbox = calculate_track_bbox(points)

    assert bbox.south < 48.0000
    assert bbox.west < 11.0000
    assert bbox.north > 48.0010
    assert bbox.east > 11.0020


def test_parse_overpass_ways_keeps_way_geometry_and_tags():
    from src.services.surface_geometry import parse_overpass_ways

    payload = {
        "elements": [
            {
                "type": "way",
                "id": 123,
                "tags": {"highway": "track", "surface": "gravel"},
                "geometry": [
                    {"lat": 48.0000, "lon": 11.0000},
                    {"lat": 48.0000, "lon": 11.0010},
                ],
            },
            {"type": "node", "id": 999, "lat": 48.0, "lon": 11.0},
        ]
    }

    ways = parse_overpass_ways(payload)

    assert len(ways) == 1
    assert ways[0].way_id == 123
    assert ways[0].tags["surface"] == "gravel"
    assert list(ways[0].geometry.coords) == [(11.0, 48.0), (11.001, 48.0)]


def test_build_split_polyline_reconstructs_subline_from_distance_bounds():
    from src.services.surface_geometry import build_split_polyline

    points = [
        TrackPoint(lat=48.0000, lon=11.0000, distance_from_start=0),
        TrackPoint(lat=48.0000, lon=11.0050, distance_from_start=500),
        TrackPoint(lat=48.0000, lon=11.0100, distance_from_start=1000),
    ]
    split = SplitSegment(
        start_distance=250,
        end_distance=750,
        length=500,
        elevation_gain=0,
        elevation_loss=0,
        name="Middle",
    )

    line = build_split_polyline(points, split)

    coords = list(line.coords)
    assert len(coords) == 3
    assert coords[0][0] == pytest.approx(11.0025)
    assert coords[-1][0] == pytest.approx(11.0075)
