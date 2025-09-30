#!/bin/bash
# Monitor analysis progress

echo "=== CRASH-VEHICLE LINKAGE PROGRESS ==="
echo ""

# Check if analysis is running
if pgrep -f "run_full_analysis.py" > /dev/null; then
    echo "Status: RUNNING ✓"
else
    echo "Status: NOT RUNNING"
fi

echo ""

# Get latest progress
if [ -f full_analysis.log ]; then
    echo "Latest progress:"
    grep -E "^\[.*Completed" full_analysis.log | tail -1
    echo ""

    # Get match count
    matches=$(grep "Total matches so far:" full_analysis.log | tail -1 | awk '{print $5}')
    echo "Total matches found: $matches"

    # Get time estimate
    time_remaining=$(grep "Estimated time remaining:" full_analysis.log | tail -1 | awk '{print $4, $5}')
    echo "Estimated time remaining: $time_remaining"

    # Count completed files
    completed=$(grep -c "^\[.*Completed" full_analysis.log)
    echo "Files completed: $completed / 113"
else
    echo "Log file not found"
fi

echo ""
echo "To view live progress: tail -f full_analysis.log"
echo "To analyze results: python3 analyze_results.py"