#!/usr/bin/env python3
"""Explore crash data structure for matching attributes"""

import csv
import sys
from collections import Counter

csv.field_size_limit(sys.maxsize)

print("="*80)
print("CRASH TABLE EXPLORATION")
print("="*80)

# Load crash data
crash_file = 'data/crash_data/crash_Untitled_query.2025-10-13.11-58.csv'
with open(crash_file, 'r') as f:
    reader = csv.DictReader(f)
    crashes = list(reader)

print(f"\nTotal crashes: {len(crashes)}")
print(f"\nSample crash record:")
sample = crashes[0]
print(f"  Crash ID: {sample['Crash identifier']}")
print(f"  Date: {sample['Crash date']}")
print(f"  Time: {sample['Crash time']}")
print(f"  Severity: {sample['Crash severity']}")
print(f"  Lat/Lon: {sample['Latitude']}, {sample['Longitude']}")
print(f"  Vehicles involved: {sample['Number of vehicles involved']}")
print(f"  Location: {sample.get('Locality/suburb', 'N/A')}")
print(f"  Road: {sample.get('Geospatial road name', 'N/A')}")

print("\n" + "="*80)
print("CRASHVEHICLE TABLE EXPLORATION")
print("="*80)

vehicle_file = 'data/crash_data/crashvehicle_Untitled_query.2025-10-13.11-59.csv'
with open(vehicle_file, 'r') as f:
    reader = csv.DictReader(f)
    vehicles = list(reader)

print(f"\nTotal crash vehicles: {len(vehicles)}")
print(f"\nSample vehicle record:")
sample_v = vehicles[0]
print(f"  Crash ID: {sample_v['Crash identifier']}")
print(f"  Vehicle ID: {sample_v['codedcrashvehicleid']}")
print(f"  Vehicle type: {sample_v.get('Vehicle type', 'N/A')}")
print(f"  Make/Model: {sample_v.get('Make ', 'N/A')} / {sample_v.get('Model', 'N/A')}")
print(f"  Direction: {sample_v.get('Direction of travel', 'N/A')}")
print(f"  Speed before crash: {sample_v.get('Suspected speed before crash ', 'N/A')}")
print(f"  Movement: {sample_v.get('Movement codes', 'N/A')}")

# Check vehicle types
vehicle_types = Counter([v.get('Vehicle type', 'Unknown') for v in vehicles])
print(f"\nVehicle types in crash data:")
for vtype, count in vehicle_types.most_common(15):
    print(f"  {vtype}: {count}")

# Check time distribution
times = [c.get('Crash time', '') for c in crashes if c.get('Crash time')]
print(f"\nTime data available: {len([t for t in times if t])} / {len(crashes)}")
print(f"Sample times: {times[:5]}")

# Check coordinate quality
coords = [(c.get('Latitude'), c.get('Longitude')) for c in crashes]
valid_coords = [(lat, lon) for lat, lon in coords if lat and lon]
print(f"\nValid coordinates: {len(valid_coords)} / {len(crashes)}")

print("\n" + "="*80)
print("POTENTIAL MATCHING ATTRIBUTES")
print("="*80)
print("\nPrimary:")
print("  ✓ Crash date + time (temporal)")
print("  ✓ Lat/Lon (spatial)")
print("  ✓ Vehicle type (validation)")
print("\nSecondary/validation:")
print("  • Direction of travel")
print("  • Speed before crash")
print("  • Movement codes")
print("  • Road name")
print("  • Number of vehicles involved")
