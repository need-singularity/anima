#!/usr/bin/env bash
# tool/h100_stage2_unified_launch.sh — H100 x4 Stage-2 unified launch (Phi 4-path)
#
# Roadmap: #10 Phi 4-path substrate independence (Stage-2 of h100_launch_manifest)
# Coordinates 4 parallel H100 pod kickoffs, one per substrate path (p1..p4),
# wires h100_auto_kill guard (idle 30min), and enforces frozen abort thresholds
# from state/h100_launch_manifest.json.
#
# raw#9  deterministic: pre-flight checks in fixed order, thresholds read from SSOT
# raw#10 proof-carrying: writes state/h100_stage2_launch_state.json with pod ids
# raw#20 H100 stop-gate: real launch REQUIRES user approval; default is --dry-run
#
# USAGE
#   tool/h100_stage2_unified_launch.sh --dry-run               # default - verify only
#   tool/h100_stage2_unified_launch.sh --apply --yes-i-mean-it # real launch
#   tool/h100_stage2_unified_launch.sh --help
#
# EXIT
#   0 = all pre-flight PASS (dry-run) OR launch succeeded (apply)
#   1 = pre-flight FAIL
#   2 = missing CLI / auth / bad arg
#   3 = --apply without explicit user confirm
set -euo pipefail

# --- constants ----------------------------------------------------------------
readonly ANIMA_ROOT="/Users/ghost/core/anima"
readonly SUBSTRATES_CFG="${ANIMA_ROOT}/config/phi_4path_substrates.json"
readonly LORA_RANK_CFG="${ANIMA_ROOT}/config/lora_rank_per_path.json"
readonly LAUNCH_MANIFEST="${ANIMA_ROOT}/state/h100_launch_manifest.json"
readonly LAUNCH_STATE="${ANIMA_ROOT}/state/h100_stage2_launch_state.json"
readonly AUTO_KILL_PODS="${ANIMA_ROOT}/config/h100_pods.json"
readonly RUNPODCTL="/opt/homebrew/bin/runpodctl"
readonly HF_CLI="/opt/homebrew/bin/hf"

readonly STAGE2_IMAGE="runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04"
# 2026-04-24 policy: auto-charge absorbs all burn. Balance/budget checks NEVER halt launch.
# config/runpod_auto_charge.json + config/h100_max_parallelism_policy.json are SSOTs.
readonly BUDGET_USD_HARD_CAP=0  # 0 = unlimited (auto-charge, no-cap policy 2026-04-24)
readonly NUMERICAL_DRIFT_BOUND="0.0002"
readonly IDLE_MINUTES_MAX=5  # 2026-04-22 ROI A2: 30→5 min
readonly PHI_REL_DELTA_MAX="0.05"
readonly MIN_PATHS_PASS=3
# 2026-04-22 ROI V1: spot bid lock — H100 SXM5 secure-cloud bid ceiling.
# runpodctl uses --cost as $/hr price CEILING (bid) for the ENTIRE pod (all GPUs total).
# secureCloud=stable supply for H100.
# 2026-04-24 ROI V2: per-pod GPU count. Default 4 for data-parallel LoRA speedup.
# Same GPU-hour as 1-GPU×4×wall; wall-clock 4× shorter. No cap under max-parallelism policy.
# Override: export ANIMA_H100_GPUCOUNT_PER_POD=<int> ; default 4.
readonly GPU_COUNT_PER_POD="${ANIMA_H100_GPUCOUNT_PER_POD:-4}"
# 2026-04-24 ROI V3: bid MUST scale with GPU count since --cost is per-pod total.
# per-GPU ceiling default 3.50 (calibrated 2026-04-22); total bid = per-GPU × count.
# Override absolute: export ANIMA_H100_BID_USD=<float>  (overrides scaling)
# Override per-GPU: export ANIMA_H100_BID_USD_PER_GPU=<float>  (keeps scaling)
readonly BID_USD_PER_HR_PER_GPU="${ANIMA_H100_BID_USD_PER_GPU:-3.50}"
_scale_bid() {
  awk -v per="${BID_USD_PER_HR_PER_GPU}" -v n="${GPU_COUNT_PER_POD}" 'BEGIN { printf "%.2f", per * n }'
}
readonly BID_USD_PER_HR="${ANIMA_H100_BID_USD:-$(_scale_bid)}"
readonly CLOUD_TIER="secureCloud"  # secureCloud | communityCloud — locked secure for H100 SXM5

