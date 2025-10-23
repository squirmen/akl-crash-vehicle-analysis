#!/usr/bin/env python3
"""
Distinguish crash-INVOLVED vehicles from witnesses.
Involved vehicles: stopped at scene, sudden deceleration, stayed after crash.
"""

import csv
import sys
from datetime import datetime, timedelta
from collections import defaultdict

csv.field_size_limit(sys.maxsize)

def parse_timestamp(ts_str):
    try:
        if '.' in ts_str:
            ts_str = ts_str.split('.')[0]
        return datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
    except:
        return None

def parse_crash_datetime(dt_str):
    try:
        return datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
    except:
        return None

print("="*80)
print("IDENTIFYING CRASH-INVOLVED VEHICLES (NOT WITNESSES)")
print("="*80)

# Load confirmed matches
print("\nLoading confirmed matches...")
matches = []
with open('confirmed_crash_vehicles_5min.csv', 'r') as f:
    reader = csv.DictReader(f)
    matches = list(reader)

print(f"Total matches: {len(matches)}")

# For each match, need to check full trip to see behavior AFTER crash
print("\nAnalyzing trip behavior around crash time...")

# Group by trip
trips_with_crashes = defaultdict(list)
for match in matches:
    trip_id = match['trip_id']
    trips_with_crashes[trip_id].append(match)

print(f"Unique trips to analyze: {len(trips_with_crashes)}")

# Load vehicle data and analyze each trip
crash_involved = []
witnesses = []

# Need to load vehicle files
from pathlib import Path
vehicle_files = list(Path('data/connected_vehicle').glob('support.NZ_report_withOD-*.csv'))

print("\nAnalyzing each trip for crash involvement indicators...")
print("(This may take a few minutes...)\n")

trip_data_cache = {}

# First pass: load all matching trips
print("Loading trip data...")
trips_needed = set(trips_with_crashes.keys())
loaded = 0

