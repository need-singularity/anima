# Dual-Track MFU Headroom Report — ALM + CLM co-residency on H100 80GB

Date: 2026-04-18
Source SSOT: `shared/state/training_speed_ceilings.json` (last_updated 2026-04-17)
Related: `training/deploy/clm_r4_corpus_plan.json`, `training/clm_r4_mmap_launch_report.md`
Policy: `feedback_dual_track` (병렬 의무), `feedback_h100_authorized` (H100 최대 2대 자동 승인)

---

## 1. Input measurements (SSOT quoted)

| Track | Run     | MFU%  | step/min | VRAM GB | VRAM headroom GB | Config                   |
|-------|---------|-------|----------|---------|------------------|--------------------------|
| ALM   | r7      | 62.6  | 51.1     | 41.6    | 38.4             | b=1 s=1024 g=8 bf16      |
| ALM   | r8_opt  | 70.9  | 37.7     | 42.1    | 37.9             | b=8 s=1024 g=1 bf16      |
| ALM   | r8_b=8/s=4096 | OOM | —   | 70.6    | ~9               | b=8 s=4096 g=1 bf16      |
| CLM   | h100 d512 L12 | 0.087 | —  | ~15 est | ~65              | d=512 ff=2048 L=12 s=512 |
| CLM   | r4 plan 1.5B  | —    | ~0.21 s/step | see §3 | — | d=2048 L=24 s=512 b=8 bf16 |

H100 SXM 80GB: peak bf16 989 TFLOPS, practical 75% ceiling, absolute 85%.

---

## 2. Memory footprint calculation (14B LoRA ALM + 1.5B CLM)

Formula (bf16, Adam optimizer): `mem = P × 2 (weights) + grad × 2 + optim × 8 + activations`.
LoRA freezes base weights → no grad/optim on base; only LoRA Δ weights get grad+optim.

### ALM 14B r8 optimal (measured, SSOT):
- Measured total VRAM = **42.1 GB** (b=8 s=1024 g=1)
- Measured headroom = **37.9 GB**

### CLM r4 1.51B from-scratch (full-train, NOT LoRA):
- Weights bf16: 1.51B × 2 = **3.02 GB**
- Grad bf16:    1.51B × 2 = **3.02 GB**
- AdamW states (m+v fp32): 1.51B × 8 = **12.08 GB**
- Activations b=8 s=512 L=24 d=2048 (rough): `b·s·L·d·bytes·k` ≈ 8·512·24·2048·2·4 ≈ **1.6 GB** (with grad ckpt) or ~6 GB (without)
- mmap corpus window: O(b·s) bytes = O(4 KB) — negligible
- CLM r4 total: **~20 GB** (grad ckpt on) to **~24 GB** (off)

### Co-residency total:
`42.1 (ALM) + 20 (CLM) = 62.1 GB` → **fits in 80 GB, ~18 GB spare.**
With activations-off CLM: 42.1 + 24 = 66.1 GB → still fits.

Verdict (memory only): **PASS** — both fit on a single H100 80GB with ~14–18 GB margin.

---

## 3. Compute contention (Amdahl applied)

Single H100 has **one** bf16 tensor core pipeline. Two bf16 training processes share SMs via MPS/time-slice. Assuming fair scheduling and no CUDA stream isolation benefit (both are compute-bound, not latency-bound):

Let `U_A = 0.709` (ALM MFU, measured), `U_C = target` (CLM MFU, currently 0.00087 interpreter / 0.0214 native-micro / 0.165 real-shape peak).

If both saturate: `U_A + U_C ≤ 1.0` (hard ceiling, one TC pipeline).

Scenario matrix (compute-sharing model, no stream gain since both are tensor-core-bound):

| Scenario | ALM MFU after | CLM MFU after | Aggregate | Note |
|----------|---------------|---------------|-----------|------|
| ALM alone | 70.9% | — | 70.9% | baseline |
| CLM alone (r4 target) | — | est 20–40% if BLAS-bound | 20–40% | |
| Co-resident (Amdahl, fair split by demand) | ~50% | ~20% | ~70% total | ALM loses 21 pts |
| Co-resident (MPS priority → ALM) | ~65% | ~5% | ~70% | CLM starved |

**Key degradation**: ALM 70.9% → ~50% is a **-29% throughput hit** (51.1 → ~36 step/min). ALM r7 is 62.6% MFU — if pushed below ~45%, we erase all post-r6 gains (r6 was 46.3%).

