"""Route-level Overpass acquisition and caching for surface lookup."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

import requests

from src.services.surface_geometry import BBox

DEFAULT_OVERPASS_ENDPOINT = "https://overpass-api.de/api/interpreter"
_SURFACE_RETRY_DELAYS = (0.5, 1.0)
_SURFACE_MAX_ATTEMPTS = len(_SURFACE_RETRY_DELAYS) + 1
_QUERY_VERSION = "surface-bbox-v1"
_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


@dataclass(frozen=True)
class RouteSurfaceData:
    payload: dict
    source: str
    endpoint: str


class SurfaceQueryError(RuntimeError):
    def __init__(
        self,
        endpoint: str,
        lat_or_detail: float | str | None = None,
        lon: float | None = None,
        detail: str | None = None,
        attempts: int = 1,
        max_attempts: int = 1,
        retry_state: str = "retry skipped",
        bbox: BBox | None = None,
    ):
        if detail is None and isinstance(lat_or_detail, str) and lon is None:
            lat = None
            detail = lat_or_detail
        else:
            lat = lat_or_detail if isinstance(lat_or_detail, (int, float)) else None

        location = ""
        if bbox is not None:
            location = (
                f" within bbox ({bbox.south:.6f}, {bbox.west:.6f}, "
                f"{bbox.north:.6f}, {bbox.east:.6f})"
            )
        elif lat is not None and lon is not None:
            location = f" at ({lat:.6f}, {lon:.6f})"

        self.endpoint = endpoint
        self.detail = detail or "unknown surface lookup error"
        self.attempts = attempts
        self.max_attempts = max_attempts
        self.retry_state = retry_state
        self.bbox = bbox
        super().__init__(
            f"Surface lookup failed via {endpoint}{location} on attempt "
            f"{attempts}/{max_attempts} ({retry_state}): {self.detail}"
        )


def build_overpass_query(bbox: BBox) -> str:
    return (
        "[out:json][timeout:25];"
        f'way["highway"]({bbox.south},{bbox.west},{bbox.north},{bbox.east});'
        "out tags geom;"
    )


def fetch_route_surface_data(
    bbox: BBox, endpoint: str | None = None, cache_dir: Path | None = None
) -> dict:
    """Fetch one route-level Overpass extract, using cache when possible."""
    return fetch_route_surface_context(
        bbox,
        endpoint=endpoint,
        cache_dir=cache_dir,
    ).payload


def fetch_route_surface_context(
    bbox: BBox, endpoint: str | None = None, cache_dir: Path | None = None
) -> RouteSurfaceData:
    """Fetch one route-level Overpass extract plus source metadata."""
    endpoint_url = endpoint or DEFAULT_OVERPASS_ENDPOINT
    cache_path = _cache_file_path(endpoint_url, bbox, cache_dir)
    cached_payload = _load_cached_response(cache_path)
    if cached_payload is not None:
        return RouteSurfaceData(
            payload=cached_payload,
            source="cache",
            endpoint=endpoint_url,
        )

    query = build_overpass_query(bbox)

    for attempt in range(1, _SURFACE_MAX_ATTEMPTS + 1):
        try:
            response = requests.post(endpoint_url, data=query, timeout=30)
            if response.status_code in _RETRYABLE_STATUS_CODES:
                raise requests.HTTPError(
                    f"HTTP {response.status_code}",
                    response=response,
                )
            response.raise_for_status()

            payload = response.json()
            _write_cached_response(cache_path, payload)
            return RouteSurfaceData(
                payload=payload,
                source="endpoint",
                endpoint=endpoint_url,
            )
        except Exception as exc:
            retryable = _is_retryable_surface_error(exc)
            if retryable and attempt < _SURFACE_MAX_ATTEMPTS:
                time.sleep(_SURFACE_RETRY_DELAYS[attempt - 1])
                continue

            raise SurfaceQueryError(
                endpoint_url,
                detail=_surface_error_detail(exc),
                attempts=attempt,
                max_attempts=_SURFACE_MAX_ATTEMPTS if retryable else 1,
                retry_state="retries exhausted" if retryable else "retry skipped",
                bbox=bbox,
            ) from exc

    raise SurfaceQueryError(
        endpoint_url,
        detail="unexpected retry loop exit",
        attempts=_SURFACE_MAX_ATTEMPTS,
        max_attempts=_SURFACE_MAX_ATTEMPTS,
        retry_state="retries exhausted",
        bbox=bbox,
    )


def _cache_file_path(
    endpoint: str, bbox: BBox, cache_dir: Path | None = None
) -> Path:
    cache_root = cache_dir or (Path.home() / ".cache" / "gpx-pacer" / "surface")
    cache_root.mkdir(parents=True, exist_ok=True)
    cache_key = sha256(
        (
            f"{endpoint}|{bbox.south:.6f}|{bbox.west:.6f}|"
            f"{bbox.north:.6f}|{bbox.east:.6f}|{_QUERY_VERSION}"
        ).encode("utf-8")
    ).hexdigest()
    return cache_root / f"{cache_key}.json"


def _load_cached_response(path: Path) -> dict | None:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _write_cached_response(path: Path, payload: dict) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle)


def _is_retryable_surface_error(exc: Exception) -> bool:
    if isinstance(exc, (requests.Timeout, requests.ConnectionError)):
        return True
    if isinstance(exc, requests.HTTPError) and exc.response is not None:
        return exc.response.status_code in _RETRYABLE_STATUS_CODES
    return False


def _surface_error_detail(exc: Exception) -> str:
    if isinstance(exc, requests.HTTPError) and exc.response is not None:
        return f"HTTP {exc.response.status_code}"
    return str(exc)
