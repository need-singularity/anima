# ALM r7 single-path retrain helper — 설계 문서 (loss-free design)

> **생성일**: 2026-04-25 (loss-free, 0-cost design only)
> **상태**: 설계 / 승인 대기 — 사용자 결정 (`r7 결정: D-qwen14|D-mistral|C`) 후 별 commit 으로 구현
> **부모 spec**: `docs/alm_r7_launch_spec_20260425.md` (commit `0acff23b`) §10
> **POLICY R4**: `.roadmap` 미수정. 기존 도구 미수정. 본 문서는 신규 helper `tool/h100_r7_single_path_retrain.bash` 의 **설계만** 정의 — 실제 bash 파일 생성은 사용자 승인 후 별 commit.
> **H-MINPATH**: spec §10 에서 식별된 tool-gap (1-pod 1-path **학습 + 추출**) 을 채우는 최소 helper.
> **H-LOSS-FREE**: 본 commit 은 docs + proposal 만. pod / GPU / API 0.

---

## 1. 목적 (Purpose)

`docs/alm_r7_launch_spec_20260425.md` (commit `0acff23b`) §10 에서 r7 Option C 또는 Option D 채택 시 **partial retrain helper 부재** 가 R6 risk 로 등록되었다. r7 의 minimum-cost 절차는 다음과 같다:

- **Option C**: p2 만 재학습 (Qwen2.5-7B → Llama-3.1-8B revert). p1/p3/p4 는 r6 자산 재사용.
- **Option D-qwen14** (권장): p4 만 재학습 (Gemma-3-12B → Qwen2.5-14B). p1/p2/p3 는 r6 자산 재사용.
- **Option D-mistral**: p4 만 재학습 (Gemma-3-12B → Mistral-7B-v0.3). p1/p2/p3 는 r6 자산 재사용.
- **Option E**: 재학습 0 (코드 변경만). helper 불요.

본 helper 는 Option C/D 분기에서 **단일 path / 단일 pod LoRA 재학습 + h_last 추출 + adapter pull + Φ gate r7 invocation** 을 한 번의 bash 호출로 수행한다.

---

## 2. Tool-gap 분석 (왜 신규 helper 가 필요한가)

### 2.1 기존 도구 매핑

| 도구 | 범위 | 학습 여부 | 1-path 단일 모드 |
|---|:---:|:---:|:---:|
| `tool/h100_stage2_unified_launch.bash` | 4-pod parallel launch wrapper | yes (학습 driver chain 호출) | **NO** (4-path 강제) |
| `tool/h100_stage2_post_launch_chain.bash` | 4-pod parallel **LoRA 학습** + h_last extract | **YES (학습)** | **NO** (4-path 강제) |
| `tool/h_last_raw_regen_r5.bash` | 1-pod sequential **forward-pass only** | **NO** (PeftModel.from_pretrained, 학습 X) | NO (4-path serial) |
| `tool/h100_stage2_adapter_pull.bash` | 학습 완료된 adapter pull 자동화 | NO | YES (path-agnostic) |

### 2.2 Gap 정의

r7 Option C/D 가 필요로 하는 **단일 도구**:

> 1-pod / 1-path / **LoRA 학습 (300 step)** + byte-weighted h_last 추출 + adapter pull + pod kill + Φ gate r7 호출

기존 도구의 두 패턴을 합성:
- **학습 driver** (heredoc Python): `tool/h100_stage2_post_launch_chain.bash` L217–297 (PYDRIVER 블록)
- **1-pod 순차 + scp + pod kill** 패턴: `tool/h_last_raw_regen_r5.bash` 전체 chain (단, 학습이 아닌 forward-pass)

helper 는 위 두 패턴의 **교차 집합**을 구현한다 — 학습 driver 를 차용하되 1-pod 1-path 로 단일화.

---

## 3. Interface 명세

### 3.1 CLI 호출 양식

```bash
bash tool/h100_r7_single_path_retrain.bash \
  --path p4 \
  --base-model Qwen/Qwen2.5-14B \
  --lora-rank 96 \
  --max-steps 300 \
  --corpus-path /root/core/anima/experiments/alm_r14/corpus_alm_r14_v1.jsonl \
  --tag r7_optD_qwen14 \
  --apply --yes-i-mean-it
```

