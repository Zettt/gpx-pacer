"""Spatial matching for route-level surface lookup."""

from dataclasses import dataclass

from pyproj import Transformer
from shapely.geometry import LineString
from shapely.strtree import STRtree

from src.services.surface_geometry import SurfaceWay, project_linestring


@dataclass(frozen=True)
class ProjectedSurfaceWay:
    way_id: int
    tags: dict[str, str]
    geometry: LineString


@dataclass(frozen=True)
class WayIndex:
    ways: list[ProjectedSurfaceWay]
    tree: STRtree
    geometry_map: dict[int, ProjectedSurfaceWay]


def build_way_index(ways: list[SurfaceWay], transformer: Transformer) -> WayIndex:
    projected_ways = [
        ProjectedSurfaceWay(
            way_id=way.way_id,
            tags=way.tags,
            geometry=project_linestring(way.geometry, transformer),
        )
        for way in ways
    ]
    geometries = [way.geometry for way in projected_ways]
    return WayIndex(
        ways=projected_ways,
        tree=STRtree(geometries),
        geometry_map={id(geometry): way for geometry, way in zip(geometries, projected_ways)},
    )


def choose_best_way(
    split_geometry: LineString, index: WayIndex, match_radius_m: float = 25.0
) -> ProjectedSurfaceWay | None:
    """Choose the best matching way using overlap first, then distance."""
    if not index.ways:
        return None

    search_area = split_geometry.buffer(match_radius_m)
    candidates = _resolve_candidates(index, index.tree.query(search_area))

    best_way: ProjectedSurfaceWay | None = None
    best_score: tuple[float, float] | None = None

    for candidate in candidates:
        distance = candidate.geometry.distance(split_geometry)
        overlap_length = candidate.geometry.intersection(search_area).length
        if overlap_length == 0 and distance > match_radius_m:
            continue

        score = (overlap_length, -distance)
        if best_score is None or score > best_score:
            best_way = candidate
            best_score = score

    return best_way


def _resolve_candidates(index: WayIndex, query_result) -> list[ProjectedSurfaceWay]:
    resolved: list[ProjectedSurfaceWay] = []

    for item in query_result:
        raw = item.item() if hasattr(item, "item") else item
        if isinstance(raw, int):
            resolved.append(index.ways[raw])
        else:
            resolved.append(index.geometry_map[id(raw)])

    return resolved
