#!/usr/bin/env bash
# tool/r6_smoke_axis2_qwen25.bash
#
# PURPOSE
#   r6-α 1-pod smoke (Axis 2 / RoPE hypothesis validation) — BEFORE committing
#   to the 4-pod r6 launch ($170-220). Question answered:
#
#     "Does RoPE-matched p2 (Qwen2.5-7B-Base, rope_theta=1e6) pair with p1
#      (Qwen3-8B r5-trained, rope_theta=1e6) at L2 < 0.10?"
#
#   Verdict dispatch:
#     VALIDATED  — p95 L2 < 0.10  → greenlight 4-pod r6 launch
#     MARGINAL   — 0.10 ≤ < 0.1471 → weakens prediction, user call
#     REJECTED   — ≥ 0.1471        → Axis-2 incomplete, HOLD r6 / r7 re-diag
#
# DESIGN (§8.2 spec, min-path option A — base-only forward-pass, no LoRA)
#   • 1× H100 SXM5 pod, secureCloud, bid $3.50/hr
#   • Qwen2.5-7B-Base loaded, NO adapter (cheapest smoke, ~25-35min = $5-8)
#   • 16 EVAL prompts (same as Φ 4-path gate)
#   • Forward-pass with BOTH pools in one run:
#       (a) last_token  → /1 schema → apples-to-apples vs p1 TRAINED_r5 (/1)
#       (b) byte_weighted_mean → /2 schema → r6 full-chain parity
#   • Pair L2 computed locally vs state/h_last_raw_p1_TRAINED_r5.json
#
# PARITY
#   _byte_weights() bit-copied from tool/h100_stage2_post_launch_chain.bash
#   (commit a4e65c6d lines 272-283). Do NOT edit independently.
#
# SCREEN DETACH
#   This script itself runs synchronously (the full remote forward is ~20-30 min
#   and we poll SSH return; Bash-tool parent is the *orchestrator*, not a user
#   terminal). If run from Claude's Bash tool and SIGHUP is a concern, invoke
#   via:  screen -dmS r6-smoke bash tool/r6_smoke_axis2_qwen25.bash --apply --yes-i-mean-it
#   Pod lifetime is guarded by IDLE_KILL_MIN=10 env on launch as backstop.
#
# USAGE
#   bash tool/r6_smoke_axis2_qwen25.bash --dry-run
#   bash tool/r6_smoke_axis2_qwen25.bash --apply --yes-i-mean-it
#
# EXIT
#   0 = smoke completed (verdict in state JSON, not in exit rc)
#   1 = pre-flight / launch fail
#   2 = ssh / bootstrap fail
#   3 = forward-pass fail
#   4 = scp / schema validation fail
#   5 = local pair-L2 compute fail
set -euo pipefail

readonly ANIMA_ROOT="/Users/ghost/core/anima"
readonly RUNPODCTL="/opt/homebrew/bin/runpodctl"
readonly HF_TOKEN_FILE="${HOME}/.cache/huggingface/token"
readonly POD_NAME="anima-r6-smoke-$(date -u +%Y%m%dT%H%M%SZ)"
readonly POD_IMAGE="runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04"
readonly BID_USD_PER_HR="${ANIMA_H100_BID_USD:-3.50}"
readonly SSH_MAX_SEC="${ANIMA_FWD_SSH_MAX_SEC:-600}"
readonly SSH_RETRY_INTERVAL=15
readonly TS="$(date -u +%Y%m%dT%H%M%SZ)"
readonly LOG="/tmp/r6_smoke_axis2_qwen25_${TS}.log"
readonly STATE_OUT="${ANIMA_ROOT}/state/r6_smoke_axis2_result_20260425.json"
readonly PODS_CFG="${ANIMA_ROOT}/config/h100_pods.json"
readonly P1_REF="${ANIMA_ROOT}/state/h_last_raw_p1_TRAINED_r5.json"
readonly P2_OUT_LT="${ANIMA_ROOT}/state/h_last_raw_p2_SMOKE_qwen25_lasttoken_20260425.json"
readonly P2_OUT_BW="${ANIMA_ROOT}/state/h_last_raw_p2_SMOKE_qwen25_20260425.json"
readonly P2_MODEL="Qwen/Qwen2.5-7B"
readonly P2_MODEL_RANK=0   # 0 = base, no adapter

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
log "pod_name=${POD_NAME} bid=\$${BID_USD_PER_HR}/hr"
log "smoke_model=${P2_MODEL} (base, no adapter)"