### 3.2 인자 목록

| 인자 | 타입 | 기본값 | 설명 |
|---|:---:|---|---|
| `--path` | enum {p1,p2,p3,p4} | (필수) | 재학습 대상 path id |
| `--base-model` | str | (필수) | HF 모델 식별자 (예: `Qwen/Qwen2.5-14B`) |
| `--lora-rank` | int | `config/lora_rank_per_path.json` 의 path entry | LoRA rank (Option D-qwen14 기본 96) |
| `--max-steps` | int | `300` | 학습 step 수 (r6 와 parity) |
| `--corpus-path` | str | `/root/core/anima/experiments/alm_r14/corpus_alm_r14_v1.jsonl` | pod-side corpus 절대 경로 |
| `--tag` | str | (필수) | 출력 파일 suffix (예: `r7_optD_qwen14`) |
| `--apply` | flag | (off=dry-run) | 실제 launch (없으면 dry-run) |
| `--yes-i-mean-it` | flag | (필수 for --apply) | H100 stop-gate 명시 승인 |
| `--gpu-count` | int | `4` | per-pod GPU 수 (14B → 4 권장, 7-8B → 2 가능) |
| `--bid-per-gpu` | float | `3.50` | $/hr per GPU (`tool/h100_stage2_unified_launch.bash` 와 동일 정책) |
| `--phi-gate` | flag | on (default) | 종료 후 `tool/phi_4path_gate.hexa --tag <tag>` 자동 호출. `--no-phi-gate` 로 disable. |
| `--qlora-on-oom` | flag | off | OOM 발생 시 QLoRA 4-bit 자동 재시도 (Option D-qwen14 R2 mitigation) |
| `--fallback-model` | str | (없음) | OOM/load 실패 시 대체 base model (예: D-qwen14 → `mistralai/Mistral-7B-v0.3`) |

### 3.3 환경변수 (override)

| 변수 | 의미 |
|---|---|
| `ANIMA_H100_BID_USD` | 절대 bid override (per-pod total) |
| `ANIMA_H100_BID_USD_PER_GPU` | per-GPU bid override |
| `ANIMA_R7_SSH_MAX_SEC` | SSH 대기 timeout (default 600s) |
| `HF_TOKEN` | (HF token 파일 fallback — `~/.cache/huggingface/token`) |
| `ANIMA_R7_KEEP_POD` | `1` 이면 종료 후 pod kill 생략 (debug 용) |

### 3.4 출력 산출물

| 경로 | 내용 |
|---|---|
| `state/trained_adapters_r7/<path>/final/` | 신규 LoRA adapter (`adapter_config.json`, `adapter_model.safetensors`) |
| `state/h_last_raw_<path>_TRAINED_r7.json` | byte-weighted h_last (schema `anima/h_last_raw/2`, 16 prompt × 256 dim) |
| `state/h_last_raw_p{1..4}_TRAINED_r7.json` | r6 → r7 tag 동기화 (재학습 안 한 path 는 **copy** 또는 **symlink** of `_r6.json`) |
| `state/h100_r7_single_path_retrain_result.json` | 실행 메타 (pod_id, ssh, cost, wall, gate_verdict) |
| `state/phi_4path_gate_last_verdict.json` | `--phi-gate` 활성 시 r7 tag 의 verdict |
| `/tmp/h100_r7_single_path_retrain_<TS>.log` | 풀 로그 |

### 3.5 Exit codes

| code | 의미 |
|:---:|---|
| 0 | 학습 + h_last + adapter pull + (optional) Φ gate 모두 성공 |
| 1 | 사전 검증 (pre-flight) 실패 / 인자 오류 |
| 2 | pod launch 실패 / SSH timeout |
| 3 | bootstrap (apt/pip/clone) 실패 |
| 4 | 학습 driver 실패 (OOM 포함, fallback 시도 후에도 실패 시) |
| 5 | adapter / h_last scp 실패 / schema 검증 실패 |
| 6 | Φ gate r7 호출 실패 (학습은 성공) — pod 는 이미 kill, 운영자가 수동 재실행 가능 |

### 3.6 Dry-run 동작

