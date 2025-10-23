# Getting Started Guide

Welcome to the Auckland Crash-Vehicle Analysis project! This guide will help you set up your environment and understand the analysis pipeline.

## Prerequisites

- **Python 3.8 or higher** (check with `python3 --version`)
- **Basic Python knowledge** (pandas, numpy)
- **Understanding of coordinate systems** (helpful but not required)
- **10+ GB disk space** for data files

## Setup Instructions

### 1. Clone the Repository

```bash
git clone <repository-url>
cd akl_crash_conn
```

### 2. Create a Virtual Environment (Recommended)

```bash
# Create virtual environment
python3 -m venv venv

# Activate it
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

This will install:
- `pandas` - Data manipulation
- `numpy` - Numerical operations
- `scipy` - Spatial indexing (KD-tree)
- `pyproj` - Coordinate transformations
- `shapely` - Geometry operations
- `matplotlib`, `seaborn` - Visualization (optional)

### 4. Verify Data Directory Structure

Ensure your data files are organized as follows:

```
akl_crash_conn/
└── data/
    ├── CAS_data.csv                              # Main crash dataset
    ├── connected_vehicle/                        # Vehicle GPS files
    │   ├── support.NZ_report_withOD-*.csv       # 113 files
    │   └── ...
    └── crash_data/                               # Additional crash queries
        ├── crash_Untitled_query.2025-10-13.11-58.csv
        └── crashvehicle_Untitled_query.2025-10-13.11-59.csv
```

**Note**: Data files are gitignored due to size and sensitivity.

## Understanding the Analysis Pipeline

The project follows a multi-phase approach:

### Phase 1: Spatial Proximity Matching

**Goal**: Find all vehicles that passed within 100m of any crash location.

**Script**: `run_full_analysis.py`

```bash
python run_full_analysis.py
```

**What it does**:
1. Loads 10,150 crashes from 2025
2. Builds a KD-tree spatial index of crash locations
3. Processes all 113 vehicle files (~965,000 trips)
4. For each GPS point in each trip, finds nearby crashes
5. Saves results incrementally to `crash_vehicle_matches_full.csv`

**Runtime**: ~2-4 hours (depends on hardware)

**Output**: `crash_vehicle_matches_full.csv` (30.9M records, ~1.5 GB)

### Phase 2: Temporal-Spatial Validation

**Goal**: Validate spatial matches using crash datetime.

**Step 2a: Score Crash Involvement**

```bash
python identify_crash_involved_vehicles.py
```

Scores each match (0-100) based on:
- Distance to crash (30 points)
- Speed at closest point (40 points)
- Deceleration (20 points)
- Crash severity bonus (10 points)

**Step 2b: Temporal Matching**

```bash
python temporal_spatial_matcher.py
```

Matches vehicle timestamps to crash datetime using progressive time windows (5, 10, 15, 20 minutes).

**Output**: `confirmed_crash_vehicles_5min.csv` (188 confirmed matches)

### Phase 3: Crash Participant Identification (Current Work)

**Goal**: Distinguish actual crash participants from witnesses and emergency responders.

**Step 3a: Filter Witnesses**

```bash
python identify_crash_involved_not_witness.py
```

Identifies vehicles with:
- Sudden deceleration before crash
- Stopped at scene
- Remained at scene >2 minutes

**Step 3b: Identify Participants**

```bash
python identify_crash_participants.py
```

Filters to actual crash participants by:
- Checking trip origin/destination (exclude hospital/emergency station origins)
- Analyzing speed profiles
- Identifying emergency responders

**Outputs**:
- `crash_participants.csv` - Likely crash-involved vehicles
- `emergency_responders.csv` - Ambulances, police, fire trucks

## Key Concepts

### Coordinate Systems

The project uses two coordinate systems:

1. **NZTM 2000 (EPSG:2193)** - New Zealand Transverse Mercator
   - Used for: Crash locations, distance calculations
   - Units: Meters
   - Optimized for New Zealand geography

2. **WGS84 (EPSG:4326)** - World Geodetic System 1984
   - Used for: Vehicle GPS trajectories, web maps
   - Units: Latitude/Longitude degrees
   - Standard GPS coordinate system

**Why two systems?**
- Distance calculations require projected coordinates (meters)
- GPS data comes in lat/lon
- We transform vehicle coordinates to NZTM for spatial matching

### Spatial Indexing (KD-tree)

Instead of checking every crash against every GPS point (billions of comparisons), we use a KD-tree:

```python
from scipy.spatial import cKDTree

# Build spatial index once
crash_coords = crashes[['X', 'Y']].values
crash_tree = cKDTree(crash_coords)

# Query efficiently
distances, indices = crash_tree.query(gps_points, distance_upper_bound=100)
```

This reduces complexity from O(n*m) to O(n log m), making the analysis feasible.

### GPS Path Format

Vehicle paths are stored as space-separated coordinate pairs:

```
"174.7645 -36.8485, 174.7646 -36.8486, 174.7647 -36.8487"
      ↑         ↑
   longitude  latitude
