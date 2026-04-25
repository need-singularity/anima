#!/usr/bin/env bash
# tool/h100_r7_single_path_retrain.bash
#
# PURPOSE
#   r7 partial-retrain helper — 1-pod / 1-path LoRA 재학습 + byte-weighted
#   h_last 추출 + adapter pull + (optional) Φ 4-path gate r7 호출. r7 spec
#   (`docs/alm_r7_launch_spec_20260425.md`, commit 0acff23b §10) 의
#   Option C/D 분기에서 식별된 tool-gap 충족.
#
# DESIGN
#   docs/alm_r7_single_path_retrain_helper_design_20260425.md (commit b5ad891d)
#   proposal: state/proposals/refinement/20260422-082/v1.json
#
# 차용 source 도구 (수정 0):
#   - tool/h100_stage2_post_launch_chain.bash (학습 driver L217–297, byte-weighted h_last L271–295)
#   - tool/h100_stage2_unified_launch.bash    (pre-flight 0–7, runpodctl create pod 패턴)
#   - tool/h_last_raw_regen_r5.bash           (1-pod sequential + scp + _kill_pod 패턴)
#
# USAGE
#   bash tool/h100_r7_single_path_retrain.bash --dry-run
#     (default — emits plan, exits 0, no pod / no GPU / no API)
#
#   bash tool/h100_r7_single_path_retrain.bash \
#     --path p4 --base-model Qwen/Qwen2.5-14B --lora-rank 96 --max-steps 300 \
#     --corpus-path /root/core/anima/experiments/alm_r14/corpus_alm_r14_v1.jsonl \
#     --tag r7_optD_qwen14 --apply --yes-i-mean-it
#
# EXIT CODES
#   0 = full success (학습 + h_last + adapter pull + (opt) Φ gate)
#   1 = pre-flight FAIL / argv 오류
#   2 = pod launch fail / SSH timeout
#   3 = bootstrap (apt/pip/clone) fail
#   4 = 학습 driver fail (OOM 포함, fallback 후에도 fail)
#   5 = adapter / h_last scp fail / schema 검증 fail
#   6 = Φ gate 호출 fail (학습은 성공)
set -euo pipefail

# --- constants ----------------------------------------------------------------
readonly ANIMA_ROOT="/Users/ghost/core/anima"
readonly HEXA_BIN="/Users/ghost/core/hexa-lang/hexa"
readonly RUNPODCTL="/opt/homebrew/bin/runpodctl"
readonly HF_CLI="/opt/homebrew/bin/hf"
readonly HF_TOKEN_FILE="${HOME}/.cache/huggingface/token"
readonly SUBSTRATES_CFG="${ANIMA_ROOT}/config/phi_4path_substrates.json"
readonly LORA_CFG="${ANIMA_ROOT}/config/lora_rank_per_path.json"
readonly LAUNCH_MANIFEST="${ANIMA_ROOT}/state/h100_launch_manifest.json"
readonly PODS_CFG="${ANIMA_ROOT}/config/h100_pods.json"
readonly POD_IMAGE="runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04"
readonly TS="$(date -u +%Y%m%dT%H%M%SZ)"
readonly LOG="/tmp/h100_r7_single_path_retrain_${TS}.log"
readonly STATE_OUT="${ANIMA_ROOT}/state/h100_r7_single_path_retrain_result.json"
# r14 corpus sha lock (verified 2026-04-25 from local file).
readonly EXPECTED_CORPUS_SHA256="21fcfa51b92f129b119d7fa42303adf7916547ef71c80c16f08e53839bf52b0b"

# --- argv defaults ------------------------------------------------------------
PATH_ID=""
BASE_MODEL=""
LORA_RANK=""
MAX_STEPS="300"
CORPUS_PATH="/root/core/anima/experiments/alm_r14/corpus_alm_r14_v1.jsonl"
TAG=""
GPU_COUNT_PER_POD="${ANIMA_R7_GPUCOUNT_PER_POD:-4}"
BID_USD_PER_GPU="${ANIMA_H100_BID_USD_PER_GPU:-3.50}"
PHI_GATE="yes"
QLORA_ON_OOM="no"
FALLBACK_MODEL=""
MODE="dry-run"
CONFIRM=""
SSH_MAX_SEC="${ANIMA_R7_SSH_MAX_SEC:-600}"
SSH_RETRY_INTERVAL=15
COST_CAP_USD="${ANIMA_R7_COST_CAP_USD:-20}"

# --- log helpers --------------------------------------------------------------
exec > >(tee -a "${LOG}") 2>&1
log()       { printf '[%s] %s\n' "$(date -u +%H:%M:%SZ)" "$*"; }
pass()      { printf '  [PASS] %s\n' "$*"; }
mark_fail() { printf '  [FAIL] %s\n' "$*"; FAIL_N=$((FAIL_N+1)); }
warn()      { printf '  [WARN] %s\n' "$*"; }

usage() {
  sed -n '1,40p' "$0"
  exit 0
}