`--apply` 없이 호출 시 다음을 출력하고 0 으로 종료:
- pre-flight 결과 (0–8)
- 계획된 `runpodctl create pod` command line
- 계획된 학습 driver env vars (PHI_PATH_ID, PHI_MODEL, PHI_LORA_RANK, ...)
- 비용 / wall 견적
- 후속 `--apply --yes-i-mean-it` invocation 양식

---

## 4. Pseudo-code outline (steps 1–7)

```
# Step 0: argv parse + dry-run check
parse_args($@)
[[ MODE=dry-run ]] && emit_plan + exit 0

# Step 1: pre-flight (loss-free, 0-cost) — §6 reuse strategy
preflight_0_runway       # spendLimit ≥ 1-pod $14/hr
preflight_1_substrates   # config/phi_4path_substrates.json 의 <path> entry 존재
preflight_2_lora_rank    # config/lora_rank_per_path.json 의 <path> entry 존재
preflight_3_manifest     # state/h100_launch_manifest.json stage2 verdict=READY
preflight_4_runpodctl    # auth OK
preflight_5_hf           # auth OK
preflight_6_pods_lock    # config/h100_pods.json writable
preflight_7_git_sync     # local HEAD == origin/main (pods shallow-clone main)
preflight_8_corpus_sha   # experiments/alm_r14/corpus_alm_r14_v1.jsonl sha lock 검증
# 추가 (r7-specific):
preflight_9_r6_assets    # state/h_last_raw_p{1..4}_TRAINED_r6.json + state/trained_adapters_r6/p{1..4}/final/ 존재
preflight_10_archive     # state/trained_adapters_r6/ archive (없으면 _TRAINED 의 r6 hard-copy 생성)

# Step 2: pod launch (1× H100 SXM5, 4 GPUs, secureCloud, bid $14/hr default)
LAUNCH_OUT = runpodctl create pod \
  --gpuType "NVIDIA H100 80GB HBM3" --gpuCount ${GPU_COUNT_PER_POD} \
  --secureCloud \
  --name anima-r7-${PATH_ID}-<model-tag>-<TS> \
  --imageName runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04 \
  --cost ${BID_USD_PER_HR} --containerDiskSize 80 --volumeSize 200 --volumePath /workspace \
  --startSSH --ports "22/tcp" \
  --env ANIMA_STAGE=2_single_path_retrain \
  --env ANIMA_ROADMAP_ENTRY=10 \
  --env HEXA_STRICT=1 \
  --env IDLE_KILL_MIN=5 \
  --env PHI_PATH_ID=${PATH_ID} \
  --env PHI_MODEL=${BASE_MODEL} \
  --env PHI_LORA_RANK=${LORA_RANK} \
  --env ANIMA_TAG=${TAG}
POD_ID = parse(LAUNCH_OUT)
trap '_kill_pod' ERR

# Step 3: pods_sync + auto_kill arm + SSH wait
bash tool/h100_pods_sync.bash
hexa run tool/h100_auto_kill.hexa --apply
wait_ssh(POD_ID, max=600s)

# Step 4: bootstrap (parallel of regen_r5: apt clang + hexa binary + git clone + pip)
ssh_exec(BOOTSTRAP_INLINE)   # 차용: post_launch_chain BOOTSTRAP_INLINE (L164-178)
ssh_exec(PIP_INSTALL)        # 차용: regen_r5 BOOTSTRAP_SH (L188-197)
# verify: torch / transformers / peft import OK + nvidia-smi GPU ≥ 4

# Step 5: ship + run training driver
DRIVER_BODY = <차용: post_launch_chain PYDRIVER (L217-297) — 단, multi-GPU 활용을 위해
              accelerate launch 옵션 또는 device_map='auto' 그대로 유지 (현 driver 는 그대로 4-GPU 사용)>
ssh_exec("cat > /workspace/train_${PATH_ID}.py" <<< DRIVER_BODY)

# 학습 + forward-pass + h_last_raw.json 작성 (driver 가 한 process 안에서 둘 다 처리)
ssh_exec(
  "HF_TOKEN='${HF_TOKEN}' \
   PHI_PATH_ID='${PATH_ID}' PHI_MODEL='${BASE_MODEL}' \
   PHI_LORA_RANK='${LORA_RANK}' PHI_MAX_STEPS='${MAX_STEPS}' \
   ANIMA_STAGE2_CORPUS_PATH='${CORPUS_PATH}' \
   nohup python3 /workspace/train_${PATH_ID}.py > /workspace/train_${PATH_ID}.log 2>&1 &
   echo $!"
)
# 동기 대기 (1-pod, 1-path 이므로 background nohup 후 polling 으로 종료 감지)
wait_for_artifact("/workspace/trained_${PATH_ID}/h_last_raw.json", interval=60s, max=8h)
# OOM 감지 (학습 fail) 시:
if --qlora-on-oom and oom_detected:
    ship modified driver with load_in_4bit=True
    rerun
elif --fallback-model and load/oom_failed:
    swap PHI_MODEL=fallback, rerun

# Step 6: pull artifacts + cleanup pod
scp /workspace/trained_${PATH_ID}/final/ → state/trained_adapters_r7/${PATH_ID}/final/
scp /workspace/trained_${PATH_ID}/h_last_raw.json → state/h_last_raw_${PATH_ID}_TRAINED_r7.json
validate_schema_2(file)
# 다른 3 path 의 r6 h_last 를 r7 tag 로 동기화 (Φ gate 가 일관된 tag 로 6 pair 재계산하도록)
for other_pid in {p1,p2,p3,p4} - {PATH_ID}:
    cp state/h_last_raw_${other_pid}_TRAINED_r6.json state/h_last_raw_${other_pid}_TRAINED_r7.json
    # 또는 symlink (jsonl reader 의 동작 보장 시 권장)
trap - ERR
_kill_pod($POD_ID)
bash tool/h100_pods_sync.bash

# Step 7: Φ gate r7 invocation (optional, default on)
if --phi-gate:
    hexa run tool/phi_4path_gate.hexa --tag ${TAG}
    GATE_VERDICT = state/phi_4path_gate_last_verdict.json
    write state/h100_r7_single_path_retrain_result.json {
      "pod_id", "wall_sec", "cost_estimate", "gate_verdict": GATE_VERDICT, ...
    }
exit 0
```

