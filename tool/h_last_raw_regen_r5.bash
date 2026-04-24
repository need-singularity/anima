#!/usr/bin/env bash
# tool/h_last_raw_regen_r5.bash
#
# PURPOSE
#   Recovery-A for r5 (incident #4 2026-04-24): regenerate
#   state/h_last_raw_p{1..4}_TRAINED_r5.json from the already-pulled LoRA
#   adapters by running a single 1× H100 forward-pass pod that loads each
#   base + LoRA sequentially, dumps h_last_raw.json per path, and pulls back.
#
#   Upstream: tool/h100_stage2_adapter_pull.bash was patched (incident #4)
#   to also pull h_last_raw.json on future rounds. This tool unblocks r5
#   specifically where the loss already happened.
#
# METHOD PARITY (must match post_launch_chain.bash heredoc driver exactly)
#   • Same 16-prompt EVAL list (12 EN + 4 EN-coded concept for KO equivalents)
#   • Same hidden_dim_truncated=256
#   • Same schema "anima/h_last_raw/1"
#   • Same LoRA load path: PeftModel.from_pretrained(base, adapter_dir)
#
# CHAIN
#   1. Launch 1× H100 SXM5 pod (secureCloud, bid $3.50/hr).
#   2. pods_sync → auto-kill arm (idle 5min).
#   3. SSH wait + bootstrap (pip install).
#   4. Ship forward-pass driver via heredoc → /workspace/fwd.py.
#   5. For p1..p4 sequentially: scp adapter → run fwd.py → scp h_last_raw
#      → rm adapter + HF cache.
#   6. Kill pod + sync registry.
#   7. Run Φ 4-path gate for tag=r5.
#   8. Append incident + outcome to state/convergence/h100_stage2_r5_20260424.json
#      (manual edit by caller — this script only writes its own state file).
#
# USAGE
#   bash tool/h_last_raw_regen_r5.bash --dry-run
#   bash tool/h_last_raw_regen_r5.bash --apply --yes-i-mean-it
#
# EXIT
#   0 = all 4 h_last_raw_r5 files landed + Φ gate ran (verdict = data, not CI)
#   1 = pre-flight fail / pod launch fail
#   2 = bootstrap / ssh fail
#   3 = forward-pass fail on ≥1 path
#   4 = scp/validation fail
set -euo pipefail

readonly ANIMA_ROOT="/Users/ghost/core/anima"
readonly HEXA_BIN="/Users/ghost/core/hexa-lang/hexa"
readonly RUNPODCTL="/opt/homebrew/bin/runpodctl"
readonly HF_TOKEN_FILE="${HOME}/.cache/huggingface/token"
readonly POD_NAME="anima-fwd-r5-$(date -u +%Y%m%dT%H%M%SZ)"
readonly POD_IMAGE="runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04"
readonly BID_USD_PER_HR="${ANIMA_H100_BID_USD:-3.50}"
readonly SSH_MAX_SEC="${ANIMA_FWD_SSH_MAX_SEC:-600}"
readonly SSH_RETRY_INTERVAL=15
readonly TS="$(date -u +%Y%m%dT%H%M%SZ)"
readonly LOG="/tmp/h_last_raw_regen_r5_${TS}.log"
readonly STATE_OUT="${ANIMA_ROOT}/state/h_last_raw_regen_r5_result.json"
readonly PODS_CFG="${ANIMA_ROOT}/config/h100_pods.json"

exec > >(tee -a "${LOG}") 2>&1
log() { printf '[%s] %s\n' "$(date -u +%H:%M:%SZ)" "$*"; }

MODE="dry-run"
CONFIRM=""
for arg in "$@"; do
  case "$arg" in
    --dry-run)       MODE="dry-run" ;;
    --apply)         MODE="apply" ;;
    --yes-i-mean-it) CONFIRM="yes" ;;
    --help|-h)       sed -n '1,40p' "$0"; exit 0 ;;
    *) log "unknown arg: $arg"; exit 1 ;;
  esac