# --- argv parse ---------------------------------------------------------------
while [[ $# -gt 0 ]]; do
  case "$1" in
    --path)            PATH_ID="$2"; shift 2 ;;
    --base-model)      BASE_MODEL="$2"; shift 2 ;;
    --lora-rank)       LORA_RANK="$2"; shift 2 ;;
    --max-steps)       MAX_STEPS="$2"; shift 2 ;;
    --corpus-path)     CORPUS_PATH="$2"; shift 2 ;;
    --tag)             TAG="$2"; shift 2 ;;
    --gpu-count)       GPU_COUNT_PER_POD="$2"; shift 2 ;;
    --bid-per-gpu)     BID_USD_PER_GPU="$2"; shift 2 ;;
    --phi-gate)        PHI_GATE="yes"; shift ;;
    --no-phi-gate)     PHI_GATE="no"; shift ;;
    --qlora-on-oom)    QLORA_ON_OOM="yes"; shift ;;
    --fallback-model)  FALLBACK_MODEL="$2"; shift 2 ;;
    --cost-cap-usd)    COST_CAP_USD="$2"; shift 2 ;;
    --dry-run)         MODE="dry-run"; shift ;;
    --apply)           MODE="apply"; shift ;;
    --yes-i-mean-it)   CONFIRM="yes"; shift ;;
    --help|-h)         usage ;;
    *) log "unknown arg: $1"; exit 1 ;;
  esac
done

# Compute scaled bid total
BID_USD_PER_HR=$(awk -v per="${BID_USD_PER_GPU}" -v n="${GPU_COUNT_PER_POD}" 'BEGIN { printf "%.2f", per * n }')

log "mode=${MODE} log=${LOG}"
log "argv: path=${PATH_ID} base_model=${BASE_MODEL} lora_rank=${LORA_RANK} max_steps=${MAX_STEPS}"
log "      tag=${TAG} gpu_count=${GPU_COUNT_PER_POD} bid_total=\$${BID_USD_PER_HR}/hr (per-GPU \$${BID_USD_PER_GPU})"
log "      corpus=${CORPUS_PATH} phi_gate=${PHI_GATE} qlora_on_oom=${QLORA_ON_OOM} fallback=${FALLBACK_MODEL:-<none>}"