### 4.1 차용 매핑 (어느 줄을 어디서 가져오는가)

| Step | 차용 source | 차용 lines |
|---|---|---|
| Step 1 (pre-flight 0–7) | `tool/h100_stage2_unified_launch.bash` | L107–306 (그대로 import, single-path 도 동일 invariant) |
| Step 1 (pre-flight 9–10) | (신규) | r7-specific r6 archive 검증 |
| Step 2 (runpodctl create) | `tool/h_last_raw_regen_r5.bash` L117–138 + `tool/h100_stage2_unified_launch.bash` L372–401 | bid scaling + secureCloud lock |
| Step 3 (pods_sync, auto_kill, SSH wait) | `tool/h100_stage2_unified_launch.bash` L443–446 + `tool/h_last_raw_regen_r5.bash` L172–184 | |
| Step 4 (bootstrap) | `tool/h100_stage2_post_launch_chain.bash` L141–213 (BOOTSTRAP_INLINE) + `tool/h_last_raw_regen_r5.bash` L186–199 (PIP_INSTALL) | |
| Step 5 (학습 driver) | `tool/h100_stage2_post_launch_chain.bash` L217–297 (PYDRIVER) — **그대로 차용** | byte-weighted pool, schema /2 |
| Step 5 (kickoff) | `tool/h100_stage2_post_launch_chain.bash` L310–325 의 단일 path 변형 | |
| Step 6 (adapter scp + h_last scp) | `tool/h_last_raw_regen_r5.bash` L319–391 의 단일 path 변형 | schema /2 검증 |
| Step 6 (pod kill) | `tool/h_last_raw_regen_r5.bash` L139–145 (`_kill_pod`) | |
| Step 7 (Φ gate) | `tool/h_last_raw_regen_r5.bash` L399–416 | tag 만 r7 로 변경 |

---

## 5. Pod size + cost 견적 per option

### 5.1 GPU 메모리 budget (bf16 LoRA, gradient checkpoint on)

