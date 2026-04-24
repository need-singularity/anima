#!/usr/bin/env bash
# tool/r6_smoke_axis2_qwen3_null.bash
#
# PURPOSE
#   r6-α Axis-2 NULL-smoke — disambiguate the training-manifold vs architecture
#   contribution to the prior Qwen2.5 smoke L2 = 0.2082 (commit 7d0a2b4c).
#
#   Prior smoke compared base-Qwen2.5-7B vs r5-LoRA-trained-Qwen3-8B; so the
#   0.2082 conflates (training drift) + (arch/RoPE drift). This null-smoke
#   runs base-Qwen3-8B on the SAME 16 prompts — giving arch-only delta when
#   compared against base-Qwen2.5-7B (already landed in state/).
#
#   Decomposition (computed locally after pod kill):
#     ARCH-ONLY       = L2( base_Qwen3-8B , base_Qwen2.5-7B )
#     TRAINING-ONLY   = L2( base_Qwen3-8B , r5-trained_Qwen3-8B )
#     REFERENCE       = L2( r5-trained_Qwen3-8B , base_Qwen2.5-7B )  == 0.2082
#
#   Verdict (on primary ARCH-ONLY last_token spectral L2):
#     GO for 4-pod r6    — L2 < 0.10
#     MARGINAL (B-smoke) — 0.10 ≤ L2 < 0.15
#     HOLD / r7 redial   — L2 ≥ 0.15
#
# DESIGN
#   • 1× H100 SXM5 pod, secureCloud, bid ≤$3.50/hr
#   • Qwen3-8B-Base loaded, NO adapter — base forward only
#   • 16 EVAL prompts identical to the prior smoke (copied from driver)
#   • Dual pool (last_token /1  +  byte_weighted /2) in one forward pass
#   • Pair spectral L2 + per-prompt raw L2 computed locally after pod kill
#
# PARITY
#   Driver heredoc is byte-identical to tool/r6_smoke_axis2_qwen25.bash except
#   for the target model and output paths. _byte_weights() bit-copy retained.
#
# SCREEN DETACH
#   The parent Bash tool runs this synchronously (~3-5 min end-to-end based on
#   the prior 133s wall). If SIGHUP is a concern, invoke via:
#     screen -dmS r6-null bash tool/r6_smoke_axis2_qwen3_null.bash --apply --yes-i-mean-it
#   Backstop: IDLE_KILL_MIN=10 env on pod launch.
#
# USAGE
#   bash tool/r6_smoke_axis2_qwen3_null.bash --dry-run
#   bash tool/r6_smoke_axis2_qwen3_null.bash --apply --yes-i-mean-it
#
# EXIT
#   0 = smoke completed (verdict in state JSON, not in exit rc)
#   1 = pre-flight / launch fail
#   2 = ssh / bootstrap fail
#   3 = forward-pass fail
#   4 = scp / schema validation fail
#   5 = local decomposition compute fail
set -euo pipefail

readonly ANIMA_ROOT="/Users/ghost/core/anima"
readonly RUNPODCTL="/opt/homebrew/bin/runpodctl"
readonly HF_TOKEN_FILE="${HOME}/.cache/huggingface/token"
readonly POD_NAME="anima-r6-null-$(date -u +%Y%m%dT%H%M%SZ)"
readonly POD_IMAGE="runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04"
readonly BID_USD_PER_HR="${ANIMA_H100_BID_USD:-3.50}"
readonly SSH_MAX_SEC="${ANIMA_FWD_SSH_MAX_SEC:-600}"
readonly SSH_RETRY_INTERVAL=15
readonly TS="$(date -u +%Y%m%dT%H%M%SZ)"
readonly LOG="/tmp/r6_smoke_axis2_qwen3_null_${TS}.log"
readonly STATE_OUT="${ANIMA_ROOT}/state/r6_smoke_axis2_null_result_20260425.json"
readonly PODS_CFG="${ANIMA_ROOT}/config/h100_pods.json"
readonly P1_TRAINED_REF="${ANIMA_ROOT}/state/h_last_raw_p1_TRAINED_r5.json"
readonly P2_BASE_LT_REF="${ANIMA_ROOT}/state/h_last_raw_p2_SMOKE_qwen25_lasttoken_20260425.json"
readonly P2_BASE_BW_REF="${ANIMA_ROOT}/state/h_last_raw_p2_SMOKE_qwen25_20260425.json"
readonly OUT_LT="${ANIMA_ROOT}/state/h_last_raw_p1_BASE_null_lasttoken_20260425.json"
readonly OUT_BW="${ANIMA_ROOT}/state/h_last_raw_p1_BASE_null_20260425.json"
readonly TARGET_MODEL="Qwen/Qwen3-8B"

