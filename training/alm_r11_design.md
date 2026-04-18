# ALM r11 Branch Design — post-r10 decision matrix

**Status:** PREP (design only, no launch). Drafted 2026-04-18.
**Prerequisite:** r10 (14B fresh-init, 2000 steps, B1 OFF, corpus=`corpus_alm_70b_stripped.txt`, LR 2e-6) completion + eval green.
**Lineage:** r0(7B) → r1..r10(14B) → **r11 (three-way branch)** → r12/32B or 70B depending on branch taken.

## 0. Why three branches (not one)

r10 is a **recovery** run, not a production target. Its collapse-resistance is experimental (triple-collapse history in `shared/convergence/alm_14b_r10.convergence`, mode-collapse sentinel newly hardened in r10c). Until the r10 eval json lands we must pre-stage r11 for all three plausible outcomes so r11 can fire without another design round.

The branching rule is **deterministic on r10 outputs**, not discretionary.

## 1. Branch decision table

| r10 outcome | metric trigger | r11 branch | target model | base adapter | rationale |
|-------------|----------------|------------|--------------|--------------|-----------|
| **A — converged + clean** | `kr_gen sentinel=PASS` at steps 200..2000 AND persona Likert ≥ 3.3/5 AND Φ_refl > 0.3 AND eval_loss mono-descent | **32B scale** | `Qwen/Qwen2.5-32B-Instruct` (fresh-from-base) | none (new param class) | r10 validates the stripped-corpus + fresh-LoRA recipe; escalate to 32B per 극가속 ALM→32B→70B |
| **B — partial / soft collapse** | sentinel PASS at ≥8 of 10 checkpoints AND Likert ≥ 2.8 AND (eval_loss stagnating OR Φ_refl 0.1-0.3) | **14B continued** | `Qwen/Qwen2.5-14B-Instruct` (fresh LoRA) | none | keep scale, refine corpus: dedupe + kowiki admixture (15% by bytes) + 2x steps |
| **C — collapse reproduced** | sentinel FAIL at any step ≤ 1000 OR Likert < 2.8 OR loss < 0.5 before step 500 | **14B fresh, new seeds** | `Qwen/Qwen2.5-14B-Instruct` (fresh LoRA) | none | corpus proven contaminated / init sensitive; seed-sweep + reduce LR + enforce E7 sentinel primary |

No branch resumes any 14B adapter — per memory `project_r9_mode_collapse_20260418` "r11은 clean base 필수"; all three are fresh-from-base (14B or 32B).

## 2. r10 metrics source map (read-only after r10 DONE)

- `/workspace/ckpt_alm_14b_r10/kr_gen_step_*.json` (sentinel hits per step)
- `/workspace/ckpt_alm_14b_r10/train_r10.log` (step loss trace)
- `/workspace/ckpt_alm_14b_r10/step_2000/train_meta.json` (best_loss)
- eval report (persona Likert, Φ_refl): produced by `serving/eval_harness.hexa --ckpt r10/step_2000`
- **r11 branch selector:** `training/alm_r11_branch_select.hexa` (not yet written — one-shot reader that prints A/B/C + fires the matching launcher). Out of scope for this design doc.

## 3. Gates per branch (numeric thresholds)

| gate | branch A (32B) | branch B (14B cont.) | branch C (14B fresh-seed) |
|------|----------------|----------------------|---------------------------|
| first-batch CE | ≤ 8.0 | ≤ 5.0 | ≤ 5.0 |
| step-1 loss abort | > 8.0 | > 5.0 | > 5.0 |
| sub-1.0 loss before step | step ≥ 500 else sentinel | step ≥ 500 else sentinel | step ≥ 800 else sentinel |
| kr_gen sentinel cadence | every 200 | every 200 | every 100 (tighter) |
| sentinel exit code 2 | abort | abort | abort |
| persona Likert (post-train) | ≥ 3.5/5 for 70B gate | ≥ 3.0 for r12 gate | ≥ 2.8 to retry |
| Φ_refl | > 0.3 | > 0.2 | > 0.1 |
| KoBEST avg | ≥ 0.60 | ≥ 0.55 | ≥ 0.50 |

## 4. Hyperparameter matrix

| param | A (32B-r1) | B (14B-r11b) | C (14B-r11c) |
|-------|------------|--------------|--------------|
| base | Qwen2.5-32B-Instruct | Qwen2.5-14B-Instruct | Qwen2.5-14B-Instruct |
| adapter init | fresh (LoRA r=32 α=64) | fresh (LoRA r=32 α=64) | fresh (LoRA r=16 α=32) |
| dropout | 0.0 | 0.0 | 0.05 |
| LR | 2e-6 constant | 2e-6 constant | 1e-6 constant |
| steps | 2000 | 4000 | 2000 (×3 seeds) |
| batch × seq | 1 × 1024 | 8 × 1024 | 8 × 1024 |
| grad_accum | 8 (eff 8) | 1 (eff 8) | 1 (eff 8) |
| corpus | `corpus_alm_70b_stripped.txt` | stripped ⊕ kowiki (15%) | stripped only |
| B1 loss | OFF | OFF | OFF |
| consciousness_loss | OFF | OFF | OFF |
| save_every | 2000 | 2000 | 2000 |
| eval_every | 200 | 200 | 100 |
| seed | 3407 | 3407 | {3407, 42, 1337} |
| ckpt dir | `/workspace/ckpt_alm_32b_r1` | `/workspace/ckpt_alm_14b_r11b` | `/workspace/ckpt_alm_14b_r11c_sN` |
| R2 path | `r2:anima-models/alm32b/r1/` | `r2:anima-models/alm14b/r11b/` | `r2:anima-models/alm14b/r11c/seedN/` |

