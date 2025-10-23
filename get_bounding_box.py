#!/usr/bin/env python3
"""Extract bounding box from vehicle GPS data"""

import csv
from pathlib import Path
import sys

csv.field_size_limit(sys.maxsize)

vehicle_dir = Path('data/connected_vehicle')
files = list(vehicle_dir.glob('support.NZ_report_withOD-*.csv'))[:10]

print(f"Sampling {len(files)} files to find bounding box...\n")

all_lats = []
all_lons = []

for f in files:
    print(f"Processing {f.name}...")
    with open(f, 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            path_str = row.get('RawPath', '')
            if not path_str:
                continue

            try:
                pairs = path_str.split(',')
                for pair in pairs[:5]:  # Sample first 5 points per trip
                    coords = pair.strip().split()
                    if len(coords) == 2:
                        lon, lat = float(coords[0]), float(coords[1])
                        all_lons.append(lon)
                        all_lats.append(lat)
            except:
                continue

print(f"\nAnalyzed {len(all_lats):,} GPS points")
print(f"\nBounding Box:")
print(f"  Latitude:  {min(all_lats):.6f} to {max(all_lats):.6f}")
print(f"  Longitude: {min(all_lons):.6f} to {max(all_lons):.6f}")
print(f"\nFor NZTA query:")
print(f"  South: {min(all_lats):.4f}")
print(f"  North: {max(all_lats):.4f}")
print(f"  West:  {min(all_lons):.4f}")
print(f"  East:  {max(all_lons):.4f}")