| Option | base size | bf16 weights | activation (bsz=1, ga=4, ctx=2048) | LoRA rank | 합계 (1 GPU) | 권장 GPU |
|:---:|:---:|---:|---:|:---:|---:|:---:|
| C (p2) | Llama-3.1-8B | ~16GB | ~6GB | 64 | ~24GB | 1× H100 80GB OK, **2× 권장 for safety** |
| D-mistral (p4) | Mistral-7B-v0.3 | ~14GB | ~6GB | 96 | ~22GB | 1× OK, **2× 권장** |
| D-qwen14 (p4) | Qwen2.5-14B | ~28GB | ~10GB | 96 | ~42GB | **4× H100 80GB 권장** (load split + DDP) |

→ helper 의 `--gpu-count` 기본값은 **4** (D-qwen14 안전 baseline). C/D-mistral 호출 시 `--gpu-count 2` 명시 권장 (비용 절감).

### 5.2 Wall + cost 견적 (300 step, r6 baseline 기준)

| Option | model | GPUs | per-step (sec) | 학습 wall | forward-pass wall | total wall | bid (per-pod $/hr) | cost |
|:---:|---|:---:|---:|---:|---:|---:|---:|---:|
| C | Llama-3.1-8B | 2 | ~3.5 | ~18min | ~3min | ~30–60min (cold-start 포함) | $7 | **$3–5** |
| D-mistral | Mistral-7B-v0.3 | 2 | ~3.5 | ~18min | ~3min | ~60–90min | $7 | **$5–8** |
| D-qwen14 | Qwen2.5-14B | 4 | ~5.0 | ~25min | ~5min | ~90–120min | $14 | **$8–12** |

(spec §2.1 표와 일치)

---

## 6. Pre-flight 재사용 전략

### 6.1 `tool/h100_stage2_unified_launch.bash` 의 pre-flight 0–7 그대로 적용 가능

| # | 항목 | 1-path 모드에서 추가 변경 |
|:---:|---|---|
| 0 | runway / spendLimit / balance | per-pod cost 가 $7–14 이므로 spendLimit=$80 기준 항상 통과 |
| 1 | substrates config | 변경된 path entry (`p<X>.model`) 가 실제 reflect 됐는지 추가 verify |
| 2 | lora rank | path-specific entry 만 read |
| 3 | manifest stage2 | 변경 불요 (READY) |
| 4 | runpodctl auth | 변경 불요 |
| 5 | hf auth | 변경 불요 |
| 6 | pod registry | 변경 불요 |
| 7 | git sync | 변경 불요 — pod 가 origin/main shallow-clone 하므로 본 spec + helper commit + push 후 통과 |

### 6.2 신규 pre-flight 8–10 (r7-specific)

| # | 항목 | 검증 내용 |
|:---:|---|---|
| 8 | corpus sha lock | `experiments/alm_r14/corpus_alm_r14_v1.jsonl` sha256 가 r6 학습 시점과 일치 (Cleanroom invariance) |
| 9 | r6 assets present | `state/h_last_raw_p{1..4}_TRAINED_r6.json` 4 개 + `state/trained_adapters_r6/p{1..4}/final/` 모두 존재. 부재 시 ABORT (Φ gate r7 호출 시점에 다른 path h_last 가 없어 6 pair 재계산 불가) |
| 10 | r6 → r7 archive sweep | `state/trained_adapters_r6/<path>/final/` (재학습 대상 path) 가 archive 되어 있어야 함 (없으면 `state/trained_adapters/<path>/final/` 에서 hard-copy 생성, helper 가 자동 수행) |

### 6.3 helper 가 호출하지 않는 외부 도구

- `tool/h100_stage2_adapter_pull.bash` — 4-pod parallel daemon 이므로 1-pod 1-path 에서는 inline scp 가 더 간결 (regen_r5 패턴 차용)
- `tool/h100_cost_tracker.bash` — 1-pod $14/hr 단순 케이스이므로 helper 자체 견적으로 충분 (선택적 호출)

---

## 7. Φ gate r7 invocation 전략

### 7.1 6 pair 재계산을 위한 h_last 동기화

Φ gate (`tool/phi_4path_gate.hexa`) 는 `state/h_last_raw_p{1..4}_TRAINED_<tag>.json` 4 개 모두 동일 tag 로 존재해야 6 pair (C(4,2)) 를 일관 계산한다.

