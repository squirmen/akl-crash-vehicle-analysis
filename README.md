# Auckland Crash-Vehicle Spatial Analysis

Spatial linkage analysis of connected vehicle GPS trajectories and crash locations in Auckland, New Zealand.

## Overview

This project identifies vehicles that passed near crash locations using spatial proximity matching. The analysis links ~965,000 vehicle trips to 10,150 crash locations from 2025.

**Status**: Phase 1 (spatial analysis) complete. Awaiting crash timestamp data for temporal validation.

## Data

### Crash Data (CAS_data.csv)
- 10,150 crashes from 2025 (891,644 total)
- NZTM coordinates (EPSG:2193)
- Severity: Fatal (185), Serious (1,221), Minor (4,962), Non-Injury (3,782)

### Vehicle Data
- 113 CSV files, ~965,000 trips total
- GPS paths (lat/lon, WGS84) with timestamps
- Speed and acceleration at each point
- Vehicle types: HCV, LCV, CAR, BUS

## Methodology

### Spatial Matching
- Buffer: 100m around each crash location
- KD-tree spatial indexing for efficient queries
- Coordinate transformation: WGS84 → NZTM
- Records closest point, distance, speed, and acceleration

### Crash Involvement Scoring
For vehicles near crashes, calculate involvement likelihood (0-100):
- **Distance score** (30pts): Closer = higher
- **Speed score** (40pts): Slower = higher
- **Deceleration score** (20pts): Negative acceleration = higher
- **Severity bonus** (10pts): Fatal/serious weighted higher

## Results

### Spatial Matches (Full Dataset)
- **30.9M** total vehicle-crash proximity matches
- **57,009** unique vehicles
- **784,297** unique trips
- **5,250** crashes with nearby vehicles

### High-Confidence Crash Involvement
- **5,538** extreme confidence cases (score ≥80)
- **161,524** very high confidence (score ≥70)
- **233,419** fatal/serious crash candidates
- Top cases: vehicles stopped within 0.5-2m of fatal crashes

### Distance Distribution
- Mean: 48m
- Median: 46m
- Range: 0.01m - 100m

## Scripts

### crash_vehicle_linkage.py
Core spatial matching engine. Parses GPS paths, builds spatial index, finds crashes within buffer distance.

### run_full_analysis.py
Batch processor for all 113 vehicle files. Saves results incrementally.

### analyze_results.py
Summary statistics: counts, distances, severity breakdown, hotspots, speed analysis.

### identify_crash_involved_vehicles_v2.py
Scores matches for crash involvement likelihood. Exports candidates by confidence level.

## Usage

```bash
# Run full spatial analysis
python run_full_analysis.py

# Analyze results
python analyze_results.py

# Score crash involvement
python identify_crash_involved_vehicles_v2.py
```

## Output Files

- `crash_vehicle_matches_full.csv` - All spatial matches (30.9M records)
- `crash_involved_extreme_confidence.csv` - Score ≥80 (5,538 records)
- `crash_involved_very_high_confidence.csv` - Score ≥70 (161,524 records)
- `crash_involved_fatal_serious.csv` - Fatal/serious only (233,419 records)
- `crash_involved_top_per_crash.csv` - Top 3 candidates per crash
- `crash_involved_vehicles_tagged.csv` - Vehicle summary for behavior analysis

## Limitations

**No temporal matching yet**: Without crash timestamps, cannot confirm actual involvement or analyze pre-crash behavior. Current results identify spatial proximity only.

Once crash timestamps are available:
- Match vehicle timestamp to crash time (±15min window)
- Filter to pre-crash periods for behavioral analysis
- Validate high-confidence candidates
- Measure driving patterns before crashes

## Requirements

```
pandas
numpy
pyproj
scipy
shapely
```

## Coordinate Systems

- Input crashes: NZTM 2000 (EPSG:2193)
- Input vehicles: WGS84 (EPSG:4326)
- Analysis: NZTM (meters)
