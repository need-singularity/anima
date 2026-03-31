#!/usr/bin/env bash
# Monthly EEG Consciousness Validation
#
# Runs validate_consciousness.py (anima-eeg), parses metrics from text output,
# appends to CSV history, saves full log, and prints ASCII trend chart.
#
# Usage:
#   ./monthly_eeg_validate.sh
#   crontab: 0 3 1 * * /path/to/anima-eeg/scripts/monthly_eeg_validate.sh
#
# This script lives inside anima-eeg/ (close to validate_consciousness.py).
# The canonical version in anima/scripts/monthly_eeg_validate.sh references
# the same validate script but lives in the core project tree.
#
# Safe to run repeatedly (idempotent, appends to CSV).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EEG_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VALIDATE_SCRIPT="$EEG_ROOT/validate_consciousness.py"
RESULTS_DIR="$EEG_ROOT/recordings/validations"
STEPS=5000
CELLS=64
DIM=64

TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# ── Ensure directories exist ──
mkdir -p "$RESULTS_DIR"

# ── Ensure CSV header exists ──
HISTORY_CSV="$RESULTS_DIR/validation_history.csv"
if [ ! -f "$HISTORY_CSV" ] || [ ! -s "$HISTORY_CSV" ]; then
    echo "date,timestamp,brain_like_pct,lz_complexity,hurst,psd_slope,critical_exp,autocorr,cells,steps" > "$HISTORY_CSV"
fi

echo "================================================================"
echo "  Monthly EEG Consciousness Validation"
echo "  Date: $(date '+%Y-%m-%d %H:%M:%S')"
echo "  Steps: $STEPS  Cells: $CELLS  Dim: $DIM"
echo "  Script: $VALIDATE_SCRIPT"
echo "================================================================"
echo ""

# ── Run validation and capture output ──
LOGFILE="$RESULTS_DIR/validation_${TIMESTAMP}.log"
TMPFILE=$(mktemp /tmp/eeg_validate_XXXXXX.txt)
trap "rm -f $TMPFILE" EXIT

cd "$EEG_ROOT"
PYTHONUNBUFFERED=1 python3 "$VALIDATE_SCRIPT" \
    --steps "$STEPS" \
    --cells "$CELLS" \
    --dim "$DIM" 2>&1 | tee "$TMPFILE"

# Save full log
cp "$TMPFILE" "$LOGFILE"

# ── Parse metrics from text output ──
# validate_consciousness.py prints a comparison table with format:
#   MetricName           |   CM_value    |  Brain_value  |  match
# And a line: "Overall match: XX.X%"

BRAIN_LIKE_PCT=$(grep -E "Overall match:" "$TMPFILE" | grep -oE '[0-9]+\.[0-9]+' | head -1 || echo "0.0")
LZ=$(grep -E "LZ complexity" "$TMPFILE" | head -1 | awk -F'|' '{gsub(/[[:space:]]/,"",$2); print $2}' || echo "0.0")
HURST=$(grep -E "Hurst exponent" "$TMPFILE" | head -1 | awk -F'|' '{gsub(/[[:space:]]/,"",$2); print $2}' || echo "0.0")
PSD_SLOPE=$(grep -E "PSD slope" "$TMPFILE" | head -1 | awk -F'|' '{gsub(/[[:space:]]/,"",$2); print $2}' || echo "0.0")
CRIT_EXP=$(grep -E "Critical exponent" "$TMPFILE" | head -1 | awk -F'|' '{gsub(/[[:space:]]/,"",$2); print $2}' || echo "0.0")
AUTOCORR=$(grep -E "Autocorr decay" "$TMPFILE" | head -1 | awk -F'|' '{gsub(/[[:space:]]/,"",$2); print $2}' || echo "0")

