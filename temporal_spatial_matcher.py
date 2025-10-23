#!/usr/bin/env python3
"""
Temporal-spatial matching of connected vehicles to crash events.
Progressive time windows: 5, 10, 15, 20 minutes.
"""

import csv
import sys
from datetime import datetime, timedelta
from collections import defaultdict
import math

csv.field_size_limit(sys.maxsize)

def parse_crash_datetime(date_str, time_str):
    """Parse crash date and time into datetime object"""
    try:
        date_part = date_str.split()[0]  # "2025-01-04 00:00:00" -> "2025-01-04"
        dt_str = f"{date_part} {time_str}"
        return datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
    except:
        return None

def parse_vehicle_timestamp(ts_str):
    """Parse vehicle timestamp"""
    try:
        # Format: "2025-01-04 12:34:56.123"
        if '.' in ts_str:
            ts_str = ts_str.split('.')[0]
        return datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
    except:
        return None

def time_delta_minutes(dt1, dt2):
    """Calculate time difference in minutes"""
    if not dt1 or not dt2:
        return None
    delta = abs((dt1 - dt2).total_seconds() / 60)
    return delta

def map_vehicle_type(connected_type, crash_type):
    """Score vehicle type match (0-1)"""
    if not connected_type or not crash_type:
        return 0.5

    # Mapping rules
    connected_type = connected_type.upper()
    crash_type = crash_type.upper()

    # Exact or close matches
    if 'CAR' in connected_type and 'CAR' in crash_type:
        return 1.0
    if 'BUS' in connected_type and 'BUS' in crash_type:
        return 1.0
    if 'HCV' in connected_type and ('TRUCK' in crash_type or 'HEAVY' in crash_type):
        return 1.0
    if 'LCV' in connected_type and ('VAN' in crash_type or 'UTE' in crash_type):
        return 0.8

    # Partial matches
    if ('HCV' in connected_type or 'LCV' in connected_type) and 'VEHICLE' in crash_type:
        return 0.5

    return 0.3  # Unknown/no match

def score_speed_match(vehicle_speed, crash_speed):
    """Score speed similarity (0-1)"""
    try:
        v_speed = float(vehicle_speed) if vehicle_speed else None
        c_speed = float(crash_speed) if crash_speed else None

        if v_speed is None or c_speed is None:
            return 0.5

        # Perfect match
        if abs(v_speed - c_speed) <= 5:
            return 1.0
        # Close match
        elif abs(v_speed - c_speed) <= 10:
            return 0.8
        # Moderate match
        elif abs(v_speed - c_speed) <= 20:
            return 0.5
        else:
            return 0.2
    except:
        return 0.5

