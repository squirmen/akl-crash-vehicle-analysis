"""Summary statistics and analysis of crash-vehicle matches"""

import pandas as pd
import numpy as np
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns

def load_results(filename='crash_vehicle_matches_full.csv'):
    print(f"Loading results from {filename}...")
    df = pd.read_csv(filename)
    print(f"Loaded {len(df):,} matches")
    return df

def basic_statistics(df):
    print("\n" + "="*80)
    print("BASIC STATISTICS")
    print("="*80)

    print(f"\nTotal matches: {len(df):,}")
    print(f"Unique vehicles: {df['vehicle_id'].nunique():,}")
    print(f"Unique trips: {df['trip_id'].nunique():,}")
    print(f"Unique crashes with nearby vehicles: {df['crash_id'].nunique():,}")

    print(f"\n\nCrash Severity Breakdown:")
    severity_counts = df['crash_severity'].value_counts()
    for severity, count in severity_counts.items():
        pct = (count / len(df)) * 100
        print(f"  {severity:20s}: {count:7,} ({pct:5.1f}%)")

    print(f"\n\nVehicle Type Breakdown:")
    vehicle_counts = df['vehicle_type'].value_counts()
    for vtype, count in vehicle_counts.items():
        pct = (count / len(df)) * 100
        print(f"  {vtype:20s}: {count:7,} ({pct:5.1f}%)")

    print(f"\n\nDistance Statistics (meters):")
    print(df['distance_to_crash'].describe())

    print(f"\n\nCrashes by distance bucket:")
    df['distance_bucket'] = pd.cut(df['distance_to_crash'],
                                     bins=[0, 25, 50, 75, 100],
                                     labels=['0-25m', '25-50m', '50-75m', '75-100m'])
    bucket_counts = df.groupby('distance_bucket')['crash_id'].nunique()
    print(bucket_counts)

def high_risk_analysis(df):
    """Identify high-risk patterns"""
    print("\n" + "="*80)
    print("HIGH-RISK ANALYSIS")
    print("="*80)

    # Fatal crashes
    fatal = df[df['crash_severity'] == 'Fatal Crash']
    print(f"\nFatal Crashes:")
    print(f"  Total matches near fatal crashes: {len(fatal):,}")
    print(f"  Unique vehicles near fatal crashes: {fatal['vehicle_id'].nunique():,}")
    print(f"  Unique fatal crash locations: {fatal['crash_id'].nunique():,}")

    # Serious crashes
    serious = df[df['crash_severity'] == 'Serious Crash']
    print(f"\nSerious Crashes:")
    print(f"  Total matches near serious crashes: {len(serious):,}")
    print(f"  Unique vehicles near serious crashes: {serious['vehicle_id'].nunique():,}")
    print(f"  Unique serious crash locations: {serious['crash_id'].nunique():,}")

    # Multiple crash involvement
    vehicle_crash_counts = df.groupby('vehicle_id').agg({
        'crash_id': 'nunique',
        'trip_id': 'nunique'
    }).reset_index()
    vehicle_crash_counts.columns = ['vehicle_id', 'num_crashes', 'num_trips']

    multi_crash = vehicle_crash_counts[vehicle_crash_counts['num_crashes'] > 5].sort_values('num_crashes', ascending=False)

    print(f"\n\nVehicles near multiple crash locations (>5):")
    print(f"  Count: {len(multi_crash):,}")
    print(f"\n  Top 10 vehicles by crash proximity:")
    print(multi_crash.head(10).to_string(index=False))

def crash_hotspots(df, top_n=20):
    """Identify crash locations with most vehicle traffic"""
    print("\n" + "="*80)
    print(f"TOP {top_n} CRASH HOTSPOTS (Most Vehicle Traffic)")
    print("="*80)

    hotspots = df.groupby(['crash_id', 'crash_location', 'crash_severity']).agg({
        'vehicle_id': 'nunique',
        'trip_id': 'count',
        'distance_to_crash': 'mean'
    }).reset_index()

    hotspots.columns = ['crash_id', 'location', 'severity', 'unique_vehicles', 'total_passes', 'avg_distance']
    hotspots = hotspots.sort_values('unique_vehicles', ascending=False)

    print(hotspots.head(top_n).to_string(index=False))

    return hotspots