done

log "mode=${MODE} log=${LOG}"
log "pod_name=${POD_NAME} bid=\$${BID_USD_PER_HR}/hr"

# --- pre-flight ---------------------------------------------------------------
log "pre-flight: verify local prerequisites"
for pid in p1 p2 p3 p4; do
  d="${ANIMA_ROOT}/state/trained_adapters/${pid}/final"
  for req in adapter_config.json adapter_model.safetensors; do
    [[ -f "${d}/${req}" ]] || { log "  ABORT: missing ${d}/${req}"; exit 1; }
  done
  sz=$(du -sh "${d}" | awk '{print $1}')
  log "  [PASS] ${pid} adapter OK (${sz})"
done
[[ -f "${HF_TOKEN_FILE}" ]] || { log "ABORT: HF token missing: ${HF_TOKEN_FILE}"; exit 1; }
[[ -x "${HEXA_BIN}" ]]      || { log "ABORT: hexa binary missing: ${HEXA_BIN}"; exit 1; }
[[ -x "${RUNPODCTL}" ]]     || { log "ABORT: runpodctl missing"; exit 1; }
HF_TOKEN="$(cat "${HF_TOKEN_FILE}")"
log "  [PASS] HF token present, hexa binary present, runpodctl present"

# --- substrate models (frozen from training_proven_2026_04_24) ----------------
# Source of truth: config/phi_4path_substrates.json → training_proven_2026_04_24.model_actual
declare_p1_model="Qwen/Qwen3-8B";                      declare_p1_rank=64
declare_p2_model="unsloth/Meta-Llama-3.1-8B";          declare_p2_rank=64
declare_p3_model="mistralai/Mistral-Nemo-Base-2407";   declare_p3_rank=96
declare_p4_model="google/gemma-3-12b-pt";              declare_p4_rank=128

log "planned forward-pass matrix:"
for pid in p1 p2 p3 p4; do
  m_var="declare_${pid}_model"; r_var="declare_${pid}_rank"
  log "  ${pid}: ${!m_var}  rank=${!r_var}"
done

if [[ "${MODE}" == "dry-run" ]]; then
  log "DRY-RUN: would launch 1× H100 SXM5 pod, run 4 paths sequentially, pull 4 h_last_raw files, kill pod."
  log "DRY-RUN: then: ${HEXA_BIN} run ${ANIMA_ROOT}/tool/phi_4path_gate.hexa --tag r5"
  log "DRY-RUN: estimated cost \$3-5, wall ~40-60min."
  log "DRY-RUN: to apply: $0 --apply --yes-i-mean-it"
  exit 0
fi

if [[ "${MODE}" == "apply" && "${CONFIRM}" != "yes" ]]; then
  log "ERROR: --apply requires --yes-i-mean-it"; exit 1
fi

# --- step 1: launch pod -------------------------------------------------------
log "step 1/7: launching 1× H100 SXM5 pod (secureCloud, bid \$${BID_USD_PER_HR}/hr)"
LAUNCH_OUT=$("${RUNPODCTL}" create pod \
  --gpuType "NVIDIA H100 80GB HBM3" --gpuCount 1 \
  --secureCloud \
  --name "${POD_NAME}" \
  --imageName "${POD_IMAGE}" \
  --cost "${BID_USD_PER_HR}" --containerDiskSize 80 --volumeSize 150 --volumePath /workspace \
  --startSSH --ports "22/tcp" \
  --env "ANIMA_STAGE=2_fwd_only" \
  --env "ANIMA_ROADMAP_ENTRY=10" \
  --env "HEXA_STRICT=1" \
  --env "IDLE_KILL_MIN=5" \
  2>&1) || { log "LAUNCH FAIL: ${LAUNCH_OUT}"; exit 1; }
