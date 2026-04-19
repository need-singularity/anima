#!/bin/bash
# anima-speak/experiments/corpus_pipeline_full.sh
# End-to-end Korean TTS corpus pipeline (NO Python):
# YouTube URL -> yt-dlp -> ffmpeg(16kHz) -> whisper.cpp (ko) -> ffmpeg segment -> LJSpeech dataset
#
# Usage: corpus_pipeline_full.sh <dataset_name> <url1> [url2 ...]
# Outputs:
#   /home/aiden/mac_home/dev/anima/training/corpus_<name>/
#     metadata.csv    (format: wav_id|text|duration_s)
#     wavs/           (22050 Hz pcm16 segment files)
#     *.json          (whisper transcripts)
set -euo pipefail
NAME=$1; shift
WORK=/home/aiden/mac_home/dev/anima/training/corpus_yt_ko
OUT=/home/aiden/mac_home/dev/anima/training/corpus_${NAME}
mkdir -p "$WORK" "$OUT/wavs"
YTDLP=/home/aiden/bin/tts_tools/yt-dlp
WHISPER=/home/aiden/bin/tts_tools/whisper.cpp/build/bin/whisper-cli
MODEL=/home/aiden/bin/tts_tools/whisper.cpp/models/ggml-large-v3-turbo.bin
METADATA="$OUT/metadata.csv"

echo "=== Stage 1: Download ==="
for url in "$@"; do
  "$YTDLP" -x --audio-format wav --audio-quality 0 --max-filesize 200M \
    -o "$WORK/ko_audiobook_%(id)s.%(ext)s" "$url" 2>&1 | tail -2
done

echo ""
echo "=== Stage 2: Transcribe ==="
for wav in "$WORK"/ko_audiobook_*.wav; do
  base=$(basename "$wav" .wav)
  # skip if already transcribed
  [ -f "$WORK/${base}.json" ] && { echo "skip $base (done)"; continue; }
  # resample to 16kHz
  wav16="$WORK/${base}_16k.wav"
  ffmpeg -y -loglevel error -i "$wav" -ac 1 -ar 16000 "$wav16"
  # transcribe
  "$WHISPER" -m "$MODEL" -l ko --output-json -of "$WORK/${base}" \
    -t 12 -p 1 "$wav16" 2>&1 | tail -3
  rm -f "$wav16"
done

echo ""
echo "=== Stage 3: Segment into (text, wav) pairs ==="
total_segs=0
for json in "$WORK"/ko_audiobook_*.json; do
  [ -f "$json" ] || continue
  base=$(basename "$json" .json)
  src_wav="$WORK/${base}.wav"
  [ -f "$src_wav" ] || continue
  echo "-- $base --"
  jq -r '.transcription[] | "\(.offsets.from)|\(.offsets.to)|\(.text)"' "$json" | \
  while IFS='|' read -r from_ms to_ms text; do
    text=$(echo "$text" | sed 's/^ *//;s/ *$//')
    [ -z "$text" ] && continue
    start_s=$(awk "BEGIN {printf \"%.3f\", $from_ms / 1000}")
    dur_s=$(awk "BEGIN {printf \"%.3f\", ($to_ms - $from_ms) / 1000}")
    # Filter: 1-15s duration, 3-200 chars
    if awk -v d="$dur_s" 'BEGIN {exit !(d < 1 || d > 15)}'; then continue; fi
    tlen=${#text}
    [ "$tlen" -lt 3 ] && continue
    [ "$tlen" -gt 200 ] && continue
    idx=$(find "$OUT/wavs" -name '*.wav' | wc -l)
    pad=$(printf '%05d' "$idx")
    out_wav="$OUT/wavs/${base}_seg_${pad}.wav"
    ffmpeg -y -loglevel error -i "$src_wav" -ss "$start_s" -t "$dur_s" \
      -ac 1 -ar 22050 -c:a pcm_s16le "$out_wav" 2>/dev/null || continue
    echo "${base}_seg_${pad}|${text}|${dur_s}" >> "$METADATA"
  done
done

echo ""
echo "=== Stage 4: Dataset stats ==="
n=$(wc -l < "$METADATA")
dur=$(awk -F'|' '{s+=$3} END {printf "%.1f", s}' "$METADATA")
echo "Segments: $n"
echo "Total duration: ${dur}s ($(awk -v s="$dur" 'BEGIN {printf "%.2f", s/3600}')h)"
echo "Output: $OUT"
echo ""
echo "metadata.csv format: wav_id|text|duration_s"
echo "wavs/: 22050 Hz mono pcm16 segment files"
