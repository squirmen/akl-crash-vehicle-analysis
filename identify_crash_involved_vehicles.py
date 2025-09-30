#!/usr/bin/env python3
"""
Score vehicle-crash matches for likelihood of crash involvement.
Uses proximity, speed, deceleration, and crash severity.
"""

import pandas as pd
import numpy as np

def load_data():
    print("Loading crash match data...")
    df = pd.read_csv('crash_vehicle_matches_full.csv')
    print(f"Loaded {len(df):,} records\n")
    return df

def calculate_involvement_score(df):
    print("="*80)
    print("CALCULATING CRASH INVOLVEMENT SCORES")
    print("="*80)
    print()

    df['speed_numeric'] = pd.to_numeric(df['speed_at_point'], errors='coerce')
    df['x_accel_numeric'] = pd.to_numeric(df['x_accel_at_point'], errors='coerce')

    df['distance_score'] = ((25 - df['distance_to_crash']) / 25 * 30).clip(0, 30)
    df['speed_score'] = ((30 - df['speed_numeric'].clip(0, 30)) / 30 * 40).clip(0, 40)
    df['decel_score'] = ((-df['x_accel_numeric'].fillna(0)).clip(-10, 10) + 10) / 20 * 20

    severity_bonus = {'Fatal Crash': 10, 'Serious Crash': 7, 'Minor Crash': 3, 'Non-Injury Crash': 0}
    df['severity_score'] = df['crash_severity'].map(severity_bonus).fillna(0)

    df['involvement_score'] = (df['distance_score'] + df['speed_score'] +
                                df['decel_score'] + df['severity_score'])

    return df

def filter_candidates(df, min_score=50):
    """Filter to high-scoring candidates"""

    print(f"Filtering to involvement score >= {min_score}...")
    candidates = df[df['involvement_score'] >= min_score].copy()
    print(f"Found {len(candidates):,} high-scoring records")
    print(f"  Unique vehicles: {candidates['vehicle_id'].nunique():,}")
    print(f"  Unique trips: {candidates['trip_id'].nunique():,}")
    print(f"  Unique crashes: {candidates['crash_id'].nunique():,}")
    print()

    return candidates

def analyze_score_distribution(df):
    """Show distribution of involvement scores"""

    print("="*80)
    print("INVOLVEMENT SCORE DISTRIBUTION")
    print("="*80)
    print()

    bins = [0, 40, 50, 60, 70, 80, 90, 100]
    labels = ['0-40 (Low)', '40-50 (Medium-Low)', '50-60 (Medium)',
              '60-70 (Medium-High)', '70-80 (High)', '80-90 (Very High)', '90-100 (Extreme)']

    df['score_category'] = pd.cut(df['involvement_score'], bins=bins, labels=labels, include_lowest=True)

    score_dist = df['score_category'].value_counts().sort_index()
    print("Score distribution:")
    for category, count in score_dist.items():
        pct = count / len(df) * 100
        print(f"  {category:25s}: {count:10,} ({pct:5.2f}%)")

    print()

def analyze_by_severity(candidates):
    """Analyze candidates by crash severity"""

    print("="*80)
    print("CANDIDATES BY CRASH SEVERITY")
    print("="*80)
    print()

    severity_stats = candidates.groupby('crash_severity').agg({
        'trip_id': 'nunique',
        'vehicle_id': 'nunique',
        'crash_id': 'nunique',
        'involvement_score': 'mean',
        'distance_to_crash': 'mean',
        'speed_numeric': 'mean'
    }).round(2)

    severity_stats.columns = ['unique_trips', 'unique_vehicles', 'unique_crashes',
                              'avg_score', 'avg_distance', 'avg_speed']

    print(severity_stats.to_string())
    print()

def get_top_candidates_per_crash(candidates, n_per_crash=3):
    """Get top N candidates for each crash"""

    print("="*80)
    print(f"TOP {n_per_crash} CANDIDATES PER CRASH")
    print("="*80)
    print()

    # Get top candidates per crash
    top_per_crash = candidates.sort_values('involvement_score', ascending=False).groupby('crash_id').head(n_per_crash)

    print(f"Selected {len(top_per_crash):,} top candidates across {top_per_crash['crash_id'].nunique():,} crashes")
    print()

    return top_per_crash

