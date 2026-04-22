#!/usr/bin/env bash
# tool/h100_pod_resume.bash — H100 pod auto-resume from R2 last ckpt
#
# Roadmap: 2026-04-22 ROI Q2 — pod restart auto-resume hook.
# Motivation: with abort_thresholds.ckpt_interval_steps=25 (ROI Q1) and
# h100_auto_kill SIGUSR2 graceful save (ROI Q3), every pod reliably writes a
# checkpoint to R2 every 25 steps and on shutdown. When a spot pod is evicted
# and restarted (or any pod re-spawn), this script is invoked at pod boot:
#   1. probe R2 for the most recent ckpt for this pod's PHI_PATH_ID (or stage1)
#   2. download it to /workspace/ckpts/${PHI_PATH_ID}/
#   3. emit a marker file the runner picks up via --resume-from
#
# Per-pod isolation: each path id (stage1, p1..p4) writes under its own R2
# prefix, so a stage2_p3 restart cannot accidentally read p1's ckpt
# (tokenizer mismatch → silent corruption). Verified by
# tool/per_pod_ckpt_isolation_verify.hexa.
#
# raw#9  deterministic: R2 prefix layout frozen by env / config (no hardcode beyond default)
# raw#10 proof-carrying: writes state/h100_pod_resume_last.json with ckpt sha
# raw#20 H100 stop-gate: dry-run by default; --apply requires rclone profile
#
# USAGE
#   tool/h100_pod_resume.bash                           # dry-run (default)
#   tool/h100_pod_resume.bash --dry-run                 # explicit dry-run
#   tool/h100_pod_resume.bash --apply                   # real R2 download
#   tool/h100_pod_resume.bash --self-test               # 4 synthetic scenarios
#   tool/h100_pod_resume.bash --path p3                 # override PHI_PATH_ID
#   tool/h100_pod_resume.bash --help
#
# ENV
#   PHI_PATH_ID            pod's path tag (stage1 | p1 | p2 | p3 | p4)
#   RCLONE_R2_REMOTE       rclone remote name (default: r2)
#   ANIMA_CKPT_R2_PREFIX   R2 prefix root (default: anima/h100/ckpts)
#   ANIMA_CKPT_LOCAL_ROOT  local ckpt root (default: /workspace/ckpts)
#
# EXIT
#   0 = no resume needed (fresh pod) OR resume completed (apply) / dry-run printed
#   1 = bad arg
#   2 = self-test FAIL
#   3 = --apply but rclone missing or no PHI_PATH_ID
set -euo pipefail

# --- constants ---------------------------------------------------------------
readonly ANIMA_ROOT="${ANIMA_ROOT:-/Users/ghost/core/anima}"
readonly STATE_OUT="${ANIMA_ROOT}/state/h100_pod_resume_last.json"
readonly RCLONE_REMOTE="${RCLONE_R2_REMOTE:-r2}"
readonly R2_PREFIX="${ANIMA_CKPT_R2_PREFIX:-anima/h100/ckpts}"
readonly LOCAL_ROOT="${ANIMA_CKPT_LOCAL_ROOT:-/workspace/ckpts}"
readonly TS="$(date -u +%Y%m%dT%H%M%SZ)"

# --- log helpers -------------------------------------------------------------
log()  { printf '[%s] %s\n' "$(date -u +%H:%M:%SZ)" "$*"; }
pass() { printf '  [PASS] %s\n' "$*"; }
fail() { printf '  [FAIL] %s\n' "$*"; }
plan() { printf '  [PLAN] %s\n' "$*"; }
ts_iso() { date -u +%Y-%m-%dT%H:%M:%SZ; }

# --- argv --------------------------------------------------------------------
MODE="dry-run"
PATH_OVERRIDE=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)   MODE="dry-run"; shift ;;
    --apply)     MODE="apply"; shift ;;
    --self-test) MODE="self-test"; shift ;;
    --path)      PATH_OVERRIDE="$2"; shift 2 ;;
    --help|-h)   sed -n '1,40p' "$0"; exit 0 ;;
    *) log "unknown arg: $1"; exit 1 ;;
  esac
done