# Budget hard cap per task spec (will kill & exit if wall exceeds this budget)
readonly COST_HARD_CAP_USD="${ANIMA_NULL_SMOKE_HARD_CAP:-2.00}"

exec > >(tee -a "${LOG}") 2>&1
log() { printf '[%s] %s\n' "$(date -u +%H:%M:%SZ)" "$*"; }

MODE="dry-run"
CONFIRM=""
for arg in "$@"; do
  case "$arg" in
    --dry-run)       MODE="dry-run" ;;
    --apply)         MODE="apply" ;;
    --yes-i-mean-it) CONFIRM="yes" ;;
    --help|-h)       sed -n '1,80p' "$0"; exit 0 ;;
    *) log "unknown arg: $arg"; exit 1 ;;
  esac
done

log "mode=${MODE} log=${LOG}"
log "pod_name=${POD_NAME} bid=\$${BID_USD_PER_HR}/hr  hard_cap=\$${COST_HARD_CAP_USD}"
log "target_model=${TARGET_MODEL} (base, no adapter)"

# --- pre-flight ---------------------------------------------------------------
log "pre-flight: verify local prerequisites"
[[ -f "${HF_TOKEN_FILE}" ]] || { log "ABORT: HF token missing: ${HF_TOKEN_FILE}"; exit 1; }
[[ -x "${RUNPODCTL}" ]]     || { log "ABORT: runpodctl missing: ${RUNPODCTL}"; exit 1; }
[[ -f "${P1_TRAINED_REF}" ]]|| { log "ABORT: p1 TRAINED r5 ref missing: ${P1_TRAINED_REF}"; exit 1; }
[[ -f "${P2_BASE_LT_REF}" ]]|| { log "ABORT: p2 base LT ref missing: ${P2_BASE_LT_REF}"; exit 1; }
[[ -f "${P2_BASE_BW_REF}" ]]|| { log "ABORT: p2 base BW ref missing: ${P2_BASE_BW_REF}"; exit 1; }
HF_TOKEN="$(cat "${HF_TOKEN_FILE}")"
LIVE_PODS=$(python3 -c "
import json
d=json.load(open('${PODS_CFG}'))
print(len(d.get('pods', [])))
" 2>/dev/null || echo "0")
if [[ "${LIVE_PODS}" != "0" ]]; then
  log "WARNING: config/h100_pods.json shows ${LIVE_PODS} live pod(s). Run tool/h100_pods_sync.bash first; ABORTING."
  exit 1
fi
log "  [PASS] HF token present, runpodctl present, 3 ref files present, pods=[]"

if [[ "${MODE}" == "dry-run" ]]; then
  log "DRY-RUN: would launch 1× H100 SXM5 pod, run Qwen3-8B-Base forward-pass (no LoRA)"
  log "DRY-RUN: pull 2 h_last files (last_token + byte_weighted), compute 4-metric L2 decomposition"
  log "DRY-RUN: write verdict to ${STATE_OUT}, kill pod"
  log "DRY-RUN: estimated cost \$0.15 based on prior 133s wall, hard cap \$${COST_HARD_CAP_USD}"
  log "DRY-RUN: to apply: $0 --apply --yes-i-mean-it"
  exit 0
fi

if [[ "${MODE}" == "apply" && "${CONFIRM}" != "yes" ]]; then
  log "ERROR: --apply requires --yes-i-mean-it"; exit 1
fi

T_START=$(date -u +%Y-%m-%dT%H:%M:%SZ)
T_START_EPOCH=$(date -u +%s)

# --- step 1: launch pod -------------------------------------------------------
log "step 1/6: launching 1× H100 SXM5 pod (secureCloud, bid \$${BID_USD_PER_HR}/hr)"
LAUNCH_OUT=$("${RUNPODCTL}" create pod \
  --gpuType "NVIDIA H100 80GB HBM3" --gpuCount 1 \
  --secureCloud \
  --name "${POD_NAME}" \
  --imageName "${POD_IMAGE}" \
  --cost "${BID_USD_PER_HR}" --containerDiskSize 80 --volumeSize 150 --volumePath /workspace \
  --startSSH --ports "22/tcp" \
  --env "ANIMA_STAGE=r6_smoke_axis2_null" \
  --env "ANIMA_ROADMAP_ENTRY=10" \
  --env "HEXA_STRICT=1" \
  --env "IDLE_KILL_MIN=10" \
  2>&1) || { log "LAUNCH FAIL: ${LAUNCH_OUT}"; exit 1; }
log "  runpodctl output: ${LAUNCH_OUT}"
POD_ID=$(echo "${LAUNCH_OUT}" | grep -oE 'pod "[a-z0-9]+" created' | head -1 | sed 's/pod "\([^"]*\)".*/\1/' || true)
if [[ -z "${POD_ID}" ]]; then
  POD_ID=$(echo "${LAUNCH_OUT}" | grep -oE '"id": "[^"]+"' | head -1 | sed 's/.*"\([^"]*\)"/\1/' || true)
fi
[[ -n "${POD_ID}" ]] || { log "ABORT: could not parse pod_id"; exit 1; }
log "  pod_id=${POD_ID}"

_kill_pod() {
  log "[CLEANUP] removing pod ${POD_ID}"
  "${RUNPODCTL}" remove pod "${POD_ID}" 2>&1 | tail -1 | sed 's/^/    /' || true
  bash "${ANIMA_ROOT}/tool/h100_pods_sync.bash" 2>&1 | tail -1 | sed 's/^/    /' || true
}
trap '_kill_pod' ERR

# --- step 2: sync pods + wait for SSH ----------------------------------------
log "step 2/6: sync config/h100_pods.json + resolve ssh host:port"
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

# Budget backstop — kill if wall already exceeded hard cap by the time SSH is up
_budget_check() {
  local now=$(date -u +%s)
  local wall=$(( now - T_START_EPOCH ))
  local cost=$(python3 -c "print(f'{${wall} / 3600.0 * ${BID_USD_PER_HR}:.4f}')")
  local over=$(python3 -c "print(1 if float('${cost}') > float('${COST_HARD_CAP_USD}') else 0)")
  if [[ "${over}" == "1" ]]; then
    log "[BUDGET] cost ${cost} > hard cap ${COST_HARD_CAP_USD}; killing pod"
    _kill_pod
    exit 1
  fi
}

# --- step 3: bootstrap --------------------------------------------------------
log "step 3/6: bootstrap pip deps"
BOOTSTRAP_SH='
set -e
export HF_HUB_ENABLE_HF_TRANSFER=1
mkdir -p /workspace/out
pip install -q --upgrade \
  "transformers>=4.44" "accelerate>=0.34" \
  "hf_transfer" "sentencepiece" "safetensors"
python3 -c "import torch,transformers; print(f\"torch={torch.__version__} transformers={transformers.__version__}\")"
nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv,noheader | head -1
'
ssh -o StrictHostKeyChecking=no -p "${SSH_PORT}" "root@${SSH_HOST}" "${BOOTSTRAP_SH}" 2>&1 | tail -6
log "  bootstrap DONE"

# --- step 4: ship forward-pass driver ----------------------------------------
log "step 4/6: ship forward-pass driver /workspace/fwd_null.py"
DRIVER_PY=$(cat <<'PYEOF'
import os, sys, json, time, traceback, gc
from pathlib import Path
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

BASE_MODEL  = os.environ['PHI_MODEL']
PATH_ID     = os.environ.get('PHI_PATH_ID', 'p1_base_null')
OUT_LT      = os.environ['PHI_OUT_LT']
OUT_BW      = os.environ['PHI_OUT_BW']
HF_TOKEN    = os.environ.get('HF_TOKEN', '')

# Exact 16 prompts bit-identical to tool/r6_smoke_axis2_qwen25.bash
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

print(f'[{time.strftime("%H:%M:%S")}] path={PATH_ID} model={BASE_MODEL} (base, no adapter)', flush=True)

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

cfg = model.config
print(f'[{time.strftime("%H:%M:%S")}] base loaded. hidden={getattr(cfg,"hidden_size",None)} '
      f'layers={getattr(cfg,"num_hidden_layers",None)} heads={getattr(cfg,"num_attention_heads",None)} '
      f'kv_heads={getattr(cfg,"num_key_value_heads",None)} '
      f'rope_theta={getattr(cfg,"rope_theta",None)} '
      f'rope_scaling={getattr(cfg,"rope_scaling",None)} '
      f'vocab={getattr(cfg,"vocab_size",None)}', flush=True)

model.eval()
print(f'[{time.strftime("%H:%M:%S")}] running {len(EVAL)} prompts (dual-pool)', flush=True)

def _byte_weights(ids_1d, tokenizer):
    weights = []
    for tid in ids_1d.tolist():
        s = tokenizer.decode([tid], skip_special_tokens=False, clean_up_tokenization_spaces=False)
        b = len(s.encode('utf-8')) if s else 1
        weights.append(b)
    total = sum(weights) or 1
    return [w / total for w in weights]

entries_lt = []
entries_bw = []
with torch.no_grad():
    for i, p in enumerate(EVAL):
        ids = tok(p, return_tensors='pt').to(model.device)
        out = model(**ids, output_hidden_states=True)
        H = out.hidden_states[-1][0].float().cpu()
        lt = H[-1].numpy()
        bpt = _byte_weights(ids['input_ids'][0].cpu(), tok)
        w = torch.tensor(bpt, dtype=H.dtype).unsqueeze(-1)
        bw = (H * w).sum(dim=0).numpy()
        entries_lt.append({
            'idx': i, 'prompt': p,
            'h': [float(x) for x in lt[:256]],
            'n_tokens': int(H.shape[0]),
        })
        entries_bw.append({
            'idx': i, 'prompt': p,
            'h': [float(x) for x in bw[:256]],
            'n_tokens': int(H.shape[0]),
            'bpt_sum': float(sum(bpt)),
        })

ts_iso = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())

Path(OUT_LT).write_text(json.dumps({
    'schema': 'anima/h_last_raw/1',
    'path_id': PATH_ID,
    'base_model': BASE_MODEL,
    'lora_rank': 0,
    'steps': 0,
    'ts': ts_iso,
    'hidden_dim_truncated': 256,
    'entries': entries_lt,
}, indent=2))

Path(OUT_BW).write_text(json.dumps({
    'schema': 'anima/h_last_raw/2',
    'reduction': 'byte_weighted_mean',
    'path_id': PATH_ID,
    'base_model': BASE_MODEL,
    'lora_rank': 0,
    'steps': 0,
    'ts': ts_iso,
    'hidden_dim_truncated': 256,
    'entries': entries_bw,
}, indent=2))

print(f'[{time.strftime("%H:%M:%S")}] DONE → {OUT_LT} + {OUT_BW} (entries={len(entries_lt)} each)', flush=True)

del model
gc.collect()
torch.cuda.empty_cache()
PYEOF
)
ssh -o StrictHostKeyChecking=no -p "${SSH_PORT}" "root@${SSH_HOST}" "cat > /workspace/fwd_null.py" <<< "${DRIVER_PY}"
log "  driver shipped ($(echo "${DRIVER_PY}" | wc -l | awk '{print $1}') lines)"

