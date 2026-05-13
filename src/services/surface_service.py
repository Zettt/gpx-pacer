"""Route-level surface detection service."""

from src.model.data import SplitSegment, TrackPoint
from src.services.surface_geometry import (
    build_projected_split_polyline,
    calculate_track_bbox,
    make_local_projection,
    parse_overpass_ways,
)
from src.services.surface_matching import build_way_index, choose_best_way
from src.services.surface_normalization import normalize_surface
from src.services.surface_overpass import (
    SurfaceQueryError,
    fetch_route_surface_context,
)


def detect_surfaces(
    splits: list[SplitSegment],
    points: list[TrackPoint],
    endpoint: str | None = None,
) -> list[SplitSegment]:
    """Fetch route data once, then assign split surfaces locally."""
    if not splits or not points:
        return splits

    print("Querying route surface data...")
    bbox = calculate_track_bbox(points)
    route_surface_data = fetch_route_surface_context(bbox, endpoint=endpoint)
    ways = parse_overpass_ways(route_surface_data.payload)
    print(_format_surface_data_summary(route_surface_data.source, len(ways)))
    projection = make_local_projection(bbox)
    index = build_way_index(ways, projection)

    for split in splits:
        split_geometry = build_projected_split_polyline(points, split, projection)
        matched_way = choose_best_way(split_geometry, index)
        split.surface = normalize_surface(
            matched_way.tags.get("surface") if matched_way else None
        )

    return splits


def _format_surface_data_summary(source: str, way_count: int) -> str:
    if source == "cache":
        return f"Using cached route surface data: {way_count} highway ways."
    return f"Using route surface data from Overpass: {way_count} highway ways."
