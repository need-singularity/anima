# ALM 14B r10 — hire_sim intrinsic training plan

**Date**: 2026-04-16
**Goal**: raise live hire_sim RAW completion from 0.5333 → 0.85+ without the client-side Path C augmentation prefix.
**Hypothesis**: if ALM learns the (augmented_prompt → compliant_response) mapping during LoRA r10, it will produce format-compliant output even when the live server sends the RAW prompt.

## Corpus

- **File**: `/Users/ghost/Dev/anima/training/deploy/hire_sim_synthetic_r10_20260416.jsonl`
- **Size**: 300 records (50 per domain × 6 domains)
- **Format**: JSONL — `{domain, difficulty, prompt, response, keywords}`
- **Synthesis**: template-based, 10 variants per 30 stratified seed tasks (Option 2; no API key available)
- **Judge acceptance**: 100% (300/300 pass deterministic hire_sim_judge)
- **Avg tokens/response**: email 136, code 108, meeting 109, doc 99, schedule 76, research 98 → total ~95K token signal
- **Diversity levers**: 10 prompt frames × 8 personas × 3–4 response templates per domain × numeric perturbation (schedule)

## Corpus conversion for LoRA

The synth file is prompt/response pairs. Convert to the ALM instruction format used by r9 (same HuggingFace `tokenizer.apply_chat_template` with Qwen2.5-Instruct chat template):

```python
# training/deploy/jsonl_to_corpus.py (one-liner, run before launching)
import json
with open("/workspace/hire_sim_r10_corpus.txt", "w") as w:
    for line in open("/workspace/hire_sim_synthetic_r10_20260416.jsonl"):
        r = json.loads(line)
        # Qwen chat format
        w.write(f"<|im_start|>user\n{r['prompt']}<|im_end|>\n")
        w.write(f"<|im_start|>assistant\n{r['response']}<|im_end|>\n\n")
```

Upload `hire_sim_synthetic_r10_20260416.jsonl` to the pod, run the convertor to produce `hire_sim_r10_corpus.txt`, then pass that file as `--corpus`.

## LoRA hyperparams (delta from r9)

r9 config: `lr=5e-6, batch=8, seq=1024, grad_accum=1, warmup=500, lora_r=32, lora_alpha=64, lora_dropout=0, steps=10000`.

r10 changes (small-corpus continued training):

| Param | r9 | r10 | Rationale |
|---|---|---|---|
| base | Qwen2.5-14B-Instruct | r9 LoRA merged | continued training on top of r9, not restart |
| corpus | corpus_large.txt (~GB) | hire_sim_r10_corpus.txt (~200KB) | 300 tasks targeted |
| steps | 10000 | **1500** | 300 records × ~5 epochs |
| lr | 5e-6 | **2e-6** | smaller; avoid catastrophic forget on base |
| batch | 8 | **4** | smaller corpus → smaller batch for more updates |
| seq | 1024 | **1024** | same |
| warmup | 500 | **100** | short run |
| lora_r | 32 | **16** | targeted task; smaller adapter to limit drift |
| lora_alpha | 64 | **32** | scale with r |
| lora_dropout | 0.0 | **0.05** | anti-overfit on small corpus |
| save_every | 2000 | **500** | allow mid-run recovery |
| eval_every | 500 | **250** | faster feedback |
| ckpt_label | production | **r10_hire_sim** | distinguish from r9 |
| loss terms | CE + holo + phi + gwt | **CE only** | task-focused; disable consciousness aux on small corpus |

## Training budget

- Steps: 1500
- Effective batch: 4 × 1024 = 4096 tokens/step
- Total tokens trained: 1500 × 4096 ≈ 6.1M tokens
- r9 measured: ~70% MFU on H100 → ~3000 tok/sec at bf16 on 14B LoRA
- ETA: 6.1M / 3000 ≈ **2000 sec = 33 min** pure compute
- With preflight + model load + ckpt save + R2 upload: **~1 hour wall-clock**
- H100 cost at $2.99/hr (RunPod H100 PCIe): **~$3**

This is an order of magnitude cheaper than the 4–6h / $12–18 original estimate because the corpus is small. If the user prefers the larger budget to add epochs, simply raise `--steps` to 4500 (3× current).

## Launch recipe

Prereq: an H100 RunPod pod with `/workspace/anima` synced to commit `166f5ee1` (ALM r9 v2.0 RC live). r9 LoRA must be present at `/workspace/ckpt_alm_14b_r9/final/` OR downloadable from `r2:anima-models/alm14b/r9/`.

### Step 1 — upload corpus

```bash
# from Mac
scp /Users/ghost/Dev/anima/training/deploy/hire_sim_synthetic_r10_20260416.jsonl \
    pod:/workspace/hire_sim_synthetic_r10_20260416.jsonl
```

### Step 2 — convert to text corpus on pod