log "  runpodctl output: ${LAUNCH_OUT}"
POD_ID=$(echo "${LAUNCH_OUT}" | grep -oE 'pod "[a-z0-9]+" created' | head -1 | sed 's/pod "\([^"]*\)".*/\1/' || true)
if [[ -z "${POD_ID}" ]]; then
  POD_ID=$(echo "${LAUNCH_OUT}" | grep -oE '"id": "[^"]+"' | head -1 | sed 's/.*"\([^"]*\)"/\1/' || true)
fi
[[ -n "${POD_ID}" ]] || { log "ABORT: could not parse pod_id"; exit 1; }
log "  pod_id=${POD_ID}"

# Cleanup helper: always kill the pod on abort/exit to avoid idle burn.
_kill_pod() {
  log "[CLEANUP] removing pod ${POD_ID}"
  "${RUNPODCTL}" remove pod "${POD_ID}" 2>&1 | tail -1 | sed 's/^/    /' || true
  bash "${ANIMA_ROOT}/tool/h100_pods_sync.bash" 2>&1 | tail -1 | sed 's/^/    /' || true
}
trap '_kill_pod' ERR

# --- step 2: sync pods + wait for SSH ----------------------------------------
log "step 2/7: sync config/h100_pods.json + resolve ssh host:port"
bash "${ANIMA_ROOT}/tool/h100_pods_sync.bash" 2>&1 | tail -2

# Extract ssh_host/port for our pod_id
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
if [[ -z "${SSH_HOST}" ]]; then
  log "ABORT: pods_sync did not populate ssh_host for ${POD_ID}"
  exit 2
fi
log "  ssh: root@${SSH_HOST}:${SSH_PORT}"

log "  waiting for SSH (max ${SSH_MAX_SEC}s)"
SSH_OK=0
attempts=$(( SSH_MAX_SEC / SSH_RETRY_INTERVAL ))
for i in $(seq 1 ${attempts}); do
  if ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -o BatchMode=yes \
     -p "${SSH_PORT}" "root@${SSH_HOST}" "true" 2>/dev/null; then
    SSH_OK=1; break
  fi
  log "    retry ${i}/${attempts} in ${SSH_RETRY_INTERVAL}s"
  sleep ${SSH_RETRY_INTERVAL}
done
[[ ${SSH_OK} -eq 1 ]] || { log "ABORT: SSH not reachable within ${SSH_MAX_SEC}s"; exit 2; }
log "  SSH OK"

# --- step 3: bootstrap (pip install prerequisites) ---------------------------
log "step 3/7: bootstrap pip deps (transformers / peft / accelerate / safetensors / hf_transfer)"
BOOTSTRAP_SH='
set -e
export HF_HUB_ENABLE_HF_TRANSFER=1
mkdir -p /workspace/adapters /workspace/out
pip install -q --upgrade \
  "transformers>=4.44" "peft>=0.12" "accelerate>=0.34" \
  "bitsandbytes>=0.43" "hf_transfer" "sentencepiece" "safetensors"
python3 -c "import torch,transformers,peft; print(f\"torch={torch.__version__} transformers={transformers.__version__} peft={peft.__version__}\")"
nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv,noheader | head -1
'
ssh -o StrictHostKeyChecking=no -p "${SSH_PORT}" "root@${SSH_HOST}" "${BOOTSTRAP_SH}" 2>&1 | tail -6
log "  bootstrap DONE"

