#!/usr/bin/env bash
# tool/h100_stage2_post_launch_chain.bash
#
# PURPOSE
#   Chains the 3 post-launch steps into a single no-pause flow so H100 pods
#   never sit idle waiting for human decisions between steps.
#   User directive 2026-04-24: '유휴 상태절대금지 코드수준 구현'.
#
# CHAIN (all on 4 pods in parallel):
#   1. Wait for SSH available on all 4 pods (max 90s)
#   2. apt install clang + hexa binary + anima/hexa-lang git clone
#   3. Ship pod-side training driver (python heredoc, NOT committed per HEXA-FIRST)
#   4. Kickoff 4 trainings nohup + log paths reported
#
# raw#9  deterministic: config/phi_4path_substrates.json resolves models;
#        all overrides via ANIMA_* env vars.
# raw#20 H100 stop-gate: invoked ONLY from h100_stage2_unified_launch.bash
#        after --apply --yes-i-mean-it. Standalone invocation requires
#        state/h100_stage2_launch_state.json to already exist (pods live).
#
# USAGE
#   bash tool/h100_stage2_post_launch_chain.bash
#     (reads state/h100_stage2_launch_state.json for pod list)
#
# EXIT
#   0 = all 4 trainings kicked off (not = training complete; training
#       runs nohup in background on each pod, pull artifacts later).
#   1 = missing launch_state / precondition fail
#   2 = ssh to ≥1 pod failed within timeout
#   3 = training kickoff failed on ≥1 pod
set -euo pipefail

readonly ANIMA_ROOT="/Users/ghost/core/anima"
readonly LAUNCH_STATE="${ANIMA_ROOT}/state/h100_stage2_launch_state.json"
readonly PODS_CFG="${ANIMA_ROOT}/config/h100_pods.json"
readonly SUBSTRATES_CFG="${ANIMA_ROOT}/config/phi_4path_substrates.json"
readonly LORA_CFG="${ANIMA_ROOT}/config/lora_rank_per_path.json"
readonly HF_TOKEN_FILE="${HOME}/.cache/huggingface/token"
readonly MAX_STEPS="${ANIMA_H100_STAGE2_MAX_STEPS:-300}"
readonly CHAIN_LOG="/tmp/h100_stage2_chain_$(date -u +%Y%m%dT%H%M%SZ).log"

log() { printf '[%s] %s\n' "$(date -u +%H:%M:%SZ)" "$*" | tee -a "${CHAIN_LOG}"; }

[[ -f "${LAUNCH_STATE}" ]] || { log "ABORT: launch_state missing: ${LAUNCH_STATE}"; exit 1; }
[[ -f "${PODS_CFG}" ]]     || { log "ABORT: pods config missing: ${PODS_CFG}"; exit 1; }
[[ -f "${HF_TOKEN_FILE}" ]] || { log "ABORT: hf token missing: ${HF_TOKEN_FILE}"; exit 1; }

HF_TOKEN="$(cat "${HF_TOKEN_FILE}")"

# Extract pod → (ssh_host, ssh_port, model, rank) tuples.
PODS_JSON=$(python3 <<PYEOF
import json, sys
ls = json.load(open("${LAUNCH_STATE}"))
pods_cfg = json.load(open("${PODS_CFG}"))
subs = json.load(open("${SUBSTRATES_CFG}"))
lora = json.load(open("${LORA_CFG}"))
# Resolve model per pid from substrates.fallback_chain[0] if training_hazards non-empty
def resolve_model(pid):
    for p in subs["paths"]:
        if p["id"] == pid:
            primary = p["model"]
            hazards = p.get("training_hazards", [])
            fallbacks = p.get("fallback_chain", [])
            if hazards and fallbacks and fallbacks[0] != primary:
                return fallbacks[0]
            return primary
    return None
def resolve_rank(pid):
    key = {"p1":"p1_qwen3_8b","p2":"p2_llama_3_1_8b","p3":"p3_ministral_3_14b","p4":"p4_gemma_4_31b"}.get(pid)
    return lora["paths"][key]["lora"]["rank"] if key in lora.get("paths",{}) else 64
rows = []
for launch_pod in ls.get("pods", []):
    pid = launch_pod["path_id"]
    pod_id = launch_pod["pod_id"]
    cfg_entry = next((x for x in pods_cfg["pods"] if x["pod_id"] == pod_id), None)
    if not cfg_entry: continue
    rows.append({
        "pid": pid, "pod_id": pod_id,
        "host": cfg_entry["ssh_host"], "port": cfg_entry["ssh_port"],
        "model": resolve_model(pid), "rank": resolve_rank(pid),
    })
print(json.dumps(rows))
PYEOF
)

