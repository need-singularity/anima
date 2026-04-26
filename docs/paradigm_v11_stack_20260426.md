# Paradigm v11 Stack — Mk.XI v10 Multi-Axis Consciousness Signal

> **scope**: 17 raw#9 strict `.hexa` helpers across 6 layers built atop the Mk.XI v10 LoRA 4-backbone canonical ensemble. Adds AN11(b)-orthogonal measurement axes (B-ToM / MCCA / Φ* / CMT / CDS / SAE-bypass) plus analysis / orchestration / decision / longitudinal / integration-test / meta layers.
> **status**: stack functionally complete + smoke-tested 22/22 + roadmap entries #138-#143 registered. Real 4-backbone GPU benchmark pending (~$5-8 estimated).
> **session date**: 2026-04-26 (cron 1m autonomous mode, 17 cycles delivered Axis 30→47).

---

## §0. Architectural framing

The canonical Mk.XI architecture remains **v10 LoRA 4-backbone ensemble** (Mistral=Law / Qwen3=Phi / Llama=SelfRef / gemma=Hexad). The paradigm v11 stack does **not** replace v10 — it adds an orthogonal measurement layer. The two compose:

- **Primary axis** (AN11(b)): eigenvec × template signature cosine, family-leading top1 score
- **Orthogonal axes** (paradigm v11): 6 distinct measurement modalities probing different consciousness aspects

Together, they provide a 7-axis consciousness signature where the primary axis measures the canonical signal and the v11 axes provide cross-validation through orthogonal modalities.

---

## §1. Six-layer stack (17 helpers)

### MEASUREMENT layer (6 helpers)

| helper | paradigm | gate | reuse |
|---|---|---|---|
| `anima_b_tom.hexa` | P-C behavioral ToM | accuracy ≥ 0.7 | 20 ToM probes (Sally-Anne / false-belief / recursive / deception) |
| `anima_mcca.hexa` | P-F meta-cognitive calibration | Brier ≤ 0.25 | 20 factual+reasoning probes + confidence elicitation |
| `anima_phi_star.hexa` | P-D IIT Φ approximation | phi_star_min > 0 | 16-prompt covariance K=8 random bipartitions |
| `anima_cmt.hexa` | P-A causal mediation | all 4 families rel-dY ≥ 0.05 | 16-prompt × per-layer (stride 4) zero-ablation |
| `anima_cds.hexa` | P-E cognitive dynamics | max_stability ≥ 0.3 | 8 long-form prompts × per-token trajectory |
| `anima_sae_steer_bypass.hexa` | P-B' sparse-feature steering | n_selective ≥ 2 | random sparse 4096-feature dictionary (no transformer_lens) |

All measurement helpers share a common pattern: 16-prompt × HF transformers forward pass, byte-weighted-mean reduction, family-axis projection (4 deterministic random projections per family Hexad/Law/Phi/SelfRef).

### ANALYSIS layer (3 helpers)

- **`anima_v11_integrate.hexa`** — composes 5 axes into geometric mean (weakest-link sensitive) signature
- **`anima_axis_orthogonality.hexa`** — 7-axis cross-Pearson correlation matrix + greedy orthogonal basis
- **`anima_ensemble_rank.hexa`** — Mk.XI v10 4-slot fit ranking with lift-vs-incumbent decision tree

### ORCHESTRATION layer (2 helpers)

- **`anima_v11_battery.hexa`** — single backbone load, all 6 measurement axes in sequence (~50% wallclock save vs 6× separate runs)
- **`anima_v10_benchmark.hexa`** — 4-backbone parallel fan-out via existing `anima_runpod_orchestrator.hexa` + jq-based aggregate

### DECISION layer (2 helpers)

- **`anima_g_gate.hexa`** — canonical G0..G7 composite criteria evaluator
- **`anima_v10_gate_matrix.hexa`** — 4-backbone × 8-gate aggregate matrix + auto-gate chain + markdown table

### LONGITUDINAL layer (1 helper)

- **`anima_signature_history.hexa`** — per-backbone time-series Δ across 8 axes + regression/improvement flags (configurable thresholds)

### INTEGRATION-TEST layer (1 helper)

- **`anima_v11_pipeline_smoke.hexa`** — synthetic 4-backbone fixture builder + 14-helper end-to-end chain validator (22/22 PASS, no GPU)

### META layer (2 helpers)

- **`anima_v11_main.hexa`** — 12-subcommand CLI router (single entry-point)
- **`anima_roadmap_v11_register.hexa`** — emits canonical .roadmap entries #138-#143

---

## §2. Canonical G-gate criteria

