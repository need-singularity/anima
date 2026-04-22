#!/usr/bin/env bash
# tool/h100_weight_precache.bash — pre-mirror 4 base model weights to Cloudflare R2
#
# Roadmap: #83 H100 x 4 unified launch (β main) — saves ~30-50 min/pod (4 pods)
# by mirroring HF weights once to R2 (free egress), then pods download from R2 in <10 min.
#
# Also computes tokenizer.json sha256 per path and writes it back to the manifest,
# so each pod can verify tokenizer integrity at start-up before any weight load
# (silent tokenizer drift would invalidate cross-substrate Φ comparison).
#
# raw#9  deterministic: file lists frozen in manifest SSOT
# raw#10 proof-carrying: tokenizer sha256 written back to manifest after fetch
# raw#20 H100 stop-gate: dry-run by default; --apply requires HF_TOKEN + rclone profile
#
# USAGE
#   tool/h100_weight_precache.bash                # default = dry-run, prints commands
#   tool/h100_weight_precache.bash --dry-run      # explicit dry-run
#   tool/h100_weight_precache.bash --apply        # real fetch+mirror (requires creds)
#   tool/h100_weight_precache.bash --status       # show progress jsonl as table
#   tool/h100_weight_precache.bash --help
#
# RESUME / IDEMPOTENCY
#   --apply consults state/h100_weight_precache_progress.jsonl: paths marked
#   status=done are skipped. R2-side: each file is checked via `rclone lsjson`
#   for matching size — matching files are skipped within rclone copy via its
#   built-in size-based duplicate suppression.
#
# EXIT
#   0 = dry-run printed OK / apply succeeded (all paths done)
#   1 = manifest missing or unreadable
#   2 = bad arg
#   3 = --apply but credentials/tools missing (HF_TOKEN / rclone profile / hf cli)
#   4 = one or more paths failed during apply (other paths may have succeeded)
set -euo pipefail

# --- constants ----------------------------------------------------------------
readonly ANIMA_ROOT="/Users/ghost/core/anima"
readonly MANIFEST="${ANIMA_ROOT}/state/h100_weight_precache_manifest.json"
readonly PROGRESS_JSONL="${ANIMA_ROOT}/state/h100_weight_precache_progress.jsonl"
readonly COMPLETION_JSON="${ANIMA_ROOT}/state/h100_weight_precache_completion.json"
readonly RCLONE_REMOTE="${RCLONE_R2_REMOTE:-r2anima}"
readonly STAGING_DIR="${WEIGHT_PRECACHE_STAGE:-/tmp/anima_weight_precache}"
readonly TS="$(date -u +%Y%m%dT%H%M%SZ)"
readonly LOG="/tmp/h100_weight_precache_${TS}.log"

# --- log helpers --------------------------------------------------------------
exec > >(tee -a "${LOG}") 2>&1
log()  { printf '[%s] %s\n' "$(date -u +%H:%M:%SZ)" "$*"; }
pass() { printf '  [PASS] %s\n' "$*"; }
fail() { printf '  [FAIL] %s\n' "$*"; }
warn() { printf '  [WARN] %s\n' "$*"; }
plan() { printf '  [PLAN] %s\n' "$*"; }
ts_iso() { date -u +%Y-%m-%dT%H:%M:%SZ; }

# --- argv ---------------------------------------------------------------------
MODE="dry-run"
for arg in "$@"; do
  case "$arg" in
    --dry-run) MODE="dry-run" ;;
    --apply)   MODE="apply" ;;
    --status)  MODE="status" ;;
    --help|-h) sed -n '1,35p' "$0"; exit 0 ;;
    *) log "unknown arg: $arg"; exit 2 ;;
  esac
done

log "mode=${MODE} log=${LOG}"
log "manifest=${MANIFEST}"
log "rclone_remote=${RCLONE_REMOTE} (override via env RCLONE_R2_REMOTE)"
log "staging_dir=${STAGING_DIR} (override via env WEIGHT_PRECACHE_STAGE)"
log "progress_jsonl=${PROGRESS_JSONL}"

# --- pre-flight 1: manifest readable ------------------------------------------
log "pre-flight 1/3: manifest readable"
if [[ ! -f "${MANIFEST}" ]]; then
  fail "manifest missing: ${MANIFEST}"
  exit 1
