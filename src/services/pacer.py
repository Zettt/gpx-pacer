import csv
import json
from datetime import timedelta
from typing import List, Optional
from src.model.data import AnalysisSplitSegment, TrackPoint, SplitSegment, PacingPlan

def create_distance_splits(points: List[TrackPoint], split_distance_meters: float) -> List[SplitSegment]:
    if not points:
        return []

    splits: List[SplitSegment] = []
    
    current_split_start_dist = points[0].distance_from_start
    current_split_gain = 0.0
    current_split_loss = 0.0
    
    # We maintain a 'virtual' previous point to handle splits that happen mid-segment
    prev_point = points[0]
    
    # Target for the first split
    target_dist = current_split_start_dist + split_distance_meters
    
    # Iterate from the second point
    idx = 1
    while idx < len(points):
        curr_point = points[idx]
        
        # While the current point is beyond the target split distance, we have one or more splits to close
        while curr_point.distance_from_start > target_dist:
            # Fraction of the segment covered by the split
            segment_len = curr_point.distance_from_start - prev_point.distance_from_start
            
            # Avoid division by zero
            if segment_len == 0:
                 # Should not happen if distances are monotonic, but safety check
                 target_dist += split_distance_meters
                 continue

            dist_into_segment = target_dist - prev_point.distance_from_start
            fraction = dist_into_segment / segment_len
            
            # Interpolate elevation at target
            ele_diff = (curr_point.ele - prev_point.ele) if (curr_point.ele is not None and prev_point.ele is not None) else 0
            interpolated_ele = (prev_point.ele + (ele_diff * fraction)) if prev_point.ele is not None else None
            
            # Calculate gain/loss for this partial segment
            if prev_point.ele is not None and interpolated_ele is not None:
                diff = interpolated_ele - prev_point.ele
                if diff > 0:
                    current_split_gain += diff
                else:
                    current_split_loss += abs(diff)
            
            # Create the split
            splits.append(SplitSegment(
                start_distance=current_split_start_dist,
                end_distance=target_dist,
                length=split_distance_meters,
                elevation_gain=current_split_gain,
                elevation_loss=current_split_loss,
                name=f"{target_dist/1000:.1f} km" # Placeholder naming
            ))
            
            # Prepare for next split
            current_split_start_dist = target_dist
            current_split_gain = 0.0
            current_split_loss = 0.0
            target_dist += split_distance_meters
            
            # The 'previous point' for the next iteration is now our interpolated point
            # We construct a temporary point
            prev_point = TrackPoint(
                lat=0, # Lat/Lon not strictly needed for elevation/distance logic here, could interpolate if needed
                lon=0,
                ele=interpolated_ele,
                distance_from_start=current_split_start_dist
            )
            
        # If we are here, curr_point is within the current split (or equal to target if we handled loop exactly)
        # Add full segment gain/loss to current split
        if prev_point.ele is not None and curr_point.ele is not None:
            diff = curr_point.ele - prev_point.ele
            if diff > 0:
                current_split_gain += diff
            else:
                current_split_loss += abs(diff)
        
        prev_point = curr_point
        idx += 1
        
    # Handle remainder split if there's any distance left
    if prev_point.distance_from_start > current_split_start_dist:
        length = prev_point.distance_from_start - current_split_start_dist
        if length > 0.1: # Avoid microscopic floating point remainders
            splits.append(SplitSegment(
                start_distance=current_split_start_dist,
                end_distance=prev_point.distance_from_start,
                length=length,
                elevation_gain=current_split_gain,
                elevation_loss=current_split_loss,
                name="Finish"
            ))

    return splits


