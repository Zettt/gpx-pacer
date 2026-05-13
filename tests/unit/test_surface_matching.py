from src.model.data import SplitSegment, TrackPoint


def test_choose_best_way_prefers_overlap_over_closer_parallel_way():
    from src.services.surface_geometry import (
        build_projected_split_polyline,
        calculate_track_bbox,
        make_local_projection,
        parse_overpass_ways,
    )
    from src.services.surface_matching import build_way_index, choose_best_way

    points = [
        TrackPoint(lat=48.0000, lon=11.0000, distance_from_start=0),
        TrackPoint(lat=48.0000, lon=11.0100, distance_from_start=1000),
    ]
    split = SplitSegment(
        start_distance=0,
        end_distance=1000,
        length=1000,
        elevation_gain=0,
        elevation_loss=0,
        name="Whole",
    )
    payload = {
        "elements": [
            {
                "type": "way",
                "id": 1,
                "tags": {"highway": "path", "surface": "asphalt"},
                "geometry": [
                    {"lat": 48.0000, "lon": 11.0000},
                    {"lat": 48.0000, "lon": 11.0100},
                ],
            },
            {
                "type": "way",
                "id": 2,
                "tags": {"highway": "service", "surface": "gravel"},
                "geometry": [
                    {"lat": 48.00004, "lon": 11.0000},
                    {"lat": 48.00004, "lon": 11.0030},
                ],
            },
        ]
    }

    bbox = calculate_track_bbox(points)
    project = make_local_projection(bbox)
    ways = parse_overpass_ways(payload)
    index = build_way_index(ways, project)
    split_line = build_projected_split_polyline(points, split, project)

    best_way = choose_best_way(split_line, index)

    assert best_way is not None
    assert best_way.way_id == 1
