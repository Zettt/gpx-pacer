from unittest.mock import patch

import pytest

from src.model.data import SplitSegment, TrackPoint
from src.services.surface_overpass import RouteSurfaceData


def _make_points() -> list[TrackPoint]:
    return [
        TrackPoint(lat=48.0000, lon=11.0000, ele=500, distance_from_start=0),
        TrackPoint(lat=48.0000, lon=11.0050, ele=500, distance_from_start=500),
        TrackPoint(lat=48.0000, lon=11.0100, ele=500, distance_from_start=1000),
    ]


def _make_splits() -> list[SplitSegment]:
    return [
        SplitSegment(
            start_distance=0,
            end_distance=500,
            length=500,
            elevation_gain=0,
            elevation_loss=0,
            name="Split 1",
        ),
        SplitSegment(
            start_distance=500,
            end_distance=1000,
            length=500,
            elevation_gain=0,
            elevation_loss=0,
            name="Split 2",
        ),
    ]


def _make_overpass_payload() -> dict:
    return {
        "elements": [
            {
                "type": "way",
                "id": 101,
                "tags": {"highway": "path", "surface": "asphalt"},
                "geometry": [
                    {"lat": 48.0000, "lon": 11.0000},
                    {"lat": 48.0000, "lon": 11.0050},
                ],
            },
            {
                "type": "way",
                "id": 102,
                "tags": {"highway": "path", "surface": "gravel"},
                "geometry": [
                    {"lat": 48.0000, "lon": 11.0050},
                    {"lat": 48.0000, "lon": 11.0100},
                ],
            },
        ]
    }


class TestDetectSurfaces:
    @patch("src.services.surface_service.fetch_route_surface_context")
    def test_fetches_route_surface_data_once(self, mock_fetch):
        from src.services.surface_service import detect_surfaces

        mock_fetch.return_value = RouteSurfaceData(
            payload=_make_overpass_payload(),
            source="endpoint",
            endpoint="https://example.test/api/interpreter",
        )

        splits = detect_surfaces(_make_splits(), _make_points())

        assert [split.surface for split in splits] == ["Asphalt", "Gravel"]
        mock_fetch.assert_called_once()

    @patch("src.services.surface_service.fetch_route_surface_context")
    def test_sets_unknown_for_unmatched_split(self, mock_fetch):
        from src.services.surface_service import detect_surfaces

        mock_fetch.return_value = RouteSurfaceData(
            payload={"elements": []},
            source="endpoint",
            endpoint="https://example.test/api/interpreter",
        )

        splits = detect_surfaces(_make_splits(), _make_points())

        assert [split.surface for split in splits] == ["Unknown", "Unknown"]

    @patch("src.services.surface_service.fetch_route_surface_context")
    def test_sets_unknown_when_way_has_no_surface_tag(self, mock_fetch):
        from src.services.surface_service import detect_surfaces

        mock_fetch.return_value = RouteSurfaceData(
            payload={
                "elements": [
                    {
                        "type": "way",
                        "id": 201,
                        "tags": {"highway": "path"},
                        "geometry": [
                            {"lat": 48.0000, "lon": 11.0000},
                            {"lat": 48.0000, "lon": 11.0100},
                        ],
                    }
                ]
            },
            source="endpoint",
            endpoint="https://example.test/api/interpreter",
        )

        splits = detect_surfaces(_make_splits(), _make_points())

        assert [split.surface for split in splits] == ["Unknown", "Unknown"]

    @patch("src.services.surface_service.fetch_route_surface_context")
    def test_passes_endpoint_to_route_fetch(self, mock_fetch):
        from src.services.surface_service import detect_surfaces

        mock_fetch.return_value = RouteSurfaceData(
            payload=_make_overpass_payload(),
            source="endpoint",
            endpoint="https://example.test/api/interpreter",
        )

        detect_surfaces(
            _make_splits(),
            _make_points(),
            endpoint="https://example.test/api/interpreter",
        )

        assert mock_fetch.call_args.kwargs["endpoint"] == "https://example.test/api/interpreter"

    @patch("src.services.surface_service.fetch_route_surface_context")
    def test_propagates_route_lookup_failures(self, mock_fetch):
        from src.services.surface_service import SurfaceQueryError, detect_surfaces

        mock_fetch.side_effect = SurfaceQueryError(
            "default",
            detail="HTTP 503",
            attempts=3,
            max_attempts=3,
            retry_state="retries exhausted",
        )

        with pytest.raises(SurfaceQueryError) as exc_info:
            detect_surfaces(_make_splits(), _make_points())

        assert "HTTP 503" in str(exc_info.value)

    @patch("src.services.surface_service.fetch_route_surface_context")
    def test_prints_one_acquisition_summary_and_no_per_split_progress(
        self, mock_fetch, capsys
    ):
        from src.services.surface_service import detect_surfaces

        mock_fetch.return_value = RouteSurfaceData(
            payload=_make_overpass_payload(),
            source="cache",
            endpoint="https://example.test/api/interpreter",
        )

        detect_surfaces(_make_splits(), _make_points())

        captured = capsys.readouterr()
        assert "Querying route surface data..." in captured.out
        assert "Using cached route surface data: 2 highway ways." in captured.out
        assert "Matching surface" not in captured.out
