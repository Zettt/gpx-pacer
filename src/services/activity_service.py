from __future__ import annotations

from pathlib import Path

from src.services.fit_service import parse_fit
from src.services.gpx_service import parse_gpx


def parse_activity(file_path: str) -> tuple[list, list, dict]:
    suffix = Path(file_path).suffix.lower()

    if suffix == ".gpx":
        track_points, waypoints = parse_gpx(file_path)
        return track_points, waypoints, {}

    if suffix == ".fit":
        return parse_fit(file_path)

    raise ValueError(f"Unsupported input format: '{suffix or '<none>'}'")