```

Each pair corresponds to:
- TimestampPath: `"2025-01-04 12:00:00, 2025-01-04 12:00:05, ..."`
- SpeedPath: `"45.2, 46.1, 44.8, ..."`
- XAccPath: `"0.5, -0.2, -1.1, ..."` (longitudinal acceleration)

## Running Analysis Scripts

### Test Mode (Quick Verification)

Many scripts have a test mode for quick verification:

```python
# In crash_vehicle_linkage.py (bottom)
matches = analyzer.run_analysis(
    year=2025,
    max_files=2,              # Only first 2 vehicle files
    max_records_per_file=1000  # Only 1000 trips per file
)
```

Run this first to verify your setup works!

### Full Analysis

Comment out the test limits for production runs:

```python
matches = analyzer.run_analysis(year=2025)  # All files, all records
```

### Resuming Interrupted Analysis

If `run_full_analysis.py` is interrupted, use the resume script:

```bash
python resume_analysis_efficient.py
```

This loads the existing results and continues from where it stopped.

## Visualization

### Generate Interactive Maps

```bash
# Showcase map with all features
python map_crashes_showcase.py

# All confirmed crashes
python map_all_confirmed_crashes.py

# Crash participants
python map_crash_participants.py
```

Maps are saved to `outputs/` directory and can be opened in any web browser.

### View a Map

```bash
# macOS
open outputs/showcase_crash_map.html

# Linux
xdg-open outputs/showcase_crash_map.html

# Windows
start outputs/showcase_crash_map.html
```

## Analysis Utilities

### Explore Crash Data

```bash
python explore_crash_data.py
```

Shows:
- Crash table structure
- Available attributes
- Severity distribution
- Coordinate quality

### Get Geographic Bounds

```bash
python get_bounding_box.py
```

Extracts lat/lon bounds from vehicle data (useful for map zoom levels).

### Analyze Results

```bash
python analyze_results.py
```

Generates summary statistics:
- Match counts by severity
- Distance distributions
- Hotspot identification
- Speed analysis

## Common Issues & Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'pyproj'"

**Solution**: Activate your virtual environment and install dependencies:
```bash
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### Issue: "FileNotFoundError: data/CAS_data.csv"

**Solution**: Ensure data files are in the correct directory structure. Check with:
```bash
ls data/CAS_data.csv
ls data/connected_vehicle/*.csv | wc -l  # Should show 113
```

### Issue: "csv.Error: field larger than field limit"

**Solution**: This is already handled in the scripts with:
```python
import csv
import sys
csv.field_size_limit(sys.maxsize)
```

If still seeing errors, you may need to increase your system's memory limits.

### Issue: Script runs for hours without output

**Solution**: This is normal for `run_full_analysis.py`. Monitor progress:
- Prints status every 500 trips
- Saves incrementally every 10 files
- Check output file size: `ls -lh crash_vehicle_matches_full.csv`

### Issue: Out of memory errors

**Solution**:
1. Close other applications
2. Use the resume script if interrupted
3. Process in batches (modify `max_files` parameter)

## Next Steps

1. **Understand Phase 1-2**: Read through the completed analyses
2. **Review Current Results**: Examine `confirmed_crash_vehicles_5min.csv`
3. **Focus on Phase 3**: Help complete crash participant identification
4. **Plan Phase 4**: Pre-crash behavior analysis

## Useful Commands

```bash
# Count records in a CSV
wc -l crash_vehicle_matches_full.csv

# View first 10 rows
head -n 10 crash_vehicle_matches_full.csv

# Check file sizes
ls -lh *.csv

# Search for a specific vehicle
grep "VehicleID" crash_vehicle_matches_full.csv

# Count unique crashes
cut -d',' -f1 crash_vehicle_matches_full.csv | sort -u | wc -l
```

## Python Snippets for Quick Analysis

### Load Results
```python
import pandas as pd

# Load full matches
df = pd.read_csv('crash_vehicle_matches_full.csv')

# Basic stats
print(f"Total matches: {len(df):,}")
print(f"Unique vehicles: {df['vehicle_id'].nunique():,}")
print(f"Mean distance: {df['distance_to_crash'].mean():.1f}m")
```

### Filter to High Confidence
```python
# Score >= 80
high_conf = df[df['involvement_score'] >= 80]
print(f"High confidence matches: {len(high_conf):,}")
```

### Analyze by Severity
```python
severity_stats = df.groupby('crash_severity').agg({
    'vehicle_id': 'count',
    'distance_to_crash': 'mean'
}).rename(columns={'vehicle_id': 'count'})
print(severity_stats)
```

## Getting Help

- **README.md**: Project overview and results
- **ANALYSIS_ROADMAP.md**: Detailed phase plans
- **Code comments**: Each script has detailed docstrings
- **Ask questions**: Don't hesitate to ask your supervisor!

## Contributing

As you work on the project:
1. Document your findings
2. Comment your code changes
3. Update the roadmap with progress
4. Create visualizations for insights

Good luck with your analysis!
