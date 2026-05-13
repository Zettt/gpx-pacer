from gpxpy.geo import haversine_distance as _gpxpy_haversine_distance


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    return _gpxpy_haversine_distance(lat1, lon1, lat2, lon2)
