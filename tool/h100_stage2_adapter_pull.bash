#!/usr/bin/env bash
# tool/h100_stage2_adapter_pull.bash
#
# PURPOSE
#   Post-training: pull FULL trained adapter dirs from all 4 pods BEFORE
#   killing. Fixes convergence mistake #5 (2026-04-24) where we pulled only
#   h_last_raw_*.json and lost /workspace/trained_pN/final/ with pod kill.
#
#   Without this tool, CP1 (#77 dest1 persona LIVE) cannot ship — the
#   trained adapter is the primary serving artifact.
#
# CHAIN
#   1. Wait until all 4 pods have completed training (h_last_raw.json exists)
#   2. scp -r /workspace/trained_pN/final/ → state/trained_adapters/pN/
#   3. Verify per-pod adapter_config.json + adapter_model.safetensors present
#   4. (Optional) kill pods after successful pull
#
# USAGE
#   bash tool/h100_stage2_adapter_pull.bash                 # pull only, keep pods
#   bash tool/h100_stage2_adapter_pull.bash --kill-after    # pull then kill
#   bash tool/h100_stage2_adapter_pull.bash --timeout 3600  # wait up to 1h (default 3600)
#
# EXIT
#   0 = all 4 adapters pulled + validated
#   1 = launch_state or pod registry missing
#   2 = ≥1 pod training did not complete within timeout
#   3 = ≥1 adapter pull failed OR validation missing adapter_model.safetensors
set -euo pipefail

readonly ANIMA_ROOT="/Users/ghost/core/anima"
readonly LAUNCH_STATE="${ANIMA_ROOT}/state/h100_stage2_launch_state.json"
readonly PODS_CFG="${ANIMA_ROOT}/config/h100_pods.json"
readonly OUT_BASE="${ANIMA_ROOT}/state/trained_adapters"
readonly RUNPODCTL="/opt/homebrew/bin/runpodctl"
readonly TS="$(date -u +%Y%m%dT%H%M%SZ)"
readonly LOG="/tmp/h100_adapter_pull_${TS}.log"

exec > >(tee -a "${LOG}") 2>&1
log() { printf '[%s] %s\n' "$(date -u +%H:%M:%SZ)" "$*"; }

KILL_AFTER=0
TIMEOUT_SEC=3600
for arg in "$@"; do
  case "$arg" in
    --kill-after)    KILL_AFTER=1 ;;
    --timeout)       shift; TIMEOUT_SEC="$1" ;;
    --timeout=*)     TIMEOUT_SEC="${arg#*=}" ;;
    --help|-h)       sed -n '1,30p' "$0"; exit 0 ;;
    *)               log "unknown arg: $arg"; exit 1 ;;
  esac
done

log "adapter_pull start (timeout=${TIMEOUT_SEC}s, kill_after=${KILL_AFTER})"
log "log=${LOG}"

[[ -f "${LAUNCH_STATE}" ]] || { log "ABORT: launch_state missing"; exit 1; }
[[ -f "${PODS_CFG}" ]]     || { log "ABORT: pods config missing"; exit 1; }

mkdir -p "${OUT_BASE}"

# Build pid → (host, port, pod_id) from launch_state JOINed with pods_cfg
POD_LIST=$(python3 <<PYEOF
import json, sys
ls = json.load(open("${LAUNCH_STATE}"))
pc = json.load(open("${PODS_CFG}"))
by_pod = {p["pod_id"]: p for p in pc.get("pods", [])}
for entry in ls.get("pods", []):
    pid = entry["path_id"]; pod_id = entry["pod_id"]
    cfg = by_pod.get(pod_id)
    if not cfg: continue
    print(f'{pid}:{pod_id}:{cfg["ssh_host"]}:{cfg["ssh_port"]}')
PYEOF
)

if [[ -z "${POD_LIST}" ]]; then
  log "ABORT: no pods found in launch_state ∩ pods_cfg"; exit 1
fi

log "pods to pull from:"
echo "${POD_LIST}" | sed 's/^/  /'

