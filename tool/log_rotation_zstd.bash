#!/usr/bin/env bash
# tool/log_rotation_zstd.bash — ROI G40: weekly log rotation → .zst
#
# Compresses log files older than --age-days (default 7) under:
#   - /tmp/*.log
#   - $ANIMA_ROOT/logs/*.log
#   - $ANIMA_ROOT/state/*.log $ANIMA_ROOT/state/*.jsonl  (only the *.log/.jsonl
#     files that look like rotating tool logs — never structural state JSON)
#
# DEFAULT: dry. Lists what would be compressed + total estimated saving.
# --apply: actually compress (zstd -19 -T0), atomically rename to .zst,
#          then remove the source ONLY if compressed file verifies.
#
# Cron-style integration (weekly):
#   crontab line:  15 4 * * 0 /Users/ghost/core/anima/tool/log_rotation_zstd.bash --apply
#
# Usage:
#   tool/log_rotation_zstd.bash                 # dry
#   tool/log_rotation_zstd.bash --apply         # really compress
#   tool/log_rotation_zstd.bash --age-days 14   # only files older than 14d
#   tool/log_rotation_zstd.bash --extra-glob '/var/log/anima/*.log'
#
set -u
ANIMA_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APPLY=0
AGE_DAYS=7
EXTRA_GLOB=""
LOG_OUT="$ANIMA_ROOT/state/log_rotation_zstd_log.jsonl"
AUDIT_OUT="$ANIMA_ROOT/state/log_rotation_zstd_last.json"

SELFTEST=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --apply)       APPLY=1; shift ;;
    --age-days)    AGE_DAYS="$2"; shift 2 ;;
    --extra-glob)  EXTRA_GLOB="$2"; shift 2 ;;
    --selftest)    SELFTEST=1; shift ;;
    -h|--help)     sed -n '2,22p' "$0"; exit 0 ;;
    *) echo "[log_rotation_zstd] unknown arg: $1" >&2; exit 2 ;;
  esac
done

if [[ "$SELFTEST" -eq 1 ]]; then
  # MINIMAL SELFTEST: parse-clean + 1 invariant (default age safe + APPLY=0).
  echo "── log_rotation_zstd selftest ──"
  bash -n "$0" || { echo "  parse FAIL"; exit 1; }
  if [[ "$APPLY" -ne 0 ]]; then echo "  invariant FAIL: --selftest must not co-occur with --apply"; exit 1; fi
  if [[ "$AGE_DAYS" -lt 1 ]]; then echo "  invariant FAIL: AGE_DAYS=$AGE_DAYS < 1 (would compress live logs)"; exit 1; fi
  echo "  parse: PASS"
  echo "  invariant: APPLY=0 default, AGE_DAYS=$AGE_DAYS >= 1"
  echo "  SELFTEST PASS"
  exit 0
fi

mkdir -p "$ANIMA_ROOT/state"
ts() { date -u +%Y-%m-%dT%H:%M:%SZ; }

if ! command -v zstd >/dev/null 2>&1; then
  echo "[log_rotation_zstd] zstd missing — exit 0 noop"
  printf '{"ts":"%s","verdict":"NOOP","reason":"zstd_missing"}\n' "$(ts)" > "$AUDIT_OUT"
  exit 0
fi

MODE="dry-run"
[[ "$APPLY" -eq 1 ]] && MODE="apply"
echo "[$(ts)] log_rotation_zstd mode=$MODE age_days=$AGE_DAYS"

# Build candidate list. Each candidate must:
#   - be a regular file
#   - end in .log OR .jsonl
#   - NOT already end in .zst
#   - mtime older than $AGE_DAYS days
TMPLIST=$(mktemp)
{
  find /tmp -maxdepth 1 -type f \( -name "*.log" -o -name "*.jsonl" \) \
       -mtime "+${AGE_DAYS}" 2>/dev/null
  find "$ANIMA_ROOT/logs" -type f \( -name "*.log" -o -name "*.jsonl" \) \
       -mtime "+${AGE_DAYS}" 2>/dev/null
  find "$ANIMA_ROOT/state" -maxdepth 1 -type f -name "*.log" \
       -mtime "+${AGE_DAYS}" 2>/dev/null
  if [[ -n "$EXTRA_GLOB" ]]; then
    # shellcheck disable=SC2086
    for f in $EXTRA_GLOB; do
      [[ -f "$f" ]] && find "$f" -mtime "+${AGE_DAYS}" 2>/dev/null
    done
  fi
} | grep -v '\.zst$' | sort -u > "$TMPLIST"

