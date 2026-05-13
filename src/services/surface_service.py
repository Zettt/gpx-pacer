"""Surface detection service — queries OpenStreetMap Overpass API for road surface types."""
import http.client
import socket
import time
from typing import List
from urllib.error import URLError

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


class SurfaceQueryError(RuntimeError):
    def __init__(
        self,
        endpoint: str,
        lat: float,
        lon: float,
        detail: str,
        attempts: int = 1,
        max_attempts: int = 1,
        retry_state: str = "retry skipped",
    ):
        self.endpoint = endpoint
        self.lat = lat
        self.lon = lon
        self.detail = detail
        self.attempts = attempts
        self.max_attempts = max_attempts
        self.retry_state = retry_state
        super().__init__(
            f"Surface lookup failed via {endpoint} at ({lat:.6f}, {lon:.6f}) "
            f"on attempt {attempts}/{max_attempts} ({retry_state}): {detail}"
        )


_SURFACE_RETRY_DELAYS = (0.5, 1.0)
_SURFACE_MAX_ATTEMPTS = len(_SURFACE_RETRY_DELAYS) + 1


def _is_retryable_surface_error(exc: Exception) -> bool:
    if isinstance(
        exc,
        (
            overpy.exception.OverpassTooManyRequests,
            overpy.exception.OverpassGatewayTimeout,
            TimeoutError,
            socket.timeout,
            URLError,
            http.client.RemoteDisconnected,
        ),
    ):
        return True

    if isinstance(exc, overpy.exception.OverpassUnknownHTTPStatusCode):
        return exc.code in {500, 502, 503, 504}

    return False


def _normalize_surface(raw: str) -> str:
    """Map an OSM surface tag value to a user-friendly label."""
    if not raw:
        return "Unknown"
    return _SURFACE_MAP.get(raw.lower(), "Unknown")


def query_surface(lat: float, lon: float, endpoint: str | None = None) -> str:
    """Query the Overpass API for the road/path surface at the given coordinate.

    Returns a human-readable surface label (e.g., "Asphalt", "Gravel") or "Unknown".
    """
    api = (
        overpy.Overpass(max_retry_count=0)
        if endpoint is None
        else overpy.Overpass(url=endpoint, max_retry_count=0)
    )
    query = f"""
        [out:json][timeout:10];
        way(around:20,{lat},{lon})["highway"];
        out tags;
    """
    endpoint_label = endpoint or "default"

    for attempt in range(1, _SURFACE_MAX_ATTEMPTS + 1):
        try:
            result = api.query(query)

            if not result.ways:
                return "Unknown"

            way = result.ways[0]
            raw_surface = way.tags.get("surface", "")
            return _normalize_surface(raw_surface)
        except Exception as exc:
            retryable = _is_retryable_surface_error(exc)
            if retryable and attempt < _SURFACE_MAX_ATTEMPTS:
                time.sleep(_SURFACE_RETRY_DELAYS[attempt - 1])
                continue

            raise SurfaceQueryError(
                endpoint_label,
                lat,
                lon,
                str(exc),
                attempts=attempt,
                max_attempts=_SURFACE_MAX_ATTEMPTS if retryable else 1,
                retry_state="retries exhausted" if retryable else "retry skipped",
            ) from exc

    raise SurfaceQueryError(
        endpoint_label,
        lat,
        lon,
        "unexpected retry loop exit",
        attempts=_SURFACE_MAX_ATTEMPTS,
        max_attempts=_SURFACE_MAX_ATTEMPTS,
        retry_state="retries exhausted",
    )


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
    splits: List[SplitSegment], points: List[TrackPoint], endpoint: str | None = None
) -> List[SplitSegment]:
    """Query surface type for each split's midpoint and populate the surface field.

    Prints progress messages so the user knows it hasn't hung.
    """
    total = len(splits)
    for i, split in enumerate(splits):
        midpoint_distance = (split.start_distance + split.end_distance) / 2
        lat, lon = _interpolate_point(points, midpoint_distance)

        print(f"Querying surface {i + 1}/{total}...")
        split.surface = query_surface(lat, lon, endpoint=endpoint)

    return splits
