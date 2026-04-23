#!/usr/bin/env bash
# h100_corpus_shard_prestage.bash
#
# Pre-stage ALM r13 + 4-path Φ measurement corpus shards to R2 so each
# H100×4 pod (#83) downloads + extracts instead of re-uploading per pod.
#
# Reads:  state/h100_corpus_shard_manifest.json
# Writes: /tmp/<shard>.tar.zst                                        (apply mode)
# Writes: state/h100_corpus_shard_progress.jsonl                       (apply mode)
# Writes: state/h100_corpus_shard_completion.json                      (apply mode)
# Uploads: r2:anima-corpus/<shard>.tar.zst                             (apply mode)
#
# Default = --dry-run: prints planned commands and exits 0.
# Use --apply to actually tar+zstd+rclone upload.
# Use --status to display per-shard progress from the jsonl ledger.
#
# RESUME / IDEMPOTENCY
#   --apply consults state/h100_corpus_shard_progress.jsonl: shards marked
#   status=done are skipped. R2-side: a successful prior upload is detected
#   by `rclone lsjson` returning a size matching the local shard (if local
#   shard cached at /tmp) — the upload step is then skipped.
#
# Requires (apply mode): rclone with `r2` remote, tar, zstd, python3
# Hard constraint: this script never modifies sources or .roadmap.
#
# EXIT
#   0 = dry-run printed OK / apply succeeded (all shards done or skipped)
#   1 = apply finished with one or more failures
#   2 = bad arg
#   3 = manifest not found
#   4 = rclone missing (apply only)
#   5 = rclone r2 remote not configured (apply only)
#   6 = required tool missing: tar / zstd / python3 (apply only)

set -euo pipefail

ROOT="/Users/ghost/core/anima"
MANIFEST="$ROOT/state/h100_corpus_shard_manifest.json"
PROGRESS_JSONL="$ROOT/state/h100_corpus_shard_progress.jsonl"
COMPLETION_JSON="$ROOT/state/h100_corpus_shard_completion.json"
TMP_DIR="${CORPUS_SHARD_STAGE:-/tmp}"
R2_REMOTE="${RCLONE_CORPUS_REMOTE:-r2}"

MODE="dry-run"
case "${1:-}" in
  --apply)   MODE="apply" ;;
  --status)  MODE="status" ;;
  --dry-run|"") MODE="dry-run" ;;
  -h|--help)
    echo "usage: $0 [--dry-run | --apply | --status]"
    echo "  default = dry-run (prints commands, exit 0, no side effects)"
    echo "  --apply  = tar + zstd -19 + rclone copy to ${R2_REMOTE}:anima-corpus/"
    echo "             idempotent + resume-capable via state/h100_corpus_shard_progress.jsonl"
    echo "  --status = show per-shard progress table from the jsonl ledger"
    echo "  env: CORPUS_SHARD_STAGE (default /tmp), RCLONE_CORPUS_REMOTE (default r2)"
    exit 0
    ;;
  *)
    echo "[ERROR] unknown flag: $1 (use --dry-run | --apply | --status | -h)" >&2
    exit 2
    ;;
esac

ts() { date -u +%Y-%m-%dT%H:%M:%SZ; }

echo "[$(ts)] h100_corpus_shard_prestage MODE=$MODE"
echo "[$(ts)] manifest: $MANIFEST"
echo "[$(ts)] progress_jsonl: $PROGRESS_JSONL"
echo "[$(ts)] tmp_dir: $TMP_DIR  r2_remote: ${R2_REMOTE}:"

if [[ ! -f "$MANIFEST" ]]; then
  echo "[ERROR] manifest not found: $MANIFEST" >&2
  exit 3
fi

