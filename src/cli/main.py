import argparse
import sys
import os
from src.services.gpx_service import parse_gpx, map_waypoints_to_track
from src.services.pacer import (
    create_analysis_splits,
    create_distance_splits,
    create_waypoint_splits,
    generate_analysis_csv,
    generate_analysis_json,
    generate_csv,
    generate_json,
)
from src.model.data import PacingPlan

def main():
    parser = argparse.ArgumentParser(description="Generate pacing plan from GPX")
    parser.add_argument("input_file", help="Path to GPX file")
    parser.add_argument("-o", "--output", help="Output CSV file path")
    parser.add_argument("-m", "--split-mode", choices=["distance", "waypoint", "analysis"], default="distance", help="Split mode")
    parser.add_argument("-d", "--split-dist", type=float, default=1.0, help="Split distance")
    parser.add_argument("-u", "--unit", choices=["km", "mi"], default="km", help="Unit for distance")
    parser.add_argument("--surface", action="store_true", help="Query OpenStreetMap for surface type per split (requires internet)")
    parser.add_argument("-f", "--format", choices=["csv", "json"], default="csv", help="Output format (default: csv)")
    
    args = parser.parse_args()
    
    # Validate input
    if not os.path.exists(args.input_file):
        print(f"Error: Input file '{args.input_file}' not found.")
        sys.exit(1)
        
    output_path = args.output
    if not output_path:
        base_name = os.path.splitext(args.input_file)[0]
        ext = "json" if args.format == "json" else "csv"
        suffix = "_analysis" if args.split_mode == "analysis" else "_pacing"
        output_path = f"{base_name}{suffix}.{ext}"
        
    # 1. Parse GPX
    try:
        track_points, waypoints = parse_gpx(args.input_file)
    except Exception as e:
        print(f"Error parsing GPX: {e}")
        sys.exit(1)
        
    if not track_points:
        print("Error: No track points found in GPX.")
        sys.exit(1)

    # 2. Calculate Splits
    splits = []
    if args.split_mode == "distance":
        # Convert unit to meters
        dist_meters = args.split_dist * 1000 if args.unit == "km" else args.split_dist * 1609.34
        splits = create_distance_splits(track_points, dist_meters)
    elif args.split_mode == "analysis":
        dist_meters = args.split_dist * 1000 if args.unit == "km" else args.split_dist * 1609.34
        splits = create_analysis_splits(track_points, dist_meters)
    else:
        # Waypoint mode
        mapped_waypoints, warnings = map_waypoints_to_track(track_points, waypoints)
        for warning in warnings:
            print(warning, file=sys.stderr)
        splits = create_waypoint_splits(track_points, mapped_waypoints)

    # 2b. Surface Detection (optional)
    if args.surface:
        from src.services.surface_service import detect_surfaces
        splits = detect_surfaces(splits, track_points)
        
    # 3. Generate Plan
    total_dist = track_points[-1].distance_from_start
    plan = PacingPlan(
        metadata={"filename": args.input_file, "total_dist": total_dist, "mode": args.split_mode},
        splits=splits
    )
    
    # 4. Write Output
    try:
        if args.split_mode == "analysis" and args.format == "json":
            generate_analysis_json(plan, output_path)
        elif args.split_mode == "analysis":
            generate_analysis_csv(plan, output_path)
        elif args.format == "json":
            generate_json(plan, output_path)
        else:
            generate_csv(plan, output_path)
        print(f"Successfully generated pacing plan: {output_path}")
    except Exception as e:
        print(f"Error writing output: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
