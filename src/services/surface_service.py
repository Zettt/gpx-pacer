"""Surface detection service — queries OpenStreetMap Overpass API for road surface types."""
from typing import List
import overpy

from src.model.data import TrackPoint, SplitSegment


# Mapping from OSM surface tag values to user-friendly labels
_SURFACE_MAP: dict[str, str] = {
    "asphalt": "Asphalt",
    "paved": "Paved",
    "concrete": "Paved",
    "concrete:plates": "Paved",
    "concrete:lanes": "Paved",
    "paving_stones": "Paved",
    "sett": "Paved",
    "cobblestone": "Paved",
    "gravel": "Gravel",
    "fine_gravel": "Gravel",
    "pebblestone": "Gravel",
    "dirt": "Unpaved",
    "earth": "Unpaved",
    "ground": "Unpaved",
    "mud": "Unpaved",
    "sand": "Unpaved",
    "grass": "Unpaved",
    "compacted": "Compacted",
    "wood": "Wood",
    "metal": "Metal",
}


def _normalize_surface(raw: str) -> str:
    """Map an OSM surface tag value to a user-friendly label."""
    if not raw:
        return "Unknown"
    return _SURFACE_MAP.get(raw.lower(), "Unknown")


def query_surface(lat: float, lon: float) -> str:
    """Query the Overpass API for the road/path surface at the given coordinate.

    Returns a human-readable surface label (e.g., "Asphalt", "Gravel") or "Unknown".
    """
    try:
        api = overpy.Overpass()
        # Query for the nearest way (road/path) within 20m of the coordinate
        query = f"""
            [out:json][timeout:10];
            way(around:20,{lat},{lon})["highway"];
            out tags;
        """
        result = api.query(query)

        if not result.ways:
            return "Unknown"

        # Use the first way's surface tag
        way = result.ways[0]
        raw_surface = way.tags.get("surface", "")
        return _normalize_surface(raw_surface)
    except Exception:
        return "Unknown"


def _interpolate_point(
    points: List[TrackPoint], target_distance: float
) -> tuple[float, float]:
    """Interpolate lat/lon at a given distance along the track."""
    if not points:
        return (0.0, 0.0)

    # Clamp to track bounds
    if target_distance <= points[0].distance_from_start:
        return (points[0].lat, points[0].lon)
    if target_distance >= points[-1].distance_from_start:
        return (points[-1].lat, points[-1].lon)

    # Find the two surrounding points
    for i in range(len(points) - 1):
        p1 = points[i]
        p2 = points[i + 1]
        if p1.distance_from_start <= target_distance <= p2.distance_from_start:
            segment_len = p2.distance_from_start - p1.distance_from_start
            if segment_len == 0:
                return (p1.lat, p1.lon)
            fraction = (target_distance - p1.distance_from_start) / segment_len
            lat = p1.lat + fraction * (p2.lat - p1.lat)
            lon = p1.lon + fraction * (p2.lon - p1.lon)
            return (lat, lon)

    # Fallback
    return (points[-1].lat, points[-1].lon)


def detect_surfaces(
    splits: List[SplitSegment], points: List[TrackPoint]
) -> List[SplitSegment]:
    """Query surface type for each split's midpoint and populate the surface field.

    Prints progress messages so the user knows it hasn't hung.
    """
    total = len(splits)
    for i, split in enumerate(splits):
        midpoint_distance = (split.start_distance + split.end_distance) / 2
        lat, lon = _interpolate_point(points, midpoint_distance)

        print(f"Querying surface {i + 1}/{total}...")
        split.surface = query_surface(lat, lon)

    return splits