def speed_analysis(df):
    """Analyze speed patterns near crashes"""
    print("\n" + "="*80)
    print("SPEED ANALYSIS")
    print("="*80)

    # Filter out missing speed data
    df_speed = df[df['speed_at_point'].notna()].copy()

    # Convert speed to numeric
    df_speed['speed_numeric'] = pd.to_numeric(df_speed['speed_at_point'], errors='coerce')
    df_speed = df_speed[df_speed['speed_numeric'].notna()]

    print(f"\nRecords with speed data: {len(df_speed):,} ({len(df_speed)/len(df)*100:.1f}%)")

    print(f"\nSpeed statistics at crash locations (mph):")
    print(df_speed['speed_numeric'].describe())

    print(f"\nSpeed by crash severity:")
    speed_by_severity = df_speed.groupby('crash_severity')['speed_numeric'].agg(['mean', 'median', 'std', 'count'])
    print(speed_by_severity)

    # High speed near crashes
    high_speed = df_speed[df_speed['speed_numeric'] > 70]
    print(f"\n\nHigh speed (>70 mph) near crashes:")
    print(f"  Count: {len(high_speed):,}")
    print(f"  Unique vehicles: {high_speed['vehicle_id'].nunique():,}")
    print(f"  Crash severity breakdown:")
    print(high_speed['crash_severity'].value_counts())

def temporal_analysis(df):
    """Analyze temporal patterns"""
    print("\n" + "="*80)
    print("TEMPORAL ANALYSIS")
    print("="*80)

    # Parse timestamps
    df_temporal = df[df['closest_timestamp'].notna()].copy()

    print(f"\nRecords with timestamp data: {len(df_temporal):,} ({len(df_temporal)/len(df)*100:.1f}%)")

    try:
        df_temporal['timestamp'] = pd.to_datetime(df_temporal['closest_timestamp'])
        df_temporal['hour'] = df_temporal['timestamp'].dt.hour
        df_temporal['day_of_week'] = df_temporal['timestamp'].dt.day_name()
        df_temporal['date'] = df_temporal['timestamp'].dt.date

        print(f"\nMatches by hour of day:")
        hourly = df_temporal['hour'].value_counts().sort_index()
        for hour, count in hourly.items():
            print(f"  {hour:02d}:00 - {count:6,}")

        print(f"\nMatches by day of week:")
        daily = df_temporal['day_of_week'].value_counts()
        print(daily)

    except Exception as e:
        print(f"Error parsing timestamps: {e}")

def export_high_priority_vehicles(df, output_file='high_priority_vehicles.csv'):
    """Export list of vehicles that should be investigated further"""
    print("\n" + "="*80)
    print("EXPORTING HIGH-PRIORITY VEHICLES")
    print("="*80)

    # Criteria for high-priority:
    # 1. Near fatal/serious crashes
    # 2. Multiple crash proximities
    # 3. High speeds near crashes

    high_priority = []

    # Near fatal crashes
    fatal_vehicles = df[df['crash_severity'] == 'Fatal Crash']['vehicle_id'].unique()
    high_priority.extend(fatal_vehicles)

    # Near serious crashes
    serious_vehicles = df[df['crash_severity'] == 'Serious Crash']['vehicle_id'].unique()
    high_priority.extend(serious_vehicles)

    # Multiple crashes
    vehicle_crash_counts = df.groupby('vehicle_id')['crash_id'].nunique()
    multi_crash_vehicles = vehicle_crash_counts[vehicle_crash_counts > 5].index.tolist()
    high_priority.extend(multi_crash_vehicles)

    # Unique list
    high_priority = list(set(high_priority))

    # Create detailed export
    priority_df = df[df['vehicle_id'].isin(high_priority)].copy()

    # Aggregate by vehicle
    vehicle_summary = priority_df.groupby('vehicle_id').agg({
        'crash_id': 'nunique',
        'trip_id': 'nunique',
        'crash_severity': lambda x: x.value_counts().to_dict(),
        'distance_to_crash': 'mean',
        'speed_at_point': lambda x: pd.to_numeric(x, errors='coerce').mean(),
        'vehicle_type': 'first'
    }).reset_index()

    vehicle_summary.columns = ['vehicle_id', 'num_crash_locations', 'num_trips', 'severity_breakdown',
                                'avg_distance_to_crashes', 'avg_speed_at_crashes', 'vehicle_type']

    vehicle_summary = vehicle_summary.sort_values('num_crash_locations', ascending=False)

    vehicle_summary.to_csv(output_file, index=False)
    print(f"\nExported {len(vehicle_summary):,} high-priority vehicles to {output_file}")

    print(f"\nTop 10 highest priority vehicles:")
    print(vehicle_summary.head(10)[['vehicle_id', 'vehicle_type', 'num_crash_locations', 'num_trips']].to_string(index=False))

def main():
    """Run complete analysis"""
    # Load results
    df = load_results('crash_vehicle_matches_full.csv')

    # Run analyses
    basic_statistics(df)
    high_risk_analysis(df)
    crash_hotspots(df, top_n=20)
    speed_analysis(df)
    temporal_analysis(df)
    export_high_priority_vehicles(df)

    print("\n" + "="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)

if __name__ == "__main__":
    main()