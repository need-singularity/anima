#!/usr/bin/env bash
# tool/cp1_serve_launch.bash — CP1 dest1 persona LIVE (roadmap #77)
#
# PURPOSE
#   Spin up a single persistent H100 pod running FastAPI + vLLM with the
#   trained p1 LoRA adapter. CP1 gate: trained adapter serves live inference
#   with p99 <500ms at bs=1 and uptime ≥99.5%/24h.
#
# PREREQ
#   state/trained_adapters/p1/ (adapter_model.safetensors + adapter_config.json)
#   — NOT locally available as of 2026-04-24 (Stage-2 pods killed before
#   full adapter dir pulled). See docs/cp1_serve_deploy_plan.md for
#   recovery paths (A re-train, B defer to r14 post-C1).
#
# USAGE
#   bash tool/cp1_serve_launch.bash --dry-run                     # default
#   bash tool/cp1_serve_launch.bash --apply --yes-i-mean-it       # real
#   bash tool/cp1_serve_launch.bash --help
#
# ENV OVERRIDES
#   CP1_ADAPTER_PATH   path to trained p1 adapter dir (default state/trained_adapters/p1)
#   CP1_BASE_MODEL     HF base model id (default Qwen/Qwen3-8B)
#   CP1_GPU_COUNT      default 1 (CP1 is single-pod persistent)
#   CP1_BID_USD        default 4.00/hr (1× H100 on-demand secureCloud cap)
#
# EXIT
#   0 = dry-run pass OR apply success
#   1 = prereq fail (adapter missing)
#   2 = pod spawn failed
#   3 = --apply without --yes-i-mean-it
set -euo pipefail

readonly ANIMA_ROOT="/Users/ghost/core/anima"
# 2026-04-24 ROI V8: adapter_pull writes to state/trained_adapters/pN/final/
# (preserving pod-side layout), so default path is final/.
readonly ADAPTER_PATH="${CP1_ADAPTER_PATH:-${ANIMA_ROOT}/state/trained_adapters/p1/final}"
readonly BASE_MODEL="${CP1_BASE_MODEL:-Qwen/Qwen3-8B}"
readonly GPU_COUNT="${CP1_GPU_COUNT:-1}"
readonly BID_USD="${CP1_BID_USD:-4.00}"
readonly CLOUD_TIER="secureCloud"
readonly POD_NAME="anima-cp1-dest1-persona"
readonly STAGE2_IMAGE="runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04"
readonly SERVE_PORT=8000
readonly STATE_OUT="${ANIMA_ROOT}/state/cp1_serve_launch_state.json"
readonly RUNPODCTL="/opt/homebrew/bin/runpodctl"
readonly TS="$(date -u +%Y%m%dT%H%M%SZ)"
readonly LOG="/tmp/cp1_serve_launch_${TS}.log"

exec > >(tee -a "${LOG}") 2>&1
log() { printf '[%s] %s\n' "$(date -u +%H:%M:%SZ)" "$*"; }

MODE="dry-run"; CONFIRM=""
for arg in "$@"; do
  case "$arg" in
    --dry-run)        MODE="dry-run" ;;
    --apply)          MODE="apply" ;;
    --yes-i-mean-it)  CONFIRM="yes" ;;
    --help|-h)        sed -n '1,30p' "$0"; exit 0 ;;
    *)                log "unknown arg: $arg"; exit 2 ;;
  esac
done

log "mode=${MODE} log=${LOG}"
log "base_model=${BASE_MODEL}  adapter=${ADAPTER_PATH}  gpu=${GPU_COUNT}  bid=\$${BID_USD}/hr"

# --- prereq check -------------------------------------------------------------
log "prereq: trained adapter dir"
if [[ ! -d "${ADAPTER_PATH}" ]]; then
  log "  [FAIL] ${ADAPTER_PATH} missing"
  log "  Recovery (docs/cp1_serve_deploy_plan.md):"
  log "    A. Re-launch Stage-2 training and scp -r /workspace/trained_p1/final/ → state/trained_adapters/p1/"
  log "    B. Defer CP1 to r14 retrain (preferred — r14 gives cleaner baseline)"
  exit 1
fi
for required in adapter_config.json adapter_model.safetensors; do
  if [[ ! -f "${ADAPTER_PATH}/${required}" ]]; then
    log "  [FAIL] ${ADAPTER_PATH}/${required} missing"
    exit 1
  fi
done
log "  [PASS] adapter_config.json + adapter_model.safetensors present"

