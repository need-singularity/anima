#!/usr/bin/env bash
# tool/corpus_shard_recompress.bash — ROI G38: corpus shard tar.zst -22 vs -19
#
# DEFAULT: dry-run. Picks a sample shard (smallest by default — keeps test
# cheap), recompresses it at zstd -22 --ultra --long=27 -T0 to a temp file,
# compares sizes vs current shard, and reports estimated savings. Original
# is never deleted.
#
# --apply: re-encode ALL discovered shards in-place via "atomic swap"
#   (.zst.new written, then mv replaces original). Original sha256 is logged
#   to state/corpus_shard_recompress_log.jsonl for rollback evidence.
#
# Usage:
#   tool/corpus_shard_recompress.bash                       # dry, sample 1 file
#   tool/corpus_shard_recompress.bash --root <dir>          # override search root
#   tool/corpus_shard_recompress.bash --sample-n 3          # try 3 shards (dry)
#   tool/corpus_shard_recompress.bash --apply               # rewrite all shards
#
set -u
ROOT_DEFAULT="$(cd "$(dirname "$0")/.." && pwd)/data/corpus_v2_clean"
CORPUS_ROOT="$ROOT_DEFAULT"
APPLY=0
SAMPLE_N=1
LEVEL_NEW=22
LEVEL_OLD=19  # informational; we don't re-decompress to confirm — we trust shard provenance.
ANIMA_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG="$ANIMA_ROOT/state/corpus_shard_recompress_log.jsonl"
AUDIT_OUT="$ANIMA_ROOT/state/corpus_shard_recompress_last.json"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --apply)    APPLY=1; shift ;;
    --root)     CORPUS_ROOT="$2"; shift 2 ;;
    --sample-n) SAMPLE_N="$2"; shift 2 ;;
    -h|--help)  sed -n '2,22p' "$0"; exit 0 ;;
    *) echo "[corpus_recompress] unknown arg: $1" >&2; exit 2 ;;
  esac
done

mkdir -p "$ANIMA_ROOT/state"
ts() { date -u +%Y-%m-%dT%H:%M:%SZ; }

if ! command -v zstd >/dev/null 2>&1; then
  echo "[corpus_recompress] zstd not installed" >&2
  exit 2
fi

if [[ ! -d "$CORPUS_ROOT" ]]; then
  echo "[corpus_recompress] root missing: $CORPUS_ROOT — exit 0 (nothing to do)"
  printf '{"ts":"%s","root":"%s","verdict":"NOOP","reason":"root_missing"}\n' \
    "$(ts)" "$CORPUS_ROOT" > "$AUDIT_OUT"
  exit 0
fi

# Discover candidate shards (.zst). Skip .new / .tmp.
SHARDS=$(find "$CORPUS_ROOT" -type f -name "*.zst" \
           ! -name "*.new" ! -name "*.tmp.*" 2>/dev/null | sort)
N_TOTAL=$(echo "$SHARDS" | grep -c . || true)
[[ -z "$SHARDS" ]] && N_TOTAL=0

MODE="dry-run"
[[ "$APPLY" -eq 1 ]] && MODE="apply"
echo "[$(ts)] corpus_recompress mode=$MODE root=$CORPUS_ROOT shards=$N_TOTAL level: $LEVEL_OLD → $LEVEL_NEW"

if [[ "$N_TOTAL" -eq 0 ]]; then
  printf '{"ts":"%s","root":"%s","shards_total":0,"verdict":"NOOP"}\n' \
    "$(ts)" "$CORPUS_ROOT" > "$AUDIT_OUT"
  exit 0
fi

# Sample selection: smallest first (dry: SAMPLE_N; apply: all).
if [[ "$APPLY" -eq 0 ]]; then
  TARGETS=$(echo "$SHARDS" | xargs -I{} stat -f '%z {}' {} 2>/dev/null \
              | sort -n | head -n "$SAMPLE_N" | awk '{print $2}')
else
  TARGETS="$SHARDS"
fi

bytes_before_total=0
bytes_after_total=0
processed=0
swapped=0
fails=0