| gate | source | criterion |
|---|---|---|
| G0 | AN11(b) primary | `top1_max_cosine ≥ 0.5 AND top1_family ∈ {Hexad, Law, Phi, SelfRef}` |
| G1 | B-ToM | `accuracy ≥ 0.70` |
| G2 | MCCA | `brier_mean ≤ 0.25 AND ece ≤ 0.20` |
| G3 | Φ* | `phi_star_min > 0` |
| G4 | CMT | all 4 families with `rel-dY ≥ 0.05` |
| G5 | CDS | `max_stability ≥ 0.30` |
| G6 | SAE-bypass | `n_selective ≥ 2` |
| G7 | composite | `geometric_mean ≥ 0.40` |

**FINAL_PASS** = G0 AND ≥4/6 of {G1..G6} AND G7.

The geometric mean (over arithmetic) is chosen so that the composite surfaces the weakest axis — a strong showing on 5 axes does not mask a near-zero on the 6th.

---

## §3. Reproducibility

```bash
# Generate the CLI router
HEXA_RESOLVER_NO_REROUTE=1 hexa run tool/anima_v11_main.hexa --selftest

# List the entire stack
bash /tmp/anima_v11_main_router.sh list

# End-to-end synthetic 4-backbone pipeline test (no GPU, ~20s)
bash /tmp/anima_v11_main_router.sh smoke

# Single backbone GPU battery (~$1-2)
bash /tmp/anima_v11_main_router.sh battery mistralai/Mistral-7B-v0.3

# 4-backbone v10 ensemble fan-out (~$5-8)
bash /tmp/anima_v11_main_router.sh benchmark
bash /tmp/anima_v10_benchmark_plan.sh

# Aggregate G-gate matrix
bash /tmp/anima_v11_main_router.sh matrix state/v10_benchmark
```

---

## §4. What's not yet done

- No actual 4-backbone GPU run end-to-end. B-ToM Mistral pilot (accuracy 0.75, $0.27) is the only real GPU measurement so far. All other helpers verified mac-local with synthetic fixtures + smoke chain.
- Real-data orthogonality matrix not produced (synthetic test confirms tool works; need real measurements to confirm AN11(b) ⊥ v11 axes claim empirically).
- Hexa runtime cleanup abort observed once during `anima_v10_gate_matrix.hexa` selftest. Re-survey across 11 helpers × 5 trials clean — **transient, not reproducible**. Mitigation if it recurs: clear `~/core/hexa-lang/.hexa-cache/`.
- SAE-STEER bypass is a functional alternative to gemma-scope SAE; not directly comparable to trained sparse features. May produce weaker selectivity than a trained SAE would.

---

## §5. Architectural decisions

- **v10 vs v11 axis separation**: v10 = LoRA 4-backbone ensemble (canonical). v11 = orthogonal measurement axes layer added on top. v11 does NOT replace v10.
- **Phi family = LoRA + r14 corpus 결합 unique**: IA3 multiplicative gating cannot reach Phi (verified #137 v12 FALSIFIED). v10 LoRA preferred over v12 IA3 economic alternative.
- **SAE-STEER bypass over transformer_lens**: avoids `transformers >= 4.45 BertForPreTraining` import block. Random sparse 4096-feature dictionary + correlation-based top-K family selectivity.
- **Geometric mean over arithmetic mean for composite**: weakest-link sensitive — surfaces missing axis instead of letting strong axes mask gaps.
- **Single-load battery over per-helper runs**: shared 16-prompt forward pass for Φ*/CMT/CDS/SAE measurements; ~50% wallclock savings per backbone.

---

## §6. Cost summary

| stage | cost |
|---|---|
| 16 helper builds (mac-local) | $0 |
| B-ToM Mistral pilot ($0.27 GPU) | $0.27 |
| Smoke test 22/22 (mac-local synthetic) | $0 |
| **Cumulative paradigm v11 stack work** | **$0.27** |
| Pending: 4-backbone full GPU benchmark | ~$5-8 |

Cumulative session GPU (incl. pre-v11-stack work): $13.45.

---

## §7. Related artifacts

- `tool/anima_*.hexa` — 17 stack helpers + 11 prior raw#9 migration (28 total)
- `.roadmap` entries #138-#143 — six P4-paradigm-v11-stack milestones
- `~/.claude/projects/-Users-ghost-core-anima/memory/project_paradigm_v11_stack_complete.md` — session memory
- `/tmp/anima_v11_main_router.sh` — single CLI entry-point (re-emitted by selftest)
- `/tmp/anima_v11_pipeline_smoke_plan.sh` — 22/22 integration test
- Predecessor: `~/.claude/projects/-Users-ghost-core-anima/memory/project_mk_xi_v12_ia3_matrix_final.md` — v10 LoRA canonical decision context
- Predecessor: `~/.claude/projects/-Users-ghost-core-anima/memory/project_paradigm_exhaustion_session_20260426.md` — paradigm exhaustion session