# --- step 1: wait for training completion on all pods ------------------------
log "step 1/4: waiting for training completion (h_last_raw.json appears)"
deadline=$(( $(date +%s) + TIMEOUT_SEC ))
while true; do
  done_n=0
  for entry in ${POD_LIST}; do
    IFS=':' read -r pid pod_id host port <<< "$entry"
    if ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -p "$port" "root@${host}" \
      "test -f /workspace/trained_${pid}/h_last_raw.json" 2>/dev/null; then
      done_n=$((done_n + 1))
    fi
  done
  if [[ "${done_n}" -eq 4 ]]; then
    log "  all 4 pods have h_last_raw.json — training complete"
    break
  fi
  if [[ $(date +%s) -ge ${deadline} ]]; then
    log "ABORT: timeout — only ${done_n}/4 pods done within ${TIMEOUT_SEC}s"
    exit 2
  fi
  log "  ${done_n}/4 done, waiting..."
  sleep 30
done

# --- step 2: pull full adapter dirs ------------------------------------------
log "step 2/4: scp -r /workspace/trained_pN/final/ → state/trained_adapters/pN/"
pull_fail=0
for entry in ${POD_LIST}; do
  IFS=':' read -r pid pod_id host port <<< "$entry"
  out_dir="${OUT_BASE}/${pid}"
  rm -rf "${out_dir}"  # clean slate per pod
  mkdir -p "${out_dir}"
  log "  [${pid}] scp from ${host}:${port}"
  if scp -o StrictHostKeyChecking=no -P "$port" -r \
    "root@${host}:/workspace/trained_${pid}/final/" "${out_dir}/" 2>&1 | tail -3; then
    log "    [PASS] ${pid} adapter pulled"
  else
    log "    [FAIL] ${pid} adapter pull failed"
    pull_fail=$((pull_fail + 1))
  fi
done

# --- step 3: validate pulled adapters ----------------------------------------
log "step 3/4: validate pulled adapters"
val_fail=0
for entry in ${POD_LIST}; do
  IFS=':' read -r pid pod_id host port <<< "$entry"
  dir="${OUT_BASE}/${pid}/final"
  missing=0
  for req in adapter_config.json adapter_model.safetensors; do
    if [[ ! -f "${dir}/${req}" ]]; then
      log "  [FAIL] ${pid}: missing ${req}"
      missing=$((missing + 1))
    fi
  done
  if [[ ${missing} -eq 0 ]]; then
    size=$(du -sh "${dir}" | awk '{print $1}')
    log "  [PASS] ${pid} validated (${size})"
  else
    val_fail=$((val_fail + 1))
  fi
done

if [[ ${pull_fail} -gt 0 || ${val_fail} -gt 0 ]]; then
  log "ADAPTER_PULL FAIL — pull_fail=${pull_fail} val_fail=${val_fail}"
  log "pods NOT killed (preserved for retry)"
  exit 3
fi

# --- step 4: optionally kill pods --------------------------------------------
if [[ ${KILL_AFTER} -eq 1 ]]; then
  log "step 4/4: killing all 4 pods (--kill-after)"
  for entry in ${POD_LIST}; do
    IFS=':' read -r pid pod_id host port <<< "$entry"
    "${RUNPODCTL}" remove pod "${pod_id}" 2>&1 | tail -1
  done
  # Sync pod registry
  bash "${ANIMA_ROOT}/tool/h100_pods_sync.bash" 2>&1 | tail -2
else
  log "step 4/4: SKIP kill (pods kept alive, --kill-after to kill)"
fi

# --- write state -------------------------------------------------------------
STATE_OUT="${ANIMA_ROOT}/state/h100_stage2_adapter_pull_state.json"
cat > "${STATE_OUT}" <<EOF
{
  "schema": "anima/h100_stage2_adapter_pull_state/1",
  "generated_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "launch_state_ref": "${LAUNCH_STATE}",
  "adapters_pulled": [
$(first=1; for entry in ${POD_LIST}; do
    IFS=':' read -r pid pod_id host port <<< "$entry"
    if [[ $first -eq 1 ]]; then first=0; else printf ',\n'; fi
    sz=$(du -sh "${OUT_BASE}/${pid}/final" 2>/dev/null | awk '{print $1}')
    printf '    {"path_id": "%s", "pod_id": "%s", "local_path": "state/trained_adapters/%s/final", "size": "%s"}' \
      "${pid}" "${pod_id}" "${pid}" "${sz}"
done)
  ],
  "pods_killed_after_pull": $(if [[ ${KILL_AFTER} -eq 1 ]]; then echo true; else echo false; fi),
  "log": "${LOG}"
}
EOF

log "state written: ${STATE_OUT}"
log "adapter_pull COMPLETE — CP1 prereq (state/trained_adapters/p1/final/) now present"
log "next: bash tool/cp1_serve_launch.bash --apply --yes-i-mean-it"
exit 0
