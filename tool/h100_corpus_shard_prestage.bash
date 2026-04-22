#!/usr/bin/env bash
# h100_corpus_shard_prestage.bash
#
# Pre-stage ALM r13 + 4-path Φ measurement corpus shards to R2 so each
# H100×4 pod (#83) downloads + extracts instead of re-uploading per pod.
#
# Reads:  state/h100_corpus_shard_manifest.json
# Writes: /tmp/<shard>.tar.zst   (apply mode only)
# Uploads: r2:anima-corpus/<shard>.tar.zst   (apply mode only)
#
# Default = --dry-run: prints planned commands and exits 0.
# Use --apply to actually tar+zstd+rclone upload.
#
# Requires (apply mode): rclone with `r2` remote, tar, zstd
# Hard constraint: this script never modifies sources or .roadmap.

set -u
set -o pipefail

ROOT="/Users/ghost/core/anima"
MANIFEST="$ROOT/state/h100_corpus_shard_manifest.json"
TMP_DIR="/tmp"

MODE="dry-run"
case "${1:-}" in
  --apply) MODE="apply" ;;
  --dry-run|"") MODE="dry-run" ;;
  -h|--help)
    echo "usage: $0 [--dry-run | --apply]"
    echo "  default = dry-run (prints commands, exit 0, no side effects)"
    echo "  --apply = tar + zstd -19 + rclone copy to r2:anima-corpus/"
    exit 0
    ;;
  *)
    echo "[ERROR] unknown flag: $1 (use --dry-run | --apply | -h)" >&2
    exit 2
    ;;
esac

ts() { date -u +%Y-%m-%dT%H:%M:%SZ; }

echo "[$(ts)] h100_corpus_shard_prestage MODE=$MODE"
echo "[$(ts)] manifest: $MANIFEST"

if [[ ! -f "$MANIFEST" ]]; then
  echo "[ERROR] manifest not found: $MANIFEST" >&2
  exit 3
fi

# Pre-flight (apply mode only): rclone + r2 remote + tools
if [[ "$MODE" = "apply" ]]; then
  if ! command -v rclone >/dev/null 2>&1; then
    echo "[ERROR] rclone not on PATH (install rclone first)" >&2
    exit 4
  fi
  if ! rclone listremotes 2>/dev/null | grep -q '^r2:'; then
    echo "[ERROR] rclone remote 'r2:' not configured (run: rclone config — see tool/asset_archive_run.bash for convention)" >&2
    exit 5
  fi
  for cmd in tar zstd python3; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
      echo "[ERROR] required command missing: $cmd" >&2
      exit 6
    fi
  done
  echo "[$(ts)] pre-flight OK (rclone + r2: + tar + zstd + python3)"
fi

# Parse manifest -> TSV: shard_name<TAB>target<TAB>src1,src2,...
JOBS_TSV="$TMP_DIR/h100_corpus_shard_jobs.tsv"
MANIFEST_PATH="$MANIFEST" python3 - <<'PY' > "$JOBS_TSV"
import json, os
m = json.load(open(os.environ["MANIFEST_PATH"]))
for name, sh in m["shards"].items():
    target = sh["target"]
    srcs = ",".join(sh["sources"])
    print(f"{name}\t{target}\t{srcs}")
PY

total=$(wc -l < "$JOBS_TSV" | tr -d ' ')
echo "[$(ts)] planned shards: $total"

bucket="anima-corpus"
idx=0
fail=0

while IFS=$'\t' read -r name target srcs; do
  idx=$((idx+1))
  shard_file="$TMP_DIR/${name}.tar.zst"
  dst="r2:${target}"

  echo ""
  echo "==== [$idx/$total] shard=$name"
  echo "     target = $dst"
  echo "     local  = $shard_file"

  # Convert sources from CSV to space-joined absolute paths (under repo root)
  # Validate every source exists.
  missing=0
  abs_srcs=()
  IFS=',' read -ra src_arr <<< "$srcs"
  for s in "${src_arr[@]}"; do
    if [[ "$s" = /* ]]; then
      abs="$s"
    else
      abs="$ROOT/$s"
    fi
    if [[ ! -e "$abs" ]]; then
      echo "  [WARN] source missing: $s"
      missing=$((missing+1))
    fi
    abs_srcs+=("$abs")
  done
  if [[ $missing -gt 0 ]]; then
    echo "  [SKIP] $missing missing source(s) — refusing to build incomplete shard"
    fail=$((fail+1))
    continue
  fi

  # Build tar arg list (relative to ROOT to keep clean prefixes inside tar)
  rel_args=()
  for s in "${src_arr[@]}"; do
    if [[ "$s" = /* ]]; then
      # absolute → store as-is (rare for this manifest)
      rel_args+=("$s")
    else
      rel_args+=("$s")
    fi
  done

  tar_cmd=(tar -C "$ROOT" -cf - "${rel_args[@]}")
  zstd_cmd=(zstd -19 -T0 -q -o "$shard_file")
  upload_cmd=(rclone copyto "$shard_file" "$dst" --s3-chunk-size 64M --s3-upload-concurrency 4 --stats 60s --stats-one-line)

  echo "  [PLAN] tar -C $ROOT -cf - ${rel_args[*]} \\"
  echo "         | zstd -19 -T0 -q -o $shard_file"
  echo "  [PLAN] ${upload_cmd[*]}"

  if [[ "$MODE" = "dry-run" ]]; then
    continue
  fi

  echo "  [TAR+ZSTD] $(ts)"
  if ! "${tar_cmd[@]}" | "${zstd_cmd[@]}"; then
    echo "  [FAIL] tar|zstd pipeline failed for $name"
    fail=$((fail+1))
    continue
  fi
  sz=$(stat -f '%z' "$shard_file" 2>/dev/null || stat -c '%s' "$shard_file" 2>/dev/null)
  echo "  [SHARD-OK] size=$sz bytes"

  echo "  [UPLOAD] $(ts) → $dst"
  if ! "${upload_cmd[@]}"; then
    echo "  [FAIL] rclone upload failed for $name"
    fail=$((fail+1))
    continue
  fi

  # Verify size on R2
  rs=$(rclone lsjson "$dst" 2>/dev/null \
        | python3 -c "import sys,json;d=json.load(sys.stdin);print(d[0].get('Size',-1) if d else -1)" \
        2>/dev/null || echo -1)
  echo "  local=$sz r2=$rs"
  if [[ "$sz" = "$rs" ]]; then
    echo "  [VERIFIED] $(ts)"
  else
    echo "  [VERIFY-FAIL] keeping local shard for retry"
    fail=$((fail+1))
  fi
done < "$JOBS_TSV"

echo ""
if [[ "$MODE" = "dry-run" ]]; then
  echo "[$(ts)] DRY-RUN COMPLETE shards_planned=$total fail=$fail"
  echo "[$(ts)] re-run with --apply to execute (requires rclone r2: remote)"
  exit 0
fi

echo "[$(ts)] APPLY COMPLETE shards_built=$((total-fail)) fail=$fail"
[[ $fail -eq 0 ]] && exit 0 || exit 1