# --- step 5: run + pull -------------------------------------------------------
log "step 5/6: run fwd_null.py (Qwen3-8B-Base forward-pass, dual-pool)"
REMOTE_OUT_LT="/workspace/out/h_last_raw_p1_base_null_lt.json"
REMOTE_OUT_BW="/workspace/out/h_last_raw_p1_base_null_bw.json"

RUN_CMD="HF_TOKEN='${HF_TOKEN}' HF_HUB_ENABLE_HF_TRANSFER=1 \
PHI_PATH_ID='p1_base_null_qwen3' PHI_MODEL='${TARGET_MODEL}' \
PHI_OUT_LT='${REMOTE_OUT_LT}' PHI_OUT_BW='${REMOTE_OUT_BW}' \
python3 /workspace/fwd_null.py"

set +e
ssh -o StrictHostKeyChecking=no -p "${SSH_PORT}" "root@${SSH_HOST}" "${RUN_CMD}" 2>&1 | tail -60
rc=$?
set -e
if [[ ${rc} -ne 0 ]]; then
  log "[FAIL] smoke driver exited rc=${rc}"
  exit 3
fi

log "  scp h_last files down"
scp -o StrictHostKeyChecking=no -P "${SSH_PORT}" \
  "root@${SSH_HOST}:${REMOTE_OUT_LT}" "${OUT_LT}" 2>&1 | tail -1 || { log "[FAIL] scp LT down"; exit 4; }
