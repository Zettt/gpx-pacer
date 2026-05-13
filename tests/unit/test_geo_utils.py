from src.lib.geo_utils import haversine_distance


def test_haversine_distance_returns_zero_for_same_point():
    assert haversine_distance(48.0, 7.0, 48.0, 7.0) == 0.0


def test_haversine_distance_matches_known_short_distance():
    distance_m = haversine_distance(48.0000, 7.0000, 48.0000, 7.0010)

    assert round(distance_m, 1) == 74.5