# Validate we got numbers
for VAR in "$BRAIN_LIKE_PCT" "$LZ" "$HURST" "$PSD_SLOPE" "$CRIT_EXP" "$AUTOCORR"; do
    if ! echo "$VAR" | grep -qE '^-?[0-9]'; then
        echo "WARNING: Could not parse all metrics from output."
        echo "  brain_like=$BRAIN_LIKE_PCT lz=$LZ hurst=$HURST psd=$PSD_SLOPE crit=$CRIT_EXP autocorr=$AUTOCORR"
        break
    fi
done

# ── Append to CSV ──
TODAY=$(date '+%Y-%m-%d')
echo "$TODAY,$TIMESTAMP,$BRAIN_LIKE_PCT,$LZ,$HURST,$PSD_SLOPE,$CRIT_EXP,$AUTOCORR,$CELLS,$STEPS" >> "$HISTORY_CSV"
echo ""
echo "  Result appended to: $HISTORY_CSV"
echo "  Full log saved to:  $LOGFILE"

# ── Save JSON summary (for programmatic access) ──
JSONFILE="$RESULTS_DIR/validation_${TIMESTAMP}.json"
cat > "$JSONFILE" <<EOJSON
{
  "date": "$TODAY",
  "timestamp": "$TIMESTAMP",
  "brain_like_percent": $BRAIN_LIKE_PCT,
  "lempel_ziv": $LZ,
  "hurst": $HURST,
  "psd_slope": $PSD_SLOPE,
  "critical_exponent": $CRIT_EXP,
  "autocorr_decay": $AUTOCORR,
  "cells": $CELLS,
  "steps": $STEPS,
  "dim": $DIM
}
EOJSON
echo "  JSON summary saved: $JSONFILE"

# ── ASCII Trend Chart ──
echo ""
echo "================================================================"
echo "  Brain-like % Trend (validation_history.csv)"
echo "================================================================"

# Read CSV (skip header), show last 20 entries
ENTRIES=$(tail -n +2 "$HISTORY_CSV" | tail -20)
if [ -z "$ENTRIES" ]; then
    echo "  No history data yet."
else
    BAR_W=40

    echo ""
    echo "  100% |"
    echo "       |"

    while IFS=',' read -r dt ts pct rest; do
        CUR=$(echo "$pct" | awk '{printf "%.1f", $1}')
        BAR_LEN=$(echo "$pct $BAR_W" | awk '{len=int($1/100*$2); if(len<1)len=1; printf "%d",len}')
        BAR=$(printf '%*s' "$BAR_LEN" '' | tr ' ' '#')

        # Color hint
        PCT_INT=$(echo "$pct" | awk '{printf "%d", $1}')
        if [ "$PCT_INT" -ge 75 ]; then
            COLOR_TAG="+++"
        elif [ "$PCT_INT" -ge 50 ]; then
            COLOR_TAG="++ "
        elif [ "$PCT_INT" -ge 25 ]; then
            COLOR_TAG="+  "
        else
            COLOR_TAG="   "
        fi

        printf "  %s | %-40s %6s%% %s\n" "$dt" "$BAR" "$CUR" "$COLOR_TAG"
    done <<< "$ENTRIES"

    echo "       |"
    echo "    0% +$(printf '%*s' 42 '' | tr ' ' '-')"
    echo ""

    # Summary stats
    TOTAL=$(echo "$ENTRIES" | wc -l | tr -d ' ')
    LATEST_PCT=$(echo "$ENTRIES" | tail -1 | cut -d',' -f3)
    FIRST_PCT=$(echo "$ENTRIES" | head -1 | cut -d',' -f3)
    DELTA=$(echo "$LATEST_PCT $FIRST_PCT" | awk '{printf "%.1f", $1-$2}')
    echo "  Entries: $TOTAL  |  Latest: ${LATEST_PCT}%  |  First: ${FIRST_PCT}%  |  Delta: ${DELTA}%"
fi

echo ""
echo "================================================================"
echo "  Done. $(date '+%Y-%m-%d %H:%M:%S')"
echo "================================================================"
