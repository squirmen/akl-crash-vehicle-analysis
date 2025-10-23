#!/usr/bin/env python3
"""Analyze confirmed crash-involved vehicles"""

import csv
import sys
from collections import Counter

csv.field_size_limit(sys.maxsize)

print("="*80)
print("CONFIRMED CRASH-INVOLVED VEHICLES - ANALYSIS")
print("="*80)

# Analyze 5min window (highest confidence)
print("\n" + "="*80)
print("5-MINUTE WINDOW (HIGHEST CONFIDENCE)")
print("="*80)

matches = []
with open('confirmed_crash_vehicles_5min.csv', 'r') as f:
    reader = csv.DictReader(f)
    matches = list(reader)

print(f"\nTotal matches: {len(matches)}")
print(f"Unique vehicles: {len(set(m['vehicle_id'] for m in matches))}")
print(f"Unique trips: {len(set(m['trip_id'] for m in matches))}")
print(f"Unique crashes: {len(set(m['nzta_crash_id'] for m in matches))}")

# Severity breakdown
print("\nCrash Severity:")
severities = Counter([m['nzta_severity'] for m in matches])
for severity, count in severities.most_common():
    pct = count / len(matches) * 100
    print(f"  {severity:20s}: {count:3d} ({pct:5.1f}%)")

# Vehicle type breakdown
print("\nConnected Vehicle Types:")
vtypes = Counter([m['vehicle_type'] for m in matches])
for vtype, count in vtypes.most_common():
    pct = count / len(matches) * 100
    print(f"  {vtype:20s}: {count:3d} ({pct:5.1f}%)")

# Distance distribution
distances = [float(m['distance_to_crash']) for m in matches]
print(f"\nDistance to crash (meters):")
print(f"  Min: {min(distances):.2f}m")
print(f"  Max: {max(distances):.2f}m")
print(f"  Avg: {sum(distances)/len(distances):.2f}m")
print(f"  Median: {sorted(distances)[len(distances)//2]:.2f}m")

# Time difference distribution
time_diffs = [float(m['time_diff_minutes']) for m in matches]
print(f"\nTime difference (minutes):")
print(f"  Min: {min(time_diffs):.2f}min")
print(f"  Max: {max(time_diffs):.2f}min")
print(f"  Avg: {sum(time_diffs)/len(time_diffs):.2f}min")
print(f"  Median: {sorted(time_diffs)[len(time_diffs)//2]:.2f}min")

# Score distribution
scores = [float(m['combined_score']) for m in matches]
print(f"\nCombined Score (0-100):")
print(f"  Min: {min(scores):.1f}")
print(f"  Max: {max(scores):.1f}")
print(f"  Avg: {sum(scores)/len(scores):.1f}")
print(f"  Median: {sorted(scores)[len(scores)//2]:.1f}")

# Top 10 examples
print("\n" + "="*80)
print("TOP 10 HIGHEST CONFIDENCE MATCHES")
print("="*80)

sorted_matches = sorted(matches, key=lambda x: float(x['combined_score']), reverse=True)

for i, m in enumerate(sorted_matches[:10], 1):
    print(f"\n{i}. Score: {float(m['combined_score']):.1f}/100")
    print(f"   Vehicle: {m['vehicle_id']} ({m['vehicle_type']})")
    print(f"   Crash: {m['nzta_severity']} - {m['nzta_location']} on {m['nzta_road']}")
    print(f"   Distance: {float(m['distance_to_crash']):.1f}m | Time diff: {float(m['time_diff_minutes']):.1f}min")
    print(f"   Crash time: {m['crash_datetime']} | Vehicle time: {m['vehicle_timestamp']}")

# Multi-crash vehicles
print("\n" + "="*80)
print("VEHICLES MATCHED TO MULTIPLE CRASHES")
print("="*80)

vehicle_crash_counts = Counter([m['vehicle_id'] for m in matches])
multi_crash = [(vid, count) for vid, count in vehicle_crash_counts.items() if count > 1]

if multi_crash:
    print(f"\nFound {len(multi_crash)} vehicles involved in multiple crashes:")
    for vid, count in sorted(multi_crash, key=lambda x: x[1], reverse=True)[:10]:
        v_matches = [m for m in matches if m['vehicle_id'] == vid]
        vtypes = set([m['vehicle_type'] for m in v_matches])
        print(f"  {vid} ({', '.join(vtypes)}): {count} crashes")
else:
    print("\nNo vehicles matched to multiple crashes in this window")

print("\n" + "="*80)
print("KEY INSIGHTS")
print("="*80)
print(f"\n✓ {len(matches)} confirmed crash-involved vehicle observations")
print(f"✓ Average distance: {sum(distances)/len(distances):.1f}m - vehicles were AT the crash")
print(f"✓ Average time diff: {sum(time_diffs)/len(time_diffs):.1f}min - vehicles were there WHEN it happened")
print(f"✓ {len(set(m['vehicle_id'] for m in matches))} unique connected vehicles matched to crashes")
print(f"✓ {len(set(m['nzta_crash_id'] for m in matches))} crashes now have identified connected vehicles")
print("\nThese matches can now be used for:")
print("  • Pre-crash driving behavior analysis")
print("  • Speed/acceleration patterns before crashes")
print("  • Route/location risk profiling")
print("  • Validation of crash causation factors")