def load_crash_data():
    """Load crash and crashvehicle data"""
    print("Loading crash data...")

    crashes = {}
    with open('data/crash_data/crash_Untitled_query.2025-10-13.11-58.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            crash_id = row['Crash identifier']
            crashes[crash_id] = {
                'crash_id': crash_id,
                'datetime': parse_crash_datetime(row['Crash date'], row['Crash time']),
                'date': row['Crash date'],
                'time': row['Crash time'],
                'severity': row['Crash severity'],
                'lat': float(row['Latitude']) if row['Latitude'] else None,
                'lon': float(row['Longitude']) if row['Longitude'] else None,
                'location': row.get('Locality/suburb', ''),
                'road': row.get('Geospatial road name', ''),
                'num_vehicles': row.get('Number of vehicles involved', '0')
            }

    print(f"Loaded {len(crashes)} crashes")

    # Load vehicle data
    print("Loading crash vehicle data...")
    crash_vehicles = defaultdict(list)
    with open('data/crash_data/crashvehicle_Untitled_query.2025-10-13.11-59.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            crash_id = row['Crash identifier']
            crash_vehicles[crash_id].append({
                'vehicle_id': row['codedcrashvehicleid'],
                'vehicle_type': row.get('Vehicle type', ''),
                'make': row.get('Make ', ''),
                'model': row.get('Model', ''),
                'direction': row.get('Direction of travel', ''),
                'speed': row.get('Suspected speed before crash ', '')
            })

    print(f"Loaded {sum(len(v) for v in crash_vehicles.values())} crash vehicles")

    return crashes, crash_vehicles

def load_spatial_matches():
    """Load existing spatial matches"""
    print("\nLoading spatial matches...")
    matches = []

    with open('crash_vehicle_matches_full.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            matches.append(row)

    print(f"Loaded {len(matches):,} spatial matches")
    return matches

def temporal_match(spatial_matches, crashes, time_windows=[5, 10, 15, 20]):
    """Add temporal validation and scoring"""
    print("\n" + "="*80)
    print("TEMPORAL-SPATIAL MATCHING")
    print("="*80)

    results_by_window = {}

    for time_window in time_windows:
        print(f"\n--- Time window: ±{time_window} minutes ---")

        matched = []
        skipped_no_time = 0
        skipped_no_crash = 0

        for i, match in enumerate(spatial_matches):
            if i % 100000 == 0 and i > 0:
                print(f"  Processed {i:,}/{len(spatial_matches):,}")

            # Get crash data
            crash_id = str(match['crash_id'])
            if crash_id not in crashes:
                skipped_no_crash += 1
                continue

            crash = crashes[crash_id]
            if not crash['datetime']:
                skipped_no_time += 1
                continue

            # Parse vehicle timestamp
            vehicle_ts = parse_vehicle_timestamp(match.get('closest_timestamp', ''))
            if not vehicle_ts:
                skipped_no_time += 1
                continue

            # Calculate time delta
            time_diff = time_delta_minutes(crash['datetime'], vehicle_ts)
            if time_diff is None or time_diff > time_window:
                continue

            # Match found! Calculate enhanced scores
            spatial_dist = float(match['distance_to_crash'])

            # Spatial score (0-100): closer = better
            # 0m=100, 10m=75, 25m=0
            spatial_score = max(0, (25 - spatial_dist) / 25 * 100)

            # Temporal score (0-100): closer = better
            # 0min=100, 2min=75, 5min=50, 10min=25, 20min=0
            temporal_score = max(0, (time_window - time_diff) / time_window * 100)

            # Combined score
            combined_score = spatial_score * 0.6 + temporal_score * 0.4

            matched.append({
                **match,
                'crash_datetime': crash['datetime'].strftime('%Y-%m-%d %H:%M'),
                'vehicle_timestamp': vehicle_ts.strftime('%Y-%m-%d %H:%M:%S'),
                'time_diff_minutes': round(time_diff, 2),
                'spatial_score': round(spatial_score, 2),
                'temporal_score': round(temporal_score, 2),
                'combined_score': round(combined_score, 2),
                'crash_severity': crash['severity'],
                'crash_location': crash['location'],
                'crash_road': crash['road']
            })

        print(f"\n  Matches found: {len(matched):,}")
        print(f"  Skipped (no timestamp): {skipped_no_time:,}")
        print(f"  Skipped (no crash data): {skipped_no_crash:,}")

        if len(matched) > 0:
            # Stats
            time_diffs = [m['time_diff_minutes'] for m in matched]
            print(f"  Time difference - Mean: {sum(time_diffs)/len(time_diffs):.2f} min, "
                  f"Median: {sorted(time_diffs)[len(time_diffs)//2]:.2f} min")

            distances = [float(m['distance_to_crash']) for m in matched]
            print(f"  Distance - Mean: {sum(distances)/len(distances):.2f} m, "
                  f"Median: {sorted(distances)[len(distances)//2]:.2f} m")

        results_by_window[time_window] = matched

    return results_by_window

def export_results(results_by_window):
    """Export matched results"""
    print("\n" + "="*80)
    print("EXPORTING RESULTS")
    print("="*80)

    for time_window, matches in results_by_window.items():
        if len(matches) == 0:
            continue

        filename = f'temporal_spatial_matches_{time_window}min.csv'

        with open(filename, 'w', newline='') as f:
            if len(matches) > 0:
                writer = csv.DictWriter(f, fieldnames=matches[0].keys())
                writer.writeheader()
                writer.writerows(matches)

        print(f"  {filename}: {len(matches):,} matches")

        # High confidence subset (top 25%)
        sorted_matches = sorted(matches, key=lambda x: x['combined_score'], reverse=True)
        high_conf = sorted_matches[:len(sorted_matches)//4]

        if len(high_conf) > 0:
            hc_filename = f'temporal_spatial_matches_{time_window}min_high_confidence.csv'
            with open(hc_filename, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=high_conf[0].keys())
                writer.writeheader()
                writer.writerows(high_conf)
            print(f"  {hc_filename}: {len(high_conf):,} matches (top 25%)")

def main():
    # Load data
    crashes, crash_vehicles = load_crash_data()
    spatial_matches = load_spatial_matches()

    # Progressive temporal matching
    results = temporal_match(spatial_matches, crashes, time_windows=[5, 10, 15, 20])

    # Export
    export_results(results)

    print("\n" + "="*80)
    print("COMPLETE")
    print("="*80)
    print("\nUse the 5min or 10min results for highest confidence matches.")
    print("These vehicles were at the crash location at the time of the crash.")

if __name__ == '__main__':
    main()
