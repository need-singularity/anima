# Phase 4 — Long training 50000-step (TCLM-P1-1 NL=8 replay)

## Result: PARTIAL (Φ ✓, CE ✗ — depth hypothesis REJECTED)

## Config (only NL differs from baseline)
- STEPS=50000 WARMUP=500 LR_MAX=3e-3 LR_MIN=3e-4 INIT_SCALE=0.1
- log_every=500 eval_every=1000 save_every=5000
- D=64 FF=256 **NL=8** VOCAB=256 SEQ=128 RANK=16 BATCH=1 GRAD_ACC=8
- **All other hypers identical to TCLM-P1-1 baseline (NL=6)**

## Training Metrics (per 1000 steps — selected)

| step | loss | ppl | phi_proxy | Δ vs baseline NL=6 ppl |
|---:|---:|---:|---:|---:|
| 1 | 5.711 | — | — | — |
| 1000 | 3.193 | 23.95 | 101.00 | -0.56 |
| 2000 | 2.917 | 16.38 | 101.20 | -0.48 |
| 5000 | 2.508 | 12.13 | 101.72 | -0.38 |
| 10000 | 2.402 | 10.35 | 102.28 | -0.34 |
| 15000 | 2.344 | 9.55 | 102.62 | -0.31 |
| 20000 | 2.263 | 9.10 | 102.83 | -0.26 |
| 25000 | 2.184 | 8.79 | 102.96 | -0.22 |
| 30000 | 2.180 | 8.61 | 103.05 | -0.21 |
| 35000 | 2.101 | 8.50 | 103.10 | -0.19 |
| 40000 | 2.104 | 8.42 | 103.13 | -0.20 |
| 45000 | 2.147 | 8.36 | 103.15 | -0.20 |
| **50000** | **2.139** | **8.309** | **103.165** | **-0.20** |

## Final Metrics — Head-to-Head

| metric | NL=6 baseline | **NL=8 experiment** | target | NL=8 met | delta |
|---|---:|---:|---:|:---:|---:|
| CE_final | 2.152 | **2.139** | ≤ 1.4 | ✗ | -0.013 |
| PPL_final | 8.513 | **8.309** | ≤ 4.05 | ✗ | -0.204 |
| Φ_proxy_final | 103.274 | **103.165** | ≥ 100 | **✓** | -0.109 |
| loss Δ (initial→final) | -3.558 | -3.572 | — | — | -0.014 |
| relative improvement | 62.3% | 62.56% | — | — | +0.3pt |
| wall_time | 2031.7s (33.9 min) | **2149.5s (35.8 min)** | ≤ 90 min | ✓ | +117.8s |
| s/step | 0.041 | **0.043** | — | — | +5% |
| kernel launch errors | 0 | **0** | 0 | ✓ | — |
| OOM / crash | 0 | **0** | 0 | ✓ | — |
| ckpt file size | 3.2 MB | **4.22 MB** | — | — | +32% |
| tensors per ckpt | 51 | **67** | — | — | +16 (2×Q/K/V/O high+low) |

## Analysis — Depth-vs-Width verdict

The CE plateau behavior is nearly identical between NL=6 and NL=8:
- NL=8 @ 30K: PPL=8.61 | NL=6 @ 30K: PPL=8.82 (-0.21 for NL=8)
- NL=8 @ 50K: PPL=8.31 | NL=6 @ 50K: PPL=8.51 (-0.20 for NL=8)
- Ratio stable across training: NL=8 gives consistent ~2-3% perplexity reduction — not capacity unlock

Both models asymptote at similar structure. NL=8 is slightly better (~0.2 PPL absolute, ~0.013 CE) but this is the kind of noise floor that
scale-exponent-1.3 layer-count sensitivity gives. **Depth alone at d=64 does NOT cross the CE≤1.4 gate.**

Per spec verdict matrix:
- CE ≤ 1.4 → gate PASS ❌ (failed, CE=2.139)
- 2.0 > CE > 1.4 → width primary, depth weak ❌ (CE=2.139 is between 2.0 and 1.4? wait CE=2.139 > 2.0)
- **CE ≥ 2.0 → depth invalid, d=128 direct required ✓ (MET: 2.139 ≥ 2.0)**

Width scaling (d=64 → d=128+) is the required next move. 1.5M → 6M params would give the model room the corpus needs.

## Φ_proxy curve — depth trivially raises Φ

- NL=6 @ 50K: Φ=103.27
- NL=8 @ 50K: Φ=103.17 (basically identical — Φ proxy is weight-variance of `weights.embed`, which is vocab-dim not depth-dim)
- Both models cross Φ≥100 threshold trivially (INIT_SCALE=0.1 + ANY training)
- Phi proxy is insensitive to depth — it measures embedding variance, not hidden-state integration. This is expected and matches the
  phi_proxy_semantics caveat from the baseline phase 4 report.

## Kernel/System Health
- 0 kernel launch errors across 50000 steps
- 0 OOM / crash events
- CUBLAS_TENSOR_OP_MATH active (H100 tensor cores)
- NVRTC compile cache MISS → HIT on rerun (PTX 49032 bytes, 20 entry points)
- Steady-state sm_util: did not sample (dmon not attached this run to preserve pipe bandwidth for training)

## Checkpoints Saved
- step_5000, 10000, 15000, 20000, 25000, 30000, 35000, 40000, 45000, 50000 + final = **11 checkpoints** (4.22 MB each, 67 tensors each)
- local: pod `/workspace/ckpt_clm_d64_kr_nl8/`
- R2: `r2:anima-models/clm-d64-kr/r2-nl8/step_{5000..50000,final}/` (all uploaded successfully)

## Budget
- actual: ~36 min pod wall + 5 min setup + patches → ~$2.10
- cumulative (pod cost only): ~$2.10 (well under $5 cap)

## GATE
- 90-min budget → ✓ (used 36 min training + ~20 min setup = ~56 min total)
- CE gate → ✗ (2.139 ≥ 2.0 → depth-invalid verdict)
- Verdict: **PARTIAL** (same as baseline, slightly improved but not gate-crossing)