def create_waypoint_splits(
    points: List[TrackPoint], 
    waypoints: List['Waypoint']
) -> List[SplitSegment]:
    """
    Create splits between waypoints. Waypoints should already have 
    distance_from_start populated (use map_waypoints_to_track first).
    """
    from src.model.data import Waypoint  # Import here to avoid circular
    
    if not points:
        return []
    
    total_distance = points[-1].distance_from_start
    
    # Build split boundaries: Start, waypoints, Finish
    boundaries: List[tuple[float, str]] = [(0.0, "Start")]
    
    for wpt in waypoints:
        # Only include waypoints that are within the track
        if 0 < wpt.distance_from_start < total_distance:
            boundaries.append((wpt.distance_from_start, wpt.name))
    
    boundaries.append((total_distance, "Finish"))
    
    # Remove duplicates (waypoints at same location)
    seen_distances: set[float] = set()
    unique_boundaries: List[tuple[float, str]] = []
    for dist, name in boundaries:
        if dist not in seen_distances:
            unique_boundaries.append((dist, name))
            seen_distances.add(dist)
    boundaries = unique_boundaries
    
    splits: List[SplitSegment] = []
    
    for i in range(len(boundaries) - 1):
        start_dist, start_name = boundaries[i]
        end_dist, end_name = boundaries[i + 1]
        
        # Calculate elevation for this segment
        gain = 0.0
        loss = 0.0
        prev_ele = None
        
        for pt in points:
            if pt.distance_from_start < start_dist:
                continue
            if pt.distance_from_start > end_dist:
                break
                
            if prev_ele is not None and pt.ele is not None:
                diff = pt.ele - prev_ele
                if diff > 0:
                    gain += diff
                else:
                    loss += abs(diff)
            
            if pt.ele is not None:
                prev_ele = pt.ele
        
        segment_name = f"{start_name} to {end_name}"
        
        splits.append(SplitSegment(
            start_distance=start_dist,
            end_distance=end_dist,
            length=end_dist - start_dist,
            elevation_gain=gain,
            elevation_loss=loss,
            name=segment_name
        ))
    
    return splits


def _interpolate_numeric(start_value: float | None, end_value: float | None, fraction: float) -> float | None:
    if start_value is None and end_value is None:
        return None
    if start_value is None:
        return end_value
    if end_value is None:
        return start_value
    return start_value + ((end_value - start_value) * fraction)


def _interpolate_timestamp(start_time, end_time, fraction: float):
    if start_time is None and end_time is None:
        return None
    if start_time is None:
        return end_time
    if end_time is None:
        return start_time
    delta = end_time - start_time
    return start_time + timedelta(seconds=delta.total_seconds() * fraction)


def _interpolate_track_point(
    start_point: TrackPoint,
    end_point: TrackPoint,
    target_distance: float,
) -> TrackPoint:
    segment_length = end_point.distance_from_start - start_point.distance_from_start
    fraction = 0.0 if segment_length == 0 else (
        (target_distance - start_point.distance_from_start) / segment_length
    )

    heart_rate = _interpolate_numeric(start_point.heart_rate_bpm, end_point.heart_rate_bpm, fraction)
    cadence = _interpolate_numeric(start_point.cadence, end_point.cadence, fraction)

    return TrackPoint(
        lat=_interpolate_numeric(start_point.lat, end_point.lat, fraction) or start_point.lat,
        lon=_interpolate_numeric(start_point.lon, end_point.lon, fraction) or start_point.lon,
        ele=_interpolate_numeric(start_point.ele, end_point.ele, fraction),
        distance_from_start=target_distance,
        timestamp=_interpolate_timestamp(start_point.timestamp, end_point.timestamp, fraction),
        heart_rate_bpm=round(heart_rate) if heart_rate is not None else None,
        cadence=round(cadence) if cadence is not None else None,
        temperature_c=_interpolate_numeric(start_point.temperature_c, end_point.temperature_c, fraction),
    )


def _append_point_if_new(points: List[TrackPoint], point: TrackPoint):
    if not points:
        points.append(point)
        return

    last_point = points[-1]
    if (
        last_point.distance_from_start != point.distance_from_start
        or last_point.timestamp != point.timestamp
    ):
        points.append(point)


def _add_elevation_change(
    start_point: TrackPoint,
    end_point: TrackPoint,
    current_gain: float,
    current_loss: float,
) -> tuple[float, float]:
    if start_point.ele is None or end_point.ele is None:
        return current_gain, current_loss

    diff = end_point.ele - start_point.ele
    if diff > 0:
        current_gain += diff
    else:
        current_loss += abs(diff)

    return current_gain, current_loss


def _average_optional(values: List[int | float | None]) -> float | None:
    present_values = [value for value in values if value is not None]
    if not present_values:
        return None
    return sum(present_values) / len(present_values)


def _max_optional(values: List[int | None]) -> int | None:
    present_values = [value for value in values if value is not None]
    if not present_values:
        return None
    return max(present_values)


