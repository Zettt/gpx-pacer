"""Unit tests for the surface detection service (TDD - written before implementation)."""
import pytest
from unittest.mock import patch, MagicMock
from src.model.data import TrackPoint, SplitSegment


# --- Tests for _normalize_surface ---

class TestNormalizeSurface:
    def test_asphalt(self):
        from src.services.surface_service import _normalize_surface
        assert _normalize_surface("asphalt") == "Asphalt"

    def test_paved(self):
        from src.services.surface_service import _normalize_surface
        assert _normalize_surface("paved") == "Paved"

    def test_gravel(self):
        from src.services.surface_service import _normalize_surface
        assert _normalize_surface("gravel") == "Gravel"

    def test_dirt(self):
        from src.services.surface_service import _normalize_surface
        assert _normalize_surface("dirt") == "Unpaved"

    def test_ground(self):
        from src.services.surface_service import _normalize_surface
        assert _normalize_surface("ground") == "Unpaved"

    def test_fine_gravel(self):
        from src.services.surface_service import _normalize_surface
        assert _normalize_surface("fine_gravel") == "Gravel"

    def test_concrete(self):
        from src.services.surface_service import _normalize_surface
        assert _normalize_surface("concrete") == "Paved"

    def test_compacted(self):
        from src.services.surface_service import _normalize_surface
        assert _normalize_surface("compacted") == "Compacted"

    def test_unknown_value(self):
        from src.services.surface_service import _normalize_surface
        assert _normalize_surface("something_exotic") == "Unknown"

    def test_empty_string(self):
        from src.services.surface_service import _normalize_surface
        assert _normalize_surface("") == "Unknown"


# --- Tests for query_surface ---

class TestQuerySurface:
    @patch("src.services.surface_service.overpy.Overpass")
    def test_returns_surface_from_way(self, mock_overpass_cls):
        from src.services.surface_service import query_surface

        # Set up mock way with surface tag
        mock_way = MagicMock()
        mock_way.tags = {"surface": "asphalt", "highway": "residential"}

        mock_result = MagicMock()
        mock_result.ways = [mock_way]

        mock_api = MagicMock()
        mock_api.query.return_value = mock_result
        mock_overpass_cls.return_value = mock_api

        result = query_surface(48.137, 11.575)
        assert result == "Asphalt"

    @patch("src.services.surface_service.overpy.Overpass")
    def test_returns_unknown_when_no_ways(self, mock_overpass_cls):
        from src.services.surface_service import query_surface

        mock_result = MagicMock()
        mock_result.ways = []

        mock_api = MagicMock()
        mock_api.query.return_value = mock_result
        mock_overpass_cls.return_value = mock_api

        result = query_surface(48.137, 11.575)
        assert result == "Unknown"

    @patch("src.services.surface_service.overpy.Overpass")
    def test_returns_unknown_when_no_surface_tag(self, mock_overpass_cls):
        from src.services.surface_service import query_surface

        mock_way = MagicMock()
        mock_way.tags = {"highway": "residential"}  # No surface tag

        mock_result = MagicMock()
        mock_result.ways = [mock_way]

        mock_api = MagicMock()
        mock_api.query.return_value = mock_result
        mock_overpass_cls.return_value = mock_api

        result = query_surface(48.137, 11.575)
        assert result == "Unknown"

    @patch("src.services.surface_service.overpy.Overpass")
    def test_handles_api_exception(self, mock_overpass_cls):
        from src.services.surface_service import query_surface

        mock_api = MagicMock()
        mock_api.query.side_effect = Exception("API timeout")
        mock_overpass_cls.return_value = mock_api

        result = query_surface(48.137, 11.575)
        assert result == "Unknown"


# --- Tests for detect_surfaces ---

class TestDetectSurfaces:
    @patch("src.services.surface_service.query_surface")
    def test_sets_surface_on_all_splits(self, mock_query):
        from src.services.surface_service import detect_surfaces

        mock_query.return_value = "Asphalt"

        points = [
            TrackPoint(lat=48.0, lon=11.0, ele=500, distance_from_start=0),
            TrackPoint(lat=48.01, lon=11.01, ele=510, distance_from_start=500),
            TrackPoint(lat=48.02, lon=11.02, ele=520, distance_from_start=1000),
        ]

        splits = [
            SplitSegment(start_distance=0, end_distance=500, length=500,
                         elevation_gain=10, elevation_loss=0, name="Split 1"),
            SplitSegment(start_distance=500, end_distance=1000, length=500,
                         elevation_gain=10, elevation_loss=0, name="Split 2"),
        ]

        result = detect_surfaces(splits, points)

        assert len(result) == 2
        assert result[0].surface == "Asphalt"
        assert result[1].surface == "Asphalt"
        assert mock_query.call_count == 2

    @patch("src.services.surface_service.query_surface")
    def test_prints_progress(self, mock_query, capsys):
        from src.services.surface_service import detect_surfaces

        mock_query.return_value = "Gravel"

        points = [
            TrackPoint(lat=48.0, lon=11.0, ele=500, distance_from_start=0),
            TrackPoint(lat=48.01, lon=11.01, ele=510, distance_from_start=1000),
        ]

        splits = [
            SplitSegment(start_distance=0, end_distance=1000, length=1000,
                         elevation_gain=10, elevation_loss=0, name="Split 1"),
        ]

        detect_surfaces(splits, points)

        captured = capsys.readouterr()
        assert "Querying surface 1/1" in captured.out

    @patch("src.services.surface_service.query_surface")
    def test_midpoint_coordinate_used(self, mock_query):
        """Verify the query is called with the midpoint coordinate of each split."""
        from src.services.surface_service import detect_surfaces

        mock_query.return_value = "Asphalt"

        points = [
            TrackPoint(lat=48.0, lon=11.0, ele=500, distance_from_start=0),
            TrackPoint(lat=48.1, lon=11.1, ele=510, distance_from_start=1000),
        ]

        splits = [
            SplitSegment(start_distance=0, end_distance=1000, length=1000,
                         elevation_gain=10, elevation_loss=0, name="Split 1"),
        ]

        detect_surfaces(splits, points)

        # The midpoint is at distance 500. With linear interpolation between
        # (48.0, 11.0) at d=0 and (48.1, 11.1) at d=1000, midpoint ≈ (48.05, 11.05)
        call_args = mock_query.call_args
        lat, lon = call_args[0]
        assert abs(lat - 48.05) < 0.01
        assert abs(lon - 11.05) < 0.01
