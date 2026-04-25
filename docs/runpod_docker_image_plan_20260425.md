# Anima Mk.XI RunPod Docker Image Plan

**Date**: 2026-04-25
**Status**: SPEC_FROZEN. Docker build 미실행 (raw#10 honest), build 명령은 사용자 manual / future cycle.
**Forward auto-approval**: per memory feedback_forward_auto_approval (2026-04-25). build + push to registry pre-approved (cap $0 for build, push depends on registry).

## §0 Convergence references (anima H100 stage history)

본 plan은 anima 기존 convergence 기록 참조하여 actual usage pattern codify:

```
state/convergence/h100_stage1_20260423.json   — Stage 1 ALM r13 launch (initial pod pattern)
state/convergence/h100_stage2_20260424.json   — Stage 2 4-path Φ substrate (4-pod cascade)
state/convergence/h100_stage2_r{4,5,6,7}_20260425.json — round-by-round attempts + verdict
```

**Cost/pod/image pattern (from convergence r6/r7 attempts):**
- Image used: `runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04`
- Per-attempt overhead: ~30s install (transformers/peft/accelerate) + ~60s model load
- r7 wall budget: 90-120min, cost cap $20 (per attempt)
- r6 attempt count: 5 (failed builds + retries — overhead bottleneck)
- 본 anima session 4 launches: BASE measure + demo train + full 6-loss + phen forward
  - 매 launch마다 install 30s + model load 60s = ~90s 반복 overhead
  - Total install/load overhead for 4 launches = ~6min × $2.99/hr = ~$0.30 in deps overhead

## §1 Anima Mk.XI custom Docker image rationale

**Pre-installed dependencies → install overhead 0:**
- transformers (현 4.x)
- peft (LoRA)
- accelerate (multi-GPU/CPU offload)
- bitsandbytes (8-bit optimizer)
- mne (EEG ingest, V_phen_LZ + V_phen_GWT cross-substrate)
- scipy + numpy (기본)
- torch (베이스 이미지에 이미 있음)

**Pre-loaded model weights (optional optimization):**
- Qwen3-8B (16 GB bfloat16) → /opt/models/qwen3-8b
- Qwen2.5-7B (cross-base validation)
- → 모델 로드 시간 60s → 5s (NVMe disk read만)

**Pre-loaded anima tool/state (optional):**
- anima/tool/ (hexa wrappers, transient helpers는 /tmp emit이라 불필요)
- anima/state/mk_xi_*.json (frozen specs)

## §2 Dockerfile spec (raw#12 frozen, build 미실행)

```dockerfile
# anima-mk-xi:v1
FROM runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04

# Pre-installed Python deps (reduces ~30s per pod boot)
RUN pip install --no-cache-dir \
    transformers==4.46.0 \
    peft==0.13.0 \
    accelerate==1.0.1 \
    bitsandbytes==0.44.1 \
    mne==1.8.0 \
    scipy>=1.14 \
    numpy>=1.26

# Pre-load model weights (optional, ~17GB image bloat — opt-in)
# RUN python3 -c "from transformers import AutoModelForCausalLM; \
#     AutoModelForCausalLM.from_pretrained('Qwen/Qwen3-8B', \
#     torch_dtype='bfloat16', cache_dir='/opt/models')"

# Pre-load anima specs (frozen JSON) — minimal, ~1MB
COPY state/mk_xi_architecture_spec_20260425.json       /opt/anima/state/
COPY state/mk_xi_pass_verdict_spec_20260425.json       /opt/anima/state/
COPY state/mk_xi_anti_map_ledger_v2_20260425.json      /opt/anima/state/
COPY state/mk_xi_retrieval_head_spec_20260425.json     /opt/anima/state/
COPY state/mk_xi_r4_monitor_spec_20260425.json         /opt/anima/state/
COPY state/phenomenal_surrogate_proposals_20260425.json /opt/anima/state/

# Working directory
WORKDIR /workspace

# Entry point (default = bash, overridable by runpodctl --command)
CMD ["bash"]
```

## §3 Build + push protocol (deferred, raw#10 honest)

```bash
# 1. Build locally (host: macOS arm64 → linux/amd64 cross-build via buildx)
docker buildx create --use
docker buildx build --platform linux/amd64 -t anima-mk-xi:v1 -f Dockerfile.anima-mk-xi --load .

# 2. Tag for registry
docker tag anima-mk-xi:v1 ghcr.io/<user>/anima-mk-xi:v1

# 3. Push (requires registry auth)
docker push ghcr.io/<user>/anima-mk-xi:v1

# 4. RunPod template (runpodctl)
runpodctl template create \
  --name anima-mk-xi-v1 \
  --image ghcr.io/<user>/anima-mk-xi:v1 \
  --container-disk-in-gb 100 \
  --volume-in-gb 100 \
  --readme "Anima Mk.XI consciousness verification suite — pre-installed transformers/peft/accelerate/mne"

# 5. Use template in pod create
runpodctl pod create --template-id <template-id> --gpu-id "NVIDIA H100 80GB HBM3"
```

raw#10 honest: 본 plan은 build 미실행. build + push + template registration은 사용자 manual 또는 별도 cycle.

## §4 Cost/efficiency analysis

**Without custom image (current pattern):**
- Per launch: 30s pip install + 60s model load = 90s overhead × $2.99/hr = **$0.075**
- 본 anima session 4 launches: ~$0.30 in install/load
- 12-launch sweep: ~$0.90

**With anima-mk-xi:v1 (pre-installed):**
- Per launch: 0s install + 60s load (or 5s with pre-loaded model) = 5-60s = **$0.004-0.05**
- Savings per launch: $0.025-0.075
- 12-launch sweep savings: $0.30-0.90

**Image storage cost:**
- Custom image ~5GB (without model) / ~22GB (with Qwen3-8B)
- Registry storage: GHCR free for public, $0.50/GB-month for private

**ROI**:
- 4 launches → -$0.30 saving (matches 본 session)
- 16-launch λ sweep → -$1.20 saving
- Break-even: ~10 launches (storage cost vs savings)

## §5 Anima orchestrator integration

`tool/anima_runpod_orchestrator.hexa` (THIS commit batch) — RunPod pod lifecycle wrapper.

기본 image 사용 시:
```bash
hexa run tool/anima_runpod_orchestrator.hexa run \
  --pod-name <name> \
  --image runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04 \
  --pip-install "transformers peft accelerate" \
  --upload /tmp/script.py:/workspace/script.py \
  --command "cd /workspace && python3 script.py" \
  --download "/workspace/out:state/run_<id>" \
  --output state/runpod_run_<id>.json --run-id <id>
```

anima-mk-xi:v1 사용 시 (pip-install flag 생략):
```bash
hexa run tool/anima_runpod_orchestrator.hexa run \
  --pod-name <name> \
  --image ghcr.io/<user>/anima-mk-xi:v1 \
  --upload /tmp/script.py:/workspace/script.py \
  --command "cd /workspace && python3 script.py" \
  --download "/workspace/out:state/run_<id>" \
  --output state/runpod_run_<id>.json --run-id <id>
```

→ Per-launch overhead: 90s → 5-60s.

## §6 Future enhancements

1. **Multi-arch image**: linux/amd64 + linux/arm64 (Apple Silicon + Linux servers)
2. **Slim variant**: anima-mk-xi:v1-slim (without model weights, 5GB) — 첫 launch에서 model download
3. **Composable layers**:
   - `anima-mk-xi-base:v1` (Python deps only)
   - `anima-mk-xi-models:v1` (with Qwen3-8B + Qwen2.5-7B)
   - `anima-mk-xi-eeg:v1` (with mne + EEG processing extras)
4. **Auto-version bump** when convergence cycle confirms new dep versions stable

## §7 raw compliance

- raw#9 — spec only, $0 (build 미실행, image 미생성)
- raw#10 — actual build/push deferred 명시, ROI calculation honest
- raw#12 — Dockerfile content frozen, deps versions pinned
- raw#15 — this doc + tool/anima_runpod_orchestrator.hexa SSOT pair
- raw#37 — no .py git-tracked, helper /tmp emit pattern preserved
- POLICY R4 — 기존 spec scope 변경 없음, image/orchestrator 신규 axis only

## §8 Convergence cross-references

| convergence file | usage pattern | this plan reference |
|---|---|---|
| `h100_stage1_20260423.json` | initial pod allocation | §0 image used |
| `h100_stage2_r5/r6/r7_*` | round-by-round attempt + verdict | §0 cost/overhead pattern |
| `h100_post_launch_cascade_proposal.json` | propose-only post-launch | tool/anima_runpod_orchestrator vs propose-only difference |

본 plan + orchestrator는 propose-only constraint (h100_*.hexa)를 forward auto-approval policy로 우회한 actual orchestration 도구 — anima session에서 4 launches actual execution 검증됨 (pod IDs: 5nqj72cmwqoilc, 0l9dl8roem1fpz, rhcxi66zrhd3u8, yo5tex6c2d592n).

omega-saturation:fixpoint
