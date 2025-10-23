# Auckland Crash-Vehicle Spatial Analysis

Spatial and temporal linkage analysis of connected vehicle GPS trajectories and crash locations in Auckland, New Zealand. This project identifies vehicles involved in crashes using multi-phase spatial-temporal matching.

## Project Status

**Phase 3: Crash Participant Identification - IN PROGRESS**

- **Phase 1 COMPLETE**: Spatial proximity matching (30.9M matches, 5,250 crashes)
- **Phase 2 COMPLETE**: Temporal-spatial validation (188 confirmed matches)
- **Phase 3 IN PROGRESS**: Distinguishing crash participants from witnesses and emergency responders

See [ANALYSIS_ROADMAP.md](ANALYSIS_ROADMAP.md) for detailed phase descriptions and next steps.

## Quick Start

See [GETTING_STARTED.md](GETTING_STARTED.md) for detailed setup instructions.

```bash
# Install dependencies
pip install -r requirements.txt

# Run full spatial analysis (Phase 1)
python run_full_analysis.py

# Score crash involvement (Phase 2)
python identify_crash_involved_vehicles.py

# Temporal-spatial matching (Phase 2)
python temporal_spatial_matcher.py

# Identify crash participants (Phase 3)
python identify_crash_participants.py
```

## Project Overview

### Research Question
Can connected vehicle GPS data identify vehicles involved in crashes and analyze their pre-crash behavior?

### Methodology

**Phase 1: Spatial Proximity Matching**
- KD-tree spatial indexing for efficient queries
- 100m buffer around crash locations
- Coordinate transformation: WGS84 → NZTM 2000
- Records closest approach point, distance, speed, acceleration

**Phase 2: Temporal-Spatial Validation**
- Progressive time windows (5, 10, 15, 20 minutes)
- Vehicle timestamp matching to crash datetime
- Multi-attribute scoring: distance (30pts), speed (40pts), deceleration (20pts), severity (10pts)
- Filter to high-confidence matches

**Phase 3: Crash Participant Identification**
- Distinguish crash-involved vehicles from witnesses
- Filter emergency responders (ambulances, police, fire)
- Analyze trip origin/destination patterns
- Identify sudden deceleration and scene presence

### Data Sources

**Crash Data** (`data/CAS_data.csv`)
- 10,150 crashes from 2025 (891,644 total records)
- NZTM 2000 coordinates (EPSG:2193)
- Crash severity: Fatal (185), Serious (1,221), Minor (4,962), Non-Injury (3,782)
- Includes crash datetime, location, severity, road information

**Connected Vehicle Data** (`data/connected_vehicle/`)
- 113 CSV files, ~965,000 trips total
- GPS trajectories (WGS84 lat/lon) with timestamps
- Speed and acceleration at each GPS point
- Vehicle types: Heavy Commercial (HCV), Light Commercial (LCV), Car (CAR), Bus (BUS)
- Trip start/end locations and times

## Results Summary

### Phase 1: Spatial Matches
- **30.9M** total proximity matches (within 100m)
- **57,009** unique vehicles
- **784,297** unique trips
- **5,250** crashes with nearby vehicles (52% of 2025 crashes)

### Phase 2: Temporal-Spatial Validation
- **188** confirmed matches (5-minute window, highest confidence)
- **177** unique vehicles, **152** unique crashes
- Mean distance: 48m, Median: 46m
- **174** witness vehicles (passed through crash location)
- **22** vehicles with sudden deceleration before crash
- **6** vehicles remained at scene >2 minutes

### Phase 3: Participant Identification (Current)
- Filtering 22 deceleration candidates
- Removing emergency responders
- Identifying actual crash-involved vehicles

## Project Structure

```
akl_crash_conn/
├── README.md                           # This file
├── GETTING_STARTED.md                  # Setup and usage guide
├── ANALYSIS_ROADMAP.md                 # Detailed phase plan
├── requirements.txt                    # Python dependencies
│
├── Core Analysis Scripts
│   ├── crash_vehicle_linkage.py       # Spatial matching engine (Phase 1)
│   ├── run_full_analysis.py           # Batch processor for all vehicles
│   ├── resume_analysis_efficient.py   # Resume interrupted analysis
│   ├── temporal_spatial_matcher.py    # Temporal matching (Phase 2)
│   ├── identify_crash_involved_vehicles.py  # Involvement scoring
│   ├── identify_crash_involved_not_witness.py  # Filter witnesses
│   └── identify_crash_participants.py # Participant identification (Phase 3)
│
├── Analysis & Reporting
│   ├── analyze_results.py             # Summary statistics
│   ├── analyze_confirmed_matches.py   # Confirmed match analysis
│   ├── explore_crash_data.py          # Data exploration
│   └── get_bounding_box.py            # Geographic bounds extraction
│
├── Visualization Scripts
│   ├── map_crashes_showcase.py        # Interactive showcase map
│   ├── map_all_confirmed_crashes.py   # All confirmed matches map
│   ├── map_crash_participants.py      # Participant visualization
│   ├── map_crash_involved_trip.py     # Individual trip mapping
│   └── map_all_crashes_interactive.py # All crashes explorer
│
├── Data Directories
│   ├── data/CAS_data.csv              # Crash dataset (gitignored)
│   ├── data/connected_vehicle/        # Vehicle GPS files (gitignored)
│   └── data/crash_data/               # Additional crash queries
│
├── Output Directories
│   ├── outputs/                       # HTML visualizations (gitignored)
│   └── archive/versions/              # Alternative script versions
│
└── Generated CSV Files (gitignored)
    ├── crash_vehicle_matches_full.csv           # All spatial matches (30.9M)
    ├── crash_involved_*_confidence.csv          # Scored candidates
    ├── confirmed_crash_vehicles_*min.csv        # Temporal matches
    ├── crash_WITNESSES.csv                      # Classified witnesses
    ├── crash_participants.csv                   # Crash participants
    └── emergency_responders.csv                 # Emergency vehicles
```