readonly TS="$(date -u +%Y%m%dT%H%M%SZ)"
readonly LOG="/tmp/h100_stage2_launch_${TS}.log"

# --- log helpers --------------------------------------------------------------
exec > >(tee -a "${LOG}") 2>&1
log()        { printf '[%s] %s\n' "$(date -u +%H:%M:%SZ)" "$*"; }
pass()       { printf '  [PASS] %s\n' "$*"; }
mark_fail()  { printf '  [FAIL] %s\n' "$*"; FAIL_N=$((FAIL_N+1)); }
warn()       { printf '  [WARN] %s\n' "$*"; }

# --- argv ---------------------------------------------------------------------
MODE="dry-run"
CONFIRM=""
AUTO_KICKOFF="yes"   # 2026-04-24 default: NO IDLE — bootstrap + training auto-chained post-spawn.
                     # Disable with --no-auto-kickoff (manual multi-step flow, old behavior).
for arg in "$@"; do
  case "$arg" in
    --dry-run)            MODE="dry-run" ;;
    --apply)              MODE="apply" ;;
    --yes-i-mean-it)      CONFIRM="yes" ;;
    --auto-kickoff)       AUTO_KICKOFF="yes" ;;
    --no-auto-kickoff)    AUTO_KICKOFF="no" ;;
    --help|-h)            sed -n '1,20p' "$0"; exit 0 ;;
    *) log "unknown arg: $arg"; exit 2 ;;
  esac
done

log "mode=${MODE} log=${LOG}"
log "anima_root=${ANIMA_ROOT}"

# 2026-04-22 ROI A3+V1: spot enforce, ondemand fallback block, bid lock verification.
if [[ "${RUNPOD_GPU_TYPE_FLAG:-}" == "ondemand" ]]; then echo "ABORT: ondemand disallowed per manifest"; exit 4; fi
# V1 spot bid lock: BID_USD_PER_HR must be a positive float; CLOUD_TIER must be secureCloud (H100 SXM5).
# 2026-04-24: upper bound scales with GPU_COUNT_PER_POD (--cost is per-pod total, not per-GPU).
# Sane per-GPU ceiling ≤ $10/hr ⇒ per-pod ceiling ≤ $10 × GPUs. Extra 20% slack for market spikes.
_BID_UPPER=$(awk -v n="${GPU_COUNT_PER_POD}" 'BEGIN { printf "%.2f", 10 * n * 1.2 }')
if ! awk -v v="${BID_USD_PER_HR}" -v max="${_BID_UPPER}" 'BEGIN{exit !(v+0>0 && v+0<=max+0)}'; then
  echo "ABORT: BID_USD_PER_HR=${BID_USD_PER_HR} out of sane range (0,${_BID_UPPER}] $/hr (per-pod total for ${GPU_COUNT_PER_POD} GPUs)"; exit 4
fi
if [[ "${CLOUD_TIER}" != "secureCloud" && "${CLOUD_TIER}" != "communityCloud" ]]; then
  echo "ABORT: CLOUD_TIER=${CLOUD_TIER} invalid (must be secureCloud|communityCloud)"; exit 4
fi
# Echo the lock so dry-run output proves the bid ceiling is wired.
log "V1 spot_bid_lock: cloud_tier=${CLOUD_TIER} bid_usd_per_hr=${BID_USD_PER_HR}"

FAIL_N=0

