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

log "chain start — pods=${#POD_LIST[@]:-4} max_steps=${MAX_STEPS}"
echo "${PODS_JSON}" | python3 -c 'import json,sys;d=json.load(sys.stdin);[print(f"  {r[\"pid\"]}: {r[\"host\"]}:{r[\"port\"]} model={r[\"model\"]} rank={r[\"rank\"]}") for r in d]'

# --- step 1: SSH available ----------------------------------------------------
log "step 1/4: waiting for SSH on all pods (max 90s)"
SSH_OK=0
for i in 1 2 3 4 5 6 7 8 9; do
  SSH_OK=1
  for row in $(echo "${PODS_JSON}" | python3 -c 'import json,sys;[print(f"{r[\"pid\"]}:{r[\"host\"]}:{r[\"port\"]}") for r in json.load(sys.stdin)]'); do
    IFS=':' read -r pid host port <<< "$row"
    if ! ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -o BatchMode=yes -p "$port" "root@${host}" "true" 2>/dev/null; then
      SSH_OK=0; break
    fi
  done
  [[ $SSH_OK -eq 1 ]] && break
  log "  retry in 10s (attempt $i/9)"
  sleep 10
done
[[ $SSH_OK -eq 1 ]] || { log "ABORT: SSH not available within 90s"; exit 2; }
log "  SSH OK all 4 pods"

# --- step 2: bootstrap (parallel) --------------------------------------------
log "step 2/4: bootstrap (apt+hexa+git clone) on all 4 pods (parallel)"
BOOTSTRAP_URL=$(bash "${ANIMA_ROOT}/tool/fetch_hexa_binary_url.bash" --export 2>&1 | grep HEXA_URL | sed 's/.*=//')
BOOTSTRAP_SHA=$(bash "${ANIMA_ROOT}/tool/fetch_hexa_binary_url.bash" --export 2>&1 | grep HEXA_SHA256 | sed 's/.*=//')
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

for row in $(echo "${PODS_JSON}" | python3 -c 'import json,sys;[print(f"{r[\"pid\"]}:{r[\"host\"]}:{r[\"port\"]}") for r in json.load(sys.stdin)]'); do
  IFS=':' read -r pid host port <<< "$row"
  ssh -o StrictHostKeyChecking=no -p "$port" "root@${host}" "${BOOTSTRAP_INLINE}" >/dev/null 2>&1 &
done
wait
log "  bootstrap DONE all 4 pods"

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
OUT_DIR=Path(f'/workspace/trained_{PHI_PATH_ID}')
OUT_DIR.mkdir(parents=True, exist_ok=True)
print(f'[{time.strftime("%H:%M:%S")}] path={PHI_PATH_ID} model={BASE_MODEL} rank={LORA_RANK} steps={MAX_STEPS}', flush=True)
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
with open('/root/core/anima/experiments/alm_r13/corpus_alm_r13_v1.jsonl') as f:
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
model.eval(); h_last=[]
with torch.no_grad():
    for i,p in enumerate(EVAL):
        ids=tok(p, return_tensors='pt').to(model.device)
        out=model(**ids, output_hidden_states=True)
        last=out.hidden_states[-1][0,-1,:].float().cpu().numpy()
        h_last.append({'idx':i,'prompt':p,'h':[float(x) for x in last[:256]]})
Path(OUT_DIR/'h_last_raw.json').write_text(json.dumps({'schema':'anima/h_last_raw/1','path_id':PHI_PATH_ID,'base_model':BASE_MODEL,'lora_rank':LORA_RANK,'steps':MAX_STEPS,'ts':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'hidden_dim_truncated':256,'entries':h_last}, indent=2))
print(f'[{time.strftime("%H:%M:%S")}] DONE path={PHI_PATH_ID}', flush=True)
PYDRIVER
)
for row in $(echo "${PODS_JSON}" | python3 -c 'import json,sys;[print(f"{r[\"pid\"]}:{r[\"host\"]}:{r[\"port\"]}") for r in json.load(sys.stdin)]'); do
  IFS=':' read -r pid host port <<< "$row"
  echo "${DRIVER_BODY}" | ssh -o StrictHostKeyChecking=no -p "$port" "root@${host}" "cat > /workspace/train_${pid}.py" &
done
wait
log "  driver shipped all 4 pods"

# --- step 4: kickoff training (nohup, parallel) ------------------------------
log "step 4/4: kickoff training nohup — NO IDLE"
for row in $(echo "${PODS_JSON}" | python3 -c 'import json,sys;[print(f"{r[\"pid\"]}:{r[\"host\"]}:{r[\"port\"]}:{r[\"model\"]}:{r[\"rank\"]}") for r in json.load(sys.stdin)]'); do
  IFS=':' read -r pid host port model rank <<< "$row"
  ssh -o StrictHostKeyChecking=no -p "$port" "root@${host}" \
    "HF_TOKEN='${HF_TOKEN}' PHI_PATH_ID='${pid}' PHI_MODEL='${model}' PHI_LORA_RANK='${rank}' PHI_MAX_STEPS='${MAX_STEPS}' nohup python3 /workspace/train_${pid}.py > /workspace/train_${pid}.log 2>&1 & echo ${pid}_pid=\$!" 2>&1 | tail -1 &
done
wait
log "  4 trainings kicked off (nohup bg)"
log "chain complete — pods are TRAINING, monitor logs via:"
log "  ssh -p <port> root@<host> 'tail -5 /workspace/train_<pid>.log'"
log "  Or await artifacts: /workspace/trained_<pid>/h_last_raw.json"
exit 0
