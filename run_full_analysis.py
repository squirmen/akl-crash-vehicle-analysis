"""
Run full crash-vehicle linkage analysis on all connected vehicle files
Processes all 113 files and saves results incrementally
"""

from crash_vehicle_linkage import CrashVehicleLinkage
import pandas as pd
from pathlib import Path
import time

def run_full_analysis():
    """Run analysis on all vehicle files with incremental saving"""

    # Initialize analyzer
    analyzer = CrashVehicleLinkage(
        crash_file='data/CAS_data.csv',
        vehicle_dir='data/connected_vehicle',
        buffer_distance=100  # 100 meters
    )

    print("="*80)
    print("FULL CRASH-VEHICLE LINKAGE ANALYSIS")
    print("="*80)

    # Load crash data
    analyzer.load_crash_data(year=2025)
    analyzer.load_vehicle_files()

    print(f"\nProcessing {len(analyzer.vehicle_files)} vehicle files...")
    print(f"This may take several hours. Results will be saved incrementally.\n")

    all_matches = []
    output_file = 'crash_vehicle_matches_full.csv'
    batch_size = 10  # Save every 10 files

    start_time = time.time()

    for file_idx, vehicle_file in enumerate(analyzer.vehicle_files, 1):
        file_start = time.time()

        try:
            # Process this file
            matches = analyzer.process_vehicle_file(vehicle_file)
            all_matches.extend(matches)

            file_time = time.time() - file_start
            elapsed = time.time() - start_time

            print(f"\n[{file_idx}/{len(analyzer.vehicle_files)}] Completed in {file_time:.1f}s")
            print(f"  Total matches so far: {len(all_matches):,}")
            print(f"  Elapsed time: {elapsed/60:.1f} min")
            print(f"  Estimated time remaining: {(elapsed/file_idx)*(len(analyzer.vehicle_files)-file_idx)/60:.1f} min")

            # Save incrementally every batch_size files
            if file_idx % batch_size == 0 or file_idx == len(analyzer.vehicle_files):
                df_matches = pd.DataFrame(all_matches)
                df_matches.to_csv(output_file, index=False)
                print(f"  >>> Saved {len(all_matches):,} matches to {output_file}")

        except Exception as e:
            print(f"  ERROR processing {vehicle_file.name}: {e}")
            continue

    # Final summary
    print("\n" + "="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)

    df_matches = pd.DataFrame(all_matches)

    print(f"\nTotal matches found: {len(df_matches):,}")
    print(f"Unique vehicles: {df_matches['vehicle_id'].nunique():,}")
    print(f"Unique trips: {df_matches['trip_id'].nunique():,}")
    print(f"Unique crashes with nearby vehicles: {df_matches['crash_id'].nunique():,}")

    print(f"\nCrash severity breakdown:")
    print(df_matches['crash_severity'].value_counts())

    print(f"\nDistance statistics (meters):")
    print(df_matches['distance_to_crash'].describe())

    print(f"\nVehicle type breakdown:")
    print(df_matches['vehicle_type'].value_counts())

    print(f"\nResults saved to: {output_file}")

    total_time = time.time() - start_time
    print(f"\nTotal processing time: {total_time/60:.1f} minutes")

    return df_matches

if __name__ == "__main__":
    df_results = run_full_analysis()