N_TOTAL=$(wc -l < "$TMPLIST" | tr -d ' ')
echo "[$(ts)] candidates=$N_TOTAL"

bytes_before_total=0
bytes_after_total=0
processed=0
failed=0

while IFS= read -r f; do
  [[ -z "$f" || ! -f "$f" ]] && continue
  before=$(stat -f '%z' "$f" 2>/dev/null || echo 0)
  out="${f}.zst"
  if [[ -f "$out" ]]; then
    echo "  [SKIP] target exists: $out"
    continue
  fi

  if [[ "$APPLY" -eq 0 ]]; then
    # Estimate compression at -19 by sampling first 1 MiB.
    head -c 1048576 "$f" 2>/dev/null | zstd -19 -T0 -q -o /tmp/.lr_sample.zst 2>/dev/null
    sample_after=$(stat -f '%z' /tmp/.lr_sample.zst 2>/dev/null || echo 0)
    sample_before=$(head -c 1048576 "$f" 2>/dev/null | wc -c | tr -d ' ')
    rm -f /tmp/.lr_sample.zst
    est_after=0
    if [[ "$sample_before" -gt 0 && "$sample_after" -gt 0 ]]; then
      est_after=$(awk -v b=$before -v sb=$sample_before -v sa=$sample_after \
                    'BEGIN{printf "%d", b * sa / sb}')
    fi
    echo "  [DRY] $f  before=$before  est_after=$est_after"
    bytes_before_total=$((bytes_before_total + before))
    bytes_after_total=$((bytes_after_total + est_after))
    processed=$((processed + 1))
    continue
  fi

  # APPLY: compress in-place, verify, then remove source.
  tmp="${f}.zst.tmp.$$"
  if ! zstd -19 -T0 -q -o "$tmp" "$f" 2>/dev/null; then
    echo "  [FAIL] zstd error for $f"
    rm -f "$tmp"
    failed=$((failed + 1))
    continue
  fi
  # Verify roundtrip: sha256(decompress(tmp)) == sha256(original)
  sha_orig=$(shasum -a 256 "$f" | awk '{print $1}')
  sha_round=$(zstd -dc "$tmp" 2>/dev/null | shasum -a 256 | awk '{print $1}')
  if [[ "$sha_orig" != "$sha_round" || -z "$sha_orig" ]]; then
    echo "  [VERIFY-FAIL] $f — keeping original"
    rm -f "$tmp"
    failed=$((failed + 1))
    printf '{"ts":"%s","path":"%s","action":"verify_failed"}\n' "$(ts)" "$f" >> "$LOG_OUT"
    continue
  fi
  if ! mv -f "$tmp" "$out"; then
    echo "  [MV-FAIL] $f"
    rm -f "$tmp"
    failed=$((failed + 1))
    continue
  fi
  after=$(stat -f '%z' "$out" 2>/dev/null || echo 0)
  rm -f "$f"
  bytes_before_total=$((bytes_before_total + before))
  bytes_after_total=$((bytes_after_total + after))
  processed=$((processed + 1))
  echo "  [OK] $f → $out  ($before → $after)"
  printf '{"ts":"%s","path":"%s","action":"compressed","bytes_before":%d,"bytes_after":%d}\n' \
    "$(ts)" "$f" "$before" "$after" >> "$LOG_OUT"
done < "$TMPLIST"
rm -f "$TMPLIST"

saved=$((bytes_before_total - bytes_after_total))
pct="0"
if [[ "$bytes_before_total" -gt 0 ]]; then
  pct=$(awk -v b=$bytes_before_total -v a=$bytes_after_total \
         'BEGIN{printf "%.2f",(b-a)*100.0/b}')
fi

cat > "$AUDIT_OUT" <<EOF
{
  "ts": "$(ts)",
  "roi_item": "G40",
  "mode": "$MODE",
  "age_days": $AGE_DAYS,
  "candidates": $N_TOTAL,
  "processed": $processed,
  "failed": $failed,
  "bytes_before_total": $bytes_before_total,
  "bytes_after_total": $bytes_after_total,
  "bytes_saved": $saved,
  "saving_pct": "$pct",
  "verdict": "$([[ $processed -gt 0 ]] && echo OK || echo NOOP)"
}
EOF

echo ""
echo "[$(ts)] DONE mode=$MODE processed=$processed failed=$failed saved=$saved bytes (${pct}%)"
exit 0
