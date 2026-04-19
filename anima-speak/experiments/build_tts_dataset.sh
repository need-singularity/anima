#!/bin/bash
# Build LJSpeech-style TTS dataset from whisper JSON + source audio
# Usage: build_tts_dataset.sh <dataset_name> <source_audio_dir>
set -u
NAME=${1:-ko_ytcorpus}
SRC=${2:-/home/aiden/mac_home/dev/anima/training/corpus_yt_ko}
OUT="/home/aiden/mac_home/dev/anima/training/corpus_${NAME}"
mkdir -p "$OUT/wavs"
METADATA="$OUT/metadata.csv"
: > "$METADATA"

total_segs=0
total_dur=0
for json in "$SRC"/*_full.json "$SRC"/*.json; do
  [ -f "$json" ] || continue
  # Find matching source audio wav (with original sample rate, not 16k)
  base=$(basename "$json" .json)
  # look for orig wav without _16k suffix
  src_wav="$SRC/${base/_full/}.wav"
  [ -f "$src_wav" ] || src_wav="$SRC/${base}.wav"
  [ -f "$src_wav" ] || { echo "no source wav for $json"; continue; }
  echo "=== $base (src=$src_wav) ==="
  
  # Parse segments and extract chunks
  jq -r '.transcription[] | "\(.offsets.from)|\(.offsets.to)|\(.text)"' "$json" | \
  while IFS='|' read -r from_ms to_ms text; do
    text=$(echo "$text" | sed 's/^ *//;s/ *$//')
    [ -z "$text" ] && continue
    start_s=$(awk "BEGIN {printf \"%.3f\", $from_ms / 1000}")
    dur_s=$(awk "BEGIN {printf \"%.3f\", ($to_ms - $from_ms) / 1000}")
    # Filter: 1-15s duration
    if awk -v d="$dur_s" 'BEGIN {exit !(d < 1 || d > 15)}'; then continue; fi
    # Quality filter: text length reasonable
    tlen=${#text}
    if [ "$tlen" -lt 3 ] || [ "$tlen" -gt 200 ]; then continue; fi
    idx=$(find "$OUT/wavs" -name '*.wav' | wc -l)
    pad=$(printf '%05d' "$idx")
    out_wav="$OUT/wavs/${base}_seg_${pad}.wav"
    # Extract at 22050 Hz mono for TTS training
    ffmpeg -y -loglevel error -i "$src_wav" -ss "$start_s" -t "$dur_s" -ac 1 -ar 22050 -c:a pcm_s16le "$out_wav" 2>/dev/null || continue
    echo "${base}_seg_${pad}|${text}|${dur_s}" >> "$METADATA"
  done
done

echo "--- Dataset built ---"
wc -l "$METADATA"
total_dur=$(awk -F'|' '{s+=$3} END {printf "%.1f", s}' "$METADATA")
echo "Total duration: ${total_dur}s ($(awk -v s="$total_dur" 'BEGIN {printf "%.1f", s/60}') min)"
echo "Output: $OUT"