def _build_analysis_split(
    split_points: List[TrackPoint],
    start_distance: float,
    end_distance: float,
    elevation_gain: float,
    elevation_loss: float,
    name: str,
) -> AnalysisSplitSegment:
    start_time = split_points[0].timestamp if split_points else None
    end_time = split_points[-1].timestamp if split_points else None
    elapsed_seconds = None
    if start_time is not None and end_time is not None:
        elapsed_seconds = (end_time - start_time).total_seconds()

    length = end_distance - start_distance
    pace_seconds_per_km = None
    if elapsed_seconds is not None and length > 0:
        pace_seconds_per_km = elapsed_seconds / (length / 1000)

    return AnalysisSplitSegment(
        start_distance=start_distance,
        end_distance=end_distance,
        length=length,
        elevation_gain=elevation_gain,
        elevation_loss=elevation_loss,
        name=name,
        start_time=start_time,
        end_time=end_time,
        elapsed_seconds=elapsed_seconds,
        pace_seconds_per_km=pace_seconds_per_km,
        average_heart_rate_bpm=_average_optional([point.heart_rate_bpm for point in split_points]),
        max_heart_rate_bpm=_max_optional([point.heart_rate_bpm for point in split_points]),
        average_cadence=_average_optional([point.cadence for point in split_points]),
        average_temperature_c=_average_optional([point.temperature_c for point in split_points]),
        point_count=len(split_points),
    )


def create_analysis_splits(
    points: List[TrackPoint],
    split_distance_meters: float,
) -> List[AnalysisSplitSegment]:
    if not points:
        return []

    splits: List[AnalysisSplitSegment] = []
    current_split_start_dist = points[0].distance_from_start
    current_split_gain = 0.0
    current_split_loss = 0.0
    current_split_points: List[TrackPoint] = [points[0]]
    prev_point = points[0]
    target_dist = current_split_start_dist + split_distance_meters

    for curr_point in points[1:]:
        while curr_point.distance_from_start >= target_dist:
            boundary_point = _interpolate_track_point(prev_point, curr_point, target_dist)
            current_split_gain, current_split_loss = _add_elevation_change(
                prev_point,
                boundary_point,
                current_split_gain,
                current_split_loss,
            )
            _append_point_if_new(current_split_points, boundary_point)

            splits.append(
                _build_analysis_split(
                    split_points=current_split_points,
                    start_distance=current_split_start_dist,
                    end_distance=target_dist,
                    elevation_gain=current_split_gain,
                    elevation_loss=current_split_loss,
                    name=f"{target_dist / 1000:.1f} km",
                )
            )

            current_split_start_dist = target_dist
            current_split_gain = 0.0
            current_split_loss = 0.0
            target_dist += split_distance_meters
            prev_point = boundary_point
            current_split_points = [boundary_point]

        current_split_gain, current_split_loss = _add_elevation_change(
            prev_point,
            curr_point,
            current_split_gain,
            current_split_loss,
        )
        _append_point_if_new(current_split_points, curr_point)
        prev_point = curr_point

    if prev_point.distance_from_start > current_split_start_dist:
        splits.append(
            _build_analysis_split(
                split_points=current_split_points,
                start_distance=current_split_start_dist,
                end_distance=prev_point.distance_from_start,
                elevation_gain=current_split_gain,
                elevation_loss=current_split_loss,
                name="Finish",
            )
        )

    return splits


def generate_csv(plan: PacingPlan, output_path: str):
    # Check if surface data is present
    has_surface = any(s.surface is not None for s in plan.splits)

    fieldnames = ["Segment Name"]
    if has_surface:
        fieldnames.append("Surface")
    fieldnames.extend([
        "Distance (km)", 
        "Split Length (km)", 
        "Gain (m)", 
        "Loss (m)", 
        "Net Change (m)",
        "Cumulative Elevation (m)",
        "Grade (%)",
        # Planning columns (Empty placeholders for now)
        "Target Pace (min/km)",
        "Split Time (min)",
        "Station Delay (min)",
        "Arrival Time",
    ])
    
    with open(output_path, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        cumulative_elevation = 0.0
        for split in plan.splits:
            cumulative_elevation += split.elevation_gain - split.elevation_loss
            row = {
                "Segment Name": split.name,
                "Distance (km)": f"{split.end_distance / 1000:.2f}",
                "Split Length (km)": f"{split.length / 1000:.2f}",
                "Gain (m)": f"{split.elevation_gain:.0f}",
                "Loss (m)": f"{split.elevation_loss:.0f}",
                "Net Change (m)": f"{split.net_change:.0f}",
                "Cumulative Elevation (m)": f"{cumulative_elevation:.0f}",
                "Grade (%)": f"{split.grade:.1f}",
                "Target Pace (min/km)": "",
                "Split Time (min)": "",
                "Station Delay (min)": "",
                "Arrival Time": "",
            }
            if has_surface:
                row["Surface"] = split.surface or ""
            writer.writerow(row)


def generate_json(plan: PacingPlan, output_path: str):
    has_surface = any(s.surface is not None for s in plan.splits)

    splits_data: list[dict] = []
    cumulative_elevation = 0.0

    for split in plan.splits:
        cumulative_elevation += split.elevation_gain - split.elevation_loss
        entry: dict = {
            "segment_name": split.name,
            "distance_km": round(split.end_distance / 1000, 2),
            "split_length_km": round(split.length / 1000, 2),
            "gain_m": round(split.elevation_gain),
            "loss_m": round(split.elevation_loss),
            "net_change_m": round(split.net_change),
            "cumulative_elevation_m": round(cumulative_elevation),
            "grade_pct": round(split.grade, 1),
        }
        if has_surface:
            entry["surface"] = split.surface or ""
        splits_data.append(entry)

    output = {
        "metadata": plan.metadata,
        "splits": splits_data,
    }

    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)


