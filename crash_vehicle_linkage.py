"""
Spatial linkage of vehicle GPS trajectories to crash locations.
Uses KD-tree spatial indexing for efficient proximity matching.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import json
from pyproj import Transformer
from shapely.geometry import Point, LineString
from shapely.ops import transform
from scipy.spatial import cKDTree
import warnings
warnings.filterwarnings('ignore')

transformer_to_nztm = Transformer.from_crs("EPSG:4326", "EPSG:2193", always_xy=True)

class CrashVehicleLinkage:
    def __init__(self, crash_file, vehicle_dir, buffer_distance=100):
        self.crash_file = crash_file
        self.vehicle_dir = Path(vehicle_dir)
        self.buffer_distance = buffer_distance
        self.crashes = None
        self.vehicle_files = []
        self.matches = []

    def load_crash_data(self, year=2025):
        print(f"Loading crash data for {year}...")
        df = pd.read_csv(self.crash_file)

        self.crashes = df[df['crashYear'] == year].copy()
        print(f"Loaded {len(self.crashes)} crashes from {year}")
        print(f"Crash severity breakdown:")
        print(self.crashes['crashSeverity'].value_counts())

        print("Building spatial index...")
        crash_coords = self.crashes[['X', 'Y']].values
        self.crash_tree = cKDTree(crash_coords)
        print("Spatial index built")

        return self.crashes

    def load_vehicle_files(self):
        self.vehicle_files = list(self.vehicle_dir.glob("support.NZ_report_withOD-*.csv"))
        print(f"\nFound {len(self.vehicle_files)} connected vehicle files")
        return self.vehicle_files

    def parse_path_string(self, path_str):
        if pd.isna(path_str) or path_str == '':
            return []

        try:
            points = []
            pairs = path_str.split(',')
            for pair in pairs:
                coords = pair.strip().split()
                if len(coords) == 2:
                    lon, lat = float(coords[0]), float(coords[1])
                    points.append((lon, lat))
            return points
        except:
            return []

    def convert_path_to_nztm(self, path_points):
        nztm_points = []
        for lon, lat in path_points:
            x, y = transformer_to_nztm.transform(lon, lat)
            nztm_points.append((x, y))
        return nztm_points

    def point_to_point_distance(self, x1, y1, x2, y2):
        return np.sqrt((x2 - x1)**2 + (y2 - y1)**2)

    def find_nearby_crashes(self, path_points_nztm):
        if not path_points_nztm:
            return []

        path_array = np.array(path_points_nztm)
        distances, indices = self.crash_tree.query(
            path_array,
            k=10,
            distance_upper_bound=self.buffer_distance
        )

        crash_matches = {}

        for point_idx, (dists, crash_indices) in enumerate(zip(distances, indices)):
            for dist, crash_idx in zip(dists, crash_indices):
                if dist <= self.buffer_distance and crash_idx < len(self.crashes):
                    if crash_idx not in crash_matches or dist < crash_matches[crash_idx][0]:
                        crash_matches[crash_idx] = (dist, point_idx)

        return [(crash_idx, dist, point_idx) for crash_idx, (dist, point_idx) in crash_matches.items()]

    def process_vehicle_file(self, vehicle_file, max_records=None):
        print(f"\nProcessing: {vehicle_file.name}")
        df_vehicles = pd.read_csv(vehicle_file, nrows=max_records)
        print(f"  Loaded {len(df_vehicles)} vehicle trips")

        matches_in_file = []

        for idx, row in df_vehicles.iterrows():
            if idx % 500 == 0 and idx > 0:
                print(f"  Processed {idx}/{len(df_vehicles)} trips, {len(matches_in_file)} matches")

            raw_path = self.parse_path_string(row['RawPath'])
            if not raw_path:
                continue

            path_nztm = self.convert_path_to_nztm(raw_path)
            nearby_crashes = self.find_nearby_crashes(path_nztm)

            for crash_idx, min_dist, closest_point_idx in nearby_crashes:
                crash = self.crashes.iloc[crash_idx]
                timestamps = row['TimestampPath'].split(',') if pd.notna(row['TimestampPath']) else []
                speeds = row['SpeedPath'].split(',') if pd.notna(row['SpeedPath']) else []
                x_accel = row['XAccPath'].split(',') if pd.notna(row['XAccPath']) else []

                match = {
                    'crash_id': crash.name,
                    'crash_x': crash['X'],
                    'crash_y': crash['Y'],
                    'crash_severity': crash['crashSeverity'],
                    'crash_location': crash.get('crashLocation1', 'Unknown'),
                    'vehicle_id': row['VehicleID'],
                    'trip_id': row['TripID'],
                    'vehicle_type': row['VehicleType'],
                    'distance_to_crash': min_dist,
                    'trip_start': row['StartDate'],
                    'trip_end': row['EndDate'],
                    'closest_point_idx': closest_point_idx,
                    'closest_timestamp': timestamps[closest_point_idx] if closest_point_idx < len(timestamps) else None,
                    'speed_at_point': speeds[closest_point_idx] if closest_point_idx < len(speeds) else None,
                    'x_accel_at_point': x_accel[closest_point_idx] if closest_point_idx < len(x_accel) else None,
                    'trip_speed_max': row.get('SpeedMax', None),
                    'trip_speed_avg': row.get('SpeedAvg', None),
                }

                matches_in_file.append(match)

        print(f"  Found {len(matches_in_file)} matches in this file")
        return matches_in_file

    def run_analysis(self, year=2025, max_files=None, max_records_per_file=None):
        self.load_crash_data(year=year)
        self.load_vehicle_files()

        if max_files:
            self.vehicle_files = self.vehicle_files[:max_files]

        all_matches = []
        for vfile in self.vehicle_files:
            matches = self.process_vehicle_file(vfile, max_records=max_records_per_file)
            all_matches.extend(matches)

        self.matches = pd.DataFrame(all_matches)

        print(f"\n{'='*60}")
        print(f"ANALYSIS COMPLETE")
        print(f"{'='*60}")
        print(f"Total crashes analyzed: {len(self.crashes)}")
        print(f"Total vehicle files processed: {len(self.vehicle_files)}")
        print(f"Total matches found: {len(self.matches)}")

        if len(self.matches) > 0:
            print(f"\nUnique vehicles near crashes: {self.matches['vehicle_id'].nunique()}")
            print(f"Unique trips near crashes: {self.matches['trip_id'].nunique()}")
            print(f"Unique crash locations with nearby vehicles: {self.matches['crash_id'].nunique()}")

            print(f"\nDistance statistics (meters):")
            print(self.matches['distance_to_crash'].describe())

        return self.matches

    def save_results(self, output_file='crash_vehicle_matches.csv'):
        if self.matches is not None and len(self.matches) > 0:
            self.matches.to_csv(output_file, index=False)
            print(f"\nResults saved to: {output_file}")
        else:
            print("\nNo matches to save")

if __name__ == "__main__":
    analyzer = CrashVehicleLinkage(
        crash_file='data/CAS_data.csv',
        vehicle_dir='data/connected_vehicle',
        buffer_distance=100
    )

    matches = analyzer.run_analysis(year=2025, max_files=2, max_records_per_file=1000)
    analyzer.save_results('crash_vehicle_matches_test.csv')

    if len(matches) > 0:
        print(f"\nSample matches:")
        print(matches.head(10))