# --- progress helpers ---------------------------------------------------------
progress_append() {
  # args: shard_name status [size_bytes] [error]
  local name="$1" status="$2" size="${3:-}" err="${4:-}"
  local err_esc="${err//\"/\\\"}"
  mkdir -p "$(dirname "$PROGRESS_JSONL")"
  if [[ -n "$size" && -n "$err" ]]; then
    printf '{"ts":"%s","shard":"%s","status":"%s","size_bytes":%s,"error":"%s"}\n' \
      "$(ts)" "$name" "$status" "$size" "$err_esc" >> "$PROGRESS_JSONL"
  elif [[ -n "$size" ]]; then
    printf '{"ts":"%s","shard":"%s","status":"%s","size_bytes":%s}\n' \
      "$(ts)" "$name" "$status" "$size" >> "$PROGRESS_JSONL"
  elif [[ -n "$err" ]]; then
    printf '{"ts":"%s","shard":"%s","status":"%s","error":"%s"}\n' \
      "$(ts)" "$name" "$status" "$err_esc" >> "$PROGRESS_JSONL"
  else
    printf '{"ts":"%s","shard":"%s","status":"%s"}\n' \
      "$(ts)" "$name" "$status" >> "$PROGRESS_JSONL"
  fi
}

shard_already_done() {
  local name="$1"
  [[ -f "$PROGRESS_JSONL" ]] || return 1
  PROGRESS_JSONL="$PROGRESS_JSONL" SHARD="$name" python3 - <<'PY' 2>/dev/null || return 1
import json, os, sys
p = os.environ["PROGRESS_JSONL"]
name = os.environ["SHARD"]
last = None
with open(p) as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except Exception:
            continue
        if r.get("shard") == name:
            last = r
sys.exit(0 if (last and last.get("status") == "done") else 1)
PY
}

file_size_bytes() {
  local f="$1"
  stat -f '%z' "$f" 2>/dev/null || stat -c '%s' "$f" 2>/dev/null || echo 0
}

# --- --status mode ------------------------------------------------------------
if [[ "$MODE" = "status" ]]; then
  echo ""
  echo "=== progress status ==="
  if [[ ! -f "$PROGRESS_JSONL" ]]; then
    echo "[WARN] no progress jsonl yet at $PROGRESS_JSONL"
    echo "[$(ts)] STATUS — no apply runs recorded"
    exit 0
  fi
  PROGRESS_JSONL="$PROGRESS_JSONL" MANIFEST="$MANIFEST" python3 - <<'PY'
import json, os
p = os.environ["PROGRESS_JSONL"]
m = json.load(open(os.environ["MANIFEST"]))
shards = list(m["shards"].keys())
last = {}
with open(p) as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except Exception:
            continue
        nm = r.get("shard")
        if nm:
            last[nm] = r
print()
print(f"  {'shard':<14} {'status':<14} {'size_bytes':>12}  detail")
print(f"  {'-'*14} {'-'*14} {'-'*12}  {'-'*40}")
for nm in shards:
    r = last.get(nm)
    if r is None:
        print(f"  {nm:<14} {'pending':<14} {'-':>12}  -")
    else:
        st = r.get("status", "?")
        sz = r.get("size_bytes", "-")
        detail = r.get("error", "")
        print(f"  {nm:<14} {st:<14} {str(sz):>12}  {detail}")
print()
PY
  echo "[$(ts)] STATUS OK"
  exit 0
fi

# --- pre-flight (apply mode only) ---------------------------------------------
if [[ "$MODE" = "apply" ]]; then
  if ! command -v rclone >/dev/null 2>&1; then
    echo "[ERROR] rclone not on PATH (install rclone first)" >&2
    exit 4
  fi
  if ! rclone listremotes 2>/dev/null | grep -q "^${R2_REMOTE}:"; then
    echo "[ERROR] rclone remote '${R2_REMOTE}:' not configured (run: rclone config)" >&2
    exit 5
  fi
  for cmd in tar zstd python3; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
      echo "[ERROR] required command missing: $cmd" >&2
      exit 6
    fi
  done
  echo "[$(ts)] pre-flight OK (rclone + ${R2_REMOTE}: + tar + zstd + python3)"
fi