scp -o StrictHostKeyChecking=no -P "${SSH_PORT}" \
  "root@${SSH_HOST}:${REMOTE_OUT_BW}" "${OUT_BW}" 2>&1 | tail -1 || { log "[FAIL] scp BW down"; exit 4; }

python3 - <<PYEOF || { log "[FAIL] schema validation"; exit 4; }
import json, sys
for path, expect_schema, expect_reduction in [
    ("${OUT_LT}", "anima/h_last_raw/1", None),
    ("${OUT_BW}", "anima/h_last_raw/2", "byte_weighted_mean"),
]:
    d = json.load(open(path))
    assert d.get('schema') == expect_schema, f"{path}: schema={d.get('schema')}"
    if expect_reduction:
        assert d.get('reduction') == expect_reduction, f"{path}: reduction={d.get('reduction')}"
    assert d.get('base_model') == "${TARGET_MODEL}", f"{path}: base_model={d.get('base_model')}"
    assert d.get('lora_rank') == 0, f"{path}: lora_rank={d.get('lora_rank')}"
    assert len(d.get('entries', [])) == 16, f"{path}: entries={len(d.get('entries',[]))}"
    assert len(d['entries'][0]['h']) == 256, f"{path}: h_dim={len(d['entries'][0]['h'])}"
    print(f"  {path}: schema OK ({expect_schema}) entries=16 h_dim=256 base=${TARGET_MODEL}")
