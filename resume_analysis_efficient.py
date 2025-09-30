"""
Resume crash-vehicle linkage analysis from where it left off
Memory-efficient version that appends to CSV without loading all data
"""

from crash_vehicle_linkage import CrashVehicleLinkage
import pandas as pd
from pathlib import Path
import time

def count_existing_matches(output_file='crash_vehicle_matches_full.csv'):
    """Count existing matches without loading into memory"""
    if not Path(output_file).exists():
        return 0, 0

    # Count rows efficiently
    row_count = sum(1 for _ in open(output_file)) - 1  # subtract header

    # Estimate files processed (avg ~270k matches per file based on your data)
    estimated_files = row_count // 270000

    return row_count, estimated_files

def resume_analysis():
    """Resume analysis from last save point - memory efficient"""

    output_file = 'crash_vehicle_matches_full.csv'

    # Initialize analyzer
    analyzer = CrashVehicleLinkage(
        crash_file='data/CAS_data.csv',
        vehicle_dir='data/connected_vehicle',
        buffer_distance=100
    )

    print("="*80)
    print("RESUMING CRASH-VEHICLE LINKAGE ANALYSIS (MEMORY EFFICIENT)")
    print("="*80)

    # Load crash data and vehicle files
    analyzer.load_crash_data(year=2025)
    analyzer.load_vehicle_files()

    # Check existing results
    start_index = 0
    existing_count = 0

    if Path(output_file).exists():
        existing_count, estimated_files = count_existing_matches(output_file)
        start_index = min(estimated_files, len(analyzer.vehicle_files) - 1)

        print(f"\nFound existing results:")
        print(f"  Matches in file: {existing_count:,}")
        print(f"  Estimated completion: ~{start_index}/{len(analyzer.vehicle_files)} files")
        print(f"\nResuming from file {start_index + 1}...")

    start_time = time.time()

    # Process remaining files
    remaining_files = analyzer.vehicle_files[start_index:]

    print(f"\nProcessing {len(remaining_files)} remaining files...\n")

    # Track total for reporting
    total_new_matches = 0

    for idx, vehicle_file in enumerate(remaining_files, start=start_index + 1):
        file_start = time.time()

        try:
            # Process this file
            matches = analyzer.process_vehicle_file(vehicle_file)

            # Append to CSV immediately without loading existing data
            if matches:
                df_batch = pd.DataFrame(matches)

                # If first batch, write with header; otherwise append
                if idx == 1 and not Path(output_file).exists():
                    df_batch.to_csv(output_file, index=False, mode='w')
                else:
                    df_batch.to_csv(output_file, index=False, mode='a', header=False)

                total_new_matches += len(matches)

            file_time = time.time() - file_start
            elapsed = time.time() - start_time

            print(f"\n[{idx}/{len(analyzer.vehicle_files)}] Completed in {file_time:.1f}s")
            print(f"  Matches this file: {len(matches):,}")
            print(f"  New matches added: {total_new_matches:,}")
            print(f"  Total matches (est): {existing_count + total_new_matches:,}")
            print(f"  Elapsed time: {elapsed/60:.1f} min")

            remaining_files_count = len(analyzer.vehicle_files) - idx
            if remaining_files_count > 0 and idx > start_index:
                avg_time = elapsed / (idx - start_index)
                print(f"  Estimated time remaining: {avg_time * remaining_files_count / 60:.1f} min")

        except Exception as e:
            print(f"  ERROR processing {vehicle_file.name}: {e}")
            continue

    # Final summary
    print("\n" + "="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)

    # Count final results
    final_count, _ = count_existing_matches(output_file)

    print(f"\nNew matches added: {total_new_matches:,}")
    print(f"Total matches in file: {final_count:,}")
    print(f"\nResults saved to: {output_file}")

    total_time = time.time() - start_time
    print(f"Resume processing time: {total_time/60:.1f} minutes")

if __name__ == "__main__":
    resume_analysis()