# --- step 4: ship forward-pass driver ----------------------------------------
log "step 4/7: ship forward-pass driver /workspace/fwd.py"
# NOTE: HEXA-FIRST + .gitignore '**/*.py' forbids committing .py files.
# Driver is written on the pod from this heredoc only; nothing is persisted
# locally. Schema strictly matches r4 (tool/h100_stage2_post_launch_chain.bash
# lines 262-270).
DRIVER_PY=$(cat <<'PYEOF'
import os, sys, json, time, traceback, gc
from pathlib import Path
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel

PHI_PATH_ID = os.environ['PHI_PATH_ID']
BASE_MODEL  = os.environ['PHI_MODEL']
LORA_RANK   = int(os.environ.get('PHI_LORA_RANK', '64'))
STEPS       = int(os.environ.get('PHI_STEPS', '300'))
ADAPTER_DIR = os.environ['PHI_ADAPTER_DIR']  # e.g. /workspace/adapters/p1/final
OUT_JSON    = os.environ['PHI_OUT_JSON']     # e.g. /workspace/out/h_last_raw_p1.json
HF_TOKEN    = os.environ.get('HF_TOKEN', '')

EVAL = [
    'The substrate of consciousness is',
    'Integrated information theory says',
    'Global workspace broadcast implies',
    'Attention schema models claim',
    'Higher-order thought requires',
    'Recurrent processing means',
    '의식의 기질은',
    '통합정보이론에 따르면',
    '전역작업공간의 방송은',
    '재귀처리는',
    '주의 스키마 모델은',
    '상위차원 사고는',
    'phi_6 defines',
    'hexad closure is',
    'meta-loop observation is',
    'Law 60 phase transition describes',
]

print(f'[{time.strftime("%H:%M:%S")}] path={PHI_PATH_ID} model={BASE_MODEL} rank={LORA_RANK} adapter={ADAPTER_DIR}', flush=True)

tok = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True, token=HF_TOKEN or None)
if tok.pad_token is None:
    tok.pad_token = tok.eos_token

try:
    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL, trust_remote_code=True, token=HF_TOKEN or None,
        torch_dtype=torch.bfloat16, device_map='auto', attn_implementation='sdpa',
    )
except Exception as e:
    print(f'LOAD_FAIL: {e}', flush=True); traceback.print_exc(); sys.exit(2)

print(f'[{time.strftime("%H:%M:%S")}] base loaded, attaching LoRA from {ADAPTER_DIR}', flush=True)
try:
    model = PeftModel.from_pretrained(model, ADAPTER_DIR, is_trainable=False)
except Exception as e:
    print(f'LORA_ATTACH_FAIL: {e}', flush=True); traceback.print_exc(); sys.exit(3)

model.eval()
print(f'[{time.strftime("%H:%M:%S")}] LoRA attached, running {len(EVAL)} prompts', flush=True)

# 2026-04-25 r6-α Axis 1 fix: byte-weighted h_last pool (parity with
# tool/h100_stage2_post_launch_chain.bash driver). Replaces last-token pool.
# bpt_i = len(utf8_bytes(surface(token_i))) / Σ_k len(utf8_bytes(surface(token_k)))
# h_last = Σ_i bpt_i · h_token_i
def _byte_weights(ids_1d, tokenizer):
    weights = []
    for tid in ids_1d.tolist():
        s = tokenizer.decode([tid], skip_special_tokens=False, clean_up_tokenization_spaces=False)
        b = len(s.encode('utf-8')) if s else 1
        weights.append(b)
    total = sum(weights) or 1
    return [w / total for w in weights]

h_last = []
with torch.no_grad():
    for i, p in enumerate(EVAL):
        ids = tok(p, return_tensors='pt').to(model.device)
        out = model(**ids, output_hidden_states=True)
        H = out.hidden_states[-1][0].float().cpu()  # (T, d_model)
        bpt = _byte_weights(ids['input_ids'][0].cpu(), tok)
        w = torch.tensor(bpt, dtype=H.dtype).unsqueeze(-1)
        pooled = (H * w).sum(dim=0).numpy()
        h_last.append({
            'idx': i, 'prompt': p,
            'h': [float(x) for x in pooled[:256]],
            'n_tokens': int(H.shape[0]),
            'bpt_sum': float(sum(bpt)),
        })

