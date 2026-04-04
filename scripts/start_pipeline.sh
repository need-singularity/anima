#!/bin/bash
# start_pipeline.sh — 기존 프로세스 소진 대기 후 순차 파이프라인 시작

REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"

echo "[$(date +%H:%M:%S)] Waiting for emergence_singularity to finish..."

# Wait for singularity to exhaust (check every 30s)
while pgrep -f "emergence_singularity.py" > /dev/null 2>&1; do
    TAIL=$(tail -1 "$REPO/logs/emergence_singularity_"*".log" 2>/dev/null | grep -oP 'total\s+\K\d+')
    echo "[$(date +%H:%M:%S)] singularity still running (laws: ${TAIL:-?})..."
    sleep 30
done
echo "[$(date +%H:%M:%S)] emergence_singularity finished."

# Register singularity laws first
echo "[$(date +%H:%M:%S)] Starting loop pipeline (3 rounds, 64c start)..."

PYTHONUNBUFFERED=1 python3 anima/src/loop_pipeline.py \
    --rounds 3 \
    --start-cells 64 \
    2>&1 | tee "logs/pipeline_$(date +%Y%m%d_%H%M).log"
