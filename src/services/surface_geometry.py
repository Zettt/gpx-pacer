"""Geometry helpers for route-level surface lookup."""

from dataclasses import dataclass

from pyproj import CRS, Geod, Transformer
from shapely.geometry import LineString

from src.model.data import SplitSegment, TrackPoint


@dataclass(frozen=True)
class BBox:
    south: float
    west: float
    north: float
    east: float


@dataclass(frozen=True)
class SurfaceWay:
    way_id: int
    tags: dict[str, str]
    geometry: LineString


def calculate_track_bbox(
    points: list[TrackPoint], buffer_m: float = 250.0
) -> BBox:
    """Calculate a buffered lat/lon bbox around the full activity track."""
    if not points:
        raise ValueError("cannot calculate bbox without track points")

    min_lat = min(point.lat for point in points)
    max_lat = max(point.lat for point in points)
    min_lon = min(point.lon for point in points)
    max_lon = max(point.lon for point in points)

    center_lat = (min_lat + max_lat) / 2
    center_lon = (min_lon + max_lon) / 2
    geod = Geod(ellps="WGS84")

    _, south, _ = geod.fwd(center_lon, min_lat, 180, buffer_m)
    _, north, _ = geod.fwd(center_lon, max_lat, 0, buffer_m)
    west, _, _ = geod.fwd(min_lon, center_lat, 270, buffer_m)
    east, _, _ = geod.fwd(max_lon, center_lat, 90, buffer_m)

    return BBox(south=south, west=west, north=north, east=east)


def parse_overpass_ways(payload: dict) -> list[SurfaceWay]:
    """Parse Overpass JSON into local way geometries."""
    ways: list[SurfaceWay] = []

    for element in payload.get("elements", []):
        if element.get("type") != "way":
            continue
        tags = element.get("tags") or {}
        if "highway" not in tags:
            continue

        coords = [
            (node["lon"], node["lat"])
            for node in element.get("geometry", [])
            if "lon" in node and "lat" in node
        ]
        if len(coords) < 2:
            continue

        ways.append(
            SurfaceWay(
                way_id=int(element["id"]),
                tags=tags,
                geometry=LineString(coords),
            )
        )

    return ways


def make_local_projection(bbox: BBox) -> Transformer:
    """Create a local metric projection centered on the activity track."""
    center_lat = (bbox.south + bbox.north) / 2
    center_lon = (bbox.west + bbox.east) / 2
    local_crs = CRS.from_proj4(
        f"+proj=aeqd +lat_0={center_lat} +lon_0={center_lon} "
        "+datum=WGS84 +units=m +no_defs"
    )
    return Transformer.from_crs("EPSG:4326", local_crs, always_xy=True)


def project_linestring(line: LineString, transformer: Transformer) -> LineString:
    return LineString([transformer.transform(x, y) for x, y in line.coords])


def build_split_polyline(points: list[TrackPoint], split: SplitSegment) -> LineString:
    """Reconstruct one split's sub-line from track distance bounds."""
    if not points:
        raise ValueError("cannot build split polyline without track points")

    coords = [_interpolate_coord(points, split.start_distance)]
    coords.extend(
        (point.lon, point.lat)
        for point in points
        if split.start_distance < point.distance_from_start < split.end_distance
    )
    coords.append(_interpolate_coord(points, split.end_distance))

    deduped: list[tuple[float, float]] = []
    for coord in coords:
        if not deduped or coord != deduped[-1]:
            deduped.append(coord)

    if len(deduped) == 1:
        deduped.append(deduped[0])

    return LineString(deduped)


def build_projected_split_polyline(
    points: list[TrackPoint], split: SplitSegment, transformer: Transformer
) -> LineString:
    return project_linestring(build_split_polyline(points, split), transformer)


def _interpolate_coord(
    points: list[TrackPoint], target_distance: float
) -> tuple[float, float]:
    if target_distance <= points[0].distance_from_start:
        return (points[0].lon, points[0].lat)
    if target_distance >= points[-1].distance_from_start:
        return (points[-1].lon, points[-1].lat)

    for index in range(len(points) - 1):
        start = points[index]
        end = points[index + 1]
        if start.distance_from_start <= target_distance <= end.distance_from_start:
            segment_length = end.distance_from_start - start.distance_from_start
            if segment_length == 0:
                return (start.lon, start.lat)
            fraction = (target_distance - start.distance_from_start) / segment_length
            lon = start.lon + fraction * (end.lon - start.lon)
            lat = start.lat + fraction * (end.lat - start.lat)
            return (lon, lat)

    return (points[-1].lon, points[-1].lat)
