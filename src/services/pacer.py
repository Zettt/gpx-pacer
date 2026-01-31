import csv
from typing import List, Optional
from src.model.data import TrackPoint, SplitSegment, PacingPlan

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


def generate_csv(plan: PacingPlan, output_path: str):
    fieldnames = [
        "Segment Name", 
        "Distance (km)", 
        "Split Length (km)", 
        "Gain (m)", 
        "Loss (m)", 
        "Cumulative Elevation (m)",
        "Grade (%)",
        # Planning columns (Empty placeholders for now)
        "Target Pace (min/km)",
        "Split Time (min)",
        "Station Delay (min)",
        "Arrival Time",
    ]
    
    with open(output_path, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        cumulative_elevation = 0.0
        for split in plan.splits:
            cumulative_elevation += split.elevation_gain - split.elevation_loss
            writer.writerow({
                "Segment Name": split.name,
                "Distance (km)": f"{split.end_distance / 1000:.2f}",
                "Split Length (km)": f"{split.length / 1000:.2f}",
                "Gain (m)": f"{split.elevation_gain:.0f}",
                "Loss (m)": f"{split.elevation_loss:.0f}",
                "Cumulative Elevation (m)": f"{cumulative_elevation:.0f}",
                "Grade (%)": f"{split.grade:.1f}",
                "Target Pace (min/km)": "",
                "Split Time (min)": "",
                "Station Delay (min)": "",
                "Arrival Time": "",
            })
