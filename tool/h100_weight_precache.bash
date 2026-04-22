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
#   tool/h100_weight_precache.bash --help
#
# EXIT
#   0 = dry-run printed OK / apply succeeded
#   1 = manifest missing or unreadable
#   2 = bad arg
#   3 = --apply but credentials missing (HF_TOKEN / rclone profile)
#   4 = mirror step failed (apply only)
set -euo pipefail

# --- constants ----------------------------------------------------------------
readonly ANIMA_ROOT="/Users/ghost/core/anima"
readonly MANIFEST="${ANIMA_ROOT}/state/h100_weight_precache_manifest.json"
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

# --- argv ---------------------------------------------------------------------
MODE="dry-run"
for arg in "$@"; do
  case "$arg" in
    --dry-run) MODE="dry-run" ;;
    --apply)   MODE="apply" ;;
    --help|-h) sed -n '1,25p' "$0"; exit 0 ;;
    *) log "unknown arg: $arg"; exit 2 ;;
  esac
done

log "mode=${MODE} log=${LOG}"
log "manifest=${MANIFEST}"
log "rclone_remote=${RCLONE_REMOTE} (override via env RCLONE_R2_REMOTE)"
log "staging_dir=${STAGING_DIR} (override via env WEIGHT_PRECACHE_STAGE)"

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

# --- emit per-path commands ---------------------------------------------------
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
  plan "hf download ${MODEL_ID} --local-dir ${STAGE} --include $(echo "${FILES}" | tr ' ' ',')"
  plan "TOK_SHA=\$(sha256sum ${STAGE}/tokenizer.json | awk '{print \$1}')   # write back to manifest"
  plan "rclone copy ${STAGE}/ ${RCLONE_REMOTE}:${R2_TARGET} --progress --transfers 4 --checkers 8"
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
printf '{\n  "schema": "anima/h100_weight_precache_tokenizer_sha/1",\n  "recorded_at": "%s",\n  "paths": {\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "${TOKENIZER_SHA_RECORD}"
first=1

HF_BIN="$(command -v hf || command -v huggingface-cli)"

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

  log "[${pid}] downloading ${MODEL_ID} -> ${STAGE}"
  mkdir -p "${STAGE}"
  if ! "${HF_BIN}" download "${MODEL_ID}" --local-dir "${STAGE}" --include "${FILES}" --token "${HF_TOKEN}"; then
    fail "[${pid}] HF download failed"
    exit 4
  fi

  if [[ -f "${STAGE}/tokenizer.json" ]]; then
    TOK_SHA=$(compute_sha256 "${STAGE}/tokenizer.json")
    log "[${pid}] tokenizer.json sha256 = ${TOK_SHA}"
    if [[ ${first} -eq 1 ]]; then first=0; else printf ',\n' >> "${TOKENIZER_SHA_RECORD}"; fi
    printf '    "%s": {"model_id": "%s", "tokenizer_sha256": "%s"}' "${pid}" "${MODEL_ID}" "${TOK_SHA}" >> "${TOKENIZER_SHA_RECORD}"
  else
    warn "[${pid}] tokenizer.json absent in download — skipping sha256"
  fi

  log "[${pid}] mirroring to ${RCLONE_REMOTE}:${R2_TARGET}"
  if ! rclone copy "${STAGE}/" "${RCLONE_REMOTE}:${R2_TARGET}" --progress --transfers 4 --checkers 8; then
    fail "[${pid}] rclone copy failed"
    exit 4
  fi
  pass "[${pid}] mirror complete"
done

printf '\n  }\n}\n' >> "${TOKENIZER_SHA_RECORD}"
log "tokenizer sha record: ${TOKENIZER_SHA_RECORD}"
log "NOTE: operator must merge the recorded sha values into the canonical manifest"
log "      (state/h100_weight_precache_manifest.json paths.<pid>.tokenizer_sha256)"
log "      so pod start-up integrity gate can compare. (manual edit avoids accidental SSOT mutation by this script.)"

log "RESULT: APPLY OK — 4 paths mirrored to ${R2_BUCKET}"
exit 0
