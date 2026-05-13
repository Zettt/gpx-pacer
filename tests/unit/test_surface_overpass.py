from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def test_fetch_route_surface_data_uses_cache_when_present(tmp_path):
    from src.services.surface_geometry import BBox
    from src.services.surface_overpass import fetch_route_surface_data

    bbox = BBox(south=48.0, west=11.0, north=48.01, east=11.01)
    cached = {"elements": [{"type": "way", "id": 1, "tags": {"highway": "path"}, "geometry": []}]}

    payload_path = tmp_path / "payload.json"
    payload_path.write_text('{"ignore": true}', encoding="utf-8")

    with patch("src.services.surface_overpass._cache_file_path", return_value=payload_path):
        payload_path.write_text(__import__("json").dumps(cached), encoding="utf-8")
        with patch("src.services.surface_overpass.requests.post") as mock_post:
            result = fetch_route_surface_data(bbox, cache_dir=tmp_path)

    assert result == cached
    mock_post.assert_not_called()


def test_fetch_route_surface_data_uses_cache_when_request_fails(tmp_path):
    from src.services.surface_geometry import BBox
    from src.services.surface_overpass import fetch_route_surface_data

    bbox = BBox(south=48.0, west=11.0, north=48.01, east=11.01)
    cached = {"elements": [{"type": "way", "id": 1, "tags": {"highway": "path"}, "geometry": []}]}
    payload_path = tmp_path / "payload.json"
    payload_path.write_text(__import__("json").dumps(cached), encoding="utf-8")

    with patch("src.services.surface_overpass._cache_file_path", return_value=payload_path):
        with patch("src.services.surface_overpass.requests.post", side_effect=RuntimeError("boom")):
            result = fetch_route_surface_data(bbox, cache_dir=tmp_path)

    assert result == cached


def test_fetch_route_surface_data_raises_without_cache_on_request_failure(tmp_path):
    from src.services.surface_geometry import BBox
    from src.services.surface_overpass import SurfaceQueryError, fetch_route_surface_data

    bbox = BBox(south=48.0, west=11.0, north=48.01, east=11.01)
    payload_path = tmp_path / "missing.json"

    with patch("src.services.surface_overpass._cache_file_path", return_value=payload_path):
        with patch("src.services.surface_overpass.requests.post", side_effect=RuntimeError("boom")):
            with pytest.raises(SurfaceQueryError) as exc_info:
                fetch_route_surface_data(bbox, cache_dir=tmp_path)

    assert "boom" in str(exc_info.value)