for f in $TARGETS; do
  before=$(stat -f '%z' "$f" 2>/dev/null || echo 0)
  echo ""
  echo "==== $f"
  echo "  before=$before bytes ($(numfmt --to=iec-i --suffix=B $before 2>/dev/null || echo $before))"

  tmp="$f.l${LEVEL_NEW}.new"
  # Decompress → recompress at -22 --ultra --long=27 -T0.
  # We pipe through zstd -dc → zstd -22 to avoid landing the raw on disk.
  if ! zstd -dc "$f" 2>/dev/null | \
       zstd -$LEVEL_NEW --ultra --long=27 -T0 -q -o "$tmp" 2>/dev/null; then
    echo "  [FAIL] recompress error"
    rm -f "$tmp"
    fails=$((fails+1))
    continue
  fi
  after=$(stat -f '%z' "$tmp" 2>/dev/null || echo 0)
  if [[ "$after" -le 0 ]]; then
    echo "  [FAIL] empty output"
    rm -f "$tmp"
    fails=$((fails+1))
    continue
  fi

  delta=$((before - after))
  pct="0"
  if [[ "$before" -gt 0 ]]; then
    pct=$(awk -v b=$before -v a=$after 'BEGIN{printf "%.2f",(b-a)*100.0/b}')
  fi
  echo "  after=$after bytes  delta=$delta  saving=${pct}%"

  bytes_before_total=$((bytes_before_total + before))
  bytes_after_total=$((bytes_after_total + after))
  processed=$((processed + 1))

  if [[ "$APPLY" -eq 1 ]]; then
    # Verify roundtrip integrity: sha256(decompress(new)) == sha256(decompress(old)).
    sha_old=$(zstd -dc "$f"   2>/dev/null | shasum -a 256 | awk '{print $1}')
    sha_new=$(zstd -dc "$tmp" 2>/dev/null | shasum -a 256 | awk '{print $1}')
    if [[ "$sha_old" != "$sha_new" || -z "$sha_old" ]]; then
      echo "  [VERIFY-FAIL] sha mismatch — keeping original"
      rm -f "$tmp"
      fails=$((fails+1))
      printf '{"ts":"%s","path":"%s","action":"verify_failed","sha_old":"%s","sha_new":"%s"}\n' \
        "$(ts)" "$f" "$sha_old" "$sha_new" >> "$LOG"
      continue
    fi
    sha_zst_old=$(shasum -a 256 "$f" | awk '{print $1}')
    if mv -f "$tmp" "$f"; then
      swapped=$((swapped + 1))
      echo "  [SWAPPED] verified (sha-decompressed match)"
      printf '{"ts":"%s","path":"%s","action":"swapped","level_new":%d,"sha_zst_old":"%s","bytes_before":%d,"bytes_after":%d}\n' \
        "$(ts)" "$f" "$LEVEL_NEW" "$sha_zst_old" "$before" "$after" >> "$LOG"
    else
      echo "  [SWAP-FAIL] mv error — keeping original"
      rm -f "$tmp"
      fails=$((fails+1))
    fi
  else
    rm -f "$tmp"
  fi
done

total_pct="0"
if [[ "$bytes_before_total" -gt 0 ]]; then
  total_pct=$(awk -v b=$bytes_before_total -v a=$bytes_after_total \
                'BEGIN{printf "%.2f",(b-a)*100.0/b}')
fi

cat > "$AUDIT_OUT" <<EOF
{
  "ts": "$(ts)",
  "roi_item": "G38",
  "mode": "$MODE",
  "root": "$CORPUS_ROOT",
  "shards_total": $N_TOTAL,
  "shards_processed": $processed,
  "shards_swapped": $swapped,
  "shards_failed": $fails,
  "level_old": $LEVEL_OLD,
  "level_new": $LEVEL_NEW,
  "bytes_before_total": $bytes_before_total,
  "bytes_after_total": $bytes_after_total,
  "bytes_saved": $((bytes_before_total - bytes_after_total)),
  "saving_pct": "$total_pct",
  "verdict": "$([[ $processed -gt 0 ]] && echo OK || echo NOOP)"
}
EOF

echo ""
echo "[$(ts)] DONE mode=$MODE processed=$processed swapped=$swapped failed=$fails saving=${total_pct}%"
exit 0
