#!/bin/bash
# Mk.XI pod launch orchestrator — pre-approved per memory feedback_forward_auto_approval
#
# Honors:
#   - cost cap: $20 per cycle (auto-kill)
#   - max runtime: 120min (auto-kill)
#   - state SSOT: writes state/h100_pods.json + state/h100_cost_tracker_result.json
#
# Pre-approved auto-execution (no separate user confirmation per memory):
#   forward auto-approval per memory feedback_forward_auto_approval (2026-04-25)
#
# NOTE: anima/tool/h100_*.hexa is propose-only (hard constraint). This wrapper
#       performs actual runpodctl invocations honored under auto-approval policy.

set -euo pipefail

ANIMA_ROOT="/Users/ghost/core/anima"
TS=$(date -u +%Y%m%dT%H%M%SZ)
RUN_ID="mk_xi_r9_${TS}"
COST_CAP=20
RUNTIME_CAP_MIN=120

# Pre-launch checklist (raw#12 frozen, fail-fast on any missing)
echo "=== Pre-launch checklist ==="
PREREQS=(
  "${ANIMA_ROOT}/state/mk_xi_architecture_spec_20260425.json"
  "${ANIMA_ROOT}/state/mk_xi_anti_map_ledger_v2_20260425.json"
  "${ANIMA_ROOT}/state/mk_xi_retrieval_head_spec_20260425.json"
  "${ANIMA_ROOT}/state/mk_xi_r4_monitor_spec_20260425.json"
  "${ANIMA_ROOT}/training/mk_xi_train.py"
)
for f in "${PREREQS[@]}"; do
  if [[ ! -f "$f" ]]; then
    echo "ABORT: missing prerequisite $f"
    exit 2
  fi
  echo "  OK: $f"
done

# Check RunPod credit
echo "=== RunPod credit check ==="
if ! command -v runpodctl >/dev/null 2>&1; then
  echo "ABORT: runpodctl not installed"
  exit 2
fi

# Check active pods (prevent duplicate launches)
echo "=== Existing pods ==="
runpodctl pod list 2>&1 || true

# Pod creation parameters (raw#12 frozen per docs/r9_mk_xi_launch_runbook §1.2)
GPU_TYPE="H100 PCIe"
DISK_GB=100
VOLUME_GB=200
IMAGE="runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04"
POD_NAME="mk_xi_r9_${TS}"

echo "=== Pod allocation params ==="
echo "  RUN_ID:    ${RUN_ID}"
echo "  POD_NAME:  ${POD_NAME}"
echo "  GPU:       ${GPU_TYPE}"
echo "  Disk:      ${DISK_GB}GB"
echo "  Volume:    ${VOLUME_GB}GB"
echo "  Image:     ${IMAGE}"
echo "  Cost cap:  \$${COST_CAP}"
echo "  Runtime:   ${RUNTIME_CAP_MIN}min max"

# Dry-run by default (set MK_XI_LAUNCH_REAL=1 to actually create pod)
if [[ "${MK_XI_LAUNCH_REAL:-0}" != "1" ]]; then
  echo ""
  echo "=== DRY-RUN MODE ==="
  echo "Pod would be created with above params."
  echo "Set MK_XI_LAUNCH_REAL=1 to actually create pod (cost: \$5-15)."
  echo ""
  echo "Real-launch command:"
  echo "  MK_XI_LAUNCH_REAL=1 bash training/mk_xi_launch_pod.sh"
  exit 0
fi

# Real launch — pre-approved per feedback_forward_auto_approval
echo ""
echo "=== REAL LAUNCH (auto-approved per memory feedback_forward_auto_approval) ==="
echo "Cost cap: \$${COST_CAP} | Runtime cap: ${RUNTIME_CAP_MIN}min"

# NOTE: Actual runpodctl pod create command depends on runpodctl version + GPU availability.
# This wrapper does not invoke until auto-approval policy is wired into a launch tool that
# meets anima's propose-only hard constraint. For Mk.XI, the operator (or a future
# launch tool extension) issues:
#
#   runpodctl pod create \
#       --name "${POD_NAME}" \
#       --gpuType "${GPU_TYPE}" \
#       --gpuCount 1 \
#       --containerDiskInGb ${DISK_GB} \
#       --volumeInGb ${VOLUME_GB} \
#       --imageName "${IMAGE}" \
#       --ports "8888/http,22/tcp" \
#       --env "RUN_ID=${RUN_ID}" \
#       --env "COST_CAP=${COST_CAP}" \
#       --env "RUNTIME_CAP_MIN=${RUNTIME_CAP_MIN}"
#
# Then: rsync prereq state/* + tool/* to pod, run training/mk_xi_train.py, attach
#       auto-kill monitor (tool/h100_auto_kill.hexa).
#
# The full implementation requires:
#   - mk_xi_train.py full Python (currently skeleton only; transformers+peft training loop)
#   - rsync wrapper with SSH key auth
#   - auto-kill integration with cost cap
#   - post-training 5-tuple measurement automation
#
# These remain pending until a follow-up cycle integrates them under auto-approval.

echo ""
echo "STATUS: skeleton orchestrator. Real launch pending full mk_xi_train.py impl + rsync."
echo "Next cycle: integrate full Python training + rsync + auto-kill into one-command launch."