PYEOF
log "  [PASS] both null h_last files landed and schema-validated"

# --- step 6: kill pod + 4-metric L2 decomposition ----------------------------
T_POD_END_EPOCH=$(date -u +%s)
POD_WALL_SEC=$(( T_POD_END_EPOCH - T_START_EPOCH ))
EST_COST_USD=$(python3 -c "print(f'{${POD_WALL_SEC} / 3600.0 * ${BID_USD_PER_HR}:.2f}')")
log "step 6/6: killing pod ${POD_ID} (wall=${POD_WALL_SEC}s ≈ \$${EST_COST_USD})"
trap - ERR
_kill_pod

log "computing 4-metric L2 decomposition locally"
PAIR_JSON=$(python3 - <<'PYEOF'
import json, numpy as np, sys, os

BASE_P1   = "/Users/ghost/core/anima/state/h_last_raw_p1_BASE_null_lasttoken_20260425.json"
BASE_P1BW = "/Users/ghost/core/anima/state/h_last_raw_p1_BASE_null_20260425.json"
BASE_P2   = "/Users/ghost/core/anima/state/h_last_raw_p2_SMOKE_qwen25_lasttoken_20260425.json"
BASE_P2BW = "/Users/ghost/core/anima/state/h_last_raw_p2_SMOKE_qwen25_20260425.json"
TRAIN_P1  = "/Users/ghost/core/anima/state/h_last_raw_p1_TRAINED_r5.json"

def load_H(path):
    d = json.load(open(path))
    rows = [e['h'] for e in d['entries']]
    return np.asarray(rows, dtype=np.float64), d

def spectrum(H):
    G = H @ H.T
    eig = np.linalg.eigvalsh(G)
    eig = np.sort(eig)[::-1][:H.shape[0]]
    s = eig.sum()
    if s <= 0:
        return np.ones_like(eig) / eig.size
    return eig / s

def pair_spec_l2(H1, H2):
    return float(np.linalg.norm(spectrum(H1) - spectrum(H2)))

def per_prompt_l2(H1, H2):
    return [float(np.linalg.norm(H1[i] - H2[i])) for i in range(H1.shape[0])]

def agg(vals):
    a = np.asarray(vals)
    return {
        'mean': float(a.mean()),
        'p50':  float(np.percentile(a, 50)),
        'p95':  float(np.percentile(a, 95)),
        'max':  float(a.max()),
        'min':  float(a.min()),
    }

H_bp1_lt, d_bp1_lt = load_H(BASE_P1)
H_bp1_bw, _        = load_H(BASE_P1BW)
H_bp2_lt, d_bp2_lt = load_H(BASE_P2)
H_bp2_bw, _        = load_H(BASE_P2BW)
H_tp1_lt, d_tp1_lt = load_H(TRAIN_P1)

assert H_bp1_lt.shape == H_bp2_lt.shape == H_tp1_lt.shape == (16, 256)
assert H_bp1_bw.shape == H_bp2_bw.shape == (16, 256)

# 4-metric decomposition (spectral L2, Φ-parity)
m = {
    'L2_baseP1_baseP2_lasttoken':     pair_spec_l2(H_bp1_lt, H_bp2_lt),   # ARCH ONLY
    'L2_baseP1_baseP2_byteweighted':  pair_spec_l2(H_bp1_bw, H_bp2_bw),   # ARCH ONLY + pool
    'L2_baseP1_trainedP1_lasttoken':  pair_spec_l2(H_bp1_lt, H_tp1_lt),   # TRAINING ONLY
    'L2_trainedP1_baseP2_lasttoken':  pair_spec_l2(H_tp1_lt, H_bp2_lt),   # REFERENCE (prior 0.2082)
}

# Per-prompt raw-vector L2 aggs
pp_aggs = {
    'baseP1_baseP2_lt':    agg(per_prompt_l2(H_bp1_lt, H_bp2_lt)),
    'baseP1_baseP2_bw':    agg(per_prompt_l2(H_bp1_bw, H_bp2_bw)),
    'baseP1_trainedP1_lt': agg(per_prompt_l2(H_bp1_lt, H_tp1_lt)),
    'trainedP1_baseP2_lt': agg(per_prompt_l2(H_tp1_lt, H_bp2_lt)),
}

L2_PRIMARY = m['L2_baseP1_baseP2_lasttoken']
L2_REF     = m['L2_trainedP1_baseP2_lasttoken']
arch_contribution = (L2_PRIMARY / L2_REF) if L2_REF > 0 else None

if L2_PRIMARY < 0.10:
    verdict = 'GO'
elif L2_PRIMARY < 0.15:
    verdict = 'MARGINAL'
else:
    verdict = 'HOLD'

payload = {
    'schema': 'anima/r6_smoke_axis2_null/1',
    'verdict': verdict,
    'primary_metric': 'L2_baseP1_baseP2_lasttoken',
    'primary_value': L2_PRIMARY,
    'thresholds': {
        'GO_below': 0.10,
        'MARGINAL_below': 0.15,
    },
    'L2_decomposition': m,
    'arch_contribution_ratio': arch_contribution,
    'per_prompt_raw_vector_L2': pp_aggs,
    'refs': {
        'base_p1_Qwen3_8B_lt': {'file': BASE_P1, 'base_model': d_bp1_lt.get('base_model'), 'ts': d_bp1_lt.get('ts')},
        'base_p2_Qwen25_7B_lt': {'file': BASE_P2, 'base_model': d_bp2_lt.get('base_model'), 'ts': d_bp2_lt.get('ts')},
        'trained_p1_Qwen3_8B_r5_lt': {'file': TRAIN_P1, 'base_model': d_tp1_lt.get('base_model'), 'ts': d_tp1_lt.get('ts'), 'lora_rank': d_tp1_lt.get('lora_rank'), 'steps': d_tp1_lt.get('steps')},
    },
    'interpretation_template': {
        'arch_only': 'L2_baseP1_baseP2_lasttoken — Qwen3-8B vs Qwen2.5-7B, both base, same prompts',
        'training_only': 'L2_baseP1_trainedP1_lasttoken — Qwen3-8B base vs r5-LoRA-trained Qwen3-8B',
        'prior_smoke_reference': 'L2_trainedP1_baseP2_lasttoken — should ≈ 0.2082 (sanity check)',
    },
}
print(json.dumps(payload))
PYEOF
)
if [[ -z "${PAIR_JSON}" ]]; then
  log "[FAIL] local decomposition compute returned empty"
  exit 5
