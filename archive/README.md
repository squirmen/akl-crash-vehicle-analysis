# Archive

This directory contains alternative versions and experimental scripts that are kept for reference but not used in the main analysis pipeline.

## versions/

Alternative implementations of temporal-spatial matching:

- `temporal_spatial_matcher_v2.py` - Enhanced version with coordinate-based crash matching for different crash ID systems (CAS vs NZTA)
- `temporal_spatial_matcher_fast.py` - Performance-optimized version using spatial filtering before temporal filtering
- `temporal_spatial_matcher_simple.py` - Lightweight implementation without scipy dependency

**Current production version:** `temporal_spatial_matcher.py` (in project root)

These versions are maintained for:
- Comparison testing
- Different deployment scenarios (e.g., low-dependency environments)
- Performance benchmarking
- Methodological documentation