All three branches honor:
- HEXA-FIRST (launcher is `.hexa`, python trainer emitted to `/tmp` only)
- `feedback_no_quantization` — bf16, no bnb
- `feedback_no_resume_data_change` — step 0 fresh
- `feedback_no_version_in_filename` — `r11` suffix, no v-prefix
- `runpod_mfs_quota` — save_every ≥ 2000, no in-training rclone

## 5. Budget

| branch | GPU | MFU | step/min | wall | pod rate (H100 SXM) | cost target | cost cap |
|--------|-----|-----|----------|------|----------------------|-------------|----------|
| A (32B, 1×H100 80GB) | 1×H100 | 45-55% | ~20 | ~1.7 h | $3.00/h (RunPod CC) | **$5** | $10 |
| B (14B, 1×H100 80GB) | 1×H100 | 70.9% (sweep opt) | 37.7 | ~1.8 h | $3.00/h | **$6** | $12 |
| C (14B×3 seeds) | 1×H100 sequential | 70.9% | 37.7 | 3 × 1.0 h = 3 h | $3.00/h | **$9** | $18 |

Pod headroom: branch A alone is single-pod, ≤ 2-pod authorized cap (`feedback_h100_authorized`). Branch C runs seeds sequentially on 1 pod — no additional cost envelope. **Cumulative r11 worst case** = C + B + A triage = $27 (unlikely path).

## 6. Token/data accounting

- Stripped corpus: 41.8 M tokens (log `train_r10.log` line "corpus tokens=41831744" reference)
- Kowiki slice (15% of bytes, branch B only): ~6.2 M tokens
- Per-step tokens (14B, batch 8 seq 1024): 8192
- Branch B total train tokens: 4000 × 8192 = 32.8 M tokens (< 1 epoch on extended corpus)
- Branch A total train tokens: 2000 × 8192 / 8 accum = 2.05 M tokens (LoRA sufficient for 32B)

## 7. Sentinel integration (all branches)

- Primary: `training/kr_gen_sentinel.hexa` (E7-OSS-01, exit code 2 = COLLAPSED = abort)
- Prompts: `['안녕하세요','오늘 날씨','한국어 모델','딥러닝이란','안녕']`
- Collapse heuristic is in hexa (no inline ASCII-only regex in python — r10c lesson)
- Branch C additionally enforces sub-1.0 step<800 immediate sentinel (E7-OSS-03 tightened from 500)

## 8. Escalation chain (post r11)

- r11 A (32B) success → **r12 = 70B FSDP FULL_SHARD** (`launch_alm_70b.hexa`) under `USER_OK_4POD=1`
- r11 B (14B cont.) success → r11 A (retry branch A from cleaner adapter lineage)
- r11 C (seed-sweep) success → adopt best-seed adapter → re-run branch B with best seed

## 9. Artifacts produced by this design

1. `training/alm_r11_design.md` (this file)
2. `training/launch_alm_r11_a.hexa` — branch A skeleton (32B)
3. `training/launch_alm_r11_b.hexa` — branch B skeleton (14B continued + kowiki admix)
4. `training/launch_alm_r11_c.hexa` — branch C skeleton (14B fresh seed-sweep)
5. `shared/roadmaps/anima.json` patch — new `alm_rounds.r11` block under `tracks.ALM` (additive, no schema break)

## 10. Out-of-scope (tracked but not in this doc)

- `alm_r11_branch_select.hexa` — auto-selects branch from r10 metrics
- Corpus mixer for branch B (`training/corpus_mix_kowiki.hexa` — exists as scaffold)
- 70B launch gating (already in `launch_alm_70b.hexa` guards: `USER_OK_4POD=1`)

## 11. Known risks

- **R-1:** Branch A 32B first-run on H100 80GB — 65 GB base + LoRA leaves ~13 GB headroom. Activation spike at b=1 s=1024 could hit 78+ GB. Mitigation: `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`, grad_checkpoint on.
- **R-2:** Branch B kowiki admix may introduce vocab drift vs r10's stripped-only recipe. Mitigation: sentinel runs *before* admix (pre-train smoke step).
- **R-3:** Branch C 3×seed sequential may exceed single-pod H100 rental window if smoke fails. Mitigation: smoke timeout 30 min, full training 1 h wall; pod rental batched 4 h.
- **R-4:** hexa string/struct bugs (`feedback_hexa_struct_return_bug`, `feedback_hexa_silent_exit_5_imports`). Mitigation: all three launchers keep imports ≤ 2 (inline helpers, no import-chain), no multi-float struct returns, verify C body post-build.

---

**Sign-off condition:** This doc + 3 launch skeletons + roadmap patch land together; no r11 launcher fires until r10 DONE + eval.