# Parse manifest -> TSV: shard_name<TAB>target<TAB>src1,src2,...
JOBS_TSV="$TMP_DIR/h100_corpus_shard_jobs.tsv"
MANIFEST_PATH="$MANIFEST" python3 - > "$JOBS_TSV" <<'PY'
import json, os
m = json.load(open(os.environ["MANIFEST_PATH"]))
for name, sh in m["shards"].items():
    target = sh["target"]
    srcs = ",".join(sh["sources"])
    print(f"{name}\t{target}\t{srcs}")
PY

total=$(wc -l < "$JOBS_TSV" | tr -d ' ')
echo "[$(ts)] planned shards: $total"

idx=0
fail=0
done_count=0
skip_count=0
declare -a VERDICTS=()

while IFS=$'\t' read -r name target srcs; do
  idx=$((idx+1))
  shard_file="$TMP_DIR/${name}.tar.zst"
  dst="${R2_REMOTE}:${target}"

  echo ""
  echo "==== [$idx/$total] shard=$name"
  echo "     target = $dst"
  echo "     local  = $shard_file"

  # Resume gate (apply only)
  if [[ "$MODE" = "apply" ]] && shard_already_done "$name"; then
    echo "  [SKIP-RESUME] progress jsonl shows status=done"
    VERDICTS+=("${name}:skipped_resume:0")
    skip_count=$((skip_count+1))
    continue
  fi

  # Convert sources from CSV; validate every source exists
  missing=0
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
  done
  if [[ $missing -gt 0 ]]; then
    echo "  [SKIP] $missing missing source(s) — refusing to build incomplete shard"
    if [[ "$MODE" = "apply" ]]; then
      progress_append "$name" "fail" "" "missing_sources=${missing}"
      VERDICTS+=("${name}:fail:0:missing_sources_${missing}")
    fi
    fail=$((fail+1))
    continue
  fi

  # Build tar arg list (relative to ROOT to keep clean prefixes inside tar)
  rel_args=()
  for s in "${src_arr[@]}"; do
    rel_args+=("$s")
  done

  upload_cmd=(rclone copyto "$shard_file" "$dst"
              --s3-chunk-size 64M --s3-upload-concurrency 4
              --stats 60s --stats-one-line)

  echo "  [PLAN] tar -C $ROOT -cf - ${rel_args[*]} \\"
  echo "         | zstd -19 -T0 -q -o $shard_file"
  echo "  [PLAN] ${upload_cmd[*]}"

  if [[ "$MODE" = "dry-run" ]]; then
    continue
  fi

  # --- apply: build shard if not already on disk with sane size ---------------
  build_needed=1
  if [[ -f "$shard_file" ]]; then
    existing_sz=$(file_size_bytes "$shard_file")
    if [[ "${existing_sz:-0}" -gt 0 ]]; then
      echo "  [STAGE-CACHE] reusing existing $shard_file (size=$existing_sz)"
      build_needed=0
    fi
  fi

  if [[ $build_needed -eq 1 ]]; then
    echo "  [TAR+ZSTD] $(ts)"
    set +e
    tar -C "$ROOT" -cf - "${rel_args[@]}" | zstd -19 -T0 -q -o "$shard_file"
    pipe_rc=("${PIPESTATUS[@]}")
    set -e
    if [[ "${pipe_rc[0]:-1}" -ne 0 || "${pipe_rc[1]:-1}" -ne 0 ]]; then
      echo "  [FAIL] tar|zstd pipeline failed for $name (rc=${pipe_rc[*]})"
      progress_append "$name" "fail" "" "tar_zstd_rc=${pipe_rc[*]}"
      VERDICTS+=("${name}:fail:0:tar_zstd_failed")
      fail=$((fail+1))
      rm -f "$shard_file" 2>/dev/null || true
      continue
    fi
  fi

  sz=$(file_size_bytes "$shard_file")
  echo "  [SHARD-OK] size=$sz bytes"

  # --- idempotency: skip upload if R2 already has matching size ---------------
  upload_needed=1
  rs_existing=$(rclone lsjson "$dst" 2>/dev/null \
        | python3 -c "import sys,json
try:
  d=json.load(sys.stdin); print(d[0].get('Size',-1) if d else -1)
except Exception:
  print(-1)" 2>/dev/null || echo -1)
  if [[ "$rs_existing" = "$sz" ]]; then
    echo "  [SKIP-UPLOAD] R2 object already matches local size ($sz)"
    upload_needed=0
  fi

  if [[ $upload_needed -eq 1 ]]; then
    echo "  [UPLOAD] $(ts) → $dst"
    set +e
    "${upload_cmd[@]}"
    rc=$?
    set -e
    if [[ $rc -ne 0 ]]; then
      echo "  [FAIL] rclone upload failed for $name (rc=$rc)"
      progress_append "$name" "fail" "$sz" "rclone_rc=$rc"
      VERDICTS+=("${name}:fail:${sz}:rclone_rc_${rc}")
      fail=$((fail+1))
      continue
    fi
  fi

  # Verify size on R2
  rs=$(rclone lsjson "$dst" 2>/dev/null \
        | python3 -c "import sys,json
try:
  d=json.load(sys.stdin); print(d[0].get('Size',-1) if d else -1)
except Exception:
  print(-1)" 2>/dev/null || echo -1)
  echo "  local=$sz r2=$rs"
  if [[ "$sz" = "$rs" ]]; then
    echo "  [VERIFIED] $(ts)"
    progress_append "$name" "done" "$sz"
    VERDICTS+=("${name}:done:${sz}")
    done_count=$((done_count+1))
  else
    echo "  [VERIFY-FAIL] keeping local shard for retry"
    progress_append "$name" "fail" "$sz" "verify_size_mismatch_local=${sz}_r2=${rs}"
    VERDICTS+=("${name}:fail:${sz}:verify_mismatch")
    fail=$((fail+1))
  fi
done < "$JOBS_TSV"

echo ""
if [[ "$MODE" = "dry-run" ]]; then
  echo "[$(ts)] DRY-RUN COMPLETE shards_planned=$total fail=$fail"
  echo "[$(ts)] re-run with --apply to execute (requires rclone ${R2_REMOTE}: remote)"
  exit 0
fi

# --- emit completion json (apply only) ----------------------------------------
{
  printf '{\n'
  printf '  "schema": "anima/h100_corpus_shard_completion/1",\n'
  printf '  "completed_at": "%s",\n' "$(ts)"
  printf '  "progress_jsonl": "%s",\n' "$PROGRESS_JSONL"
  printf '  "summary": {"done": %d, "skipped_resume": %d, "fail": %d, "total": %d},\n' \
    "$done_count" "$skip_count" "$fail" "$total"
  printf '  "verdicts": {\n'
  vfirst=1
  for v in "${VERDICTS[@]}"; do
    nm="${v%%:*}"; rest="${v#*:}"
    status="${rest%%:*}"; rest="${rest#*:}"
    if [[ "$rest" == *:* ]]; then
      sz="${rest%%:*}"; tail_field="${rest#*:}"
    else
      sz="$rest"; tail_field=""
    fi
    if [[ $vfirst -eq 1 ]]; then vfirst=0; else printf ',\n'; fi
    if [[ "$status" == "done" ]]; then
      printf '    "%s": {"status": "done", "size_bytes": %s}' "$nm" "$sz"
    elif [[ "$status" == "skipped_resume" ]]; then
      printf '    "%s": {"status": "skipped_resume"}' "$nm"
    else
      printf '    "%s": {"status": "fail", "size_bytes": %s, "error": "%s"}' "$nm" "$sz" "$tail_field"
    fi
  done
  printf '\n  }\n}\n'
} > "$COMPLETION_JSON"
echo "[$(ts)] completion json: $COMPLETION_JSON"

echo "[$(ts)] APPLY COMPLETE shards_built=$done_count skipped=$skip_count fail=$fail"
[[ $fail -eq 0 ]] && exit 0 || exit 1