```bash
ssh pod
python3 -c '
import json
with open("/workspace/hire_sim_r10_corpus.txt", "w") as w:
    for line in open("/workspace/hire_sim_synthetic_r10_20260416.jsonl"):
        r = json.loads(line)
        w.write(f"<|im_start|>user\n{r[chr(39)+\"prompt\"+chr(39)]}<|im_end|>\n")
        w.write(f"<|im_start|>assistant\n{r[chr(39)+\"response\"+chr(39)]}<|im_end|>\n\n")
print("corpus ready")
'
wc -l /workspace/hire_sim_r10_corpus.txt
```

### Step 3 — launch r10 training (on pod)

```bash
HEXA_BIN=hexa
CKPT_DIR=/workspace/ckpt_alm_14b_r10
rm -rf $CKPT_DIR && mkdir -p $CKPT_DIR

$HEXA_BIN run /workspace/anima/training/train_alm_14b.hexa \
    --corpus /workspace/hire_sim_r10_corpus.txt \
    --base-lora /workspace/ckpt_alm_14b_r9/final \
    --steps 1500 \
    --lr 2e-6 \
    --batch 4 \
    --seq 1024 \
    --grad-accum 1 \
    --warmup 100 \
    --lora-r 16 \
    --lora-alpha 32 \
    --lora-dropout 0.05 \
    --ckpt-dir $CKPT_DIR \
    --save-every 500 \
    --eval-every 250 \
    --model-tag alm14b \
    --round 10 \
    --ckpt-label r10_hire_sim \
    --unsloth --liger \
    2>&1 | tee $CKPT_DIR/train_r10.log
```

Note: verify `train_alm_14b.hexa` supports `--base-lora` (continued training entry point); if not, fall back to training on the merged r9 base model and pass it via `--model-path`.

### Step 4 — R2 upload after training

```bash
rclone copy $CKPT_DIR r2:anima-models/alm14b/r10/ -v --s3-no-check-bucket
```

### Step 5 — live eval

Swap the serving adapter to r10 then rerun:

```bash
# Mac side — RAW (no Path C) eval
HIRE_SIM_OUTPUT=/Users/ghost/Dev/anima/training/deploy/hire_sim_alm_r10_raw_20260416.json \
hexa /Users/ghost/Dev/anima/training/deploy/hire_sim_baseline.hexa

# Gate check: completion_rate >= 0.85 ⇒ v2.1 shipped
```

## Expected delta

Based on the Path C pattern:
- r9 RAW: 0.5333 (baseline)
- r9 + Path C augmentation: 0.8667 (+0.33)
- r10 RAW projection: **0.75–0.85** (+0.22–0.32)

Reasoning: Path C teaches the CLIENT to format the prompt; r10 teaches the MODEL to expect and produce that format. We should recover 70–90% of the Path C delta as the model internalizes the augmentation rules. Failure modes that will still hurt r10:
- Hard difficulty tasks (6 in stratified-30) remain the long tail; Path C hit 67% on hard.
- The email `respond`/`negotiate`/`termination`/`board` long-tail keywords may need real-work corpus supplement (see open question below).

If r10 lands 0.80–0.84, ship as v2.1 with `clm_gate` fallback and plan r11 with real-work corpus.
If r10 lands ≥ 0.85, ship as v2.1 GA — Path C can be retired.

## Open question

**Is 300-task synthetic enough, or do we need real work corpus supplement?**

- 300 template-based synthetics cover 30 seed tasks × 10 variants. Keyword diversity is narrow (10–13 unique keywords per domain) — the model may memorize the keyword set rather than generalize the augmentation pattern.
- To test generalization, run r10 eval on tasks 31–100 from `hire_sim_100.hexa` (unseen during training). If completion rate is within 5pp of stratified-30, the pattern generalizes. If it drops by >10pp, synthetic is not enough.
- Real-work corpus candidates:
  1. The 100 tasks in `hire_sim_100.hexa` (real human-drafted prompts; responses would need Claude-API synthesis or paid human annotation).
  2. `v3_employee_capability_path_20260416.md` earmarks `TALM-P4-1 실업무 corpus LoRA (48 H100h $144)` — plug that corpus in if available.
- Recommended sequence: launch r10 on synthetic → measure on unseen 70 tasks → if gap exists, do r11 with real corpus supplement.

## No-go triggers

- **Abort** if r10 RAW drops below 0.50 (r9 baseline). Indicates catastrophic forgetting; reduce lr to 1e-6 and retry.
- **Abort** if eval loss plateaus before step 500 with training loss still dropping — overfit; reduce epochs by cutting to 750 steps.
- **Pod safety**: apply R14 `runpod_mfs_quota` rules — no in-training R2 upload, save_every ≥ 500, rclone only after training process exits.

## Status

- [x] Corpus synthesized: 300/300 pass judge
- [x] Training plan drafted
- [ ] **Awaiting user approval to launch** (H100 pod at $3, ~1h wall clock)
- [ ] r10 LoRA merge + serve swap
- [ ] v2.1 GA eval