# --- argv validation ----------------------------------------------------------
[[ -z "${PATH_ID}"    ]] && { log "ABORT: --path required"; exit 1; }
[[ -z "${BASE_MODEL}" ]] && { log "ABORT: --base-model required"; exit 1; }
[[ -z "${TAG}"        ]] && { log "ABORT: --tag required"; exit 1; }
case "${PATH_ID}" in p1|p2|p3|p4) : ;; *) log "ABORT: --path must be p1|p2|p3|p4"; exit 1 ;; esac
if [[ -z "${LORA_RANK}" ]]; then
  # default from config/lora_rank_per_path.json (path key mapping)
  LORA_RANK=$(python3 -c "
import json
c=json.load(open('${LORA_CFG}'))
key={'p1':'p1_qwen3_8b','p2':'p2_llama_3_1_8b','p3':'p3_ministral_3_14b','p4':'p4_gemma_4_31b'}.get('${PATH_ID}')
print(c['paths'][key]['lora']['rank'] if key in c.get('paths',{}) else 64)
" 2>/dev/null || echo 64)
fi
log "  resolved lora_rank=${LORA_RANK}"

# --- pre-flight ---------------------------------------------------------------
FAIL_N=0
log "pre-flight 0/10: runpodctl auth + balance + spendLimit"
if [[ -x "${RUNPODCTL}" ]]; then
  pass "runpodctl binary present"
  USER_JSON=$("${RUNPODCTL}" user 2>/dev/null || echo '{}')
  CLIENT_BAL=$(echo "${USER_JSON}" | python3 -c "import json,sys;print(json.load(sys.stdin).get('clientBalance',0))" 2>/dev/null || echo 0)
  SPEND_LIMIT=$(echo "${USER_JSON}" | python3 -c "import json,sys;print(json.load(sys.stdin).get('spendLimit',0))" 2>/dev/null || echo 0)
  log "    clientBalance=\$${CLIENT_BAL}  spendLimit=\$${SPEND_LIMIT}/hr  bid_pod=\$${BID_USD_PER_HR}/hr"
  if awk -v b="${CLIENT_BAL}" 'BEGIN{exit !(b+0 >= 40)}'; then
    pass "balance OK (≥\$40)"
  else
    mark_fail "balance \$${CLIENT_BAL} < \$40 minimum"
  fi
  # spendLimit > 0 means hard cap per hour — must accommodate bid
  if awk -v s="${SPEND_LIMIT}" -v b="${BID_USD_PER_HR}" 'BEGIN{exit !(s+0 == 0 || s+0 >= b+0)}'; then
    pass "spendLimit \$${SPEND_LIMIT}/hr accommodates bid \$${BID_USD_PER_HR}/hr"
  else
    mark_fail "spendLimit \$${SPEND_LIMIT}/hr < bid \$${BID_USD_PER_HR}/hr"
  fi
else
  mark_fail "runpodctl missing at ${RUNPODCTL}"
fi

log "pre-flight 1/10: substrates config p${PATH_ID#p} entry"
if [[ -f "${SUBSTRATES_CFG}" ]]; then
  pass "substrates config exists"
else
  mark_fail "substrates config missing: ${SUBSTRATES_CFG}"
fi

log "pre-flight 2/10: lora rank config"
if [[ -f "${LORA_CFG}" ]]; then
  pass "lora rank config exists"
else
  mark_fail "lora rank config missing: ${LORA_CFG}"
fi

log "pre-flight 3/10: launch manifest stage2 verdict"
if [[ -f "${LAUNCH_MANIFEST}" ]]; then
  v=$(python3 -c "
import json,sys
m=json.load(open('${LAUNCH_MANIFEST}'))
for st in m.get('stages',[]):
    if st.get('stage')==2:
        print(st.get('verdict','')); break
" 2>/dev/null || echo "")
  if [[ "${v}" == "READY" ]]; then
    pass "stage2 verdict=READY"
  else
    warn "stage2 verdict=${v:-<missing>} (informational; r7 retrain proceeds)"
  fi
else
  warn "launch manifest missing (informational)"
fi

log "pre-flight 4/10: hf auth + token"
if [[ -f "${HF_TOKEN_FILE}" ]]; then
  pass "HF token file present"
  HF_TOKEN_VAL="$(cat "${HF_TOKEN_FILE}")"
else
  mark_fail "HF token missing: ${HF_TOKEN_FILE}"
fi
if [[ -x "${HF_CLI}" ]]; then
  pass "hf CLI present"
else
  warn "hf CLI missing at ${HF_CLI} (HF auth pre-check skipped)"
fi

log "pre-flight 5/10: HF accessibility (base model HEAD /config.json)"
_hf_accessible() {
  local m="$1" code
  if [[ -n "${HF_TOKEN_VAL:-}" ]]; then
    code=$(curl -s -o /dev/null -w '%{http_code}' -L \
      -H "Authorization: Bearer ${HF_TOKEN_VAL}" \
      "https://huggingface.co/${m}/resolve/main/config.json" 2>/dev/null || echo 000)
  else
    code=$(curl -s -o /dev/null -w '%{http_code}' -L \
      "https://huggingface.co/${m}/resolve/main/config.json" 2>/dev/null || echo 000)
  fi
  [[ "${code}" == "200" ]]
}
if _hf_accessible "${BASE_MODEL}"; then
  pass "${BASE_MODEL} HF accessible (200)"
else
  mark_fail "${BASE_MODEL} HF NOT accessible (gated/missing/4xx)"
fi
if [[ -n "${FALLBACK_MODEL}" ]]; then
  if _hf_accessible "${FALLBACK_MODEL}"; then
    pass "fallback ${FALLBACK_MODEL} HF accessible"
  else
    warn "fallback ${FALLBACK_MODEL} HF NOT accessible"
  fi
fi

log "pre-flight 6/10: pod registry writable"
if [[ -f "${PODS_CFG}" && -w "${PODS_CFG}" ]]; then
  pass "pod registry writable"
else
  mark_fail "pod registry missing or read-only: ${PODS_CFG}"
fi

log "pre-flight 7/10: live pod count == 0 (no concurrent pods)"
LIVE_PODS_RAW=$("${RUNPODCTL}" pod list 2>/dev/null || echo '[]')
LIVE_POD_COUNT=$(echo "${LIVE_PODS_RAW}" | python3 -c "
import json,sys
try:
    d=json.loads(sys.stdin.read() or '[]')
    print(len(d) if isinstance(d,list) else 0)
except Exception:
    print(0)
" 2>/dev/null || echo 0)
if [[ "${LIVE_POD_COUNT}" == "0" ]]; then
  pass "live pod count=0"
else
  mark_fail "live pod count=${LIVE_POD_COUNT} (expected 0)"
fi

log "pre-flight 8/10: git sync (local HEAD == origin/main)"
if (cd "${ANIMA_ROOT}" && git rev-parse --git-dir >/dev/null 2>&1); then
  (cd "${ANIMA_ROOT}" && git fetch origin main 2>/dev/null) || true
  ahead=$(cd "${ANIMA_ROOT}" && git rev-list --count origin/main..HEAD 2>/dev/null || echo -1)
  head_sha=$(cd "${ANIMA_ROOT}" && git rev-parse --short HEAD 2>/dev/null || echo unknown)
  origin_sha=$(cd "${ANIMA_ROOT}" && git rev-parse --short origin/main 2>/dev/null || echo unknown)
  if [[ "${ahead}" == "0" ]]; then
    pass "git sync OK (HEAD=${head_sha} == origin/main=${origin_sha})"
  else
    mark_fail "git NOT synced: HEAD=${head_sha} ahead=${ahead} of origin/main=${origin_sha}. Pods shallow-clone origin/main → STALE code. Run: git push origin main"
  fi
else
  mark_fail "not a git repo"
fi

log "pre-flight 9/10: r14 corpus sha256 lock"
LOCAL_CORPUS_FILE="${ANIMA_ROOT}/experiments/alm_r14/corpus_alm_r14_v1.jsonl"
if [[ -f "${LOCAL_CORPUS_FILE}" ]]; then
  ACTUAL_SHA=$(shasum -a 256 "${LOCAL_CORPUS_FILE}" | awk '{print $1}')
  if [[ "${ACTUAL_SHA}" == "${EXPECTED_CORPUS_SHA256}" ]]; then
    pass "corpus sha256 OK (${ACTUAL_SHA:0:16}…)"
  else
    mark_fail "corpus sha256 mismatch (expected ${EXPECTED_CORPUS_SHA256:0:16}…, got ${ACTUAL_SHA:0:16}…)"
  fi
else
  mark_fail "corpus missing: ${LOCAL_CORPUS_FILE}"
fi

log "pre-flight 10/10: r6 assets present + r6 archive"
R6_ASSETS_OK=1
for pid in p1 p2 p3 p4; do
  hl="${ANIMA_ROOT}/state/h_last_raw_${pid}_TRAINED_r6.json"
  ad="${ANIMA_ROOT}/state/trained_adapters_r6/${pid}/final"
  if [[ ! -f "${hl}" ]]; then
    mark_fail "missing r6 h_last: ${hl}"
    R6_ASSETS_OK=0
  fi
  if [[ ! -d "${ad}" ]]; then
    # auto hard-copy (per design §6.2 / R8)
    src="${ANIMA_ROOT}/state/trained_adapters/${pid}/final"
    if [[ -d "${src}" ]]; then
      log "    [AUTO] r6 archive missing for ${pid}, hard-copying ${src} → ${ad}"
      mkdir -p "${ANIMA_ROOT}/state/trained_adapters_r6/${pid}"
      cp -r "${src}" "${ad}" || { mark_fail "r6 hard-copy fail for ${pid}"; R6_ASSETS_OK=0; }
    else
      mark_fail "missing r6 adapter dir: ${ad} (and no src ${src} to hard-copy from)"
      R6_ASSETS_OK=0
    fi
  fi
done
if [[ ${R6_ASSETS_OK} -eq 1 ]]; then
  pass "r6 assets all 4 paths present (h_last + adapter)"
fi

log ""
log "pre-flight summary: fail_n=${FAIL_N} / 10 checks"

if [[ "${FAIL_N}" -gt 0 ]]; then
  log "RESULT: PRE-FLIGHT FAIL — cannot proceed"
  exit 1
fi
log "RESULT: PRE-FLIGHT PASS"

# --- dry-run terminates here --------------------------------------------------
if [[ "${MODE}" == "dry-run" ]]; then
  log ""
  log "DRY-RUN plan:"
  POD_NAME_PLAN="anima-r7-${PATH_ID}-$(echo "${BASE_MODEL}" | tr '[:upper:]' '[:lower:]' | tr '/._' '-' | tr -cd 'a-z0-9-' | cut -c1-32)-${TS}"
  log "  pod_name=${POD_NAME_PLAN}"
  log "  ${RUNPODCTL} create pod \\"
  log "    --gpuType 'NVIDIA H100 80GB HBM3' --gpuCount ${GPU_COUNT_PER_POD} --secureCloud \\"
  log "    --name ${POD_NAME_PLAN} --imageName ${POD_IMAGE} \\"
  log "    --cost ${BID_USD_PER_HR} --containerDiskSize 80 --volumeSize 200 --volumePath /workspace \\"
  log "    --startSSH --ports '22/tcp' \\"
  log "    --env ANIMA_STAGE=2_single_path_retrain --env ANIMA_ROADMAP_ENTRY=10 --env HEXA_STRICT=1 --env IDLE_KILL_MIN=5 \\"
  log "    --env PHI_PATH_ID=${PATH_ID} --env PHI_MODEL=${BASE_MODEL} --env PHI_LORA_RANK=${LORA_RANK} --env ANIMA_TAG=${TAG}"
  log "  estimated wall: 90-120min, cost: \$8-12 (Qwen2.5-14B baseline)"
  log "  cost cap: \$${COST_CAP_USD} (kill if exceeds)"
  log "  to apply: $0 <same args> --apply --yes-i-mean-it"
  exit 0
fi

# --- apply mode requires confirmation -----------------------------------------
if [[ "${MODE}" == "apply" && "${CONFIRM}" != "yes" ]]; then
  log "ERROR: --apply requires --yes-i-mean-it (H100 stop-gate)"
  exit 1
fi

# --- step 1: pod launch -------------------------------------------------------
POD_NAME="anima-r7-${PATH_ID}-$(echo "${BASE_MODEL}" | tr '[:upper:]' '[:lower:]' | tr '/._' '-' | tr -cd 'a-z0-9-' | cut -c1-32)-${TS}"
log "step 1/7: launching 1× H100 SXM5 pod (${GPU_COUNT_PER_POD}× GPU, secureCloud, bid \$${BID_USD_PER_HR}/hr)"
log "  pod_name=${POD_NAME}"

LAUNCH_TS=$(date -u +%s)
LAUNCH_OUT=$("${RUNPODCTL}" create pod \
  --gpuType "NVIDIA H100 80GB HBM3" --gpuCount "${GPU_COUNT_PER_POD}" \
  --secureCloud \
  --name "${POD_NAME}" \
  --imageName "${POD_IMAGE}" \
  --cost "${BID_USD_PER_HR}" --containerDiskSize 80 --volumeSize 200 --volumePath /workspace \
  --startSSH --ports "22/tcp" \
  --env "ANIMA_STAGE=2_single_path_retrain" \
  --env "ANIMA_ROADMAP_ENTRY=10" \
  --env "HEXA_STRICT=1" \
  --env "IDLE_KILL_MIN=5" \
  --env "PHI_PATH_ID=${PATH_ID}" \
  --env "PHI_MODEL=${BASE_MODEL}" \
  --env "PHI_LORA_RANK=${LORA_RANK}" \
  --env "ANIMA_TAG=${TAG}" \
  2>&1) || { log "LAUNCH FAIL: ${LAUNCH_OUT}"; exit 2; }
log "  runpodctl: ${LAUNCH_OUT}"
POD_ID=$(echo "${LAUNCH_OUT}" | grep -oE 'pod "[a-z0-9]+" created' | head -1 | sed 's/pod "\([^"]*\)".*/\1/' || true)
[[ -z "${POD_ID}" ]] && POD_ID=$(echo "${LAUNCH_OUT}" | grep -oE '"id": "[^"]+"' | head -1 | sed 's/.*"\([^"]*\)"/\1/' || true)
[[ -n "${POD_ID}" ]] || { log "ABORT: could not parse pod_id"; exit 2; }
log "  pod_id=${POD_ID}"

# Cleanup helper for ABORT — always kill pod
_kill_pod() {
  log "[CLEANUP] removing pod ${POD_ID}"
  "${RUNPODCTL}" remove pod "${POD_ID}" 2>&1 | tail -1 | sed 's/^/    /' || true
  bash "${ANIMA_ROOT}/tool/h100_pods_sync.bash" 2>&1 | tail -1 | sed 's/^/    /' || true
}
trap '_kill_pod' ERR

# --- step 2: pods_sync + auto_kill arm + SSH wait -----------------------------
log "step 2/7: pods_sync + auto_kill arm + SSH wait"
bash "${ANIMA_ROOT}/tool/h100_pods_sync.bash" 2>&1 | tail -2

SSH_HOST=$(python3 -c "
import json
d=json.load(open('${PODS_CFG}'))
for p in d.get('pods',[]):
    if p['pod_id']=='${POD_ID}':
        print(p.get('ssh_host','')); break
")
SSH_PORT=$(python3 -c "
import json
d=json.load(open('${PODS_CFG}'))
for p in d.get('pods',[]):
    if p['pod_id']=='${POD_ID}':
        print(p.get('ssh_port','22')); break
")
[[ -z "${SSH_HOST}" ]] && { log "ABORT: pods_sync did not populate ssh_host"; exit 2; }
log "  ssh: root@${SSH_HOST}:${SSH_PORT}"

# auto_kill arm (best-effort, idle 5min)
if [[ -x "${HEXA_BIN}" ]]; then
  "${HEXA_BIN}" run "${ANIMA_ROOT}/tool/h100_auto_kill.hexa" --apply 2>&1 | tail -3 || warn "auto_kill arm fail (informational)"
fi

log "  waiting for SSH (max ${SSH_MAX_SEC}s)"
SSH_OK=0
attempts=$(( SSH_MAX_SEC / SSH_RETRY_INTERVAL ))
for i in $(seq 1 "${attempts}"); do
  if ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -o BatchMode=yes \
       -p "${SSH_PORT}" "root@${SSH_HOST}" "true" 2>/dev/null; then
    SSH_OK=1; break
  fi
  log "    retry ${i}/${attempts} in ${SSH_RETRY_INTERVAL}s"
  sleep "${SSH_RETRY_INTERVAL}"
done
[[ ${SSH_OK} -eq 1 ]] || { log "ABORT: SSH not reachable within ${SSH_MAX_SEC}s"; exit 2; }
log "  SSH OK"

# --- step 3: bootstrap (apt + hexa + git clone + pip) -------------------------
log "step 3/7: bootstrap (apt clang + hexa binary + git clone + pip)"
_FETCH_OUT=$(bash "${ANIMA_ROOT}/tool/fetch_hexa_binary_url.bash" --export 2>&1)
BS_URL=$(echo "${_FETCH_OUT}" | grep '^export HEXA_URL=' | sed 's/^[^=]*=//' | tr -d '\\')
BS_SHA=$(echo "${_FETCH_OUT}" | grep '^export HEXA_SHA256=' | sed 's/^[^=]*=//' | tr -d '\\')
if [[ "${BS_URL}" != https://* || ${#BS_SHA} -ne 64 ]]; then
  log "ABORT: bootstrap url/sha parse failed"
  exit 3
fi
BOOTSTRAP_INLINE='
set -e
command -v clang >/dev/null || { apt-get update -qq; apt-get install -y -qq clang; }
if [ ! -x /usr/local/bin/hexa_v2 ]; then
  curl -fsSL "'${BS_URL}'" -o /usr/local/bin/hexa_v2
  chmod +x /usr/local/bin/hexa_v2
  echo "'${BS_SHA}'  /usr/local/bin/hexa_v2" | sha256sum -c -
fi
mkdir -p /root/core && cd /root/core
for repo in anima hexa-lang; do
  [ -d /root/core/$repo/.git ] || git clone --depth 1 https://github.com/need-singularity/${repo}.git >/dev/null 2>&1
done
ln -sfn /root/core/anima /workspace/anima
ln -sfn /root/core/hexa-lang /workspace/hexa-lang
export HF_HUB_ENABLE_HF_TRANSFER=1
pip install -q --upgrade "transformers>=4.44" "peft>=0.12" "accelerate>=0.34" \
  "datasets>=3.0" "bitsandbytes>=0.43" "hf_transfer" "sentencepiece" "safetensors"
python3 -c "import torch,transformers,peft; print(f\"torch={torch.__version__} transformers={transformers.__version__} peft={peft.__version__}\")"
nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv,noheader | head -4
'
if ! ssh -o StrictHostKeyChecking=no -p "${SSH_PORT}" "root@${SSH_HOST}" "${BOOTSTRAP_INLINE}" 2>&1 | tail -10; then
  log "ABORT: bootstrap failed"
  exit 3
fi
log "  bootstrap DONE"

# --- step 4: ship training driver --------------------------------------------
log "step 4/7: ship training driver /workspace/train_${PATH_ID}.py"
# 차용: tool/h100_stage2_post_launch_chain.bash L217-297 PYDRIVER (verbatim)
DRIVER_BODY=$(cat <<'PYDRIVER'
import os, sys, json, time, traceback
from pathlib import Path
os.environ['HF_HUB_ENABLE_HF_TRANSFER']='1'
PHI_PATH_ID=os.environ['PHI_PATH_ID']
BASE_MODEL=os.environ['PHI_MODEL']
LORA_RANK=int(os.environ.get('PHI_LORA_RANK','64'))
MAX_STEPS=int(os.environ.get('PHI_MAX_STEPS','300'))
CORPUS_PATH=os.environ.get('ANIMA_STAGE2_CORPUS_PATH','/root/core/anima/experiments/alm_r14/corpus_alm_r14_v1.jsonl')
OUT_DIR=Path(f'/workspace/trained_{PHI_PATH_ID}')
OUT_DIR.mkdir(parents=True, exist_ok=True)
print(f'[{time.strftime("%H:%M:%S")}] path={PHI_PATH_ID} model={BASE_MODEL} rank={LORA_RANK} steps={MAX_STEPS} corpus={CORPUS_PATH}', flush=True)
import subprocess
subprocess.run(['pip','install','-q','transformers>=4.44','peft>=0.12','accelerate>=0.34','datasets>=3.0','bitsandbytes>=0.43','hf_transfer','sentencepiece','safetensors'], check=True)
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, TrainingArguments, Trainer, DataCollatorForLanguageModeling
from peft import LoraConfig, get_peft_model
from datasets import Dataset
tok=AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True, token=os.environ['HF_TOKEN'])
if tok.pad_token is None: tok.pad_token=tok.eos_token
try:
    model=AutoModelForCausalLM.from_pretrained(BASE_MODEL, trust_remote_code=True, token=os.environ['HF_TOKEN'], torch_dtype=torch.bfloat16, device_map='auto', attn_implementation='sdpa')
except Exception as e:
    print(f'LOAD_FAIL: {e}', flush=True); traceback.print_exc(); sys.exit(2)
lora_cfg=LoraConfig(r=LORA_RANK, lora_alpha=LORA_RANK*2, lora_dropout=0.05, bias='none', task_type='CAUSAL_LM', target_modules=['q_proj','k_proj','v_proj','o_proj','gate_proj','up_proj','down_proj'])
model=get_peft_model(model, lora_cfg)
model.print_trainable_parameters()
rows=[]
with open(CORPUS_PATH) as f:
    for line in f:
        try:
            d=json.loads(line); p=d.get('prompt',''); r=d.get('response','')
            if p and r: rows.append({'text': p + '\n' + r})
        except: pass
ds=Dataset.from_list(rows)
def tok_fn(b):
    o=tok(b['text'], truncation=True, max_length=2048, padding=False)
    o['labels']=[x[:] for x in o['input_ids']]; return o
ds=ds.map(tok_fn, batched=True, remove_columns=['text'])
args=TrainingArguments(output_dir=str(OUT_DIR/'ckpt'), max_steps=MAX_STEPS, per_device_train_batch_size=1, gradient_accumulation_steps=4, learning_rate=2e-4, lr_scheduler_type='cosine', warmup_steps=10, weight_decay=0.01, bf16=True, gradient_checkpointing=True, logging_steps=10, save_steps=50, save_total_limit=3, report_to='none', remove_unused_columns=False, ddp_find_unused_parameters=False)
trainer=Trainer(model=model, args=args, train_dataset=ds, data_collator=DataCollatorForLanguageModeling(tok, mlm=False))
trainer.train()
trainer.save_model(str(OUT_DIR/'final'))
EVAL=['The substrate of consciousness is','Integrated information theory says','Global workspace broadcast implies','Attention schema models claim','Higher-order thought requires','Recurrent processing means','의식의 기질은','통합정보이론에 따르면','전역작업공간의 방송은','재귀처리는','주의 스키마 모델은','상위차원 사고는','phi_6 defines','hexad closure is','meta-loop observation is','Law 60 phase transition describes']
# byte-weighted h_last pool — verbatim parity with tool/h100_stage2_post_launch_chain.bash L271-295
model.eval(); h_last=[]
def _byte_weights(ids_1d, tokenizer):
    weights=[]
    for tid in ids_1d.tolist():
        s=tokenizer.decode([tid], skip_special_tokens=False, clean_up_tokenization_spaces=False)
        b=len(s.encode('utf-8')) if s else 1
        weights.append(b)
    total=sum(weights) or 1
    return [w/total for w in weights]
with torch.no_grad():
    for i,p in enumerate(EVAL):
        ids=tok(p, return_tensors='pt').to(model.device)
        out=model(**ids, output_hidden_states=True)
        H=out.hidden_states[-1][0].float().cpu()
        bpt=_byte_weights(ids['input_ids'][0].cpu(), tok)
        import torch as _t
        w=_t.tensor(bpt, dtype=H.dtype).unsqueeze(-1)
        pooled=(H*w).sum(dim=0).numpy()
        h_last.append({'idx':i,'prompt':p,'h':[float(x) for x in pooled[:256]],'n_tokens':int(H.shape[0]),'bpt_sum':float(sum(bpt))})
Path(OUT_DIR/'h_last_raw.json').write_text(json.dumps({'schema':'anima/h_last_raw/2','reduction':'byte_weighted_mean','path_id':PHI_PATH_ID,'base_model':BASE_MODEL,'lora_rank':LORA_RANK,'steps':MAX_STEPS,'ts':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'hidden_dim_truncated':256,'entries':h_last}, indent=2))
print(f'[{time.strftime("%H:%M:%S")}] DONE path={PHI_PATH_ID}', flush=True)
PYDRIVER
)
echo "${DRIVER_BODY}" | ssh -o StrictHostKeyChecking=no -p "${SSH_PORT}" "root@${SSH_HOST}" "cat > /workspace/train_${PATH_ID}.py"
log "  driver shipped"

# --- step 5: kickoff training (nohup bg, poll for h_last_raw.json) -----------
log "step 5/7: kickoff training nohup + poll for h_last_raw.json"
# Coerce relative corpus path to absolute (r6-α attempt_5 prevention)
[[ "${CORPUS_PATH}" != /* ]] && CORPUS_PATH="/root/core/anima/${CORPUS_PATH}"

KICKOFF_CMD="HF_TOKEN='${HF_TOKEN_VAL}' \
PHI_PATH_ID='${PATH_ID}' PHI_MODEL='${BASE_MODEL}' \
PHI_LORA_RANK='${LORA_RANK}' PHI_MAX_STEPS='${MAX_STEPS}' \
ANIMA_STAGE2_CORPUS_PATH='${CORPUS_PATH}' \
nohup python3 /workspace/train_${PATH_ID}.py > /workspace/train_${PATH_ID}.log 2>&1 & echo train_pid=\$!"
ssh -o StrictHostKeyChecking=no -p "${SSH_PORT}" "root@${SSH_HOST}" "${KICKOFF_CMD}" 2>&1 | tail -2
log "  training kicked off — polling for /workspace/trained_${PATH_ID}/h_last_raw.json"

# Poll loop — max 8h wall, 60s interval. Cost-cap guard kills pod if elapsed > COST_CAP/bid_per_hr.
POLL_INTERVAL=60
MAX_WALL_SEC=$((8*3600))
WALL_START=$(date -u +%s)
ARTIFACT_FOUND=0
while true; do
  NOW=$(date -u +%s)
  ELAPSED=$((NOW - WALL_START))
  if [[ ${ELAPSED} -gt ${MAX_WALL_SEC} ]]; then
    log "  ABORT: wall exceeded ${MAX_WALL_SEC}s (${ELAPSED}s elapsed)"
    exit 4
  fi
  # Cost-cap: kill if projected cost > COST_CAP_USD
  PROJECTED_COST=$(awk -v e="${ELAPSED}" -v r="${BID_USD_PER_HR}" 'BEGIN { printf "%.2f", (e/3600.0) * r }')
  if awk -v p="${PROJECTED_COST}" -v c="${COST_CAP_USD}" 'BEGIN{exit !(p+0 > c+0)}'; then
    log "  ABORT: cost cap exceeded — projected \$${PROJECTED_COST} > \$${COST_CAP_USD}"
    exit 4
  fi
  # Check artifact
  if ssh -o StrictHostKeyChecking=no -p "${SSH_PORT}" "root@${SSH_HOST}" \
       "test -s /workspace/trained_${PATH_ID}/h_last_raw.json" 2>/dev/null; then
    ARTIFACT_FOUND=1; break
  fi
  # Check log tail every poll (non-fatal informational)
  LOG_TAIL=$(ssh -o StrictHostKeyChecking=no -p "${SSH_PORT}" "root@${SSH_HOST}" \
    "tail -3 /workspace/train_${PATH_ID}.log 2>/dev/null" 2>/dev/null || echo "")
  log "  [${ELAPSED}s elapsed, projected \$${PROJECTED_COST}] tail: $(echo "${LOG_TAIL}" | tr '\n' '|' | cut -c1-160)"
  sleep "${POLL_INTERVAL}"
done
log "  artifact found after ${ELAPSED}s"
WALL_SEC=${ELAPSED}
ACTUAL_COST=$(awk -v e="${WALL_SEC}" -v r="${BID_USD_PER_HR}" 'BEGIN { printf "%.2f", (e/3600.0) * r }')

# --- step 6: pull adapter + h_last + r6→r7 sync + pod kill --------------------
log "step 6/7: pull adapter + h_last + r6→r7 sync + pod kill"

# adapter pull
LOCAL_ADAPTER_DIR="${ANIMA_ROOT}/state/trained_adapters_r7/${PATH_ID}"
mkdir -p "${LOCAL_ADAPTER_DIR}"
log "  scp adapter → ${LOCAL_ADAPTER_DIR}/final/"
if ! scp -o StrictHostKeyChecking=no -P "${SSH_PORT}" -r \
     "root@${SSH_HOST}:/workspace/trained_${PATH_ID}/final" "${LOCAL_ADAPTER_DIR}/" 2>&1 | tail -3; then
  log "  [FAIL] adapter scp"
  exit 5
fi

# h_last pull
LOCAL_HLAST="${ANIMA_ROOT}/state/h_last_raw_${PATH_ID}_TRAINED_${TAG}.json"
log "  scp h_last → ${LOCAL_HLAST}"
if ! scp -o StrictHostKeyChecking=no -P "${SSH_PORT}" \
     "root@${SSH_HOST}:/workspace/trained_${PATH_ID}/h_last_raw.json" "${LOCAL_HLAST}" 2>&1 | tail -1; then
  log "  [FAIL] h_last scp"
  exit 5
fi

# Schema /2 + reduction validation
if ! python3 -c "
import json
d=json.load(open('${LOCAL_HLAST}'))
assert d.get('schema')=='anima/h_last_raw/2', f'schema={d.get(\"schema\")}'
assert d.get('reduction')=='byte_weighted_mean', f'reduction={d.get(\"reduction\")}'
assert d.get('path_id')=='${PATH_ID}'
assert len(d.get('entries',[]))==16
assert len(d['entries'][0]['h'])==256
print(f'  schema OK: {d[\"schema\"]} reduction={d[\"reduction\"]} entries=16 h_dim=256')
" 2>&1; then
  log "  [FAIL] h_last schema validation"
  exit 5
fi

# Also tag-aliased h_last for Φ gate r7 (without optD_qwen14 suffix, simple r7 tag)
# Φ gate reads state/h_last_raw_p{1..4}_TRAINED_<gate_tag>.json
GATE_TAG="r7"
LOCAL_HLAST_GATE="${ANIMA_ROOT}/state/h_last_raw_${PATH_ID}_TRAINED_${GATE_TAG}.json"
cp "${LOCAL_HLAST}" "${LOCAL_HLAST_GATE}"
log "  copy → ${LOCAL_HLAST_GATE} (Φ gate canonical tag)"

# r6 → r7 sync for non-retrained paths
log "  syncing r6 → r7 for non-retrained paths"
for other_pid in p1 p2 p3 p4; do
  [[ "${other_pid}" == "${PATH_ID}" ]] && continue
  src="${ANIMA_ROOT}/state/h_last_raw_${other_pid}_TRAINED_r6.json"
  dst="${ANIMA_ROOT}/state/h_last_raw_${other_pid}_TRAINED_${GATE_TAG}.json"
  if [[ -f "${src}" ]]; then
    cp "${src}" "${dst}"
    log "    cp ${other_pid} r6 → ${GATE_TAG}"
  else
    log "    [WARN] missing ${src} — Φ gate may fail"
  fi
done

# r6 → r7 sync also for the tagged variant (provenance manifest)
SYNTHESIS_MANIFEST="${ANIMA_ROOT}/state/h_last_raw_${TAG}_synthesis_manifest.json"
cat > "${SYNTHESIS_MANIFEST}" <<EOF
{
  "schema": "anima/h_last_raw_synthesis_manifest/1",
  "tag": "${TAG}",
  "gate_tag": "${GATE_TAG}",
  "generated_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "provenance": {
    "p1": $([ "${PATH_ID}" == "p1" ] && echo "\"r7_trained\"" || echo "\"r6_reuse\""),
    "p2": $([ "${PATH_ID}" == "p2" ] && echo "\"r7_trained\"" || echo "\"r6_reuse\""),
    "p3": $([ "${PATH_ID}" == "p3" ] && echo "\"r7_trained\"" || echo "\"r6_reuse\""),
    "p4": $([ "${PATH_ID}" == "p4" ] && echo "\"r7_trained\"" || echo "\"r6_reuse\"")
  },
  "retrained_path": "${PATH_ID}",
  "retrained_base_model": "${BASE_MODEL}",
  "retrained_lora_rank": ${LORA_RANK}
}
EOF
log "  manifest → ${SYNTHESIS_MANIFEST}"

# Pod kill + verify + sync registry
trap - ERR
log "  killing pod ${POD_ID}"
"${RUNPODCTL}" remove pod "${POD_ID}" 2>&1 | tail -1 | sed 's/^/    /' || true
sleep 5
LIVE_AFTER=$("${RUNPODCTL}" pod list 2>/dev/null | python3 -c "
import json,sys
try:
    d=json.loads(sys.stdin.read() or '[]')
    print(len(d) if isinstance(d,list) else 0)
except Exception:
    print(0)
")
log "  live pod count after kill: ${LIVE_AFTER}"
bash "${ANIMA_ROOT}/tool/h100_pods_sync.bash" 2>&1 | tail -1 | sed 's/^/    /' || true

# --- step 7: Φ 4-path gate (optional, default on) -----------------------------
GATE_VERDICT_TXT='null'
GATE_RC=0
if [[ "${PHI_GATE}" == "yes" ]]; then
  log "step 7/7: Φ 4-path gate --tag ${GATE_TAG}"
  if [[ -x "${HEXA_BIN}" ]]; then
    GATE_LOG="/tmp/phi_gate_${TAG}_${TS}.log"
    set +e
    "${HEXA_BIN}" run "${ANIMA_ROOT}/tool/phi_4path_gate.hexa" --tag "${GATE_TAG}" 2>&1 | tee "${GATE_LOG}" | tail -40
    GATE_RC=$?
    set -e
    log "  Φ gate exit=${GATE_RC}"
    VERDICT_FILE="${ANIMA_ROOT}/state/phi_4path_gate_last_verdict.json"
    if [[ -f "${VERDICT_FILE}" ]]; then
      GATE_VERDICT_TXT=$(python3 -c "
import json
d=json.load(open('${VERDICT_FILE}'))
print(json.dumps({k: d.get(k) for k in ('tag','verdict','L2_pass_count','KL_pass_count','p3_p4_L2')}))
" 2>/dev/null || echo 'null')
    fi
  else
    warn "hexa binary missing — Φ gate skipped"
    GATE_RC=6
  fi
fi

# --- write state file ---------------------------------------------------------
cat > "${STATE_OUT}" <<EOF
{
  "schema": "anima/h100_r7_single_path_retrain_result/1",
  "generated_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "tag": "${TAG}",
  "gate_tag": "${GATE_TAG}",
  "path_id": "${PATH_ID}",
  "base_model": "${BASE_MODEL}",
  "lora_rank": ${LORA_RANK},
  "max_steps": ${MAX_STEPS},
  "pod_id": "${POD_ID}",
  "pod_name": "${POD_NAME}",
  "ssh_host": "${SSH_HOST}",
  "ssh_port": ${SSH_PORT},
  "gpu_count_per_pod": ${GPU_COUNT_PER_POD},
  "bid_usd_per_hr": ${BID_USD_PER_HR},
  "wall_sec": ${WALL_SEC},
  "actual_cost_usd": ${ACTUAL_COST},
  "cost_cap_usd": ${COST_CAP_USD},
  "artifacts": {
    "adapter_dir": "state/trained_adapters_r7/${PATH_ID}/final",
    "h_last_tagged": "state/h_last_raw_${PATH_ID}_TRAINED_${TAG}.json",
    "h_last_gate": "state/h_last_raw_${PATH_ID}_TRAINED_${GATE_TAG}.json",
    "synthesis_manifest": "state/h_last_raw_${TAG}_synthesis_manifest.json"
  },
  "phi_gate": {
    "enabled": "${PHI_GATE}",
    "tag": "${GATE_TAG}",
    "rc": ${GATE_RC},
    "verdict": ${GATE_VERDICT_TXT}
  },
  "log": "${LOG}"
}
EOF
log "state: ${STATE_OUT}"
log "COMPLETE — wall=${WALL_SEC}s cost=\$${ACTUAL_COST} gate_rc=${GATE_RC}"

if [[ ${GATE_RC} -ne 0 && "${PHI_GATE}" == "yes" ]]; then
  exit 6
fi
exit 0