## Key Scripts

### Core Pipeline

**`crash_vehicle_linkage.py`**
Spatial matching engine using KD-tree indexing. Parses GPS paths, transforms coordinates, finds crashes within 100m buffer.

**`run_full_analysis.py`**
Batch processor for all 113 vehicle files. Incremental saving, progress tracking, estimated completion time.

**`temporal_spatial_matcher.py`**
Temporal matching with progressive time windows (5, 10, 15, 20 minutes). Validates spatial matches with crash datetime.

**`identify_crash_participants.py`**
Current focus: Distinguishes actual crash participants from witnesses and emergency responders using trip patterns and behavior.

### Analysis Utilities

**`analyze_results.py`**
Summary statistics: match counts, distance distributions, severity breakdowns, hotspot identification.

**`identify_crash_involved_vehicles.py`**
Scores matches 0-100 for crash involvement likelihood using distance, speed, deceleration, and severity.

### Visualization

**`map_crashes_showcase.py`**
Interactive HTML map with click functionality, speed heatmaps, statistics panel, and animated transitions.

## Output Files

### Spatial Matches
- `crash_vehicle_matches_full.csv` - All 30.9M proximity matches
- `crash_vehicle_matches_test.csv` - Test subset

### Scored Candidates
- `crash_involved_extreme_confidence.csv` - Score ≥80 (5,538 records)
- `crash_involved_very_high_confidence.csv` - Score ≥70 (161,524 records)
- `crash_involved_high_confidence.csv` - Score ≥60
- `crash_involved_fatal_serious.csv` - Fatal/serious crashes only (233,419 records)

### Temporal Matches
- `confirmed_crash_vehicles_5min.csv` - 5-minute window (188 matches)
- `confirmed_crash_vehicles_10min.csv` - 10-minute window
- `confirmed_crash_vehicles_15min.csv` - 15-minute window
- `confirmed_crash_vehicles_20min.csv` - 20-minute window
- `*_TOP25pct.csv` - Top 25% scoring matches for each window

### Classification
- `crash_WITNESSES.csv` - Vehicles passing through crash location
- `crash_participants.csv` - Actual crash-involved vehicles
- `emergency_responders.csv` - Ambulances, police, fire trucks

### Summaries
- `crash_involved_vehicles_summary.csv` - Aggregated statistics
- `crash_involved_vehicles_tagged.csv` - Tagged for behavior analysis
- `high_priority_vehicles.csv` - High-confidence candidates

## Coordinate Systems

- **Input crashes**: NZTM 2000 (EPSG:2193) - meters, optimized for New Zealand
- **Input vehicles**: WGS84 (EPSG:4326) - latitude/longitude
- **Analysis**: NZTM (all distance calculations in meters)
- **Visualizations**: WGS84 (for web mapping libraries)

## Requirements

See `requirements.txt` for full dependency list.

**Core:**
- Python 3.8+
- pandas, numpy
- scipy (KD-tree spatial indexing)
- pyproj (coordinate transformations)
- shapely (geometry operations)

**Optional (visualization):**
- matplotlib, seaborn

## Next Steps

1. **Complete Phase 3**: Finalize crash participant identification
2. **Phase 4**: Pre-crash behavior analysis (30-60 seconds before crash)
3. **Phase 5**: Statistical validation and summary report
4. **Phase 6**: Extended temporal windows for witness vehicle analysis

See [ANALYSIS_ROADMAP.md](ANALYSIS_ROADMAP.md) for detailed plans.

## Known Limitations

- GPS sampling rates vary (1-30 second intervals)
- Some crashes have sparse vehicle coverage
- Crash timestamps may be approximate (reported vs actual time)
- Emergency responders included in initial matches (filtered in Phase 3)

## Citation

Auckland crash data sourced from New Zealand Transport Agency (NZTA) Crash Analysis System (CAS).

## License

Research project - contact repository owner for usage permissions.