# --- pre-flight 1: substrates config ------------------------------------------
log "pre-flight 1/6: phi_4path_substrates.json"
MODEL_P1=""; MODEL_P2=""; MODEL_P3=""; MODEL_P4=""
if [[ -f "${SUBSTRATES_CFG}" ]]; then
  pass "substrates config exists"
  path_count=$(grep -cE '"id": "p[1-4]"' "${SUBSTRATES_CFG}" || true)
  if [[ "${path_count}" -eq 4 ]]; then
    pass "4 paths (p1..p4) verified"
  else
    mark_fail "expected 4 paths, got ${path_count}"
  fi
  MODEL_P1=$(grep -A3 '"id": "p1"' "${SUBSTRATES_CFG}" | grep -oE '"model": "[^"]+"' | head -1 | sed 's/"model": "\(.*\)"/\1/')
  MODEL_P2=$(grep -A3 '"id": "p2"' "${SUBSTRATES_CFG}" | grep -oE '"model": "[^"]+"' | head -1 | sed 's/"model": "\(.*\)"/\1/')
  MODEL_P3=$(grep -A3 '"id": "p3"' "${SUBSTRATES_CFG}" | grep -oE '"model": "[^"]+"' | head -1 | sed 's/"model": "\(.*\)"/\1/')
  MODEL_P4=$(grep -A3 '"id": "p4"' "${SUBSTRATES_CFG}" | grep -oE '"model": "[^"]+"' | head -1 | sed 's/"model": "\(.*\)"/\1/')
  log "    p1=${MODEL_P1}  p2=${MODEL_P2}  p3=${MODEL_P3}  p4=${MODEL_P4}"

  # 2026-04-24 ROI V4: HF accessibility pre-check + auto-fallback from fallback_chain.
  # Prevents mid-launch pod-side failures (p2 gated / p3 multimodal / p4 qlora incompat
  # — captured in state/convergence/h100_stage2_20260424.json mistakes 3-5).
  HF_TOKEN_FILE="${HOME}/.cache/huggingface/token"
  HF_TOKEN_VAL=""
  if [[ -f "${HF_TOKEN_FILE}" ]]; then
    HF_TOKEN_VAL="$(cat "${HF_TOKEN_FILE}")"
  fi

  _hf_accessible() {
    # HEAD /config.json — returns 0 iff 200 OK (accessible).
    local model="$1"
    local code
    if [[ -n "${HF_TOKEN_VAL}" ]]; then
      code=$(curl -s -o /dev/null -w '%{http_code}' -L \
        -H "Authorization: Bearer ${HF_TOKEN_VAL}" \
        "https://huggingface.co/${model}/resolve/main/config.json" 2>/dev/null || echo 000)
    else
      code=$(curl -s -o /dev/null -w '%{http_code}' -L \
        "https://huggingface.co/${model}/resolve/main/config.json" 2>/dev/null || echo 000)
    fi
    [[ "${code}" == "200" ]]
  }

  _resolve_model_with_fallback() {
    # _resolve_model_with_fallback <pid>  → echoes resolved model id
    local pid="$1"
    local primary fallbacks hazards_n
    primary=$(python3 -c 'import json,sys
c=json.load(open(sys.argv[1]))
for p in c["paths"]:
    if p["id"]==sys.argv[2]:
        print(p["model"]); break' "${SUBSTRATES_CFG}" "${pid}" 2>/dev/null)
    fallbacks=$(python3 -c 'import json,sys
c=json.load(open(sys.argv[1]))
for p in c["paths"]:
    if p["id"]==sys.argv[2]:
        fc=p.get("fallback_chain",[])
        print(" ".join(fc)); break' "${SUBSTRATES_CFG}" "${pid}" 2>/dev/null)
    hazards_n=$(python3 -c 'import json,sys
c=json.load(open(sys.argv[1]))
for p in c["paths"]:
    if p["id"]==sys.argv[2]:
        print(len(p.get("training_hazards",[]))); break' "${SUBSTRATES_CFG}" "${pid}" 2>/dev/null || echo 0)

    # HAZARD-AWARE: if primary has known training_hazards (multimodal wrapper,
    # dev-version transformers dep, etc.), bypass HF HEAD check and use
    # fallback_chain[0] directly. HEAD returns 200 for these but runtime
    # model-loading fails — cannot be detected at HTTP level.
    if [[ "${hazards_n}" -gt 0 ]]; then
      local first_fb
      first_fb=$(echo "${fallbacks}" | awk '{print $1}')
      if [[ -n "${first_fb}" ]] && [[ "${first_fb}" != "${primary}" ]]; then
        if _hf_accessible "${first_fb}"; then
          log "  [HAZARD_SUBST] ${pid}: ${primary} → ${first_fb} (training_hazards=${hazards_n}, bypass HEAD)"
          echo "${first_fb}"
          return 0
        fi
      fi
    fi

    # No hazards path: trust primary if accessible
    if _hf_accessible "${primary}"; then
      echo "${primary}"
      return 0
    fi
    log "  [WARN] ${pid}: primary ${primary} UNREACHABLE — trying fallback chain"
    for fb in ${fallbacks}; do
      if [[ "${fb}" == "${primary}" ]]; then continue; fi
      if _hf_accessible "${fb}"; then
        log "  [SUBST] ${pid}: ${primary} → ${fb}"
        echo "${fb}"
        return 0
      fi
    done
    log "  [FAIL] ${pid}: NO fallback accessible for primary=${primary}"
    echo ""
    return 1
  }

  log "  HF accessibility pre-check (2026-04-24 ROI V4):"
  MODEL_P1_RESOLVED=$(_resolve_model_with_fallback p1) || FAIL_N=$((FAIL_N+1))
  MODEL_P2_RESOLVED=$(_resolve_model_with_fallback p2) || FAIL_N=$((FAIL_N+1))
  MODEL_P3_RESOLVED=$(_resolve_model_with_fallback p3) || FAIL_N=$((FAIL_N+1))
  MODEL_P4_RESOLVED=$(_resolve_model_with_fallback p4) || FAIL_N=$((FAIL_N+1))
  # Apply resolved substitutions
  [[ -n "${MODEL_P1_RESOLVED}" ]] && MODEL_P1="${MODEL_P1_RESOLVED}"
  [[ -n "${MODEL_P2_RESOLVED}" ]] && MODEL_P2="${MODEL_P2_RESOLVED}"
  [[ -n "${MODEL_P3_RESOLVED}" ]] && MODEL_P3="${MODEL_P3_RESOLVED}"
  [[ -n "${MODEL_P4_RESOLVED}" ]] && MODEL_P4="${MODEL_P4_RESOLVED}"
  log "  resolved: p1=${MODEL_P1}  p2=${MODEL_P2}  p3=${MODEL_P3}  p4=${MODEL_P4}"
else
  mark_fail "substrates config missing: ${SUBSTRATES_CFG}"
fi

# --- pre-flight 2: lora rank config -------------------------------------------
log "pre-flight 2/6: lora_rank_per_path.json (P2.1 Agent output)"
if [[ -f "${LORA_RANK_CFG}" ]]; then
  pass "lora rank config exists"
else
  mark_fail "lora rank config missing: ${LORA_RANK_CFG} - P2.1 Agent must land it first"
fi

# --- pre-flight 3: launch manifest stage2 verdict -----------------------------
log "pre-flight 3/6: h100_launch_manifest.json stage2 verdict"
if [[ -f "${LAUNCH_MANIFEST}" ]]; then
  stage2_verdict=$(python3 -c 'import json,sys
m=json.load(open(sys.argv[1]))
for st in m.get("stages",[]):
    if st.get("stage")==2:
        print(st.get("verdict","")); break' "${LAUNCH_MANIFEST}" 2>/dev/null || true)
  log "    stage2_verdict=${stage2_verdict:-<none>}"
  if [[ "${stage2_verdict}" == "READY" ]]; then
    pass "stage2 verdict=READY"
  else
    mark_fail "stage2 verdict=${stage2_verdict:-<missing>} - expected READY (re-run tool/h100_launch_manifest_spec.hexa after Stage-1 close)"
  fi
else
  mark_fail "launch manifest missing: ${LAUNCH_MANIFEST}"
fi

# --- pre-flight 4: runpodctl auth ---------------------------------------------
log "pre-flight 4/6: runpodctl auth"
if [[ -x "${RUNPODCTL}" ]]; then
  pass "runpodctl binary: ${RUNPODCTL}"
  if "${RUNPODCTL}" pod list >/dev/null 2>&1; then
    pass "runpodctl authenticated (pod list OK)"
  else
    mark_fail "runpodctl not authenticated - run: runpodctl doctor"
  fi
else
  mark_fail "runpodctl not found at ${RUNPODCTL}"
fi

# --- pre-flight 5: huggingface auth -------------------------------------------
log "pre-flight 5/6: huggingface auth"
if [[ -x "${HF_CLI}" ]]; then
  pass "hf binary: ${HF_CLI}"
  hf_out="$("${HF_CLI}" auth whoami 2>&1 || true)"
  hf_user_line=$(printf '%s\n' "${hf_out}" | sed 's/\x1b\[[0-9;]*m//g' | grep -iE '^user' | head -1 || true)
  if [[ -n "${hf_user_line}" ]]; then
    pass "hf authenticated (${hf_user_line})"
  else
    mark_fail "hf not authenticated - run: hf auth login"
  fi
else
  mark_fail "hf CLI not found at ${HF_CLI}"
fi

# --- pre-flight 6: auto_kill registry writable --------------------------------
log "pre-flight 6/6: h100_auto_kill pod registry writable"
if [[ -f "${AUTO_KILL_PODS}" && -w "${AUTO_KILL_PODS}" ]]; then
  pass "auto_kill registry present + writable: ${AUTO_KILL_PODS}"
else
  mark_fail "auto_kill registry missing or read-only: ${AUTO_KILL_PODS}"
fi

# --- summary ------------------------------------------------------------------
log ""
log "pre-flight summary: fail_n=${FAIL_N} / 6 checks"
log "policy: auto-charge ENABLED · balance/budget 언급 및 gate 완전 무시 (config/runpod_auto_charge.json + config/h100_max_parallelism_policy.json)"
log "abort_thresholds:"
log "  numerical_drift_bound  = ${NUMERICAL_DRIFT_BOUND}"
log "  idle_minutes_max       = ${IDLE_MINUTES_MAX}"
log "  phi_rel_delta_max      = ${PHI_REL_DELTA_MAX}"
log "  min_paths_pass         = ${MIN_PATHS_PASS}"
log "  gpu_count_per_pod      = ${GPU_COUNT_PER_POD} (max-parallelism policy; same GPU-hour, shorter wall)"

if [[ "${FAIL_N}" -gt 0 ]]; then
  log "RESULT: PRE-FLIGHT FAIL - cannot proceed with launch"
  exit 1
fi
log "RESULT: PRE-FLIGHT PASS"

# --- dry-run stops here -------------------------------------------------------
if [[ "${MODE}" == "dry-run" ]]; then
  log ""
  log "DRY-RUN: emitting planned runpodctl commands (NOT executing):"
  idx=0
  for path_model in "p1:${MODEL_P1}" "p2:${MODEL_P2}" "p3:${MODEL_P3}" "p4:${MODEL_P4}"; do
    idx=$((idx+1))
    pid="${path_model%%:*}"
    mdl="${path_model##*:}"
    mdl_tag=$(echo "${mdl}" | tr '[:upper:]' '[:lower:]' | tr '/._' '-' | tr -cd 'a-z0-9-' | cut -c1-32)
    pod_name="anima-${pid}-${mdl_tag}"
    log "  [${idx}/4] ${RUNPODCTL} create pod --gpuType 'NVIDIA H100 80GB HBM3' --gpuCount ${GPU_COUNT_PER_POD} \\"
    log "         --${CLOUD_TIER} \\"
    log "         --name ${pod_name} --imageName ${STAGE2_IMAGE} \\"
    log "         --cost ${BID_USD_PER_HR} --containerDiskSize 80 --volumeSize 200 --volumePath /workspace \\"
    log "         --startSSH --ports '22/tcp' \\"
    log "         --env ANIMA_STAGE=2 --env ANIMA_ROADMAP_ENTRY=10 --env HEXA_STRICT=1 \\"
    log "         --env PHI_PATH_ID=${pid} --env PHI_MODEL='${mdl}' --env PHI_THRESHOLD_REL=${PHI_REL_DELTA_MAX} \\"
    log "         --env PHI_GPUS_PER_POD=${GPU_COUNT_PER_POD} --env IDLE_KILL_MIN=${IDLE_MINUTES_MAX}"
  done
  log ""
  log "DRY-RUN: launch_state would be written to: ${LAUNCH_STATE}"
  log "DRY-RUN: auto_kill registry would be appended with 4 new pods (source=nvidia_smi, idle_threshold=${IDLE_MINUTES_MAX}min)"
  log "DRY-RUN: to actually launch (H100 STOP-GATE applies) run: $0 --apply --yes-i-mean-it"
  exit 0
fi

# --- apply mode: require explicit confirm -------------------------------------
if [[ "${MODE}" == "apply" && "${CONFIRM}" != "yes" ]]; then
  log "ERROR: --apply requires --yes-i-mean-it (H100 stop-gate - user approval mandatory)"
  exit 3
fi

# --- real launch (apply) ------------------------------------------------------
log "APPLY: kicking off 4x pods × ${GPU_COUNT_PER_POD} H100 GPU each = $((4 * GPU_COUNT_PER_POD)) GPUs total (Stage-2 Phi 4-path, max-parallelism policy)"
LAUNCHED_PODS=()
idx=0
for path_model in "p1:${MODEL_P1}" "p2:${MODEL_P2}" "p3:${MODEL_P3}" "p4:${MODEL_P4}"; do
  idx=$((idx+1))
  pid="${path_model%%:*}"
  mdl="${path_model##*:}"
  mdl_tag=$(echo "${mdl}" | tr '[:upper:]' '[:lower:]' | tr '/._' '-' | tr -cd 'a-z0-9-' | cut -c1-32)
  pod_name="anima-${pid}-${mdl_tag}"
  log "  [${idx}/4] launching ${pod_name} ..."
  # V1 spot bid lock: --secureCloud + --cost <bid ceiling>. runpodctl picks the
  # cheapest available offering at-or-below this ceiling; ondemand fallback was
  # already blocked above by RUNPOD_GPU_TYPE_FLAG guard.
  out=$("${RUNPODCTL}" create pod \
    --gpuType "NVIDIA H100 80GB HBM3" --gpuCount "${GPU_COUNT_PER_POD}" \
    --"${CLOUD_TIER}" \
    --name "${pod_name}" \
    --imageName "${STAGE2_IMAGE}" \
    --cost "${BID_USD_PER_HR}" --containerDiskSize 80 --volumeSize 200 --volumePath /workspace \
    --startSSH --ports "22/tcp" \
    --env "ANIMA_STAGE=2" \
    --env "ANIMA_ROADMAP_ENTRY=10" \
    --env "HEXA_STRICT=1" \
    --env "PHI_PATH_ID=${pid}" \
    --env "PHI_MODEL=${mdl}" \
    --env "PHI_THRESHOLD_REL=${PHI_REL_DELTA_MAX}" \
    --env "PHI_GPUS_PER_POD=${GPU_COUNT_PER_POD}" \
    --env "IDLE_KILL_MIN=${IDLE_MINUTES_MAX}" \
    2>&1) || { log "LAUNCH FAIL path=${pid}: ${out}"; exit 4; }
  # 2026-04-24 fix: runpodctl 1.x emits plain-text `pod "<id>" created for $X.XX / hr`
  # (not JSON `"id":"..."`). Support both formats; set -e + pipefail safe via || true.
  pod_id=$(echo "${out}" | grep -oE 'pod "[a-z0-9]+" created' | head -1 | sed 's/pod "\([^"]*\)".*/\1/' || true)
  if [[ -z "${pod_id}" ]]; then
    pod_id=$(echo "${out}" | grep -oE '"id": "[^"]+"' | head -1 | sed 's/.*"\([^"]*\)"/\1/' || true)
  fi
  if [[ -z "${pod_id}" ]]; then
    log "LAUNCH FAIL path=${pid}: could not parse pod_id from runpodctl output:"
    log "${out}"
    exit 4
  fi
  log "    -> pod_id=${pod_id}"
  LAUNCHED_PODS+=("${pid}:${pod_id}:${pod_name}")
done

log "writing ${LAUNCH_STATE}"
{
  printf '{\n'
  printf '  "schema": "anima.h100_stage2_launch_state.v1",\n'
  printf '  "launched_at": "%s",\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf '  "stage": 2,\n'
  printf '  "roadmap_entry": 10,\n'
  printf '  "policy": {\n'
  printf '    "auto_charge": true,\n'
  printf '    "balance_check_gates": false,\n'
  printf '    "gpu_count_per_pod": %d,\n' "${GPU_COUNT_PER_POD}"
  printf '    "max_parallelism_policy": "config/h100_max_parallelism_policy.json"\n'
  printf '  },\n'
  printf '  "abort_thresholds": {\n'
  printf '    "numerical_drift_bound": %s,\n' "${NUMERICAL_DRIFT_BOUND}"
  printf '    "idle_minutes_max": %d,\n' "${IDLE_MINUTES_MAX}"
  printf '    "phi_rel_delta_max": %s,\n' "${PHI_REL_DELTA_MAX}"
  printf '    "min_paths_pass": %d\n' "${MIN_PATHS_PASS}"
  printf '  },\n'
  printf '  "pods": [\n'
  first=1
  for entry in "${LAUNCHED_PODS[@]}"; do
    pid="${entry%%:*}"; rest="${entry#*:}"; pod_id="${rest%%:*}"; pod_name="${rest#*:}"
    if [[ $first -eq 1 ]]; then first=0; else printf ',\n'; fi
    printf '    {"path_id": "%s", "pod_id": "%s", "pod_name": "%s"}' "${pid}" "${pod_id}" "${pod_name}"
  done
  printf '\n  ],\n'
  printf '  "log": "%s"\n' "${LOG}"
  printf '}\n'
} > "${LAUNCH_STATE}"

log "launch state written"

# 2026-04-24 ROI V5: AUTO_KICKOFF chain — pods spawn → pods_sync → auto_kill arm →
# ssh bootstrap parallel → training driver ship + parallel kickoff. NO IDLE state.
# User directive: '유휴 상태절대금지 코드수준 구현' → enforced here, not in human loop.
if [[ "${AUTO_KICKOFF}" == "yes" ]]; then
  log "AUTO_KICKOFF: chaining bootstrap + training (--no-auto-kickoff to skip)"

  log "  step 1/4: sync config/h100_pods.json from live runpodctl"
  bash "${ANIMA_ROOT}/tool/h100_pods_sync.bash" 2>&1 | tail -3

  log "  step 2/4: arm h100_auto_kill (idle ${IDLE_MINUTES_MAX}min threshold)"
  /Users/ghost/core/hexa-lang/hexa "${ANIMA_ROOT}/tool/h100_auto_kill.hexa" --apply 2>&1 | tail -3

  log "  step 3/4: pod bootstrap (hexa + repo clone) — parallel 4 ssh"
  # The post-spawn bootstrap + training kickoff chain is orchestrated by a
  # dedicated helper to keep this launch script tight. If the helper is
  # missing, log a clear next-command hint and exit — never hang idle.
  CHAIN_TOOL="${ANIMA_ROOT}/tool/h100_stage2_post_launch_chain.bash"
  if [[ -x "${CHAIN_TOOL}" ]]; then
    bash "${CHAIN_TOOL}" 2>&1 | tail -10
  else
    log "  [NOTE] ${CHAIN_TOOL} not authored yet — next manual step:"
    log "         bash ${CHAIN_TOOL}   (after it lands)"
    log "         OR for current session: see state/convergence/h100_stage2_*.json for"
    log "         the ad-hoc ssh-heredoc bootstrap pattern used 2026-04-23."
  fi
else
  log "  AUTO_KICKOFF disabled — operator must manually:"
  log "    1. bash tool/h100_pods_sync.bash"
  log "    2. hexa run tool/h100_auto_kill.hexa --apply"
  log "    3. ssh to each pod + bootstrap + ship training driver + kickoff"
fi

log "APPLY: complete. ${#LAUNCHED_PODS[@]} pods launched (GPU per pod: ${GPU_COUNT_PER_POD}, total: $(( ${#LAUNCHED_PODS[@]} * GPU_COUNT_PER_POD )))"
log "Monitor: runpodctl pod list | jq '.[] | {id,name,desiredStatus,costPerHr}'"
exit 0
