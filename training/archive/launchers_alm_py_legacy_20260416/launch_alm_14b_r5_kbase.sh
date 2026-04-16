#!/usr/bin/env bash
# launch_alm_14b_r5_kbase.sh — ALM 14B-class r5 LoRA (Korean base SWAP)
#                              on RunPod H100 80GB
#
# Purpose:
#   r4 (Qwen2.5-14B-Instruct) reached eval_loss 0.0289 but Korean generation
#   is incoherent (UTF-8 surrogates, Chinese leakage, English fragments).
#   Root cause: Qwen is multilingual, not Korean-pretrained. This launcher
#   pivots to a Korean-pretrained base of the same size class so the LoRA
#   has a real Korean prior to snap onto.
#
# Base swap (vs r4):
#   - base:         Qwen/Qwen2.5-14B-Instruct  ->  beomi/OPEN-SOLAR-KO-10.7B
#   - model_tag:    alm14b                     ->  alm14b_kbase
#   - round:        4                          ->  5
#   - ckpt_dir:     /workspace/ckpt_alm_14b_r4 ->  /workspace/ckpt_alm_14b_r5_kbase
#   - r2_prefix:    alm14b/r4                  ->  alm14b_kbase/r5
#
# r4 parity preserved (do NOT tweak):
#   - lora_r=64 alpha=128 dropout=0.05
#   - target_modules: q/k/v/o + gate/up/down (7 modules, Llama arch → same names)
#   - batch=1 grad_accum=8 (effective batch 8)
#   - seq=1024 lr=5e-6 warmup=500 steps=10000
#   - save_every=2000 eval_every=500
#
# Base model: beomi/OPEN-SOLAR-KO-10.7B (verified 2026-04-12)
#   - Apache-2.0 license (commercial OK)
#   - LlamaForCausalLM (peft target_modules parity with r4)
#   - 48 layers, 4096 hidden, 14336 intermediate, 32 Q / 8 KV heads, GQA
#   - vocab 46592 (Korean-expanded), max_pos 4096
#   - bf16 native on disk: ~21.7 GB for 8 safetensors shards
#   - Pretraining: Llama-2-depth-up-scaled base + continued pretrain on
#                  AI Hub + Modu (모두의 말뭉치) + KoWiki, 15 B+ tokens
#   - Same corpus domain as /workspace/anima/training/corpus_large.txt
#
# Expected steady-state:
#   - GPU memory:   ~28-32 GB / 80 GB (~48-52 GB headroom — very comfortable)
#   - Throughput:   ~22-26 step/min (0.76× params vs 14B r4 @ 18.5 step/min)
#   - ETA:          ~6.5-7.5 h for 10 000 steps
#
# Trigger condition (HUMAN-GATED, enforced by preflight below):
#   - /workspace/READY_FOR_R5_KBASE marker MUST exist.
#   - Created manually by operator after reviewing r4 generation at step
#     4000-6000. This is a DIFFERENT marker from READY_FOR_32B — the two
#     paths are independent alternatives, not sequential.
#
# Run on RunPod H100 80GB:
#   1. Confirm r4 generation is still incoherent at step 4000+ (eval loss
#      alone is not the signal — must inspect actual Korean output).
#   2. `echo "r4 generation incoherent at step NNNN" > /workspace/READY_FOR_R5_KBASE`
#   3. scp this script + train_alm_14b_r5_kbase.hexa to /workspace/
#      (train_alm_14b.py is already on the pod from r4).
#   4. (Optional) Free /workspace/hf_cache if space is tight — see note below.
#   5. bash launch_alm_14b_r5_kbase.sh
#
# DISK NOTE (/workspace is 100 GB):
#   Existing Qwen14B cache (~28 GB) MUST stay — still serving r4 eval.
#   Existing Qwen32B cache (~62 GB) CAN be deleted if we commit to the
#   base-swap path, freeing ~62 GB for the SOLAR-KO download (22 GB).
#   Trade-off: deleting Qwen32B forfeits the 32B r1 option until re-downloaded.
#     rm -rf /workspace/hf_cache/models--Qwen--Qwen2.5-32B-Instruct
#   Alternative: SOLAR-KO is only 22 GB, so if Qwen14B (28) + Qwen32B (62)
#   + SOLAR-KO (22) = 112 GB which OVERFLOWS 100 GB. At least one of
#   {Qwen32B, Qwen14B} must be evicted. Qwen14B cannot be evicted while
#   r4 is running → Qwen32B is the only option.
#
set -euo pipefail

