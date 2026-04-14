import gpxpy
import gpxpy.gpx
from typing import List, Tuple
from src.model.data import TrackPoint, Waypoint


def _parse_track_point_extensions(point: gpxpy.gpx.GPXTrackPoint) -> tuple[int | None, int | None, float | None]:
    heart_rate_bpm = None
    cadence = None
    temperature_c = None

    for extension in point.extensions:
        for child in extension:
            tag_name = child.tag.split("}")[-1]
            if child.text is None:
                continue
            if tag_name == "hr":
                heart_rate_bpm = int(child.text)
            elif tag_name == "cad":
                cadence = int(child.text)
            elif tag_name == "atemp":
                temperature_c = float(child.text)

    return heart_rate_bpm, cadence, temperature_c

def parse_gpx(file_path: str) -> Tuple[List[TrackPoint], List[Waypoint]]:
    """
    Parses a GPX file and returns a list of TrackPoints (with cumulative distance)
    and a list of Waypoints.
    """
    with open(file_path, 'r') as gpx_file:
        gpx = gpxpy.parse(gpx_file)

    track_points: List[TrackPoint] = []
    waypoints: List[Waypoint] = []
    
    # Process Tracks
    cumulative_distance = 0.0
    previous_point = None

    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                
                # Calculate distance from previous point
                if previous_point:
                    dist = point.distance_2d(previous_point)
                    if dist:
                         cumulative_distance += dist

                heart_rate_bpm, cadence, temperature_c = _parse_track_point_extensions(point)
                
                track_points.append(TrackPoint(
                    lat=point.latitude,
                    lon=point.longitude,
                    ele=point.elevation,
                    distance_from_start=cumulative_distance,
                    timestamp=point.time,
                    heart_rate_bpm=heart_rate_bpm,
                    cadence=cadence,
                    temperature_c=temperature_c,
                ))
                previous_point = point

    # Process Waypoints
    # Note: gpxpy parses top-level waypoints.
    # We map them to the track distance in a later step (pacer logic), 
    # here we just extract them.
    for wpt in gpx.waypoints:
        waypoints.append(Waypoint(
            name=wpt.name if wpt.name else f"Waypoint {wpt.latitude},{wpt.longitude}",
            lat=wpt.latitude,
            lon=wpt.longitude,
            distance_from_start=0.0 # To be calculated relative to track
        ))

    return track_points, waypoints


def map_waypoints_to_track(
    track_points: List[TrackPoint], 
    waypoints: List[Waypoint],
    off_route_threshold_m: float = 100.0
) -> Tuple[List[Waypoint], List[str]]:
    """
    Map waypoints to their nearest track points and assign distance_from_start.
    Waypoints are sorted by their distance along the track.
    
    Returns:
        Tuple of (mapped_waypoints, warnings) where warnings contains messages
        about any waypoints that are more than off_route_threshold_m from the track.
    """
    from src.lib.geo_utils import haversine_distance
    
    if not track_points or not waypoints:
        return [], []
    
    mapped_waypoints: List[Waypoint] = []
    warnings: List[str] = []
    
    for wpt in waypoints:
        min_dist_m = float('inf')
        nearest_track_dist = 0.0
        nearest_tp = track_points[0]
        
        # Find the nearest track point using haversine distance
        for tp in track_points:
            dist_m = haversine_distance(wpt.lat, wpt.lon, tp.lat, tp.lon)
            if dist_m < min_dist_m:
                min_dist_m = dist_m
                nearest_track_dist = tp.distance_from_start
                nearest_tp = tp
        
        # Warn if waypoint is far from track
        if min_dist_m > off_route_threshold_m:
            warnings.append(
                f"Warning: '{wpt.name}' is {min_dist_m:.0f}m from the track "
                f"(mapped to {nearest_track_dist/1000:.1f}km)"
            )
        
        mapped_waypoints.append(Waypoint(
            name=wpt.name,
            lat=wpt.lat,
            lon=wpt.lon,
            distance_from_start=nearest_track_dist
        ))
    
    # Sort by distance along track
    mapped_waypoints.sort(key=lambda w: w.distance_from_start)
    
    return mapped_waypoints, warnings