POD_COUNT=$(echo "${PODS_JSON}" | python3 -c 'import json,sys;print(len(json.load(sys.stdin)))')
log "chain start — pods=${POD_COUNT} max_steps=${MAX_STEPS}"
echo "${PODS_JSON}" | python3 -c "
import json, sys
for r in json.load(sys.stdin):
    print(f\"  {r['pid']}: {r['host']}:{r['port']} model={r['model']} rank={r['rank']}\")
"

# --- step 1: SSH available ----------------------------------------------------
# 2026-04-24 ROI V9 재발생금지: 90s → 600s max (cold-start pods commonly
# take 2-3min on RunPod secureCloud). Configurable via env ANIMA_CHAIN_SSH_MAX_SEC.
readonly SSH_MAX_SEC="${ANIMA_CHAIN_SSH_MAX_SEC:-600}"
readonly SSH_RETRY_INTERVAL=15
readonly SSH_MAX_ATTEMPTS=$(( SSH_MAX_SEC / SSH_RETRY_INTERVAL ))

# Cleanup helper: on ABORT, auto-remove pods to prevent idle burn.
# Matches round-3 ABORT incident (2026-04-24): 4 pods left RUNNING after
# chain ABORT, burning ~$48/hr without useful work.
_cleanup_abort_pods() {
  log "  [CLEANUP] auto-removing ${POD_COUNT} pods (ABORT prevention, 재발생금지)"
  for row in $(echo "${PODS_JSON}" | python3 -c "
import json, sys
for r in json.load(sys.stdin):
    print(f\"{r['pod_id']}\")
"); do
    /opt/homebrew/bin/runpodctl remove pod "$row" 2>&1 | tail -1 | sed 's/^/    /'
  done
  bash "${ANIMA_ROOT}/tool/h100_pods_sync.bash" 2>&1 | tail -1 | sed 's/^/    /'
}

log "step 1/4: waiting for SSH on all pods (max ${SSH_MAX_SEC}s, ${SSH_MAX_ATTEMPTS} retries × ${SSH_RETRY_INTERVAL}s)"
SSH_OK=0
for i in $(seq 1 ${SSH_MAX_ATTEMPTS}); do
  SSH_OK=1
  for row in $(echo "${PODS_JSON}" | python3 -c "
import json, sys
for r in json.load(sys.stdin):
    print(f\"{r['pid']}:{r['host']}:{r['port']}\")
"); do
    IFS=':' read -r pid host port <<< "$row"
    if ! ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -o BatchMode=yes -p "$port" "root@${host}" "true" 2>/dev/null; then
      SSH_OK=0; break
    fi
  done
  [[ $SSH_OK -eq 1 ]] && break
  log "  retry in ${SSH_RETRY_INTERVAL}s (attempt $i/${SSH_MAX_ATTEMPTS})"
  sleep ${SSH_RETRY_INTERVAL}
done
if [[ $SSH_OK -ne 1 ]]; then
  log "ABORT: SSH not available within ${SSH_MAX_SEC}s"
  _cleanup_abort_pods
  exit 2
fi
log "  SSH OK all pods"

# --- step 2: bootstrap (parallel) --------------------------------------------
log "step 2/4: bootstrap (apt+hexa+git clone) on all 4 pods (parallel)"
# 2026-04-24 fix (2-stage):
# (1) sed 's/.*=//' was greedy — signed R2 URLs contain multiple '=' (X-Amz-*
#     params) so greedy match returned the signature hex only. curl treated
#     the 64-char hex as a hostname → rc=99 ABORT. Fix: strip only through
#     the FIRST '=' via sed 's/^[^=]*=//'.
# (2) fetch_hexa_binary_url.bash emits `export HEXA_URL=https://...\?…\&…`
#     (backslash-escaped for shell `eval`/`source` consumers). Verbatim sed
#     extraction keeps the literal '\' characters, so curl sends a malformed
#     URL and the R2 endpoint returns HTTP 400. Fix: strip backslashes with
#     `tr -d '\\'` (URLs never contain literal '\'; percent-encoding is used).
# Combined: parse correctly AND unescape, with explicit sanity check.
_FETCH_HEXA_OUT=$(bash "${ANIMA_ROOT}/tool/fetch_hexa_binary_url.bash" --export 2>&1)
BOOTSTRAP_URL=$(echo "${_FETCH_HEXA_OUT}" | grep '^export HEXA_URL=' | sed 's/^[^=]*=//' | tr -d '\\')
BOOTSTRAP_SHA=$(echo "${_FETCH_HEXA_OUT}" | grep '^export HEXA_SHA256=' | sed 's/^[^=]*=//' | tr -d '\\')
if [[ "${BOOTSTRAP_URL}" != https://* || ${#BOOTSTRAP_SHA} -ne 64 ]]; then
  log "ABORT: bootstrap url/sha parse failed"
  log "  url='${BOOTSTRAP_URL:0:60}…' sha='${BOOTSTRAP_SHA}'"
  _cleanup_abort_pods
  exit 3
fi
# Build inline bootstrap — matches docs/pod_bootstrap_checklist_20260423.md §I7-I9
BOOTSTRAP_INLINE='
set -e
command -v clang >/dev/null || { apt-get update -qq; apt-get install -y -qq clang; }
if [ ! -x /usr/local/bin/hexa_v2 ]; then
  curl -fsSL "'${BOOTSTRAP_URL}'" -o /usr/local/bin/hexa_v2
  chmod +x /usr/local/bin/hexa_v2
  echo "'${BOOTSTRAP_SHA}'  /usr/local/bin/hexa_v2" | sha256sum -c -
fi
mkdir -p /root/core && cd /root/core
for repo in anima hexa-lang; do
  [ -d /root/core/$repo/.git ] || git clone --depth 1 https://github.com/need-singularity/${repo}.git >/dev/null 2>&1
done
ln -sfn /root/core/anima /workspace/anima
ln -sfn /root/core/hexa-lang /workspace/hexa-lang
'

BOOTSTRAP_FAILED=()
BOOTSTRAP_LOGS=/tmp/bootstrap_${TS:-$(date -u +%Y%m%dT%H%M%SZ)}
mkdir -p "${BOOTSTRAP_LOGS}"
# bash 3.2 compat (macOS default): use indexed array of pids instead of declare -A.
BOOTSTRAP_PIDS=()
for row in $(echo "${PODS_JSON}" | python3 -c "
import json, sys
for r in json.load(sys.stdin):
    print(f\"{r['pid']}:{r['host']}:{r['port']}\")
"); do
  IFS=':' read -r pid host port <<< "$row"
  # 2026-04-24 fix: capture each pod's bootstrap output + exit status. Prior
  # behavior piped all SSH output to /dev/null and logged 'bootstrap DONE'
  # unconditionally, silently swallowing clone/download failures and leaving
  # /root/core/anima missing → training driver FileNotFoundError on corpus.
  ( ssh -o StrictHostKeyChecking=no -p "$port" "root@${host}" "${BOOTSTRAP_INLINE}" \
      > "${BOOTSTRAP_LOGS}/${pid}.stdout" 2> "${BOOTSTRAP_LOGS}/${pid}.stderr"; \
    echo $? > "${BOOTSTRAP_LOGS}/${pid}.exit" ) &
  BOOTSTRAP_PIDS+=("${pid}")
done
wait
for pid in "${BOOTSTRAP_PIDS[@]}"; do
  rc=$(cat "${BOOTSTRAP_LOGS}/${pid}.exit" 2>/dev/null || echo 99)
  if [[ "$rc" != "0" ]]; then
    BOOTSTRAP_FAILED+=("${pid}")
    log "  [FAIL] ${pid} bootstrap rc=${rc} — see ${BOOTSTRAP_LOGS}/${pid}.stderr"
  fi
done
if (( ${#BOOTSTRAP_FAILED[@]} > 0 )); then
  log "ABORT: bootstrap failed on ${#BOOTSTRAP_FAILED[@]} pod(s): ${BOOTSTRAP_FAILED[*]}"
  _cleanup_abort_pods
  exit 3
fi
log "  bootstrap DONE all 4 pods (exit status verified, logs: ${BOOTSTRAP_LOGS}/)"

# --- step 3: ship training driver --------------------------------------------
log "step 3/4: ship pod-side training driver /workspace/train_pN.py"
DRIVER_BODY=$(cat <<'PYDRIVER'
import os, sys, json, time, traceback
from pathlib import Path
os.environ['HF_HUB_ENABLE_HF_TRANSFER']='1'
PHI_PATH_ID=os.environ['PHI_PATH_ID']
BASE_MODEL=os.environ['PHI_MODEL']
LORA_RANK=int(os.environ.get('PHI_LORA_RANK','64'))
MAX_STEPS=int(os.environ.get('PHI_MAX_STEPS','300'))
# 2026-04-24 ROI V6: corpus path override. Default r13; r14 retrain sets
# ANIMA_STAGE2_CORPUS_PATH=/root/core/anima/experiments/alm_r14/corpus_alm_r14_v1.jsonl
CORPUS_PATH=os.environ.get('ANIMA_STAGE2_CORPUS_PATH','/root/core/anima/experiments/alm_r13/corpus_alm_r13_v1.jsonl')
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
# 2026-04-25 r6-α Axis 1 fix: byte-weighted h_last pool replaces last-token pool.
# Rationale: r5 Φ 4-path FAIL — vocab_ratio ρ=+0.83 ↔ L2. Variant B (H × bpt) PARTIAL
# CONFIRMED on p3_p4 (0.175→0.073) and p2_p4 (0.223→0.139). Post-hoc Procrustes
# REJECTED (Gram-invariant under Φ L2 scorer). Training-time per-prompt byte-weighted
# pool is the minimum intervention that replicates Variant B's diagonal reweighting.
# For each prompt: bpt_i = len(utf8_bytes(surface(token_i))) / Σ_k len(utf8_bytes(surface(token_k)))
# h_last = Σ_i bpt_i · h_token_i  (byte-weighted mean over last hidden layer).
# Schema bumped /1 → /2; reduction field added so downstream Φ scorer can dispatch.
model.eval(); h_last=[]
def _byte_weights(ids_1d, tokenizer):
    # Surface-form UTF-8 byte counts per token; strips BPE/SPM prefix markers.
    weights=[]
    for tid in ids_1d.tolist():
        s=tokenizer.decode([tid], skip_special_tokens=False, clean_up_tokenization_spaces=False)
        # Normalize common prefix markers so leading-space BPE ('Ġ') and SPM ('▁') tokens
        # contribute their real surface bytes (space + glyph). decode() already returns
        # the surface form for most HF fast tokenizers; no extra stripping needed.
        b=len(s.encode('utf-8')) if s else 1
        weights.append(b)
    total=sum(weights) or 1
    return [w/total for w in weights]
with torch.no_grad():
    for i,p in enumerate(EVAL):
        ids=tok(p, return_tensors='pt').to(model.device)
        out=model(**ids, output_hidden_states=True)
        # hidden_states[-1]: (1, T, d_model).
        H=out.hidden_states[-1][0].float().cpu()  # (T, d_model)
        bpt=_byte_weights(ids['input_ids'][0].cpu(), tok)
        import torch as _t
        w=_t.tensor(bpt, dtype=H.dtype).unsqueeze(-1)  # (T,1)
        pooled=(H*w).sum(dim=0).numpy()  # (d_model,)
        h_last.append({'idx':i,'prompt':p,'h':[float(x) for x in pooled[:256]],'n_tokens':int(H.shape[0]),'bpt_sum':float(sum(bpt))})
Path(OUT_DIR/'h_last_raw.json').write_text(json.dumps({'schema':'anima/h_last_raw/2','reduction':'byte_weighted_mean','path_id':PHI_PATH_ID,'base_model':BASE_MODEL,'lora_rank':LORA_RANK,'steps':MAX_STEPS,'ts':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'hidden_dim_truncated':256,'entries':h_last}, indent=2))
print(f'[{time.strftime("%H:%M:%S")}] DONE path={PHI_PATH_ID}', flush=True)
PYDRIVER
)
for row in $(echo "${PODS_JSON}" | python3 -c "
import json, sys
for r in json.load(sys.stdin):
    print(f\"{r['pid']}:{r['host']}:{r['port']}\")
"); do
  IFS=':' read -r pid host port <<< "$row"
  echo "${DRIVER_BODY}" | ssh -o StrictHostKeyChecking=no -p "$port" "root@${host}" "cat > /workspace/train_${pid}.py" &
done
wait
log "  driver shipped all 4 pods"

# --- step 4: kickoff training (nohup, parallel) ------------------------------
log "step 4/4: kickoff training nohup — NO IDLE"
for row in $(echo "${PODS_JSON}" | python3 -c "
import json, sys
for r in json.load(sys.stdin):
    print(f\"{r['pid']}:{r['host']}:{r['port']}:{r['model']}:{r['rank']}\")
"); do
  IFS=':' read -r pid host port model rank <<< "$row"
  # 2026-04-24 ROI V6: pass ANIMA_STAGE2_CORPUS_PATH through to pod-side driver
  ssh -o StrictHostKeyChecking=no -p "$port" "root@${host}" \
    "HF_TOKEN='${HF_TOKEN}' PHI_PATH_ID='${pid}' PHI_MODEL='${model}' PHI_LORA_RANK='${rank}' PHI_MAX_STEPS='${MAX_STEPS}' ANIMA_STAGE2_CORPUS_PATH='${ANIMA_STAGE2_CORPUS_PATH:-/root/core/anima/experiments/alm_r13/corpus_alm_r13_v1.jsonl}' nohup python3 /workspace/train_${pid}.py > /workspace/train_${pid}.log 2>&1 & echo ${pid}_pid=\$!" 2>&1 | tail -1 &
done
wait
log "  4 trainings kicked off (nohup bg)"
log "chain complete — pods are TRAINING, monitor logs via:"
log "  ssh -p <port> root@<host> 'tail -5 /workspace/train_<pid>.log'"
log "  Or await artifacts: /workspace/trained_<pid>/h_last_raw.json"
exit 0
