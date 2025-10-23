#!/usr/bin/env python3
"""
Phase 3: Identify Actual Crash Participants
Filter sudden deceleration vehicles to exclude emergency responders.
"""

import csv
import sys
from pathlib import Path
from pyproj import Transformer

csv.field_size_limit(sys.maxsize)

print("="*80)
print("PHASE 3: IDENTIFYING CRASH PARTICIPANTS")
print("="*80)

# Load vehicles with sudden deceleration or stayed at scene
print("\nLoading vehicles with involvement indicators...")
candidates = []
with open('crash_WITNESSES.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        # Extract vehicles with sudden deceleration or stayed at scene
        sudden_decel = row['sudden_deceleration'] == 'True'
        stayed = row['stayed_at_scene'] == 'True'

        if sudden_decel or stayed:
            candidates.append(row)

print(f"Found {len(candidates)} candidates with involvement indicators")
print(f"  - Sudden deceleration: {sum(1 for c in candidates if c['sudden_deceleration'] == 'True')}")
print(f"  - Stayed at scene: {sum(1 for c in candidates if c['stayed_at_scene'] == 'True')}")

# Load trip data to check start/end locations
print("\nLoading trip origin/destination data...")
vehicle_files = list(Path('data/connected_vehicle').glob('support.NZ_report_withOD-*.csv'))

trip_locations = {}
trips_needed = set([c['trip_id'] for c in candidates])

loaded = 0
for vfile in vehicle_files:
    if not trips_needed:
        break

    with open(vfile, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['TripID'] in trips_needed:
                # Parse origin and destination coordinates
                origin = row.get('Origin', '')
                destination = row.get('Destination', '')

                # Parse RawPath to get first and last coordinates
                raw_path = row['RawPath'].split(',')
                if len(raw_path) >= 2:
                    # First point
                    first_parts = raw_path[0].strip().split()
                    if len(first_parts) == 2:
                        origin_lon, origin_lat = float(first_parts[0]), float(first_parts[1])
                    else:
                        origin_lon, origin_lat = None, None

                    # Last point
                    last_parts = raw_path[-1].strip().split()
                    if len(last_parts) == 2:
                        dest_lon, dest_lat = float(last_parts[0]), float(last_parts[1])
                    else:
                        dest_lon, dest_lat = None, None

                    trip_locations[row['TripID']] = {
                        'origin_lat': origin_lat,
                        'origin_lon': origin_lon,
                        'dest_lat': dest_lat,
                        'dest_lon': dest_lon,
                        'trip_start': row.get('TripStart', ''),
                        'trip_end': row.get('TripEnd', ''),
                        'travel_time_min': row.get('TravelTimeMinutes', ''),
                        'distance_miles': row.get('TravelDistanceMiles', '')
                    }

                    trips_needed.remove(row['TripID'])
                    loaded += 1

                    if loaded % 10 == 0:
                        print(f"  Loaded {loaded} trips...")

print(f"Loaded {len(trip_locations)} trip origin/destination records")

# Known hospital/emergency service locations in Auckland
# These are approximate coordinates for major facilities
HOSPITALS = {
    'Auckland City Hospital': (-36.8606, 174.7690),
    'North Shore Hospital': (-36.7918, 174.7512),
    'Middlemore Hospital': (-37.0088, 174.9385),
    'Waitakere Hospital': (-36.8977, 174.6241),
    'Greenlane Hospital': (-36.8936, 174.7968),
}

def distance_to_nearest_hospital(lat, lon):
    """Calculate distance to nearest hospital in meters."""
    if lat is None or lon is None:
        return None

    transformer = Transformer.from_crs("EPSG:4326", "EPSG:2193", always_xy=True)
    x, y = transformer.transform(lon, lat)

    min_dist = float('inf')
    for name, (h_lat, h_lon) in HOSPITALS.items():
        h_x, h_y = transformer.transform(h_lon, h_lat)
        dist = ((x - h_x)**2 + (y - h_y)**2)**0.5
        if dist < min_dist:
            min_dist = dist

    return min_dist

# Classify candidates
print("\nClassifying candidates...")
emergency_responders = []
crash_participants = []
unknown = []

for candidate in candidates:
    trip_id = candidate['trip_id']

    if trip_id not in trip_locations:
        unknown.append(candidate)
        continue

    trip_loc = trip_locations[trip_id]

    # Check if trip starts or ends at hospital
    origin_hospital_dist = distance_to_nearest_hospital(
        trip_loc['origin_lat'],
        trip_loc['origin_lon']
    )
    dest_hospital_dist = distance_to_nearest_hospital(
        trip_loc['dest_lat'],
        trip_loc['dest_lon']
    )

    # Classification logic
    is_emergency = False
    reason = []

    # Starts at hospital (ambulance dispatched)
    if origin_hospital_dist is not None and origin_hospital_dist < 500:
        is_emergency = True
        reason.append(f"Origin near hospital ({origin_hospital_dist:.0f}m)")

    # Ends at hospital (ambulance returning with patient)
    if dest_hospital_dist is not None and dest_hospital_dist < 500:
        is_emergency = True
        reason.append(f"Destination near hospital ({dest_hospital_dist:.0f}m)")

    # Stayed at scene AND high speed approach (typical ambulance behavior)
    if candidate['stayed_at_scene'] == 'True':
        try:
            max_speed = float(candidate['trip_speed_max'])
            if max_speed > 80:  # >80 mph suggests emergency vehicle
                is_emergency = True
                reason.append(f"High speed approach ({max_speed:.0f} mph)")
        except:
            pass

    # Add classification result
    result = {**candidate}
    result['origin_hospital_dist'] = origin_hospital_dist if origin_hospital_dist else ''
    result['dest_hospital_dist'] = dest_hospital_dist if dest_hospital_dist else ''
    result['classification'] = 'EMERGENCY_RESPONDER' if is_emergency else 'CRASH_PARTICIPANT'
    result['classification_reason'] = '; '.join(reason) if reason else 'Sudden deceleration at crash'

    if is_emergency:
        emergency_responders.append(result)
    else:
        crash_participants.append(result)

print("\n" + "="*80)
print("CLASSIFICATION RESULTS")
print("="*80)
print(f"\nEmergency Responders: {len(emergency_responders)}")
print(f"Crash Participants: {len(crash_participants)}")
print(f"Unknown (missing trip data): {len(unknown)}")

# Show sample emergency responders
if emergency_responders:
    print("\n" + "-"*80)
    print("EMERGENCY RESPONDERS (Sample)")
    print("-"*80)
    for i, er in enumerate(emergency_responders[:5], 1):
        print(f"\n{i}. Trip: {er['trip_id'][:20]}...")
        print(f"   Vehicle: {er['vehicle_type']}")
        print(f"   Crash: {er['nzta_severity']} at {er['nzta_location']}")
        print(f"   Reason: {er['classification_reason']}")

# Show sample crash participants
if crash_participants:
    print("\n" + "-"*80)
    print("CRASH PARTICIPANTS (Sample)")
    print("-"*80)
    for i, cp in enumerate(crash_participants[:5], 1):
        print(f"\n{i}. Trip: {cp['trip_id'][:20]}...")
        print(f"   Vehicle: {cp['vehicle_type']}")
        print(f"   Crash: {cp['nzta_severity']} at {cp['nzta_location']}")
        print(f"   Distance: {cp['distance_to_crash']}m")
        print(f"   Time diff: {cp['time_diff_minutes']} min")
        print(f"   Speed at crash: {cp['speed_at_point']} mph")
        print(f"   Sudden decel: {cp['sudden_deceleration']}")
        print(f"   Stayed at scene: {cp['stayed_at_scene']}")

# Export results
if emergency_responders:
    with open('emergency_responders.csv', 'w', newline='') as f:
        fieldnames = list(emergency_responders[0].keys())
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(emergency_responders)
    print(f"\n✓ Exported: emergency_responders.csv ({len(emergency_responders)} records)")

if crash_participants:
    with open('crash_participants.csv', 'w', newline='') as f:
        fieldnames = list(crash_participants[0].keys())
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(crash_participants)
    print(f"✓ Exported: crash_participants.csv ({len(crash_participants)} records)")

print("\n" + "="*80)
print("ANALYSIS COMPLETE")
print("="*80)
print("\nNext steps:")
print("  1. Review crash_participants.csv for likely crash-involved vehicles")
print("  2. Proceed to Phase 4: Pre-crash behavior analysis")
print("  3. Update showcase map to highlight crash participants vs witnesses")