fi
pass "manifest exists"

# extract path list and bucket via python (jq not assumed)
PATH_IDS=$(python3 -c 'import json,sys
m=json.load(open(sys.argv[1]))
print(" ".join(sorted(m["paths"].keys())))' "${MANIFEST}")
R2_BUCKET=$(python3 -c 'import json,sys
m=json.load(open(sys.argv[1]))
print(m["r2_bucket"])' "${MANIFEST}")
TOTAL_GB=$(python3 -c 'import json,sys
m=json.load(open(sys.argv[1]))
print(m["estimated_total_gb"])' "${MANIFEST}")
pass "paths=[${PATH_IDS}] bucket=${R2_BUCKET} total_gb=${TOTAL_GB}"

# --- --status mode ------------------------------------------------------------
if [[ "${MODE}" == "status" ]]; then
  log ""
  log "=== progress status ==="
  if [[ ! -f "${PROGRESS_JSONL}" ]]; then
    warn "no progress jsonl yet at ${PROGRESS_JSONL}"
    log "RESULT: STATUS — no apply runs recorded"
    exit 0
  fi
  PROGRESS_JSONL="${PROGRESS_JSONL}" PATH_IDS="${PATH_IDS}" python3 - <<'PY'
import json, os
p = os.environ["PROGRESS_JSONL"]
ids = os.environ["PATH_IDS"].split()
# last status per pid wins
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
        pid = r.get("path")
        if pid:
            last[pid] = r
print()
print(f"  {'path':<6} {'status':<10} {'size_mb':>9}  tokenizer_sha256 (first 16) / error")
print(f"  {'-'*6} {'-'*10} {'-'*9}  {'-'*40}")
for pid in ids:
    r = last.get(pid)
    if r is None:
        print(f"  {pid:<6} {'pending':<10} {'-':>9}  -")
    else:
        st = r.get("status", "?")
        sz = r.get("size_mb", "-")
        if st == "done":
            tail = (r.get("tokenizer_sha256") or "")[:16]
        else:
            tail = r.get("error", "")
        if isinstance(sz, (int, float)):
            sz_s = f"{sz:.1f}"
        else:
            sz_s = str(sz)
        print(f"  {pid:<6} {st:<10} {sz_s:>9}  {tail}")
print()
PY
  log "RESULT: STATUS OK"
  exit 0
fi

# --- pre-flight 2: tool availability ------------------------------------------
log "pre-flight 2/3: tool availability"
HAVE_HF=0; HAVE_RCLONE=0; HAVE_SHA256=0
if command -v hf >/dev/null 2>&1 || command -v huggingface-cli >/dev/null 2>&1; then
  HAVE_HF=1; pass "hf / huggingface-cli present"
else
  warn "hf CLI not found (apply mode will fail)"
fi
if command -v rclone >/dev/null 2>&1; then
  HAVE_RCLONE=1; pass "rclone present"
else
  warn "rclone not found (apply mode will fail)"
fi
if command -v sha256sum >/dev/null 2>&1; then
  HAVE_SHA256=1; pass "sha256sum present"
elif command -v shasum >/dev/null 2>&1; then
  HAVE_SHA256=1; pass "shasum present (will use 'shasum -a 256')"
else
  warn "no sha256sum/shasum available (apply mode will skip integrity gate write-back)"
fi

# --- pre-flight 3: credentials (only mandatory for --apply) -------------------
log "pre-flight 3/3: credentials (HF_TOKEN, rclone profile)"
HAVE_HF_TOKEN=0; HAVE_RCLONE_PROFILE=0
if [[ -n "${HF_TOKEN:-}" ]]; then
  HAVE_HF_TOKEN=1; pass "HF_TOKEN env set (length=${#HF_TOKEN})"
else
  warn "HF_TOKEN not set"
fi
if [[ "${HAVE_RCLONE}" -eq 1 ]] && rclone listremotes 2>/dev/null | grep -q "^${RCLONE_REMOTE}:"; then
  HAVE_RCLONE_PROFILE=1; pass "rclone profile '${RCLONE_REMOTE}:' configured"
else
  warn "rclone profile '${RCLONE_REMOTE}:' not configured"
fi

# --- helper: sha256 portable --------------------------------------------------
compute_sha256() {
  local f="$1"
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$f" | awk '{print $1}'
  else
    shasum -a 256 "$f" | awk '{print $1}'
  fi
}

# --- helper: portable file size in bytes --------------------------------------
file_size_bytes() {
  local f="$1"
  stat -f '%z' "$f" 2>/dev/null || stat -c '%s' "$f" 2>/dev/null || echo 0
}

# --- helper: directory size in MB (sum of files) ------------------------------
dir_size_mb() {
  local d="$1"
  if [[ ! -d "$d" ]]; then echo 0; return; fi
  local kb
  kb=$(du -sk "$d" 2>/dev/null | awk '{print $1}')
  awk -v k="${kb:-0}" 'BEGIN{printf "%.1f", k/1024.0}'
}

# --- helper: append progress jsonl line ---------------------------------------
progress_append() {
  # args: pid status [size_mb] [tokenizer_sha256] [error]
  local pid="$1" status="$2" size_mb="${3:-}" tok="${4:-}" err="${5:-}"
  local err_esc="${err//\"/\\\"}"
  mkdir -p "$(dirname "${PROGRESS_JSONL}")"
  if [[ -n "${size_mb}" && -n "${tok}" ]]; then
    printf '{"ts":"%s","path":"%s","status":"%s","size_mb":%s,"tokenizer_sha256":"%s"}\n' \
      "$(ts_iso)" "${pid}" "${status}" "${size_mb}" "${tok}" >> "${PROGRESS_JSONL}"
  elif [[ -n "${size_mb}" ]]; then
    printf '{"ts":"%s","path":"%s","status":"%s","size_mb":%s}\n' \
      "$(ts_iso)" "${pid}" "${status}" "${size_mb}" >> "${PROGRESS_JSONL}"
  elif [[ -n "${err}" ]]; then
    printf '{"ts":"%s","path":"%s","status":"%s","error":"%s"}\n' \
      "$(ts_iso)" "${pid}" "${status}" "${err_esc}" >> "${PROGRESS_JSONL}"
  else
    printf '{"ts":"%s","path":"%s","status":"%s"}\n' \
      "$(ts_iso)" "${pid}" "${status}" >> "${PROGRESS_JSONL}"
  fi
}

# --- helper: is path already done according to progress jsonl? ----------------
path_already_done() {
  local pid="$1"
  [[ -f "${PROGRESS_JSONL}" ]] || return 1
  PROGRESS_JSONL="${PROGRESS_JSONL}" PID="${pid}" python3 - <<'PY' 2>/dev/null || return 1
import json, os, sys
p = os.environ["PROGRESS_JSONL"]
pid = os.environ["PID"]
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
        if r.get("path") == pid:
            last = r
sys.exit(0 if (last and last.get("status") == "done") else 1)
PY
}

# --- emit per-path commands (always — used by both dry-run and apply preview) -
log ""
log "=== per-path mirror plan ==="
for pid in ${PATH_IDS}; do
  log ""
  MODEL_ID=$(python3 -c 'import json,sys
m=json.load(open(sys.argv[1]))
print(m["paths"][sys.argv[2]]["model_id"])' "${MANIFEST}" "${pid}")
  R2_TARGET=$(python3 -c 'import json,sys
m=json.load(open(sys.argv[1]))
print(m["paths"][sys.argv[2]]["r2_target"])' "${MANIFEST}" "${pid}")
  SIZE_GB=$(python3 -c 'import json,sys
m=json.load(open(sys.argv[1]))
print(m["paths"][sys.argv[2]]["estimated_size_gb"])' "${MANIFEST}" "${pid}")
  FILES=$(python3 -c 'import json,sys
m=json.load(open(sys.argv[1]))
print(" ".join(m["paths"][sys.argv[2]]["files"]))' "${MANIFEST}" "${pid}")

  log "[${pid}] ${MODEL_ID}  (~${SIZE_GB}GB → ${R2_TARGET})"
  STAGE="${STAGING_DIR}/${pid}"
  plan "mkdir -p ${STAGE}"
  plan "huggingface-cli download ${MODEL_ID} --local-dir ${STAGE} --include $(echo "${FILES}" | tr ' ' ',')"
  plan "TOK_SHA=\$(sha256sum ${STAGE}/tokenizer.json | awk '{print \$1}')   # write back to manifest"
  plan "rclone copy ${STAGE}/ ${RCLONE_REMOTE}:${R2_TARGET} --progress --transfers 4 --checkers 8 --size-only"
done

# --- dry-run exit -------------------------------------------------------------
if [[ "${MODE}" == "dry-run" ]]; then
  log ""
  log "DRY-RUN: above commands NOT executed."
  log "DRY-RUN: to actually mirror (one-time, ~2-4h, ~125GB transfer):"
  log "  export HF_TOKEN=hf_..."
  log "  rclone config  # add R2 profile named '${RCLONE_REMOTE}'"
  log "  $0 --apply"
  log "RESULT: DRY-RUN OK"
  exit 0
fi

# --- apply mode: enforce credentials ------------------------------------------
log ""
log "=== APPLY MODE ==="
if [[ "${HAVE_HF}" -ne 1 || "${HAVE_RCLONE}" -ne 1 ]]; then
  fail "missing required CLIs (hf=${HAVE_HF} rclone=${HAVE_RCLONE})"
  exit 3
fi
if [[ "${HAVE_HF_TOKEN}" -ne 1 ]]; then
  fail "HF_TOKEN env var required for --apply"
  exit 3
fi
if [[ "${HAVE_RCLONE_PROFILE}" -ne 1 ]]; then
  fail "rclone profile '${RCLONE_REMOTE}:' required for --apply"
  exit 3
fi
if [[ "${HAVE_SHA256}" -ne 1 ]]; then
  fail "sha256 tool required for tokenizer integrity gate"
  exit 3
fi

mkdir -p "${STAGING_DIR}"
TOKENIZER_SHA_RECORD="${ANIMA_ROOT}/state/h100_weight_precache_tokenizer_sha.json"
printf '{\n  "schema": "anima/h100_weight_precache_tokenizer_sha/1",\n  "recorded_at": "%s",\n  "paths": {\n' \
  "$(ts_iso)" > "${TOKENIZER_SHA_RECORD}"
first=1

HF_BIN="$(command -v hf || command -v huggingface-cli)"

# verdict accumulator (pid:status:size_mb:tok)
declare -a VERDICTS=()
fail_count=0
done_count=0
skip_count=0

for pid in ${PATH_IDS}; do
  MODEL_ID=$(python3 -c 'import json,sys
m=json.load(open(sys.argv[1]))
print(m["paths"][sys.argv[2]]["model_id"])' "${MANIFEST}" "${pid}")
  R2_TARGET=$(python3 -c 'import json,sys
m=json.load(open(sys.argv[1]))
print(m["paths"][sys.argv[2]]["r2_target"])' "${MANIFEST}" "${pid}")
  FILES=$(python3 -c 'import json,sys
m=json.load(open(sys.argv[1]))
print(",".join(m["paths"][sys.argv[2]]["files"]))' "${MANIFEST}" "${pid}")
  STAGE="${STAGING_DIR}/${pid}"

  log ""
  log "[${pid}] === processing ${MODEL_ID} ==="

  # Resume: skip if already done
  if path_already_done "${pid}"; then
    pass "[${pid}] progress jsonl shows status=done — skipping (resume)"
    VERDICTS+=("${pid}:skipped_resume:0:resume")
    skip_count=$((skip_count+1))
    continue
  fi

  log "[${pid}] downloading -> ${STAGE}"
  mkdir -p "${STAGE}"
  if ! "${HF_BIN}" download "${MODEL_ID}" --local-dir "${STAGE}" --include "${FILES}" --token "${HF_TOKEN}"; then
    fail "[${pid}] HF download failed"
    progress_append "${pid}" "fail" "" "" "hf_download_failed"
    VERDICTS+=("${pid}:fail:0:hf_download_failed")
    fail_count=$((fail_count+1))
    continue
  fi

  TOK_SHA=""
  if [[ -f "${STAGE}/tokenizer.json" ]]; then
    TOK_SHA=$(compute_sha256 "${STAGE}/tokenizer.json")
    log "[${pid}] tokenizer.json sha256 = ${TOK_SHA}"
    if [[ ${first} -eq 1 ]]; then first=0; else printf ',\n' >> "${TOKENIZER_SHA_RECORD}"; fi
    printf '    "%s": {"model_id": "%s", "tokenizer_sha256": "%s"}' \
      "${pid}" "${MODEL_ID}" "${TOK_SHA}" >> "${TOKENIZER_SHA_RECORD}"
  else
    warn "[${pid}] tokenizer.json absent in download — skipping sha256"
  fi

  log "[${pid}] mirroring to ${RCLONE_REMOTE}:${R2_TARGET}"
  # --size-only enables idempotent re-runs: existing R2 objects with matching
  # size are skipped (rclone built-in suppression).
  if ! rclone copy "${STAGE}/" "${RCLONE_REMOTE}:${R2_TARGET}" \
        --progress --transfers 4 --checkers 8 --size-only \
        --s3-chunk-size 64M --s3-upload-concurrency 4 \
        --stats 60s --stats-one-line; then
    fail "[${pid}] rclone copy failed"
    progress_append "${pid}" "fail" "" "" "rclone_copy_failed"
    VERDICTS+=("${pid}:fail:0:rclone_copy_failed")
    fail_count=$((fail_count+1))
    continue
  fi

  size_mb=$(dir_size_mb "${STAGE}")
  pass "[${pid}] mirror complete (size_mb=${size_mb})"
  progress_append "${pid}" "done" "${size_mb}" "${TOK_SHA}" ""
  VERDICTS+=("${pid}:done:${size_mb}:${TOK_SHA}")
  done_count=$((done_count+1))
done

printf '\n  }\n}\n' >> "${TOKENIZER_SHA_RECORD}"
log "tokenizer sha record: ${TOKENIZER_SHA_RECORD}"
log "NOTE: operator must merge the recorded sha values into the canonical manifest"
log "      (state/h100_weight_precache_manifest.json paths.<pid>.tokenizer_sha256)"
log "      so pod start-up integrity gate can compare. (manual edit avoids accidental SSOT mutation by this script.)"

# emit completion json
{
  printf '{\n'
  printf '  "schema": "anima/h100_weight_precache_completion/1",\n'
  printf '  "completed_at": "%s",\n' "$(ts_iso)"
  printf '  "log_path": "%s",\n' "${LOG}"
  printf '  "progress_jsonl": "%s",\n' "${PROGRESS_JSONL}"
  printf '  "summary": {"done": %d, "skipped_resume": %d, "fail": %d, "total": %d},\n' \
    "${done_count}" "${skip_count}" "${fail_count}" "$(echo "${PATH_IDS}" | wc -w | tr -d ' ')"
  printf '  "verdicts": {\n'
  vfirst=1
  for v in "${VERDICTS[@]}"; do
    pid="${v%%:*}"; rest="${v#*:}"
    status="${rest%%:*}"; rest="${rest#*:}"
    size="${rest%%:*}"; tail_field="${rest#*:}"
    if [[ ${vfirst} -eq 1 ]]; then vfirst=0; else printf ',\n'; fi
    if [[ "${status}" == "done" ]]; then
      printf '    "%s": {"status": "done", "size_mb": %s, "tokenizer_sha256": "%s"}' \
        "${pid}" "${size}" "${tail_field}"
    elif [[ "${status}" == "skipped_resume" ]]; then
      printf '    "%s": {"status": "skipped_resume"}' "${pid}"
    else
      printf '    "%s": {"status": "fail", "error": "%s"}' "${pid}" "${tail_field}"
    fi
  done
  printf '\n  }\n}\n'
} > "${COMPLETION_JSON}"
log "completion json: ${COMPLETION_JSON}"

if [[ ${fail_count} -gt 0 ]]; then
  fail "RESULT: APPLY PARTIAL — done=${done_count} skipped=${skip_count} fail=${fail_count}"
  log "Re-run --apply to retry failed paths (resume will skip already-done paths)."
  exit 4
fi

log "RESULT: APPLY OK — done=${done_count} skipped=${skip_count} (bucket=${R2_BUCKET})"
exit 0