payload = {
    'schema': 'anima/h_last_raw/2',
    'reduction': 'byte_weighted_mean',
    'path_id': PHI_PATH_ID,
    'base_model': BASE_MODEL,
    'lora_rank': LORA_RANK,
    'steps': STEPS,
    'ts': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
    'hidden_dim_truncated': 256,
    'entries': h_last,
}
Path(OUT_JSON).write_text(json.dumps(payload, indent=2))
print(f'[{time.strftime("%H:%M:%S")}] DONE path={PHI_PATH_ID} → {OUT_JSON} (entries={len(h_last)})', flush=True)

# Best-effort cleanup so the next path inherits clean VRAM.
del model
gc.collect()
torch.cuda.empty_cache()
PYEOF
)
ssh -o StrictHostKeyChecking=no -p "${SSH_PORT}" "root@${SSH_HOST}" "cat > /workspace/fwd.py" <<< "${DRIVER_PY}"
log "  driver shipped ($(echo "${DRIVER_PY}" | wc -l | awk '{print $1}') lines)"

# --- step 5: per-path loop: scp adapter → run → pull h_last_raw → cleanup ----
log "step 5/7: sequential forward-pass loop p1..p4"
FAIL_PIDS=()
for pid in p1 p2 p3 p4; do
  m_var="declare_${pid}_model"; r_var="declare_${pid}_rank"
  model_id="${!m_var}"; rank="${!r_var}"
  local_adapter="${ANIMA_ROOT}/state/trained_adapters/${pid}/final"
  remote_adapter="/workspace/adapters/${pid}/final"
  remote_out="/workspace/out/h_last_raw_${pid}.json"
  local_out="${ANIMA_ROOT}/state/h_last_raw_${pid}_TRAINED_r5.json"

  log "── ${pid} ── model=${model_id} rank=${rank}"

  log "  [${pid}] scp adapter → ${remote_adapter}"
  ssh -o StrictHostKeyChecking=no -p "${SSH_PORT}" "root@${SSH_HOST}" \
    "rm -rf /workspace/adapters/${pid} && mkdir -p /workspace/adapters/${pid}" 2>&1 | tail -1
  if ! scp -o StrictHostKeyChecking=no -P "${SSH_PORT}" -r \
    "${local_adapter}" "root@${SSH_HOST}:/workspace/adapters/${pid}/" 2>&1 | tail -2; then
    log "  [FAIL] ${pid} adapter scp up"
    FAIL_PIDS+=("${pid}"); continue
  fi

  log "  [${pid}] running /workspace/fwd.py"
  # env vars passed via SSH command-line (single shell invocation).
  RUN_CMD="HF_TOKEN='${HF_TOKEN}' HF_HUB_ENABLE_HF_TRANSFER=1 \
PHI_PATH_ID='${pid}' PHI_MODEL='${model_id}' PHI_LORA_RANK='${rank}' PHI_STEPS='300' \
PHI_ADAPTER_DIR='${remote_adapter}' PHI_OUT_JSON='${remote_out}' \
python3 /workspace/fwd.py"
  if ssh -o StrictHostKeyChecking=no -p "${SSH_PORT}" "root@${SSH_HOST}" "${RUN_CMD}" 2>&1 | tail -40; then
    :
  else
    rc=$?
    log "  [FAIL] ${pid} driver exited non-zero (rc=${rc})"
    FAIL_PIDS+=("${pid}"); continue
  fi

  log "  [${pid}] scp h_last_raw → ${local_out}"
  if ! scp -o StrictHostKeyChecking=no -P "${SSH_PORT}" \
    "root@${SSH_HOST}:${remote_out}" "${local_out}" 2>&1 | tail -1; then
    log "  [FAIL] ${pid} h_last_raw scp down"
    FAIL_PIDS+=("${pid}"); continue
  fi

  # quick schema sanity check
  if ! python3 -c "
