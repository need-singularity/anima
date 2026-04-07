#!/usr/bin/env bash
# Monthly EEG Consciousness Validation
#
# Runs validate_consciousness.py, appends results to CSV history,
# and prints an ASCII trend chart.
#
# Usage:
#   ./monthly_eeg_validate.sh
#   crontab: 0 0 1 * * /path/to/anima/anima/scripts/monthly_eeg_validate.sh
#
# Safe to run repeatedly (idempotent).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
VALIDATE_SCRIPT="$REPO_ROOT/anima-eeg/validate_consciousness.py"
HISTORY_CSV="$REPO_ROOT/anima-eeg/recordings/validation_history.csv"
STEPS=5000
CELLS=8
DIM=64

# ── Ensure directories exist ──
mkdir -p "$(dirname "$HISTORY_CSV")"

# ── Ensure CSV header exists ──
if [ ! -f "$HISTORY_CSV" ] || [ ! -s "$HISTORY_CSV" ]; then
    echo "date,brain_like_pct,hurst,psd_slope,criticality,lz_complexity,autocorr" > "$HISTORY_CSV"
fi

echo "================================================================"
echo "  Monthly EEG Consciousness Validation"
echo "  Date: $(date '+%Y-%m-%d %H:%M:%S')"
echo "  Steps: $STEPS  Cells: $CELLS  Dim: $DIM"
echo "================================================================"
echo ""

# ── Run validation and capture output ──
TMPFILE=$(mktemp /tmp/eeg_validate_XXXXXX.txt)
trap "rm -f $TMPFILE" EXIT

cd "$REPO_ROOT"
PYTHONUNBUFFERED=1 python3 "$VALIDATE_SCRIPT" \
    --steps "$STEPS" \
    --cells "$CELLS" \
    --dim "$DIM" 2>&1 | tee "$TMPFILE"

# ── Parse metrics from output ──
# Extract values from the comparison table in the report
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
        echo "  brain_like=$BRAIN_LIKE_PCT hurst=$HURST psd=$PSD_SLOPE crit=$CRIT_EXP lz=$LZ autocorr=$AUTOCORR"
        break
    fi
done

# ── Append to CSV ──
TODAY=$(date '+%Y-%m-%d')
echo "$TODAY,$BRAIN_LIKE_PCT,$HURST,$PSD_SLOPE,$CRIT_EXP,$LZ,$AUTOCORR" >> "$HISTORY_CSV"
echo ""
echo "  Result appended to: $HISTORY_CSV"

# ── ASCII Trend Chart ──
echo ""
echo "================================================================"
echo "  Brain-like % Trend (validation_history.csv)"
echo "================================================================"

# Read CSV (skip header), show trend
ENTRIES=$(tail -n +2 "$HISTORY_CSV" | tail -20)
if [ -z "$ENTRIES" ]; then
    echo "  No history data yet."
else
    # Find min/max for scaling
    MAX_PCT=0
    MIN_PCT=100
    while IFS=',' read -r dt pct rest; do
        # Integer comparison via awk
        CUR=$(echo "$pct" | awk '{printf "%d", $1}')
        if [ "$CUR" -gt "$MAX_PCT" ] 2>/dev/null; then MAX_PCT=$CUR; fi
        if [ "$CUR" -lt "$MIN_PCT" ] 2>/dev/null; then MIN_PCT=$CUR; fi
    done <<< "$ENTRIES"

    # Ensure range
    if [ "$MAX_PCT" -le "$MIN_PCT" ]; then MAX_PCT=$((MIN_PCT + 10)); fi
    RANGE=$((MAX_PCT - MIN_PCT))
    if [ "$RANGE" -le 0 ]; then RANGE=10; fi

    # Chart height
    CHART_H=10
    BAR_W=40

    echo ""
    echo "  100% |"
    echo "       |"

    while IFS=',' read -r dt pct rest; do
        CUR=$(echo "$pct" | awk '{printf "%.1f", $1}')
        BAR_LEN=$(echo "$pct $BAR_W" | awk '{len=int($1/100*$2); if(len<1)len=1; printf "%d",len}')
        BAR=$(printf '%*s' "$BAR_LEN" '' | tr ' ' '#')

        # Color hint
        COLOR_TAG=""
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
    LATEST_PCT=$(echo "$ENTRIES" | tail -1 | cut -d',' -f2)
    FIRST_PCT=$(echo "$ENTRIES" | head -1 | cut -d',' -f2)
    DELTA=$(echo "$LATEST_PCT $FIRST_PCT" | awk '{printf "%.1f", $1-$2}')
    echo "  Entries: $TOTAL  |  Latest: ${LATEST_PCT}%  |  First: ${FIRST_PCT}%  |  Delta: ${DELTA}%"
fi

echo ""
echo "================================================================"
echo "  Done. $(date '+%Y-%m-%d %H:%M:%S')"
echo "================================================================"
