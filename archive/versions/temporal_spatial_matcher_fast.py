#!/usr/bin/env python3
"""
Fast temporal-spatial matching: filter spatially first, then temporally.
"""

import csv
import sys
from datetime import datetime
from collections import defaultdict

csv.field_size_limit(sys.maxsize)

def parse_crash_datetime(date_str, time_str):
    try:
        date_part = date_str.split()[0]
        dt_str = f"{date_part} {time_str}"
        return datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
    except:
        return None

def parse_vehicle_timestamp(ts_str):
    try:
        if '.' in ts_str:
            ts_str = ts_str.split('.')[0]
        return datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
    except:
        return None

def time_delta_minutes(dt1, dt2):
    if not dt1 or not dt2:
        return None
    return abs((dt1 - dt2).total_seconds() / 60)

print("="*80)
print("FAST TEMPORAL-SPATIAL MATCHING")
print("="*80)

# Step 1: Load crash data with timestamps
print("\n1. Loading crash data...")
crashes = {}
with open('data/crash_data/crash_Untitled_query.2025-10-13.11-58.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        crash_id = row['Crash identifier']
        crashes[crash_id] = {
            'datetime': parse_crash_datetime(row['Crash date'], row['Crash time']),
            'severity': row['Crash severity'],
            'location': row.get('Locality/suburb', ''),
            'road': row.get('Geospatial road name', '')
        }

print(f"   Loaded {len(crashes):,} crashes")

# Step 2: Pre-filter spatial matches (close proximity only)
print("\n2. Pre-filtering spatial matches (distance ≤ 25m)...")
close_matches = []
total = 0

with open('crash_vehicle_matches_full.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        total += 1
        if total % 1000000 == 0:
            print(f"   Processed {total//1000000}M records, found {len(close_matches):,} close matches")

        distance = float(row['distance_to_crash'])
        if distance <= 25:  # 25m threshold
            close_matches.append(row)

print(f"   Total processed: {total:,}")
print(f"   Close matches (≤25m): {len(close_matches):,}")

# Step 3: Apply temporal filters progressively
print("\n3. Applying temporal filters...")

time_windows = [5, 10, 15, 20]
results_by_window = {}

for time_window in time_windows:
    print(f"\n   Time window: ±{time_window} minutes")

    matched = []
    for match in close_matches:
        crash_id = str(match['crash_id'])

        if crash_id not in crashes:
            continue

        crash = crashes[crash_id]
        if not crash['datetime']:
            continue

        vehicle_ts = parse_vehicle_timestamp(match.get('closest_timestamp', ''))
        if not vehicle_ts:
            continue

        time_diff = time_delta_minutes(crash['datetime'], vehicle_ts)
        if time_diff is None or time_diff > time_window:
            continue

        # Calculate scores
        spatial_dist = float(match['distance_to_crash'])
        spatial_score = max(0, (25 - spatial_dist) / 25 * 100)
        temporal_score = max(0, (time_window - time_diff) / time_window * 100)
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

    print(f"      Matches: {len(matched):,}")

    if len(matched) > 0:
        time_diffs = [m['time_diff_minutes'] for m in matched]
        avg_time = sum(time_diffs) / len(time_diffs)
        median_time = sorted(time_diffs)[len(time_diffs)//2]

        distances = [float(m['distance_to_crash']) for m in matched]
        avg_dist = sum(distances) / len(distances)
        median_dist = sorted(distances)[len(distances)//2]

        print(f"      Time diff - Avg: {avg_time:.2f}min, Median: {median_time:.2f}min")
        print(f"      Distance - Avg: {avg_dist:.2f}m, Median: {median_dist:.2f}m")

        # Unique vehicles and trips
        unique_vehicles = len(set(m['vehicle_id'] for m in matched))
        unique_trips = len(set(m['trip_id'] for m in matched))
        unique_crashes = len(set(m['crash_id'] for m in matched))

        print(f"      Unique vehicles: {unique_vehicles:,}")
        print(f"      Unique trips: {unique_trips:,}")
        print(f"      Unique crashes: {unique_crashes:,}")

    results_by_window[time_window] = matched

# Step 4: Export results
print("\n" + "="*80)
print("EXPORTING RESULTS")
print("="*80)

for time_window, matches in results_by_window.items():
    if len(matches) == 0:
        continue

    filename = f'temporal_spatial_matches_{time_window}min.csv'
    with open(filename, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=matches[0].keys())
        writer.writeheader()
        writer.writerows(matches)

    print(f"✓ {filename}: {len(matches):,} matches")

    # Top 25% by score
    sorted_matches = sorted(matches, key=lambda x: x['combined_score'], reverse=True)
    high_conf = sorted_matches[:max(1, len(sorted_matches)//4)]

    hc_filename = f'temporal_spatial_matches_{time_window}min_high_confidence.csv'
    with open(hc_filename, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=high_conf[0].keys())
        writer.writeheader()
        writer.writerows(high_conf)

    print(f"✓ {hc_filename}: {len(high_conf):,} matches (top 25%)")

print("\n" + "="*80)
print("COMPLETE")
print("="*80)
print("\n✓ Vehicles matched to crashes by space AND time")
print("✓ Use 5min window for highest confidence")
print("✓ These vehicles were at crash location when crash occurred")