echo "================================================"
echo "  ALM 14B r5 kbase — LoRA r=64 alpha=128, Korean"
echo "  base: beomi/OPEN-SOLAR-KO-10.7B (Apache-2.0)"
echo "================================================"

# ── Preflight: trigger marker (human-gated) ──
MARKER="/workspace/READY_FOR_R5_KBASE"
if [[ ! -f "$MARKER" ]]; then
    echo "[preflight] ✗ $MARKER missing"
    echo "[preflight]   r5_kbase is human-gated: operator must review r4 generation"
    echo "[preflight]   quality at step 4000-6000 before creating the marker."
    echo "[preflight]   To launch after review:"
    echo "[preflight]     echo 'r4 gen incoherent at step N, reason ...' > $MARKER"
    echo "[preflight]     bash launch_alm_14b_r5_kbase.sh"
    exit 1
fi
echo "[preflight] ✓ trigger marker present: $MARKER"
cat "$MARKER" 2>/dev/null || true

# ── Preflight: DO NOT conflict with READY_FOR_32B path ──
# READY_FOR_R5_KBASE and READY_FOR_32B are alternatives, not sequential. If
# both markers exist it means two different launch decisions were made. Warn
# loudly but do NOT auto-resolve — that is the operator's call.
if [[ -f "/workspace/READY_FOR_32B" ]]; then
    echo "[preflight] ⚠ BOTH /workspace/READY_FOR_R5_KBASE AND"
    echo "[preflight]   /workspace/READY_FOR_32B exist. These paths are"
    echo "[preflight]   alternatives — make sure the 32B launcher is NOT"
    echo "[preflight]   also running on this H100 (would OOM both runs)."
    echo "[preflight]   If 32B is done, delete READY_FOR_32B and re-run."
    echo "[preflight]   Continuing in 5 s — Ctrl-C to abort."
    sleep 5
fi

# ── Preflight: hexa config parse ──
HEXA_BIN="${HEXA_BIN:-/usr/local/bin/hexa}"
HEXA_CFG="/workspace/train_alm_14b_r5_kbase.hexa"
if [[ -x "$HEXA_BIN" && -f "$HEXA_CFG" ]]; then
    echo "[preflight] parse-checking $HEXA_CFG ..."
    "$HEXA_BIN" "$HEXA_CFG" > /workspace/train_alm_14b_r5_kbase.plan.log 2>&1 || {
        echo "[preflight] ✗ train_alm_14b_r5_kbase.hexa failed to parse"
        cat /workspace/train_alm_14b_r5_kbase.plan.log
        exit 1
    }
    echo "[preflight] ✓ hexa config OK (see /workspace/train_alm_14b_r5_kbase.plan.log)"
else
    echo "[preflight] ⚠ hexa binary or config missing — continuing without dry-run"
    echo "[preflight]   (HEXA_BIN=$HEXA_BIN  HEXA_CFG=$HEXA_CFG)"
fi

# ── Preflight: GPU / corpus / disk / HF token ──
echo "[preflight] checking GPU..."
nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv,noheader

echo "[preflight] checking corpus..."
CORPUS="/workspace/anima/training/corpus_large.txt"
if [[ ! -f "$CORPUS" ]]; then
    echo "[preflight] ✗ corpus missing: $CORPUS"
    exit 1
fi
ls -lh "$CORPUS"

echo "[preflight] checking disk..."
df -h /workspace

echo "[preflight] HF_TOKEN set: ${HF_TOKEN:+yes}"
# Note: beomi/OPEN-SOLAR-KO-10.7B is public Apache-2.0, no token required.

