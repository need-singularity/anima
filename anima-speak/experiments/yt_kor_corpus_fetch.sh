#!/bin/bash
# anima-speak/experiments/yt_kor_corpus_fetch.sh
# Fetches Korean audiobook audio from YouTube channels for TTS training
# Usage: yt_kor_corpus_fetch.sh <output_dir> <url1> <url2> ...
set -u
OUT=${1:-/home/aiden/mac_home/dev/anima/training/corpus_yt_ko}
shift
mkdir -p "$OUT"
YTDLP=/home/aiden/bin/tts_tools/yt-dlp
for url in "$@"; do
  echo "=== $url ==="
  "$YTDLP" -x --audio-format wav --audio-quality 0 --max-filesize 100M \
    -o "$OUT/ko_audiobook_%(id)s.%(ext)s" "$url" 2>&1 | tail -3
done
echo ""
echo "--- Downloaded ---"
ls -lh "$OUT"/*.wav | head -20
echo "Total size:"
du -sh "$OUT"

# Recommended channels (single-speaker Korean audiobooks for TTS training):
# https://www.youtube.com/@mintaudiobook      — 민트 오디오북
# https://www.youtube.com/@sdiary-audiobook   — 책읽는S다이어리
# https://www.youtube.com/@aktree             — 아크나
