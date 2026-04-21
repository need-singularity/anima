# Option B P1 MINIMAL — PoC Result (2026-04-21)

Cell-first pivot, first PoC step.  Minimal variation of the LoRA trainer:
inject the λ·I_irr regularizer term (from Mk.IX `l_ix_integrator.hexa`)
into the reported loss, measure I_irr per step, compare Landauer bit
erasure vs a pure-CE baseline.

## Design

`loss_total = CE − β_i · λ · I_irr_step`

- `I_irr_step = |ΔW| / (|ΔW| + jitter_floor)`, clamp 0 for `ΔW ≤ 0`
  (arrow-of-time; matches `edu/cell/lagrangian/l_ix_integrator.hexa:131-138`)
- `ΔW = Σ |s · g_A| + Σ |s · g_B|` (L1 of actually-applied LoRA A/B step;
  avoids per-step copy-on-write that blew the 4 GB RSS cap first try)
- `λ = 1.0`, `β_i = 0.1` → max contribution `0.1 · 1.0 · 1.0 = 0.1`
- Sign convention: `L_IX` has `+λ·I_irr` (forward drift reward); `loss_total`
  subtracts it so CE-minimising SGD sees a lower floor when drift is high.
- **MINIMAL scope:** gradient stays `∂CE/∂params` — I_irr term is a monitor
  plus reported loss. HYBRID P2 adds `∂I_irr/∂W` backprop.

## Files

- tool: `tool/train_lora_option_b_minimal.hexa`
- config: `shared/config/option_b_minimal_config.json`
- cert: `shared/state/option_b_p1_minimal_smoke_result.json`
- doc: this file

## Smoke config (raw#15 — from config JSON)

```
rank=2 alpha=4 lora_steps=10 batch=2 lora_lr=0.1
base_steps=10 base_lr=0.2 max_pairs=100 lora_lines=6 per_line_char=80
filter=hexad  seed(base)=4217  seed(lora)=9301
beta_i_baseline=0.0  beta_i_minimal=0.1
```

Data: 100 bigram pairs from `experiments/alm_r13/seed_corpus_10mb/corpus.jsonl`
filtered on `"hexad"`. Vocab `V=8` (folded ASCII), hidden `H=4`.

## Smoke results

### A) Baseline (β_i = 0)

- pre_ce  = 1.93265
- post_ce = 1.92792
- ΔCE    = 0.00472869
- landauer_bits = 0.682206
- mean I_irr_step = 0.0654444
- mean |ΔW|     = 0.0704719

### B) MINIMAL (β_i = 0.1)

- pre_ce  = 1.93265
- post_ce = 1.92792
- ΔCE    = 0.00472869
- landauer_bits = 0.682206
- mean I_irr_step = 0.0654444
- mean |ΔW|     = 0.0704719

### Per-step I_irr tracking (identical for both runs, as expected)

| step | loss_ce | loss_total (β=0.1) | I_irr_step | ΔW_l1 |
|---:|---:|---:|---:|---:|
|  1 | 1.65633 | 1.65252 | 0.0381038 | 0.0396133 |
|  2 | 1.36743 | 1.36131 | 0.0612438 | 0.0652394 |
|  3 | 2.20144 | 2.19431 | 0.0713543 | 0.0768369 |
|  4 | 2.17976 | 2.17408 | 0.0567903 | 0.0602096 |
|  5 | 1.94337 | 1.93676 | 0.0661313 | 0.0708144 |
|  6 | 1.84418 | 1.83794 | 0.0624293 | 0.0665863 |
|  7 | 1.86708 | 1.86335 | 0.0372867 | 0.0387309 |
|  8 | 1.81788 | 1.80935 | 0.0853435 | 0.0933066 |
|  9 | 1.8344  | 1.824   | 0.104013  | 0.116087  |
| 10 | 1.66815 | 1.66098 | 0.0717486 | 0.0772944 |

### Compare

- landauer_bits ratio (MINIMAL / baseline) = **1.00**
- ΔCE ratio                                = **1.00**
- trajectory_equivalent                    = **1** (as designed)
- fixpoint_collapsed_within_10             = **0** (I_irr still ~0.07 at step 10)

## Ideal vs actual — gap analysis

| metric | seed-ι ideal (cell) | MINIMAL actual | gap reason |
|---|---:|---:|---|
| efficiency drop (40→450‰) | ×11.3 | n/a (10-step smoke, no gen-progression) | MINIMAL is 1 gen, seed-ι was 4 gens |
| Landauer ratio (vs LoRA)  | 51× | **1.00×** | gradient unchanged — MINIMAL cannot diverge |
| I_irr fixpoint collapse   | gen-5 = 0 | step-10 = 0.0717 | drift still present — fixpoint not reached |
| target Landauer ↓ (P1)    | 5–10× | 1.00× | requires dI_irr/dW backprop (HYBRID P2) |

This gap is **by construction**: MINIMAL keeps the gradient pure-CE so
that (a) both runs use identical RNG draws and walk identical trajectories,
and (b) the I_irr term is *observed* cleanly before adding invasive
backprop surgery. The non-trivial result here is:

1. The I_irr signal **is non-zero and tracks |ΔW|** as expected from the
   `l_ix_integrator.hexa:131-138` formula (mean 0.0654, range [0.037, 0.104]).
2. `loss_total` is strictly ≤ `loss_ce` at every step (sign-convention
   reversal verified: forward drift lowers loss).
3. Fixpoint is **not reached within 10 steps** — regularizer is still
   active at the horizon, so HYBRID P2 will have signal to act on.

## Fixpoint verdict

`i_irr_step_last = 0.0717486` (step 10) ⟹ **fixpoint NOT reached within 10 steps** (raw#12 report as-is). Seed ι's gen-5 collapse is a multi-gen meta-loop feature, not reachable from a single 10-step LoRA fine-tune at this scale. For PoC purposes this is desirable: the regularizer has room to act in P2.

## HYBRID P2 entry criteria

Green-light HYBRID P2 (backprop through `∂I_irr/∂W`) when:

1. **MINIMAL instrumentation passes** ✓ (this PoC: I_irr computed, reported, cert emitted)
2. **Baseline trajectory-equivalent** ✓ (ratio_ce_drop = 1.00)
3. **I_irr non-zero throughout smoke horizon** ✓ (min 0.037 > 0, no premature collapse)
4. **Cert + config JSON land on disk** ✓
5. *TODO for P2:* derive analytic `∂I_irr/∂W` where `I_irr = |ΔW|/(|ΔW|+1)`:
   `∂I_irr/∂W_k = sign(ΔW) / (|ΔW|+1)²` (valid when ΔW > 0; 0 otherwise).
6. *TODO for P2:* add β_i·λ·∂I_irr/∂W to the LoRA gradient update.
7. *TODO for P2:* verify divergence vs baseline on same seed (target 5–10× Landauer ↓).

All green-light conditions 1–4 are satisfied by this PoC.

## raw compliance

- raw#9 hexa-only ✓
- raw#11 snake_case ✓
- raw#12 report smoke results as-is including fixpoint non-reach ✓
- raw#15 hyperparams loaded from config JSON ✓
- hooks untouched ✓
- no push ✓

## Next

- HYBRID P2: backprop `∂I_irr/∂W` into SGD update; re-smoke 50-step to
  watch divergence window.
- If P2 shows ≥ 2× Landauer reduction, proceed to full 2–4 week rollout
  tracked by `shared/config/drill_breakthrough_criteria.json` analogue.