helper 의 Step 6 종료 직후:
```
재학습 path = ${PATH_ID} (예: p4)
신규: state/h_last_raw_${PATH_ID}_TRAINED_r7.json (학습된 14B Qwen)
재사용: state/h_last_raw_p1_TRAINED_r6.json → state/h_last_raw_p1_TRAINED_r7.json (cp)
재사용: state/h_last_raw_p2_TRAINED_r6.json → state/h_last_raw_p2_TRAINED_r7.json (cp)
재사용: state/h_last_raw_p3_TRAINED_r6.json → state/h_last_raw_p3_TRAINED_r7.json (cp)
```

cp vs symlink 결정:
- **cp 권장** (jsonl reader 가 path 마다 schema field `tag` 를 확인할 가능성 — symlink 가 `_r6` source 를 노출하지 않도록 cp 가 안전)
- **alternative**: 메타 파일 `state/h_last_raw_r7_synthesis_manifest.json` 에 명시 ({"p1":"r6_reuse", "p2":"r6_reuse", "p3":"r6_reuse", "p4":"r7_trained"}) 추가 권장 — provenance 보존

### 7.2 Φ gate 호출

```
hexa run tool/phi_4path_gate.hexa --tag ${TAG}
```

`${TAG}` 예: `r7_optD_qwen14`. gate 는 `state/h_last_raw_p{1..4}_TRAINED_r7_optD_qwen14.json` 을 읽도록 수정 필요? — 현재 hexa 파일은 tag 가 단순 `r7` 일 가능성. **r7 결정 시점에 tag naming 통일 필요** (spec §5.2 의 `r7_optD_qwen14` 와 hexa 의 tag arg 형식 정합 검증을 helper 의 pre-flight 11 로 추가 권장).

---

## 8. Risk register

| ID | Risk | 완화 |
|:---:|---|---|
| R1 | **OOM** Qwen2.5-14B / 4× H100 80GB / bf16 LoRA r=96 | (a) `--qlora-on-oom` 자동 4-bit fallback (~16GB weight). (b) `--fallback-model mistralai/Mistral-7B-v0.3`. (c) rank 96 → 64 다운. driver 가 OOM exception 잡아 재시도. |
| R2 | **adapter pull network burst** — 14B rank=96 LoRA = ~2.1GB safetensors. scp 단일 connection 으로 ~5–10min 소요 가능 | scp 의 `-c aes128-gcm@openssh.com` 빠른 cipher 명시. timeout 1800s 적용. 실패 시 재시도 1회. |
| R3 | **다른 3 path h_last r6 → r7 동기화 실수** (hard-link symlink 이슈) | helper 가 cp 수행 후 sha256 검증 + manifest jsonl 작성. Φ gate 직전 4 파일 존재 + non-empty 검증. |
| R4 | **Φ gate hexa 가 tag 길이 / 글자 제약 예 `r7_optD_qwen14` 내 underscore handling 문제** | helper 의 pre-flight 11: `hexa run tool/phi_4path_gate.hexa --tag <TAG> --dry-run` 으로 사전 검증. 실패 시 ABORT before pod launch. |
| R5 | **idle pod 잔존** — 학습 완료 후 helper 가 죽어도 pod live 위험 (cost burn) | (a) `IDLE_KILL_MIN=5` env (auto-kill). (b) trap ERR + EXIT 둘 다 `_kill_pod` 호출. (c) `tool/h100_auto_kill.hexa` arm 단계 step 3 에서 수행. |
| R6 | **bootstrap fail** (apt repo 변경, hexa binary URL signing rotation) | post_launch_chain 의 BOOTSTRAP_INLINE 변경 사항을 helper 가 동기 import (sed/grep 비용 0). bootstrap fail 시 자동 cleanup + exit 3. |
| R7 | **base model HF accessibility 변경** (gating, 토큰 만료) | helper 의 pre-flight 1 에서 `unified_launch.bash` 의 `_hf_accessible` + `_resolve_model_with_fallback` import — primary unreachable 시 fallback_chain 자동 사용. |
| R8 | **r6 archive 누락** (`state/trained_adapters_r6/` 부재) | pre-flight 10 에서 자동 hard-copy 생성 (state/trained_adapters/p<X>/final/ → state/trained_adapters_r6/p<X>/final/). copy 실패 시 ABORT. |
| R9 | **multi-GPU split** Qwen2.5-14B / `device_map='auto'` 가 4 GPU 에 비균등 분산 → DDP 학습 시 sync 비용 증가 | 14B 의 경우 `device_map={'transformer': 0, 'lm_head': 1}` 명시 또는 단일 GPU full-load + LoRA only. 첫 시도는 default `auto` 로 (r12 시점 검증 패턴), 실패 시 `--single-gpu-load` flag 추가 (제 2차 commit). |
| R10 | **wall timeout** 14B 가 예상 120min 초과 시 | helper 의 wait_for_artifact 의 max 를 8h (480min) 로 설정 (cost cap = $14 × 8 = $112 — sane upper). 그 이전에 pod 자체 idle-kill 가 5min idle 감지 → 자동 종료. |