def show_examples(candidates, n=30):
    """Show top examples"""

    print("="*80)
    print(f"TOP {n} HIGHEST CONFIDENCE CRASH INVOLVEMENTS")
    print("="*80)
    print()

    top = candidates.nlargest(n, 'involvement_score')

    for idx, (_, row) in enumerate(top.iterrows(), 1):
        print(f"{idx}. Score: {row['involvement_score']:.1f}/100")
        print(f"   Trip: {row['trip_id']} | Vehicle: {row['vehicle_id']} ({row['vehicle_type']})")
        print(f"   Crash #{row['crash_id']}: {row['crash_severity']} - {row['crash_location']}")
        print(f"   Distance: {row['distance_to_crash']:.1f}m | Speed: {row['speed_numeric']:.1f} mph | X-accel: {row['x_accel_numeric']:.2f}")
        print(f"   Component scores - Dist: {row['distance_score']:.1f}, Speed: {row['speed_score']:.1f}, Decel: {row['decel_score']:.1f}, Severity: {row['severity_score']:.1f}")
        print()

def export_results(candidates, top_per_crash):
    """Export results"""

    print("="*80)
    print("EXPORTING RESULTS")
    print("="*80)
    print()

    # All high-scoring candidates
    output_file = 'crash_involved_candidates_scored.csv'
    candidates.to_csv(output_file, index=False)
    print(f"✓ All candidates (score >= 50): {output_file}")
    print(f"  {len(candidates):,} records")

    # Very high confidence (score >= 70)
    very_high = candidates[candidates['involvement_score'] >= 70]
    high_file = 'crash_involved_very_high_confidence.csv'
    very_high.to_csv(high_file, index=False)
    print(f"✓ Very high confidence (score >= 70): {high_file}")
    print(f"  {len(very_high):,} records")

    # Extreme confidence (score >= 80)
    extreme = candidates[candidates['involvement_score'] >= 80]
    extreme_file = 'crash_involved_extreme_confidence.csv'
    extreme.to_csv(extreme_file, index=False)
    print(f"✓ Extreme confidence (score >= 80): {extreme_file}")
    print(f"  {len(extreme):,} records")

    # Top per crash
    top_file = 'crash_involved_top_per_crash.csv'
    top_per_crash.to_csv(top_file, index=False)
    print(f"✓ Top candidates per crash: {top_file}")
    print(f"  {len(top_per_crash):,} records across {top_per_crash['crash_id'].nunique():,} crashes")

    # Fatal/serious only
    fatal_serious = candidates[candidates['crash_severity'].isin(['Fatal Crash', 'Serious Crash'])]
    fs_file = 'crash_involved_fatal_serious.csv'
    fatal_serious.to_csv(fs_file, index=False)
    print(f"✓ Fatal & serious crashes only: {fs_file}")
    print(f"  {len(fatal_serious):,} records")

    print()

    # Vehicle summary
    vehicle_summary = candidates.groupby('vehicle_id').agg({
        'trip_id': 'nunique',
        'crash_id': 'nunique',
        'involvement_score': ['mean', 'max'],
        'vehicle_type': 'first',
        'crash_severity': lambda x: x.value_counts().to_dict()
    }).reset_index()

    vehicle_summary.columns = ['vehicle_id', 'num_trips', 'num_crashes',
                                'avg_score', 'max_score', 'vehicle_type', 'crash_severities']
    vehicle_summary = vehicle_summary.sort_values('max_score', ascending=False)

    vehicle_file = 'crash_involved_vehicles_tagged.csv'
    vehicle_summary.to_csv(vehicle_file, index=False)
    print(f"✓ Vehicle summary (for behavioral analysis): {vehicle_file}")
    print(f"  {len(vehicle_summary):,} vehicles")
    print()

    return vehicle_summary

def main():
    # Load
    df = load_data()

    # Calculate scores
    df = calculate_involvement_score(df)

    # Show distribution
    analyze_score_distribution(df)

    # Filter candidates
    candidates = filter_candidates(df, min_score=50)

    # Analyze by severity
    analyze_by_severity(candidates)

    # Get top per crash
    top_per_crash = get_top_candidates_per_crash(candidates, n_per_crash=3)

    # Show examples
    show_examples(candidates, n=30)

    # Export
    vehicle_summary = export_results(candidates, top_per_crash)

    print("="*80)
    print("SUMMARY")
    print("="*80)
    print()
    print(f"✓ Scored {len(df):,} vehicle-crash proximity records")
    print(f"✓ Identified {len(candidates):,} high-confidence crash involvement candidates")
    print(f"✓ Tagged {len(vehicle_summary):,} vehicles for behavioral analysis")
    print(f"✓ Covered {candidates['crash_id'].nunique():,} crash locations")
    print()
    print("NEXT STEPS:")
    print("1. Review top candidates by crash in: crash_involved_top_per_crash.csv")
    print("2. Focus on extreme confidence cases (score >= 80)")
    print("3. Use crash_involved_vehicles_tagged.csv to compare driving behavior:")
    print("   - Crash-involved vs non-involved vehicles")
    print("   - Patterns in vehicles with multiple crash involvements")
    print()

if __name__ == '__main__':
    main()