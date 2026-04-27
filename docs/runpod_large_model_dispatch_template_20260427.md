# RunPod large-model dispatch template (own 4 step d evolution, 2026-04-27)

## Context

own 4 (anima/.own own 4: training-resource-root-cause-only) mandates 4-step response to GPU/runpod failures: (a) diagnosis + (b) canonical helper code fix + (c) defensive harden + (d) **canonicalization evolve** — recurring fix patterns absorbed as default mode in canonical helper.

Today's 5-attempt cycle on gemma-2-27b (v1 OOM / v2 platform-fault / v3 platform-fault / int8 bnb-CPU-only-wheel) produced 7 reusable patterns. This runbook codifies them as a **dispatch template** that any future >20B model dispatch should follow.

Future task: fold into `tool/anima_runpod_orchestrator.hexa` as `--template large-model` flag, OR new `tool/anima_large_model_dispatch_template.hexa`.

## 7 patterns (priority order, evidence-cited)

### Pattern 1 — HF_HOME=/workspace/.hf_cache mandatory for >7B models

**Why**: container disk (overlay 50-100GB) gets ENOSPC during HF cache for any model >20GB. mfs `/workspace` (685T or 287GB pod-local) handles arbitrary size.

**Evidence**: task #9 phase1 ENOSPC on container disk → phase2 fix HF_HOME=/workspace/.hf_cache → all subsequent attempts PASS the disk-space step.

**Implementation**:
```python
import os
os.environ['HF_HOME'] = '/workspace/.hf_cache'  # MUST be set BEFORE any HF imports
os.environ['HF_HUB_CACHE'] = '/workspace/.hf_cache'
```

### Pattern 2 — device_map='auto' + low_cpu_mem_usage=True for >20B models

**Why**: default `from_pretrained(torch_dtype=fp16)` allocates full fp16 weight in CPU RAM before sharding to GPU. For 27B fp16 (~54GB), this overruns container-default ~60GB host RAM → silent OOM.

**Evidence**: task #11 v1 silent SIGKILL after 360s + 59GB HF cache → v2 fix `device_map='auto' + low_cpu_mem_usage=True + memInGb=251` resolved CPU RAM bound but new failure mode emerged (platform-level termination).

**Implementation**:
```python
from transformers import AutoModelForCausalLM
model = AutoModelForCausalLM.from_pretrained(
    model_id,
    torch_dtype=torch.float16,
    device_map='auto',           # accelerate sharded load
    low_cpu_mem_usage=True,      # don't allocate full fp16 in CPU RAM
)
```

### Pattern 3 — HF_HUB_DISABLE_XET=1 + snapshot_download(max_workers=1) for repeat platform-termination

**Why**: HF xet (Rust download accelerator) uses 51-61 concurrent connections. Even when not the root cause, sequential download is more diagnostic + bypasses xet panic potential.

**Evidence**: v3 fix verified xet was NOT the cause (same termination), but pattern remains good defensive practice.

**Implementation**:
```python
import os
os.environ['HF_HUB_DISABLE_XET'] = '1'  # BEFORE HF imports
from huggingface_hub import snapshot_download
local_dir = snapshot_download(
    repo_id=model_id,
    local_dir='/workspace/snapshots/' + model_id.split('/')[-1],
    max_workers=1,                       # single-thread sequential
    resume_download=True,                # idempotent retry-safe
)
# Then: from_pretrained(local_dir, ...) NOT model_id
```

### Pattern 4 — sys.excepthook + structured summary.json fallback

**Why**: silent crashes (SIGKILL, ImportError, RuntimeError) leave wrapper.log incomplete. sys.excepthook ensures every termination produces structured JSON for diagnosis.

**Evidence**: v3 ModuleNotFoundError caught by sys.excepthook → JSON written → agent auto-recovered (pip install + relaunch). Without harness, would have been silent.

**Implementation**:
```python
import sys, json, traceback, time
def _on_exception(exc_type, exc_val, exc_tb):
    err = {
        'schema': 'anima/cmt/3',
        'backbone': MODEL_ID,
        'mode': MODE,
        'status': 'UNHANDLED_EXCEPTION',
        'exc_type': exc_type.__name__,
        'exc_val': str(exc_val),
        'traceback': ''.join(traceback.format_exception(exc_type, exc_val, exc_tb)),
        'ts': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
    }
    with open(OUTPUT_JSON, 'w') as f:
        json.dump(err, f, indent=2)
    sys.__excepthook__(exc_type, exc_val, exc_tb)
sys.excepthook = _on_exception
```

### Pattern 5 — Memory probe sentinels per checkpoint

**Why**: silent OOM/termination requires precise breakpoint identification. Per-stage memory snapshots (CPU RSS + GPU memory_allocated) allow post-hoc triangulation of failure point.

**Evidence**: v2 wrapper sentinel `__GEMMA_27B_RETRY_V2_MEM__ tag=TOKENIZER_LOADED cuda_gb=0.0 host_rss_gb=0.69` documented memory state at every checkpoint, enabling H1/H4 hypothesis discrimination.