---

## 9. 구현 trigger 조건

### 9.1 본 helper 가 **실제 bash 파일로 구현되는** 시점

다음 사용자 입력 중 **하나** 가 별 turn 에서 도착하면 별 commit 으로 구현:

| 입력 | 동작 |
|---|---|
| `r7 결정: D-qwen14` | helper 구현 + `config/phi_4path_substrates.json` p4 entry 갱신 commit |
| `r7 결정: D-mistral` | helper 구현 + `config/phi_4path_substrates.json` p4 entry 갱신 (Mistral-7B-v0.3) commit |
| `r7 결정: C` | helper 구현 + `config/phi_4path_substrates.json` p2 entry revert commit |
| `r7 결정: E` | helper **불요** — `tool/phi_4path_gate.hexa` 에 `--exclude p4` flag 만 추가 commit |

### 9.2 본 commit 의 anti-scope (재확인)

- 본 commit 은 **docs + proposal 만**. bash 파일 0.
- pod / GPU / API 호출 0.
- `tool/h100_stage2_*.bash` / `tool/h_last_raw_regen_r5.bash` 미수정.
- `.roadmap` 미수정 (POLICY R4).
- 사이블링 에이전트 (Phase β-A endpoint config emit) 와 path overlap 0.

---

## 10. 다음 단계 (out-of-scope of this design doc)

1. (사용자) `r7 결정: <opt>` 를 별 turn 으로 입력 → 본 design 의 §9.1 에 따라 helper 구현 commit.
2. 구현 commit 에서:
   - `tool/h100_r7_single_path_retrain.bash` 생성 (본 design §3–§7 그대로 따름)
   - `config/phi_4path_substrates.json` 의 path entry 갱신 (Option C/D 별)
   - dry-run 실행 → 운영자 승인 → `--apply --yes-i-mean-it`
3. 결과 산출:
   - `state/phi_4path_gate_last_verdict.json` r7 verdict
   - `docs/alm_r7_closure_<TS>.md` (r7 PASS/FAIL 클로저)

---

## 11. 참조

- 부모 spec: `docs/alm_r7_launch_spec_20260425.md` (commit `0acff23b`) §10 (Phase 4 helper gap)
- 차용 source 도구:
  - `tool/h100_stage2_post_launch_chain.bash` (학습 driver L217–297)
  - `tool/h_last_raw_regen_r5.bash` (1-pod sequential pattern)
  - `tool/h100_stage2_unified_launch.bash` (pre-flight 0–7)
- r6-α closure: `1e064038`
- H-axis3 진단: `44783b28`
- POLICY R4: `.roadmap` lock
- HEXA-FIRST: 본 helper 의 driver 는 heredoc 에 inline (committed .py 0 — `.gitignore '**/*.py'` 준수)

---

## 12. Anti-scope (본 design doc 이 하지 않는 것)

- bash 파일 `tool/h100_r7_single_path_retrain.bash` 생성 — 0 (사용자 결정 후 별 commit)
- `config/phi_4path_substrates.json` 수정 — 0
- pod 런치 — 0
- GPU / API 호출 — 0
- 기존 도구 (post_launch_chain / regen_r5 / unified_launch) 수정 — 0
- `.roadmap` 수정 — 0 (POLICY R4)
- r6 artifacts 변경 — 0 (rollback 보호)
- 사이블링 에이전트 (Phase β-A endpoint config emit) overlap — 0