fi

python3 - <<PYEOF
import json, sys
pair = json.loads('''${PAIR_JSON}''')
pair['pod'] = {
    'pod_id':    '${POD_ID}',
    'pod_name':  '${POD_NAME}',
    'bid_usd_per_hr': ${BID_USD_PER_HR},
    'start_utc': '${T_START}',
    'end_utc':   '$(date -u +%Y-%m-%dT%H:%M:%SZ)',
    'wall_sec':  ${POD_WALL_SEC},
    'est_cost_usd': float('${EST_COST_USD}'),
    'ssh_host':  '${SSH_HOST}',
    'ssh_port':  ${SSH_PORT},
    'image':     '${POD_IMAGE}',
    'cloud':     'secureCloud',
}
pair['artifacts'] = {
    'base_p1_last_token': '${OUT_LT}'.replace('${ANIMA_ROOT}/', ''),
    'base_p1_byte_weighted': '${OUT_BW}'.replace('${ANIMA_ROOT}/', ''),
    'tool_log': '${LOG}',
}
with open('${STATE_OUT}', 'w') as f:
    json.dump(pair, f, indent=2)
m = pair['L2_decomposition']
print(f"[state] ${STATE_OUT}")
print(f"[verdict] {pair['verdict']}  primary=L2_baseP1_baseP2_lasttoken={pair['primary_value']:.4f}")
print(f"[4-metric L2 table]")
print(f"  ARCH ONLY       L2_baseP1_baseP2_lasttoken    = {m['L2_baseP1_baseP2_lasttoken']:.4f}")
print(f"  ARCH + pool     L2_baseP1_baseP2_byteweighted = {m['L2_baseP1_baseP2_byteweighted']:.4f}")
print(f"  TRAINING ONLY   L2_baseP1_trainedP1_lasttoken = {m['L2_baseP1_trainedP1_lasttoken']:.4f}")
print(f"  REFERENCE       L2_trainedP1_baseP2_lasttoken = {m['L2_trainedP1_baseP2_lasttoken']:.4f} (prior smoke = 0.2082)")
print(f"[arch_contribution = arch_only / reference] = {pair['arch_contribution_ratio']:.4f}")
PYEOF

log "COMPLETE — pod killed, null artifacts written, verdict recorded in ${STATE_OUT}"
exit 0