# ── HF cache: use pre-staged /workspace location (100GB partition) ──
# / (overlay) is only 50GB and fills up with multiple 14B+ bases. /workspace
# has 100GB. SOLAR-KO bf16-native (~22 GB) fits alongside Qwen14B (~28 GB)
# ONLY IF Qwen32B (~62 GB) is evicted first.
export HF_HUB_CACHE="/workspace/hf_cache"
export HF_HOME="/workspace/hf_cache"
export TRANSFORMERS_CACHE="/workspace/hf_cache"

# Preflight: confirm Qwen14B cache is present (still serving r4 eval) and
# warn about disk. DO NOT auto-evict anything — that is a manual decision.
QWEN14_CACHE="/workspace/hf_cache/models--Qwen--Qwen2.5-14B-Instruct"
QWEN32_CACHE="/workspace/hf_cache/models--Qwen--Qwen2.5-32B-Instruct"
SOLARKO_CACHE="/workspace/hf_cache/models--beomi--OPEN-SOLAR-KO-10.7B"
if [[ -d "$QWEN14_CACHE" ]]; then
    Q14_SIZE=$(du -sh "$QWEN14_CACHE" 2>/dev/null | awk '{print $1}')
    echo "[preflight] ✓ Qwen2.5-14B cache: $Q14_SIZE (KEEP — r4 still uses this)"
fi
if [[ -d "$QWEN32_CACHE" ]]; then
    Q32_SIZE=$(du -sh "$QWEN32_CACHE" 2>/dev/null | awk '{print $1}')
    echo "[preflight] ⚠ Qwen2.5-32B cache: $Q32_SIZE"
    echo "[preflight]   If /workspace is tight, this can be removed manually:"
    echo "[preflight]     rm -rf $QWEN32_CACHE"
    echo "[preflight]   This forfeits the 32B r1 option until re-downloaded."
fi
if [[ -d "$SOLARKO_CACHE" ]]; then
    SK_SIZE=$(du -sh "$SOLARKO_CACHE" 2>/dev/null | awk '{print $1}')
    echo "[preflight] ✓ OPEN-SOLAR-KO-10.7B pre-staged: $SK_SIZE"
else
    echo "[preflight] ⚠ OPEN-SOLAR-KO-10.7B NOT pre-staged — first launch will download ~22 GB"
    # Free-space sanity check: ~22 GB for the base + ~5 GB working + 5 GB ckpt margin.
    AVAIL=$(df -BG /workspace | awk 'NR==2 {print $4}' | tr -d 'G')
    if [[ "$AVAIL" -lt 30 ]]; then
        echo "[preflight] ✗ only ${AVAIL} GB free in /workspace, need ~30 GB for download + ckpt"
        echo "[preflight]   Free space first (e.g. rm -rf $QWEN32_CACHE) then re-run."
        exit 1
    fi
fi

# ── Fresh checkpoint dir (never reuse — R17) ──
CKPT_DIR="/workspace/ckpt_alm_14b_r5_kbase"
rm -rf "$CKPT_DIR"
mkdir -p "$CKPT_DIR"

# ── Launch ──
# Reuses train_alm_14b.py (same trainer as r4 — only --base and metadata
# flags change). When hexa-lang ships native cuBLAS bindings (AN3), this
# launcher will be absorbed into train_alm_14b_r5_kbase.hexa.
python3 /workspace/train_alm_14b.py \
    --base beomi/OPEN-SOLAR-KO-10.7B \
    --corpus "$CORPUS" \
    --steps 10000 \
    --lr 5e-6 \
    --batch 1 \
    --grad-accum 8 \
    --seq 1024 \
    --warmup 500 \
    --lora-r 64 \
    --lora-alpha 128 \
    --lora-dropout 0.05 \
    --target-modules q_proj k_proj v_proj o_proj gate_proj up_proj down_proj \
    --ckpt-dir "$CKPT_DIR" \
    --save-every 2000 \
    --eval-every 500 \
    --model-tag alm14b_kbase \
    --round 5 \
    2>&1 | tee "$CKPT_DIR/train_r5_kbase.log"

echo "[done] 14B r5 kbase training complete — check $CKPT_DIR"
echo "[next] python3 /workspace/eval_alm_14b.py --ckpt $CKPT_DIR/step_10000"
echo "[next] Inspect Korean coherence on held-out prompts BEFORE promoting."