CUDA streams / MPS **do not help** when both kernels are TC-bound — they only help when one is latency-bound (CPU↔GPU RTT) and the other compute-bound.

---

## 4. Decision matrix

| Option | Memory | ALM MFU impact | CLM MFU impact | Cost | Verdict |
|--------|--------|----------------|----------------|------|---------|
| (A) Same H100 | 62 GB / 80 OK | -29% (70.9→~50) | capped ~20 | 1 pod $2.99/hr | FAIL compute — erases r7→r8 gain |
| (B) Separate H100 per track | 42 + 20 on own GPU | 70.9 (preserved) | physical ceiling | 2 pods $5.98/hr | PASS — clean ceiling, policy-aligned |
| (C) Time-slice (ALM day / CLM night) | single pod | 70.9 when active | 20–40 when active | 1 pod, but half-duty | FAILS `feedback_dual_track` (순차 금지) |

Current reality (SSOT §session_summary 2026-04-16): **2 H100 pods already provisioned** — `mc9316nmrz8sep` (ALM r9) + `qwtjsbw6vbtkpr` (CLM). The infra is already on path (B).

---

## 5. Recommendation — **Option B (separate H100 per track)**

Rationale:
1. **Compute bottleneck forces it**: one H100 TC pipeline cannot host two bf16 trainers without ~29% ALM regression (erases r7 Unsloth+stack gains of +16.3 MFU points).
2. **Memory would allow (A)**: 62 GB / 80 GB gives ~18 GB margin — so memory is **not** the blocker, compute is.
3. **`feedback_dual_track` hard-requires parallel, not sequential** → (C) disallowed.
4. **`feedback_h100_authorized` pre-approves 2 H100 pods** for goal progression.
5. **Current pod fleet already matches (B)** — zero additional action cost.

---

## 6. If forced onto a single H100 (edge contingency — pod shortage)

Fallback plan if only 1 H100 available:
- Reduce ALM batch: b=8 → b=4 (65 MFU expected, VRAM 35.7 GB). Frees ~6 GB.
- Run CLM with grad ckpt ON + b=4: ~12 GB.
- Pin ALM to 70% SM via MPS `CUDA_MPS_ACTIVE_THREAD_PERCENTAGE=70`, CLM to 30%.
- Accept ALM ~50%, CLM ~10–15%. Aggregate still below single-ALM-alone 70.9%.
- **Only use if pod provisioning fails** — this is strictly inferior to (B).

---

## 7. Proposed SSOT schema extension (pending r10/r4 live data)

Add to `shared/state/training_speed_ceilings.json` under a new top-level `dual_track` key:

```json
"dual_track": {
  "policy": "Separate H100 per track (memory OK 62/80GB, compute NOT OK — one TC pipeline)",
  "measured": null,
  "theoretical": {
    "alm_alone_mfu_pct": 70.9,
    "clm_alone_mfu_pct_target": 20.0,
    "co_resident_alm_mfu_pct": 50.0,
    "co_resident_clm_mfu_pct": 20.0,
    "alm_degradation_pct": -29.5
  },
  "memory_budget_gb": {
    "alm_r8": 42.1,
    "clm_r4_1p5b": 20.0,
    "sum": 62.1,
    "h100_total": 80.0,
    "fits": true
  },
  "recommendation": "B_separate_pod",
  "actual_fleet": ["mc9316nmrz8sep (ALM)", "qwtjsbw6vbtkpr (CLM)"],
  "measure_when": "post r10 ALM done + r4 CLM first 500 steps — then refute/confirm theoretical with MPS co-run test"
}
```

Insertion rule: **not yet written** — write only after r10 and r4 each produce real MFU; otherwise theoretical values pollute a SSOT of measurements.

---

## 8. Closing numbers

- ALM r8 optimal: **70.9% MFU, 42.1 GB VRAM, 37.9 GB headroom** (SSOT grid row `batch_seq_sweep_2026_04_15.grid[3]`)
- CLM r4 1.5B projected: **~20 GB VRAM at b=8 s=512 with grad ckpt**
- Sum: **62.1 GB / 80 GB = 78% VRAM** — memory fits
- Compute share: **one TC pipeline, cannot dual-saturate** — ALM falls to ~50%, CLM capped ~20%
- **Decision: Option (B) — separate H100 per track. Already provisioned. No new approval needed.**