# --- pre-flight ---------------------------------------------------------------
log "pre-flight: verify local prerequisites"
[[ -f "${HF_TOKEN_FILE}" ]] || { log "ABORT: HF token missing: ${HF_TOKEN_FILE}"; exit 1; }
[[ -x "${RUNPODCTL}" ]]     || { log "ABORT: runpodctl missing: ${RUNPODCTL}"; exit 1; }
[[ -f "${P1_REF}" ]]        || { log "ABORT: p1 reference h_last missing: ${P1_REF}"; exit 1; }
HF_TOKEN="$(cat "${HF_TOKEN_FILE}")"
# verify no live pods
LIVE_PODS=$(python3 -c "
import json
d=json.load(open('${PODS_CFG}'))
print(len(d.get('pods', [])))
" 2>/dev/null || echo "0")
if [[ "${LIVE_PODS}" != "0" ]]; then
  log "WARNING: config/h100_pods.json shows ${LIVE_PODS} live pod(s). Run tool/h100_pods_sync.bash first; ABORTING to avoid confusion."
  exit 1
fi
log "  [PASS] HF token present, runpodctl present, p1 ref present, pods=[]"

if [[ "${MODE}" == "dry-run" ]]; then
  log "DRY-RUN: would launch 1× H100 SXM5 pod, run Qwen2.5-7B-Base forward-pass (no LoRA)"
  log "DRY-RUN: pull 2 h_last files (last_token + byte_weighted), compute p1_p2 pair L2 locally"
  log "DRY-RUN: write verdict to ${STATE_OUT}, kill pod"
  log "DRY-RUN: estimated cost \$5-8, wall ~25-35min"
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
  --env "ANIMA_STAGE=r6_smoke_axis2" \
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

# Cleanup helper
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
log "step 4/6: ship forward-pass driver /workspace/fwd_smoke.py"
# Driver dumps BOTH pools (last_token + byte_weighted) in one forward pass.
# _byte_weights() is BIT-COPIED from tool/h100_stage2_post_launch_chain.bash
# (commit a4e65c6d) to ensure Φ 4-path parity at r6.
DRIVER_PY=$(cat <<'PYEOF'
import os, sys, json, time, traceback, gc
from pathlib import Path
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

BASE_MODEL  = os.environ['PHI_MODEL']
PATH_ID     = os.environ.get('PHI_PATH_ID', 'p2_smoke')
OUT_LT      = os.environ['PHI_OUT_LT']   # last-token
OUT_BW      = os.environ['PHI_OUT_BW']   # byte-weighted
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

# Report arch details to confirm RoPE theta match expectation.
cfg = model.config
print(f'[{time.strftime("%H:%M:%S")}] base loaded. hidden={getattr(cfg,"hidden_size",None)} '
      f'layers={getattr(cfg,"num_hidden_layers",None)} heads={getattr(cfg,"num_attention_heads",None)} '
      f'kv_heads={getattr(cfg,"num_key_value_heads",None)} '
      f'rope_theta={getattr(cfg,"rope_theta",None)} '
      f'rope_scaling={getattr(cfg,"rope_scaling",None)} '
      f'vocab={getattr(cfg,"vocab_size",None)}', flush=True)

model.eval()
print(f'[{time.strftime("%H:%M:%S")}] running {len(EVAL)} prompts (dual-pool)', flush=True)

# BIT-COPY from tool/h100_stage2_post_launch_chain.bash _byte_weights()
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
        H = out.hidden_states[-1][0].float().cpu()  # (T, d_model)
        # (a) last-token pool
        lt = H[-1].numpy()
        # (b) byte-weighted pool
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

# (a) last-token → schema /1 (legacy parity, compares directly to p1 r5)
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

# (b) byte-weighted → schema /2 (r6 full-chain parity)
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
ssh -o StrictHostKeyChecking=no -p "${SSH_PORT}" "root@${SSH_HOST}" "cat > /workspace/fwd_smoke.py" <<< "${DRIVER_PY}"
log "  driver shipped ($(echo "${DRIVER_PY}" | wc -l | awk '{print $1}') lines)"

# --- step 5: run + pull -------------------------------------------------------
log "step 5/6: run fwd_smoke.py (Qwen2.5-7B-Base forward-pass, dual-pool)"
REMOTE_OUT_LT="/workspace/out/h_last_raw_p2_smoke_lt.json"
REMOTE_OUT_BW="/workspace/out/h_last_raw_p2_smoke_bw.json"

RUN_CMD="HF_TOKEN='${HF_TOKEN}' HF_HUB_ENABLE_HF_TRANSFER=1 \
PHI_PATH_ID='p2_smoke_qwen25' PHI_MODEL='${P2_MODEL}' \
PHI_OUT_LT='${REMOTE_OUT_LT}' PHI_OUT_BW='${REMOTE_OUT_BW}' \
python3 /workspace/fwd_smoke.py"

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
  "root@${SSH_HOST}:${REMOTE_OUT_LT}" "${P2_OUT_LT}" 2>&1 | tail -1 || { log "[FAIL] scp LT down"; exit 4; }
scp -o StrictHostKeyChecking=no -P "${SSH_PORT}" \
  "root@${SSH_HOST}:${REMOTE_OUT_BW}" "${P2_OUT_BW}" 2>&1 | tail -1 || { log "[FAIL] scp BW down"; exit 4; }

# schema sanity
python3 - <<PYEOF || { log "[FAIL] schema validation"; exit 4; }
import json, sys
for path, expect_schema, expect_reduction in [
    ("${P2_OUT_LT}", "anima/h_last_raw/1", None),
    ("${P2_OUT_BW}", "anima/h_last_raw/2", "byte_weighted_mean"),
]:
    d = json.load(open(path))
    assert d.get('schema') == expect_schema, f"{path}: schema={d.get('schema')}"
    if expect_reduction:
        assert d.get('reduction') == expect_reduction, f"{path}: reduction={d.get('reduction')}"
    assert len(d.get('entries', [])) == 16, f"{path}: entries={len(d.get('entries',[]))}"
    assert len(d['entries'][0]['h']) == 256, f"{path}: h_dim={len(d['entries'][0]['h'])}"
    print(f"  {path}: schema OK ({expect_schema}) entries=16 h_dim=256")
PYEOF
log "  [PASS] both smoke h_last files landed and schema-validated"

# --- step 6: kill pod + local pair-L2 compute --------------------------------
T_POD_END_EPOCH=$(date -u +%s)
POD_WALL_SEC=$(( T_POD_END_EPOCH - T_START_EPOCH ))
EST_COST_USD=$(python3 -c "print(f'{${POD_WALL_SEC} / 3600.0 * ${BID_USD_PER_HR}:.2f}')")
log "step 6/6: killing pod ${POD_ID} (wall=${POD_WALL_SEC}s ≈ \$${EST_COST_USD})"
trap - ERR
_kill_pod

log "computing pair L2 (Φ scorer parity) locally"
# Φ scorer: H = stack(h); G = H @ H.T; eig = eigvalsh(G) top n_prompts desc, norm sum=1;
# L2 = ||spec_i - spec_j||_2. We compute p1_p2 L2 under BOTH pools.
PAIR_JSON=$(python3 - <<'PYEOF'
import json, numpy as np, sys, os

P1 = "/Users/ghost/core/anima/state/h_last_raw_p1_TRAINED_r5.json"
P2_LT = "/Users/ghost/core/anima/state/h_last_raw_p2_SMOKE_qwen25_lasttoken_20260425.json"
P2_BW = "/Users/ghost/core/anima/state/h_last_raw_p2_SMOKE_qwen25_20260425.json"

def load_H(path):
    d = json.load(open(path))
    rows = [e['h'] for e in d['entries']]
    return np.asarray(rows, dtype=np.float64), d

def spectrum(H):
    # H: (n, d).  G = H H^T; top n eigs desc, normalized sum=1.
    G = H @ H.T
    eig = np.linalg.eigvalsh(G)
    eig = np.sort(eig)[::-1][:H.shape[0]]
    s = eig.sum()
    if s <= 0:
        return np.ones_like(eig) / eig.size
    return eig / s

def pair_l2(a, b):
    return float(np.linalg.norm(a - b))

def per_prompt_l2(H1, H2):
    # Per-prompt raw vector distance (informational — not the Φ L2 metric but useful for
    # distribution diagnostic). Φ L2 operates on *spectra*; for per-prompt we use raw h.
    return [float(np.linalg.norm(H1[i] - H2[i])) for i in range(H1.shape[0])]

H1, d1 = load_H(P1)
H2_lt, d2_lt = load_H(P2_LT)
H2_bw, d2_bw = load_H(P2_BW)

assert H1.shape == H2_lt.shape == H2_bw.shape, f"shape mismatch: {H1.shape} {H2_lt.shape} {H2_bw.shape}"

spec1 = spectrum(H1)
spec2_lt = spectrum(H2_lt)
spec2_bw = spectrum(H2_bw)

l2_spec_lt = pair_l2(spec1, spec2_lt)
l2_spec_bw = pair_l2(spec1, spec2_bw)

# Per-prompt raw-vector distances (for distribution one-liner)
pp_lt = per_prompt_l2(H1, H2_lt)
pp_bw = per_prompt_l2(H1, H2_bw)

def agg(vals):
    a = np.asarray(vals)
    return {
        'mean': float(a.mean()),
        'p50':  float(np.percentile(a, 50)),
        'p95':  float(np.percentile(a, 95)),
        'max':  float(a.max()),
        'min':  float(a.min()),
    }

# Verdict uses the SPECTRAL L2 (the Φ gate metric), apples-to-apples via LAST-TOKEN pool
# (p1 r5 is /1 last-token, so p2_lt is the correct comparator for RoPE signal isolation).
L2_PRIMARY = l2_spec_lt
THRESH_VALIDATE = 0.10
THRESH_REJECT = 0.1471   # r5 p95 bound from phi_4path_gate.hexa

if L2_PRIMARY < THRESH_VALIDATE:
    verdict = 'VALIDATED'
elif L2_PRIMARY < THRESH_REJECT:
    verdict = 'MARGINAL'
else:
    verdict = 'REJECTED'

payload = {
    'schema': 'anima/r6_smoke_axis2/1',
    'verdict': verdict,
    'r5_baseline_p1_p2_L2': 0.152,
    'r6_target_p95_L2': THRESH_VALIDATE,
    'reject_threshold_L2': THRESH_REJECT,
    'spectral_L2': {
        'last_token':     l2_spec_lt,
        'byte_weighted':  l2_spec_bw,
        'primary':        'last_token',
        'primary_value':  L2_PRIMARY,
    },
    'per_prompt_raw_vector_L2': {
        'last_token':    {'values': pp_lt, 'agg': agg(pp_lt)},
        'byte_weighted': {'values': pp_bw, 'agg': agg(pp_bw)},
    },
    'p1_ref': {
        'file': P1,
        'schema': d1.get('schema'),
        'base_model': d1.get('base_model'),
        'ts': d1.get('ts'),
        'lora_rank': d1.get('lora_rank'),
        'steps': d1.get('steps'),
    },
    'p2_smoke': {
        'base_model': d2_lt.get('base_model'),
        'ts': d2_lt.get('ts'),
        'lora_rank': 0,
        'steps': 0,
        'note': 'base-only forward-pass (no LoRA) — min-path Option A',
    },
}
print(json.dumps(payload))
PYEOF
)
if [[ -z "${PAIR_JSON}" ]]; then
  log "[FAIL] local pair-L2 compute returned empty"
  exit 5
fi

# merge with run metadata + write final state
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
    'p2_last_token_h_last': '${P2_OUT_LT}'.replace('${ANIMA_ROOT}/', ''),
    'p2_byte_weighted_h_last': '${P2_OUT_BW}'.replace('${ANIMA_ROOT}/', ''),
    'tool_log': '${LOG}',
}
with open('${STATE_OUT}', 'w') as f:
    json.dump(pair, f, indent=2)
print(f"[state] ${STATE_OUT}")
print(f"[verdict] {pair['verdict']}  spectral_L2 last_token={pair['spectral_L2']['last_token']:.4f}  "
      f"byte_weighted={pair['spectral_L2']['byte_weighted']:.4f}")
print(f"[r5 baseline p1_p2] 0.1520   [r6 target p95] <0.10   [r5 p95 reject bound] 0.1471")
pp_lt = pair['per_prompt_raw_vector_L2']['last_token']['agg']
print(f"[per-prompt raw L2 last_token] min={pp_lt['min']:.3f} p50={pp_lt['p50']:.3f} "
      f"p95={pp_lt['p95']:.3f} max={pp_lt['max']:.3f} mean={pp_lt['mean']:.3f}")
PYEOF

log "COMPLETE — pod killed, smoke artifacts written, verdict recorded in ${STATE_OUT}"
exit 0