def _format_optional_number(value: float | int | None, decimals: int = 1) -> str:
    if value is None:
        return ""
    if isinstance(value, int):
        return str(value)
    return f"{value:.{decimals}f}"


def generate_analysis_csv(plan: PacingPlan, output_path: str):
    fieldnames = [
        "Segment Name",
        "Start Dist (m)",
        "End Dist (m)",
        "Split Length (m)",
        "Start Time",
        "End Time",
        "Elapsed (s)",
        "Pace (s/km)",
        "Avg HR (bpm)",
        "Max HR (bpm)",
        "Avg Cadence",
        "Avg Temp (C)",
        "Gain (m)",
        "Loss (m)",
        "Net Change (m)",
        "Grade (%)",
        "Point Count",
    ]

    with open(output_path, "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for split in plan.splits:
            if not isinstance(split, AnalysisSplitSegment):
                continue

            writer.writerow({
                "Segment Name": split.name,
                "Start Dist (m)": f"{split.start_distance:.2f}",
                "End Dist (m)": f"{split.end_distance:.2f}",
                "Split Length (m)": f"{split.length:.2f}",
                "Start Time": split.start_time.isoformat() if split.start_time else "",
                "End Time": split.end_time.isoformat() if split.end_time else "",
                "Elapsed (s)": _format_optional_number(split.elapsed_seconds, decimals=1),
                "Pace (s/km)": _format_optional_number(split.pace_seconds_per_km, decimals=1),
                "Avg HR (bpm)": _format_optional_number(split.average_heart_rate_bpm, decimals=1),
                "Max HR (bpm)": _format_optional_number(split.max_heart_rate_bpm),
                "Avg Cadence": _format_optional_number(split.average_cadence, decimals=1),
                "Avg Temp (C)": _format_optional_number(split.average_temperature_c, decimals=1),
                "Gain (m)": f"{split.elevation_gain:.0f}",
                "Loss (m)": f"{split.elevation_loss:.0f}",
                "Net Change (m)": f"{split.net_change:.0f}",
                "Grade (%)": f"{split.grade:.1f}",
                "Point Count": split.point_count,
            })


def generate_analysis_json(plan: PacingPlan, output_path: str):
    splits_data: list[dict] = []

    for split in plan.splits:
        if not isinstance(split, AnalysisSplitSegment):
            continue

        splits_data.append({
            "segment_name": split.name,
            "start_dist_m": round(split.start_distance, 2),
            "end_dist_m": round(split.end_distance, 2),
            "split_length_m": round(split.length, 2),
            "start_time": split.start_time.isoformat() if split.start_time else None,
            "end_time": split.end_time.isoformat() if split.end_time else None,
            "elapsed_s": round(split.elapsed_seconds, 2) if split.elapsed_seconds is not None else None,
            "pace_s_per_km": round(split.pace_seconds_per_km, 2) if split.pace_seconds_per_km is not None else None,
            "avg_hr_bpm": round(split.average_heart_rate_bpm, 2) if split.average_heart_rate_bpm is not None else None,
            "max_hr_bpm": split.max_heart_rate_bpm,
            "avg_cadence": round(split.average_cadence, 2) if split.average_cadence is not None else None,
            "avg_temp_c": round(split.average_temperature_c, 2) if split.average_temperature_c is not None else None,
            "gain_m": round(split.elevation_gain),
            "loss_m": round(split.elevation_loss),
            "net_change_m": round(split.net_change),
            "grade_pct": round(split.grade, 1),
            "point_count": split.point_count,
        })

    output = {
        "metadata": plan.metadata,
        "splits": splits_data,
    }

    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