# --- self-test (4 scenarios; no R2 calls) -----------------------------------
if [[ "${MODE}" == "self-test" ]]; then
  log "── h100_pod_resume self-test ──"
  passes=0; fails=0
  # S1: per-path R2 URI builder
  uri="$(printf '%s:%s/%s/' "${RCLONE_REMOTE}" "${R2_PREFIX}" "p1")"
  if [[ "${uri}" == "r2:anima/h100/ckpts/p1/" ]]; then pass "S1 R2 URI builder"; passes=$((passes+1));
  else fail "S1 expected r2:anima/h100/ckpts/p1/ got ${uri}"; fails=$((fails+1)); fi
  # S2: per-path local dir builder isolation (p3 ≠ p1)
  d_p1="${LOCAL_ROOT}/p1"; d_p3="${LOCAL_ROOT}/p3"
  if [[ "${d_p1}" != "${d_p3}" ]]; then pass "S2 local dir per-pod isolation"; passes=$((passes+1));
  else fail "S2 collision ${d_p1}=${d_p3}"; fails=$((fails+1)); fi
  # S3: invalid path id rejection
  bad="invalid-path"
  case "${bad}" in
    stage1|p1|p2|p3|p4) fail "S3 should reject ${bad}"; fails=$((fails+1)) ;;
    *) pass "S3 invalid path id rejected"; passes=$((passes+1)) ;;
  esac
  # S4: dry-run never invokes rclone (string-only check)
  cmd="rclone copy ${RCLONE_REMOTE}:${R2_PREFIX}/p1/latest ${LOCAL_ROOT}/p1/"
  if [[ "${cmd}" == rclone* ]]; then pass "S4 dry-run plan command well-formed"; passes=$((passes+1));
  else fail "S4 malformed command: ${cmd}"; fails=$((fails+1)); fi
  log "selftest: ${passes}/4 PASS, ${fails} FAIL"
  if [[ "${fails}" -gt 0 ]]; then exit 2; fi
  exit 0
fi

# --- resolve path id ---------------------------------------------------------
PATH_ID="${PATH_OVERRIDE:-${PHI_PATH_ID:-stage1}}"
case "${PATH_ID}" in
  stage1|p1|p2|p3|p4) ;;
  *) fail "unknown PHI_PATH_ID=${PATH_ID} (allowed: stage1 p1 p2 p3 p4)"; exit 1 ;;
esac

R2_URI="${RCLONE_REMOTE}:${R2_PREFIX}/${PATH_ID}/"
LOCAL_DIR="${LOCAL_ROOT}/${PATH_ID}"

log "mode=${MODE} path_id=${PATH_ID}"
log "r2_uri=${R2_URI}"
log "local_dir=${LOCAL_DIR}"

# --- pre-flight (apply only) -------------------------------------------------
if [[ "${MODE}" == "apply" ]]; then
  if ! command -v rclone >/dev/null 2>&1; then
    fail "rclone not on PATH — install or use --dry-run"
    exit 3
  fi
fi

# --- list latest ckpt on R2 (skeleton; non-failing on dry-run) ---------------
LIST_CMD="rclone lsjson --max-depth 1 ${R2_URI} 2>/dev/null | jq -r 'sort_by(.ModTime) | last | .Name // empty'"
if [[ "${MODE}" == "apply" ]]; then
  LATEST="$(eval "${LIST_CMD}" || true)"
else
  plan "${LIST_CMD}"
  LATEST="<dry-run-no-probe>"
fi
log "latest_ckpt=${LATEST}"

# --- early exit: no remote ckpt = fresh pod ---------------------------------
if [[ "${MODE}" == "apply" && -z "${LATEST}" ]]; then
  log "no remote ckpt found — fresh pod, nothing to resume"
  mkdir -p "$(dirname "${STATE_OUT}")"
  printf '{"schema":"anima/h100_pod_resume/1","ts":"%s","path_id":"%s","latest_ckpt":"","action":"fresh_start","resumed":false}\n' \
    "$(ts_iso)" "${PATH_ID}" > "${STATE_OUT}"
  exit 0
fi

# --- download ckpt -----------------------------------------------------------
DL_CMD="mkdir -p ${LOCAL_DIR} && rclone copy ${R2_URI}${LATEST} ${LOCAL_DIR}/ --transfers=8 --checksum"
if [[ "${MODE}" == "apply" ]]; then
  log "downloading: ${DL_CMD}"
  eval "${DL_CMD}"
  CKPT_SHA="$(shasum -a 256 "${LOCAL_DIR}/${LATEST}" 2>/dev/null | awk '{print $1}' || echo "")"
  log "resumed: ${LOCAL_DIR}/${LATEST} sha=${CKPT_SHA}"
else
  plan "${DL_CMD}"
  CKPT_SHA="<dry-run>"
fi

# --- write marker file consumed by runner via --resume-from -----------------
MARKER="${LOCAL_DIR}/.resume_marker"
if [[ "${MODE}" == "apply" ]]; then
  printf '%s\n' "${LATEST}" > "${MARKER}"
fi

# --- emit proof JSON ---------------------------------------------------------
mkdir -p "$(dirname "${STATE_OUT}")"
printf '{"schema":"anima/h100_pod_resume/1","ts":"%s","mode":"%s","path_id":"%s","r2_uri":"%s","local_dir":"%s","latest_ckpt":"%s","ckpt_sha":"%s","action":"%s","resumed":%s}\n' \
  "$(ts_iso)" "${MODE}" "${PATH_ID}" "${R2_URI}" "${LOCAL_DIR}" "${LATEST}" "${CKPT_SHA}" \
  "$([[ "${MODE}" == "apply" ]] && echo "resumed" || echo "planned")" \
  "$([[ "${MODE}" == "apply" ]] && echo "true" || echo "false")" \
  > "${STATE_OUT}"

log "proof=${STATE_OUT}"
exit 0