**Implementation**:
```python
import psutil, torch
def _mem_sentinel(tag):
    rss_gb = psutil.Process().memory_info().rss / 1e9
    cuda_gb = torch.cuda.memory_allocated() / 1e9 if torch.cuda.is_available() else 0
    print(f'__MEM__ tag={tag} cuda_gb={cuda_gb:.2f} host_rss_gb={rss_gb:.2f}', flush=True)
# Call at: START / TOKENIZER_LOADED / LOAD_START / LOAD_DONE / each-10-layers
```

### Pattern 6 — Cumulative-bytes-threshold awareness (~30-40GB) for split download/load

**Why**: int8 alt path 1 evidence — 15GB sequential download PASS, 54GB attempts FAIL repeatedly. Inferred RunPod orchestrator terminates pods exceeding cumulative ~30-40GB downloaded. Solution: split into dedicated download pod + measurement pod via persistent network volume.

**Evidence**: today's 5-attempt cycle convergent threshold inference (verdict_int8.json H1 weakened analysis).

**Implementation strategy** (alt path 2):
```bash
# Stage 1: dedicated download pod (long-running OK, no measurement deadline)
runpodctl pod create --name dl-prep --gpu-id "NVIDIA H100 80GB HBM3" \
    --image runpod/pytorch:2.4.0 \
    --volume volumeId=<network-vol-id> --volume-mount-path /weights \
    --command "huggingface-cli download <model_id> --local-dir /weights/<model_id>"

# Stage 2: measurement pod attaches volume, no download burden
runpodctl pod create --name measure --gpu-id "..." \
    --volume volumeId=<network-vol-id> --volume-mount-path /weights \
    --command "python wrapper.py --local-path /weights/<model_id>"
```

### Pattern 7 — bnb GPU wheel pre-flight check before launch

**Why**: pip-installed `bitsandbytes` may be CPU-only wheel even on CUDA-capable systems. RuntimeError comes mid-load, wasting download time.

**Evidence**: alt path 1 int8 wrapper crashed AFTER 295s of successful download due to bnb 0.43.3 CPU-only wheel.

**Implementation** (pre-flight check):
```python
import torch
if QUANTIZATION_USED and not torch.cuda.is_available():
    raise RuntimeError("Pre-flight FAIL: bnb quantization requested but torch.cuda not available")
import bitsandbytes
if not bitsandbytes.cuda_setup.main.cudart_load_failed:
    raise RuntimeError("Pre-flight FAIL: bitsandbytes wheel was compiled without CUDA support")
# Only proceed to from_pretrained after pre-flight PASS
```

Alternative: use a runpod image with bnb pre-installed CUDA-aware (e.g., `nvidia/pytorch:24.x` which has bnb-cuda built-in).

## Composite template (all 7 patterns)

For any new dispatch of a model with `params_b > 20`, the wrapper MUST:
1. Set `HF_HOME` env BEFORE imports (Pattern 1)
2. Set `HF_HUB_DISABLE_XET=1` env BEFORE imports (Pattern 3)
3. Install `sys.excepthook` BEFORE any heavy operation (Pattern 4)
4. Emit `__MEM__` sentinel at every checkpoint (Pattern 5)
5. For >40B model: use 2-stage (Pattern 6) split download/load via persistent network volume
6. For quantization: pre-flight check (Pattern 7) BEFORE attempting load
7. Use `device_map='auto' + low_cpu_mem_usage=True` (Pattern 2) for fp16 load

## Followup tasks

- (high) implement `tool/anima_large_model_dispatch_template.hexa` that emits a wrapper template encoding all 7 patterns. Pre-flight selftest validates patterns against generated wrapper text.
- (high) implement `tool/anima_runpod_orchestrator.hexa --template large-model` flag that auto-applies all 7 when params_b > 20.
- (medium) implement `tool/runpod_resource_lint.hexa` that scans wrapper text for the 7 patterns, warns on absence.
- (medium) update memory `feedback_forward_auto_approval` to reference this runbook + own 4 + own 5.
- (low) cross-link from `tool/anima_runpod_orchestrator.hexa` header docstring to this file.

## raw#10 caveats

- 7 patterns are derived from N=4 attempts on a single model (gemma-2-27b); cross-validation needed on Llama-3.1-70B (after task #6 unblock) and Qwen3-72B if accessible
- Pattern 6 (cumulative-bytes-threshold) is INFERRED from int8 PASS vs fp16 FAIL data — exact threshold unconfirmed; could be ingress quota OR network throughput timeout OR specific RunPod template behavior
- Patterns are anima-specific (own 4 + own 5 scope); cross-repo propagation requires sister repo policy alignment per raw 47
- Template is currently descriptive; canonicalization into hexa tool is followup work

## Cross-references

- `state/blockers/gemma_27b_repeat_silent_platform_termination.json` — omega-blocker spec
- `state/v11_gemma_familyinternal/verdict.json` (v1) + `verdict_retry_v2.json` + `verdict_int8.json` — empirical evidence
- `anima/.own` own 4 (training-resource-root-cause-only) + own 5 (completeness-no-cap)
- `anima/.raw` raw 45 (omega-blocker-autofire) + raw 80 (sentinel-result-decoding) + raw 86 (cost-attribution)