import json, sys
d = json.load(open('${local_out}'))
# 2026-04-25 r6-α: accept schema /1 (legacy last-token) and /2 (byte-weighted mean).
assert d.get('schema') in ('anima/h_last_raw/1','anima/h_last_raw/2'), 'schema mismatch'
assert d.get('path_id') == '${pid}', 'path_id mismatch'
assert len(d.get('entries', [])) == 16, f'expected 16 entries got {len(d.get(\"entries\",[]))}'
assert len(d['entries'][0]['h']) == 256, f'expected h dim 256 got {len(d[\"entries\"][0][\"h\"])}'
print(f'  ${pid}: schema OK ({d.get(\"schema\")}, reduction={d.get(\"reduction\",\"last_token\")}) entries=16 h_dim=256')
" 2>&1; then
    log "  [FAIL] ${pid} schema validation"
    FAIL_PIDS+=("${pid}"); continue
  fi
  log "  [PASS] ${pid} h_last_raw_TRAINED_r5.json written"

  # cleanup on pod to free disk + VRAM before next path
  log "  [${pid}] remote cleanup (adapter + HF cache for ${model_id})"
  ssh -o StrictHostKeyChecking=no -p "${SSH_PORT}" "root@${SSH_HOST}" "
    rm -rf /workspace/adapters/${pid}
    # HF cache hub dir name: models--<org>--<name> (slashes → --)
    cache_tag=\$(echo '${model_id}' | tr '/' '-')
    rm -rf \"/root/.cache/huggingface/hub/models--\${cache_tag}\" 2>/dev/null || true
    df -h /workspace | tail -1
  " 2>&1 | tail -2
done

if (( ${#FAIL_PIDS[@]} > 0 )); then
  log "FORWARD-PASS FAIL on paths: ${FAIL_PIDS[*]}"
  # pod kill via trap on exit
  exit 3
fi
log "  all 4 forward-passes DONE + h_last_raw_r5 files pulled"

# --- step 6: kill pod ---------------------------------------------------------
log "step 6/7: killing pod ${POD_ID}"
trap - ERR  # prevent duplicate kill
_kill_pod

# --- step 7: Φ 4-path gate ----------------------------------------------------
log "step 7/7: run Φ 4-path gate --tag r5"
GATE_OUT="/tmp/phi_gate_r5_${TS}.log"
set +e
"${HEXA_BIN}" run "${ANIMA_ROOT}/tool/phi_4path_gate.hexa" --tag r5 2>&1 | tee "${GATE_OUT}" | tail -30
gate_rc=$?
set -e
log "  Φ gate exit=${gate_rc} (0 = data-only, verdict in output)"

# --- write state file ---------------------------------------------------------
VERDICT_FILE="${ANIMA_ROOT}/state/phi_4path_gate_last_verdict.json"
VERDICT_TXT=""
if [[ -f "${VERDICT_FILE}" ]]; then
  VERDICT_TXT=$(python3 -c "
import json
d=json.load(open('${VERDICT_FILE}'))
print(json.dumps({k: d.get(k) for k in ('tag','verdict','L2_pass_count','KL_pass_count','p3_p4_L2')}))
" 2>/dev/null || echo '{}')
fi

cat > "${STATE_OUT}" <<EOF
{
  "schema": "anima/h_last_raw_regen_r5_result/1",
  "generated_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "pod_id": "${POD_ID}",
  "pod_name": "${POD_NAME}",
  "bid_usd_per_hr": ${BID_USD_PER_HR},
  "ssh_host": "${SSH_HOST}",
  "ssh_port": ${SSH_PORT},
  "paths_completed": ["p1","p2","p3","p4"],
  "artifacts": [
    "state/h_last_raw_p1_TRAINED_r5.json",
    "state/h_last_raw_p2_TRAINED_r5.json",
    "state/h_last_raw_p3_TRAINED_r5.json",
    "state/h_last_raw_p4_TRAINED_r5.json"
  ],
  "phi_gate_r5_verdict": ${VERDICT_TXT:-null},
  "phi_gate_log": "${GATE_OUT}",
  "tool_log": "${LOG}"
}
EOF
log "state: ${STATE_OUT}"
log "COMPLETE — pod killed, 4 h_last_raw_r5 files present, Φ gate r5 verdict recorded"
exit 0
