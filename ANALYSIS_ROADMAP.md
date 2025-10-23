# Analysis Roadmap

## Current Status

**✅ Phase 1: Spatial-Temporal Matching - COMPLETE**
- 188 confirmed vehicle-crash matches (5-minute temporal window, 25m spatial threshold)
- 177 unique vehicles, 152 unique crashes
- Interactive visualization complete

**✅ Phase 2: Vehicle Classification - COMPLETE**
- 174 witnesses (passed through crash location)
- 22 vehicles with sudden deceleration before crash
- 6 vehicles that remained at scene >2 minutes (likely emergency responders)

## Planned Analysis Steps

### 🔄 Phase 3: Identify Crash Participants (IN PROGRESS)

Filter 22 sudden deceleration vehicles to exclude emergency responders and identify actual crash-involved vehicles.

**Approach:**
- Check trip start/end locations (hospitals, fire stations indicate emergency vehicles)
- Analyze speed profile: emergency vehicles often have high speeds approaching scene
- Check time at scene vs arrival time relative to crash
- Flag vehicles with origin/destination at emergency service facilities

**Expected Output:**
- crash_participants.csv (vehicles likely involved in crash)
- emergency_responders.csv (ambulances, police, fire trucks)
- analysis summary with confidence scores

### ⏳ Phase 4: Pre-Crash Behavior Analysis

Analyze driving behavior in 30-60 seconds before crash for confirmed participants.

**Metrics:**
- Speed trajectory (accelerating, decelerating, constant)
- Maximum deceleration rate
- Lateral acceleration (steering patterns)
- Heading relative to crash point
- Speed variability

**Comparisons:**
- Crash participants vs witnesses
- By crash severity (Fatal/Serious/Minor/Non-Injury)
- By vehicle type (HCV/LCV/Car/Bus)

**Expected Output:**
- Behavioral signatures distinguishing crash-involved from witness vehicles
- Statistical models for crash involvement probability
- Validation of matching methodology

### ⏳ Phase 5: Statistical Summary & Validation

Create comprehensive summary for data vendor demonstration.

**Components:**
- Match rate by crash severity
- Match rate by vehicle type
- Temporal distribution (time of day, day of week)
- Spatial distribution (road types, locations)
- Match quality metrics (distance, time difference, scores)
- Confidence intervals and validation statistics

**Deliverables:**
- Executive summary document
- Statistical analysis report
- Interactive dashboard (completed)
- Data quality assessment

### ⏳ Phase 6: Extended Temporal Analysis (Optional)

Expand matching to wider temporal windows.

**Approach:**
- Test 10-minute, 15-minute, 20-minute windows
- Analyze trade-off between match quantity and quality
- Identify optimal window for different use cases

**Goal:**
- Capture more witness vehicles for crash reconstruction
- Understand GPS sampling rate impact on matching
- Validate temporal threshold selection

## Data Quality Notes

**Known Limitations:**
- GPS sampling rates vary (1-30 second intervals)
- Some crashes have sparse vehicle coverage
- Crash timestamps may be approximate (reported time vs actual time)
- Emergency responders included in initial matches

**Validation Needed:**
- Ground truth comparison (if available from police reports)
- Cross-validation with crash descriptions (number of vehicles involved)
- Sensitivity analysis on thresholds

## Technical Debt

- [ ] Remove debug console.log statements from showcase map
- [ ] Optimize trip path loading (currently loads all 178 paths on page load)
- [ ] Add export functionality for filtered datasets
- [x] Document coordinate system transformations (NZTM/WGS84) - Added to GETTING_STARTED.md
- [x] Create requirements.txt - Completed
- [x] Organize project structure - HTML files moved to outputs/, archive created
- [x] Update README with current phase status - Completed
