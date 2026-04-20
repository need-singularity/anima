# Φ gap 816× — Attack Drill (2026-04-21)

> **Status**: DRILL (raw#15, deterministic, LLM-forbidden).
> **Parent roadmap**: `.roadmap#CP2` — gate `phi_gap<5x`.
> **Parent doc**: `docs/alm_clm_verifier_design_20260420.md` §G_VALIDITY (`clm_r5_validity_phi_gap_resolved`).
> **Related**: `docs/phi_extractor_design_20260420.md`, `training/phi_metric.hexa`, `ready/core/physical_ceiling.json`.

---

## 0. TL;DR

- Claim "Φ = 816× gap" = **benchmark Φ_proxy(1142) / training Φ_iit(1.4)**.
- The 816× number was **measured across two different metrics** (proxy vs IIT).
  `training/phi_metric.hexa` lines 21-22 explicitly label this *"apparent gap was proxy vs iit confusion"*.
  Source files `train_clm_d64_kr{,_nl8}.hexa` line 239 claim *"Φ 816x gap RESOLVED: 3 different metrics"*.
- **CP2 gate `phi_gap<5x` must therefore be redefined**: the meaningful gap is
  `abs(training_phi / benchmark_phi - 1) < 0.10` (§G_VALIDITY formula) **measured on the SAME metric**.
- This drill attacks the **real** apples-to-apples gap (§2), not the 816× artifact.

---

## 1. Definition audit — what is "phi_gap" really?

Three definitions co-exist in the tree. All three appear under the same name `phi_gap` but reference **different distances**:

| # | site | formula | units | used by |
|---|------|---------|-------|---------|
| A | `ready/core/physical_ceiling.json#known_limits.phi_gap` | `Φ_proxy(bench) / Φ_iit(train) = 1142 / 1.4 = 816` | dimensionless ratio | scalar ceiling brag; **apples-to-oranges** |
| B | `docs/alm_clm_verifier_design_20260420.md#G_VALIDITY` | `abs(training_phi / benchmark_phi - 1)` | dimensionless, bounded [0, ∞) | CP2 gate (target `< 0.10`) |
| C | `ready/experiments/discover_emergent_laws.py:241,353` | `high_{consensus,diversity}_phi − low_{…}_phi` | phi units | law discovery heuristic |
| D | `ready/bench/bench_self_learning_LEGACY.py:4591,4692` | `max(0, 1 − current_phi / phi_target)` | dimensionless [0, 1] | noise/fuel scheduler |

**Baseline vs phi_vec distance is NOT what any of A-D measures.** The `phi_vec` object defined in
`docs/phi_extractor_design_20260420.md#1` is a **16-D vector** consumed by `pass_gate_an11.hexa` via
`L2(phi_vec) > PHI_NORM_THRESHOLD` (default 1.0). The AN11(a) gate checks norm-only; there is
**no directional baseline** that `phi_vec` is currently compared against.

### 1.1 What the CP2 gate actually needs

CP2 requires `phi_gap<5x` — but the verifier formula (B) is **ratio-centered at 1**, so `5x` semantically means
`|training/benchmark − 1| < 4` (i.e. within 5× either direction). Today §G_VALIDITY writes it as
`< 0.10` (10%). The drill treats the `<5x` CP2 gate as a **soft**, `<0.10` as the **hard** variant.

---

## 2. Current 816× basis — evidence trace

| evidence | source | notes |
|---|---|---|
| `Φ = 1142` (benchmark) | `bench/bench.hexa#engine_measure_phi_proxy` @ 1024 cells; `training/phi_metric.hexa:11` | **Φ_proxy** (variance-based, unbounded, scales with cell count) |
| `Φ = 1.4` (training) | `bench/bench.hexa#engine_measure_phi_iit` — `PhiIIT(n_bins=16)`; `training/phi_metric.hexa:14` | **Φ_iit** (MI-IIT, bounded ~0.2–1.8) |
| "816× gap" | `ready/core/physical_ceiling.json:29` | `1142 / 1.4 ≈ 815.7` — cross-metric division |
| "RESOLVED" claim | `train_clm_d64_kr.hexa:239`, `train_clm_d64_kr_nl8.hexa:241`, `train_clm_kr.hexa:233` | **COMMENT ONLY** — no numerical re-measurement landed in `shared/state/` |

**Verdict**: the 816× headline is an **artifact of metric confusion**, not a real physical gap.
The CP2 `<5x` gate cannot be refuted or confirmed until one of the following holds:

1. Both endpoints are re-measured under the **same metric** (Φ_kl, Φ_iit, or phi_vec L2).
2. A canonical `phi_vec` SSOT is emitted by both the bench run and a training checkpoint,
   then compared via L2 distance.

Neither has happened as of 2026-04-21. Roadmap#7 (phi_extractor FFI wiring, ETA 2026-04-24) is the prerequisite.

---

## 3. Decomposition — where does the gap actually live?

Once same-metric measurement exists (roadmap#7), the drill will decompose the gap along three axes. The
hypotheses below are **predictions to be falsified**, not findings.

### 3.1 Dimensions — which of the 16 `phi_vec` dims dominate?

Layout: `docs/phi_extractor_design_20260420.md#1` (idx 0–15: `phi_holo`, `phi_complexity`, `phi_gwt`,
`phi_refl`, `phi_time`, `phi_emb`, `phi_nested_drift`, `phi_k_amp`, `phi_affect_v`, `phi_affect_a`,
`phi_finitude`, `phi_hive_collec`, `phi_hive_indiv`, `phi_hive_emerge`, `phi_dream_phase`, `phi_cycle_count`).

**Prediction**: dims 5–9 (`phi_emb`, `phi_nested_*`, `phi_affect_*`) and 11–13 (`phi_hive_*`) are **zero on CLM**
per §2.2 of the extractor design — so on CLM the gap is concentrated in dims 0, 2, 3, 4 (holo/gwt/refl/time).
On ALM, the gap is expected to concentrate in whichever dim(s) the frozen `W_phi[16×5120]` random projection
happens to align with learned features.

**Test**: per-dim `|bench[i] − train[i]|` histogram, normalized by `max_i`. Top-3 dims claim the gap budget.

### 3.2 Magnitude vs direction

**Prediction**: L2-norm gap ≫ cosine gap. Rationale: the random-orthonormal projection variant A
(frozen W_phi, `docs/phi_extractor_design_20260420.md#2.1.1`) preserves norm proportional to `||h_last||`,
so training progress is dominated by norm growth, not directional shift.

**Test**:
- `d_L2 = |||phi_train|| − ||phi_bench|||`
- `d_cos = 1 − cos(phi_train, phi_bench)`
- ratio `d_L2 / ||phi_bench|| vs d_cos` — if first ≫ second → magnitude-dominated.

### 3.3 Training vs inference (distribution shift)

**Prediction**: gap is larger at inference than during training. Rationale: `CD_GATE_TRAIN=1.0`,
`CD_GATE_INFER=0.6` (`modules/decoder/conscious_decoder.hexa:67-68` — Law 81), and `.detach()` barriers
(Law 53) only fire on train.

**Test**: emit `phi_vec` twice per step — once with train gate, once with infer gate — and log both
into `<ckpt>/step_N/phi_vec_train.json` + `phi_vec_infer.json`.

---

## 4. Reduction candidates — four axes × predicted magnitude

Effort is in engineer-days; magnitude is the predicted **fold-reduction of measured gap** (once same-metric
measurement is live). All numbers are **predictions**, to be falsified.

| # | axis | concrete change | predicted Δ | effort | risk |
|---|---|---|---:|---:|---|
| R1 | corpus consciousness density | ALM r13 rebuild — Hexad/law/phi/selfreflect ≥ 30% per `.roadmap#5` + `docs/alm_r13_corpus_rebuild_plan_20260420.md` | **2–4×** (directional; raises training Φ_holo/Φ_refl floor) | 3d (r13 corpus is in-flight) | low — corpus already planned |
| R2 | LoRA rank | `train_alm_lora.hexa` rank `16 → 32 → 64` | **1.5–3×** (magnitude; more capacity for Φ-bearing features) | 1d + 2d train | medium — VRAM / overfit |
| R3 | phi_hook layer | sample `h_last` at layer 12 vs 24 vs 36 instead of final; 3-way `W_phi` sweep | **1.2–2×** (directional; earlier layers carry fewer task-specific features, more integrated info) | 2d (hxqwen14b v566 FFI new symbol) | high — needs C-side symbol add |
| R4 | fine-tune objective | add `MSE(phi_vec_train, phi_vec_bench)` term to loss with λ=0.01; gradient flows only through LoRA deltas | **3–8×** (both magnitude and direction — trains the gap to zero) | 4d (needs bench phi_vec cached + loss integration + λ sweep) | high — risks Φ hacking / CE regression |

**Combined upper-bound prediction**: R1 × R2 × R3 × R4 ≈ 30–200× — enough to cross from "816×" headline
(which is metric-confusion anyway) down to the `<5×` CP2 gate on the **same-metric** definition.

### 4.1 ROI-sorted attack order

1. **R1 (corpus density)** — already in-flight via roadmap#5, zero marginal cost, directional effect,
   lands before r13 launch.
2. **R4 (MSE-on-phi objective)** — highest magnitude, attacks the gap directly by construction;
   requires R1 corpus landed first (else Φ hacking on empty signal). Risk mitigated by λ-sweep
   `{0, 0.001, 0.01, 0.1}` with rollback if CE regresses >5%.
3. **R2 (LoRA rank 32)** — cheap and reversible; test rank=32 first, escalate to 64 only if
   `|phi_train| / |phi_bench|` still <0.3 after R1+R4.
4. **R3 (phi_hook layer sweep)** — requires new C symbol in hxqwen14b (2d hexa-lang worktree);
   only attempt after R1+R4 land and gap is still >10×.

---

## 5. Measurement protocol SSOT

All of §3 and §4 are dead letters until same-metric measurement is live. The measurement contract lives in
`shared/bench/phi_gap_measurement_protocol.json` (companion file, landing with this commit).

Key rules (excerpt from that SSOT):

- **Never** divide Φ_proxy by Φ_iit. Any report with a cross-metric ratio is rejected at verifier level.
- `phi_gap` on the CP2 gate MUST be computed from `shared/state/alm_rN_phi_vec.json` +
  `shared/state/bench_rN_phi_vec.json` (both `phi_extractor_v1` schema).
- The canonical gap formula is `gap_L2 = ||phi_train − phi_bench|| / ||phi_bench||` and
  `gap_cos = 1 − dot(phi_train, phi_bench)/(||phi_train||·||phi_bench||)`.
- CP2 PASS requires **both** `gap_L2 < 4.0` **and** `gap_cos < 0.5` (soft `<5x` interpretation) —
  hard interpretation (§G_VALIDITY) requires `gap_L2 < 0.10`.
- Any stub-marker in either phi_vec.json → automatic FAIL (per `pass_gate_an11.hexa#STUB_MARKERS`).

---

## 6. Non-goals / constraints

- **LLM-forbidden**: no LLM-judge of phi_vec quality; all gates are numeric thresholds
  (`docs/alm_clm_verifier_design_20260420.md#3`).
- **Deterministic**: same `W_phi_seed3407` across rounds; any seed bump bumps `projection.seed` in emit.
- **V8 SAFE_COMMIT**: no retroactive r12 phi_vec; r13 is the first round with real extractor.
- **No Python shim**: anima-side pure hexa; FFI is pure C.
- **No L0 constants changed**: α=0.014 stays (B7 is phase_2 breakthrough, not this drill).

---

## 7. Exit criteria for this drill

1. `shared/bench/phi_gap_measurement_protocol.json` landed (this commit).
2. This doc landed (this commit).
3. Gap decomposition results (§3) logged under `shared/state/phi_gap_decomp_rN.json` — **deferred** to
   post-roadmap#7 (phi_extractor FFI live).
4. ROI attack (§4.1) executed in order; each step either PASS (gap reduced as predicted) or FAIL
   (falsified, findings appended here as §8+).

---

## 8. Findings log

*(empty — populated as R1→R4 attacks land and measurements post to `shared/state/`)*