for vfile in vehicle_files:
    if not trips_needed:
        break

    with open(vfile, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['TripID'] in trips_needed:
                trip_data_cache[row['TripID']] = row
                trips_needed.remove(row['TripID'])
                loaded += 1
                if loaded % 10 == 0:
                    print(f"  Loaded {loaded}/{len(trips_with_crashes)} trips...")

print(f"\nLoaded {len(trip_data_cache)} trip records")

# Analyze each trip
for trip_id, crash_matches in trips_with_crashes.items():
    if trip_id not in trip_data_cache:
        continue

    trip_data = trip_data_cache[trip_id]

    # Parse trip data
    timestamps = trip_data['TimestampPath'].split(',')
    raw_path = trip_data['RawPath'].split(',')
    speeds = trip_data['SpeedPath'].split(',')
    x_accel = trip_data.get('XAccPath', '').split(',')

    # Parse coordinates
    coords = []
    for point_str in raw_path:
        parts = point_str.strip().split()
        if len(parts) == 2:
            lon, lat = float(parts[0]), float(parts[1])
            coords.append((lon, lat))

    # For each crash this trip was near
    for match in crash_matches:
        crash_time = parse_crash_datetime(match['crash_datetime'])
        closest_point_idx = int(match['closest_point_idx'])
        crash_x = float(match['crash_x'])
        crash_y = float(match['crash_y'])

        if not crash_time:
            continue

        # Check behavior AFTER crash
        points_after_crash = []
        for i in range(closest_point_idx, min(closest_point_idx + 20, len(timestamps))):
            ts = parse_timestamp(timestamps[i])
            if ts and ts >= crash_time:
                # Calculate distance from crash
                if i < len(coords):
                    # Simple distance calc (approximation)
                    from pyproj import Transformer
                    transformer = Transformer.from_crs("EPSG:4326", "EPSG:2193", always_xy=True)
                    px, py = transformer.transform(coords[i][0], coords[i][1])
                    dist = ((px - crash_x)**2 + (py - crash_y)**2)**0.5

                    try:
                        speed_val = float(speeds[i]) if i < len(speeds) and speeds[i] and speeds[i] != 'null' else 0
                    except:
                        speed_val = 0

                    points_after_crash.append({
                        'time_after_crash': (ts - crash_time).total_seconds() / 60,
                        'distance': dist,
                        'speed': speed_val
                    })

        # Analyze post-crash behavior
        if not points_after_crash:
            continue

        # Indicators of involvement (not just witness):
        # 1. Stayed within 50m for >2 minutes
        # 2. Speed dropped to <10 mph and stayed low
        # 3. Multiple points at crash location

        stayed_at_scene = False
        num_points_at_scene = sum(1 for p in points_after_crash if p['distance'] < 50)
        time_at_scene = max([p['time_after_crash'] for p in points_after_crash if p['distance'] < 50], default=0)
        avg_speed_at_scene = sum([p['speed'] for p in points_after_crash if p['distance'] < 50]) / max(num_points_at_scene, 1)

        if num_points_at_scene >= 3 and avg_speed_at_scene < 10:
            stayed_at_scene = True

        # Check for sudden deceleration BEFORE crash
        sudden_decel = False
        if closest_point_idx > 0 and closest_point_idx < len(speeds):
            try:
                speed_before = float(speeds[max(0, closest_point_idx - 1)]) if speeds[max(0, closest_point_idx - 1)] not in ['', 'null', None] else 0
                speed_at = float(speeds[closest_point_idx]) if speeds[closest_point_idx] not in ['', 'null', None] else 0

                if speed_before - speed_at > 20:  # 20+ mph drop
                    sudden_decel = True
            except:
                pass

        # Check x-acceleration
        strong_decel_accel = False
        if x_accel and closest_point_idx < len(x_accel):
            try:
                x_accel_val = float(x_accel[closest_point_idx])
                if abs(x_accel_val) > 5:  # Strong acceleration/deceleration
                    strong_decel_accel = True
            except:
                pass

        # Classify
        involvement_indicators = sum([stayed_at_scene, sudden_decel, strong_decel_accel])

        result = {
            **match,
            'stayed_at_scene': stayed_at_scene,
            'num_points_at_scene': num_points_at_scene,
            'time_at_scene_minutes': round(time_at_scene, 2),
            'avg_speed_at_scene': round(avg_speed_at_scene, 1),
            'sudden_deceleration': sudden_decel,
            'strong_accel': strong_decel_accel,
            'involvement_indicators': involvement_indicators,
            'likely_role': 'INVOLVED' if involvement_indicators >= 2 else 'WITNESS'
        }

        if involvement_indicators >= 2:
            crash_involved.append(result)
        else:
            witnesses.append(result)

print("\n" + "="*80)
print("RESULTS")
print("="*80)

print(f"\nLikely INVOLVED (stopped at scene, sudden decel, etc): {len(crash_involved)}")
print(f"Likely WITNESSES (passed through): {len(witnesses)}")

# Top involved
if crash_involved:
    print("\n" + "="*80)
    print("TOP 20 LIKELY CRASH-INVOLVED VEHICLES")
    print("="*80)

    sorted_involved = sorted(crash_involved, key=lambda x: x['involvement_indicators'], reverse=True)

    for i, v in enumerate(sorted_involved[:20], 1):
        print(f"\n{i}. Vehicle: {v['vehicle_id'][:20]}... ({v['vehicle_type']})")
        print(f"   Crash: {v['nzta_severity']} at {v['nzta_location']}")
        print(f"   Crash time: {v['crash_datetime']}")
        print(f"   Distance from crash: {v['distance_to_crash']}m")
        print(f"   Stayed at scene: {v['stayed_at_scene']} ({v['num_points_at_scene']} points, {v['time_at_scene_minutes']}min)")
        print(f"   Avg speed at scene: {v['avg_speed_at_scene']} mph")
        print(f"   Sudden deceleration: {v['sudden_deceleration']}")
        print(f"   Strong accel change: {v['strong_accel']}")
        print(f"   → Role: {v['likely_role']}")

# Export
if crash_involved:
    with open('crash_INVOLVED_vehicles.csv', 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=crash_involved[0].keys())
        writer.writeheader()
        writer.writerows(crash_involved)
    print(f"\n✓ Exported: crash_INVOLVED_vehicles.csv ({len(crash_involved)} records)")

if witnesses:
    with open('crash_WITNESSES.csv', 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=witnesses[0].keys())
        writer.writeheader()
        writer.writerows(witnesses)
    print(f"✓ Exported: crash_WITNESSES.csv ({len(witnesses)} records)")

print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print("\n✓ Separated crash-involved vehicles from witnesses")
print("✓ Involved vehicles: stopped at scene, sudden deceleration")
print("✓ Witnesses: passed through, continued journey")