# --- dry-run output -----------------------------------------------------------
if [[ "${MODE}" == "dry-run" ]]; then
  log ""
  log "DRY-RUN: planned pod spawn:"
  log "  ${RUNPODCTL} create pod --gpuType 'NVIDIA H100 80GB HBM3' --gpuCount ${GPU_COUNT} \\"
  log "    --${CLOUD_TIER} --name ${POD_NAME} --imageName ${STAGE2_IMAGE} \\"
  log "    --cost ${BID_USD} --containerDiskSize 120 --volumeSize 100 --volumePath /workspace \\"
  log "    --startSSH --ports '22/tcp,${SERVE_PORT}/http' \\"
  log "    --env ANIMA_ROLE=cp1-serve --env CP1_BASE_MODEL=${BASE_MODEL} \\"
  log "    --env CP1_SERVE_PORT=${SERVE_PORT} --env IDLE_KILL_MIN=0   # persistent, auto_kill DISABLED"
  log ""
  log "DRY-RUN: post-spawn chain (ssh, pod-side):"
  log "  1. scp -r ${ADAPTER_PATH} root@<pod>:/workspace/adapter_p1/"
  log "  2. pip install fastapi uvicorn vllm peft transformers>=4.44 hf_transfer"
  log "  3. ship serve driver (python heredoc, NOT committed per HEXA-FIRST)"
  log "  4. nohup python3 /workspace/serve.py > /workspace/serve.log 2>&1 &"
  log "  5. curl http://<pod>:${SERVE_PORT}/health  # expect {\"status\":\"ready\",\"adapter\":\"p1\"}"
  log ""
  log "DRY-RUN: CP1 gate (manual verification post-apply):"
  log "  - p99 latency <500ms at bs=1: ab -n 1000 -c 1 http://<pod>:${SERVE_PORT}/infer"
  log "  - uptime ≥99.5% / 24h observation: external uptime checker"
  log "  - /phi endpoint returns valid spectrum JSON"
  log ""
  log "DRY-RUN: to actually launch run: $0 --apply --yes-i-mean-it"
  exit 0
fi

# --- apply mode ---------------------------------------------------------------
if [[ "${CONFIRM}" != "yes" ]]; then
  log "ERROR: --apply requires --yes-i-mean-it"
  exit 3
fi

log "APPLY: spawning CP1 pod"
out=$("${RUNPODCTL}" create pod \
  --gpuType "NVIDIA H100 80GB HBM3" --gpuCount "${GPU_COUNT}" \
  --"${CLOUD_TIER}" \
  --name "${POD_NAME}" \
  --imageName "${STAGE2_IMAGE}" \
  --cost "${BID_USD}" --containerDiskSize 120 --volumeSize 100 --volumePath /workspace \
  --startSSH --ports "22/tcp,${SERVE_PORT}/http" \
  --env "ANIMA_ROLE=cp1-serve" \
  --env "CP1_BASE_MODEL=${BASE_MODEL}" \
  --env "CP1_SERVE_PORT=${SERVE_PORT}" \
  --env "IDLE_KILL_MIN=0" \
  2>&1) || { log "LAUNCH FAIL: ${out}"; exit 2; }

# runpodctl 1.x output parser (see tool/h100_stage2_unified_launch.bash ROI V5)
pod_id=$(echo "${out}" | grep -oE 'pod "[a-z0-9]+" created' | head -1 | sed 's/pod "\([^"]*\)".*/\1/' || true)
if [[ -z "${pod_id}" ]]; then
  log "LAUNCH FAIL: could not parse pod_id from:"; log "${out}"; exit 2
fi
log "  pod_id=${pod_id}  name=${POD_NAME}  port=${SERVE_PORT}"

# Write state JSON
cat > "${STATE_OUT}" <<EOF
{
  "schema": "anima/cp1_serve_launch_state/1",
  "launched_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "roadmap_entry": 77,
  "pod_id": "${pod_id}",
  "pod_name": "${POD_NAME}",
  "base_model": "${BASE_MODEL}",
  "adapter_path": "${ADAPTER_PATH}",
  "gpu_count": ${GPU_COUNT},
  "bid_usd_per_hr": ${BID_USD},
  "cloud_tier": "${CLOUD_TIER}",
  "serve_port": ${SERVE_PORT},
  "policy": {"auto_kill_min": 0, "persistent": true, "note": "CP1 is persistent; does NOT join h100_auto_kill registry"},
  "log": "${LOG}",
  "next_step": "ssh bootstrap + serve driver + health check (see docs/cp1_serve_deploy_plan.md §Deploy recipe)"
}
EOF
log "launch state written: ${STATE_OUT}"
log "APPLY: complete. CP1 pod live. Next manual step: ssh bootstrap + serve driver ship."
exit 0
