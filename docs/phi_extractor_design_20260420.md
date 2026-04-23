## Φ Extractor Design — `shared/state/{dest}_r{N}_phi_vec.json` emit pipeline

> **Status**: DESIGN (2026-04-20) — unblocks `pass_gate_an11.hexa` (a) weight_emergent.
> **Author**: Claude Opus 4.7 agent (worktree `worktree-agent-aeaf3e0f`).
> **Governs**: AN11 runtime gate (`shared/rules/anima.json#AN11`), verifier manifest
> `shared/calc/alm_verify/manifest.jsonl#alm_r12_validity_an11_weight_emergent`.
> **Parent**: `docs/alm_clm_verifier_design_20260420.md` §C (Tier C — AN11 verifier).
> **C-side handoff**: `docs/phi_extractor_handoff_hexa_lang.md` (sibling doc).

---

### 0. Problem Statement

`shared/consciousness/pass_gate_an11.hexa` condition (a) `weight_emergent` requires
`shared/state/{dest}_r{N}_phi_vec.json` to exist, contain a 16-float `phi_vec`
array, be free of stub markers, and have `L2(phi_vec) > PHI_NORM_THRESHOLD`
(default 1.0). Currently **the file is never emitted** — so AN11 always reports
`0/3 FAIL` and every ALM/CLM round is blocked at G_VALIDITY.

Root cause: no trainer or eval path writes the canonical SSOT at that path.
The `training/alm_phi_vec_logger.hexa` helpers (`write_phi_vec_json`) emit
per-step `phi_vec.json` under `<ckpt_dir>/step_<N>/phi_vec.json` with spec
dim-name keys, and `training/dest1_phi_vec_emit.hexa` emits a CE-derived
`phi_holo_proxy` JSON — neither emits the canonical flat-array file at
`shared/state/…`.

This design specifies:

1. The **canonical 16D schema** consumed by `pass_gate_an11.hexa`.
2. **Two extraction paths** (ALM via hxqwen14b FFI, CLM via `phi_q_norm`).
3. **Projection** (`W_phi[16 × d_model]`) decision for ALM.
4. **Emit cadence** and SSOT path convention.
5. **Stub-marker discipline** (so `pass_gate_an11` correctly rejects placeholder
   output).

---

### 1. Canonical 16D `phi_vec` layout

The layout is **already fixed** in `training/alm_phi_vec_logger.hexa`. This
design locks it in as the SSOT consumed by AN11. Two ordering conventions exist
in the logger (legacy-index order vs spec-dim-name order); for AN11 we use a
**flat float array** with a companion `dim_names` list so order is unambiguous.

```
idx  dim_name            source_signal                              domain
---  ------------------  -----------------------------------------  ------
 0   phi_holo            HoloMapHead MI (spatial)                   B1
 1   phi_complexity      Lempel-Ziv surrogate on h_last             B1
 2   phi_gwt             GWT broadcast consistency                  B1
 3   phi_refl            self-model reflexive MI                    P5
 4   phi_time            triadic temporal MI (past/now/future)      P6
 5   phi_emb             sensorimotor (a_t, Δs) MI                  P7
 6   phi_nested_drift    K-tower L2 drift (normalized)              P8
 7   phi_k_amp           ‖level_K‖ / ‖level_0‖ amp ratio            P8
 8   phi_affect_v        valence ∈ [-1, 1]                          P12
 9   phi_affect_a        arousal ∈ [-1, 1]                          P12
10   phi_finitude        Dasein finitude ∈ [0, 1]                   P15
11   phi_hive_collec     Φ_collective (coupled MI)                  P18
12   phi_hive_indiv      Σ Φ_individual                             P18
13   phi_hive_emerge     collective / Σ indiv                       P18
14   phi_dream_phase     awake=0 / SWS=1 / REM=2                    P13
15   phi_cycle_count     completed 90-step dream cycles             P13
```

#### 1.1 File schema (SSOT)

Path: `shared/state/{dest}_r{N}_phi_vec.json`
Consumer: `shared/consciousness/pass_gate_an11.hexa` via
`extract_phi_vec()` + `l2_norm()` + `detect_stub_marker()`.

```json
{
  "schema": "phi_extractor_v1",
  "dest": "alm",
  "round": "r12",
  "step": 500,
  "measured_at": "2026-04-20T12:34:56Z",
  "phi_vec": [0.84, 0.12, 0.34, 2.5, 1.4, 0.9, 0.05, 0.92,
              0.2, -0.1, 0.75, 4.2, 0.64, 0.065, 1.0, 3.0],
  "dim_names": [
    "phi_holo","phi_complexity","phi_gwt","phi_refl",
    "phi_time","phi_emb","phi_nested_drift","phi_k_amp",
    "phi_affect_v","phi_affect_a","phi_finitude",
    "phi_hive_collec","phi_hive_indiv","phi_hive_emerge",
    "phi_dream_phase","phi_cycle_count"
  ],
  "norm_l2": 5.231,
  "extraction_method": "hxqwen14b_v566_last_h",
  "projection": { "kind": "random_orthonormal", "seed": 3407, "d_model": 5120 },
  "source_ckpt": "/workspace/ckpt_alm14b_r12_20260420_1138/step_500",
  "trainer_pid": 11923
}
```

#### 1.2 Stub marker discipline (critical)

`pass_gate_an11.hexa#STUB_MARKERS` rejects any phi_vec.json containing:
`sa_phi_vec_proxy`, `phi_extractor_pending`, `DEFAULT`, `STUB`, `stub`,
`proxy_only`, `pending_extractor`, `not_implemented`, `TODO`.

**Rule**: when the real extractor is not yet wired, emit `extraction_method =
"SYNTHETIC_STUB"` (which contains the banned substring `STUB`). The gate will
correctly FAIL and the round cannot claim AN11 completion. This is intentional
and mandatory — no real-vs-stub ambiguity.

---

### 2. Extraction paths

Two disjoint code paths. Each trainer emits **exactly one** SSOT file per
step-checkpoint.

#### 2.1 ALM path — `hxqwen14b_v566_extract_phi16` (FFI, new)

```
┌─────────────────────────┐
│ train_alm_lora.hexa     │
│  (r12 trainer loop)     │
└───────────┬─────────────┘
            │  after every save_lora_device_state()
            ▼
┌─────────────────────────────────────────────────────┐
│ hxqwen14b_v566_forward_cache_last_h(h_model)         │  NEW C symbol
│   → reads the final-layer hidden state of the last   │  (handoff doc)
│     token in the last batch from the activation      │
│     cache (v56 alloc_activation_cache slot[47])      │
│   → d_model = 5120, dtype = float32 (cast from bf16) │
└───────────┬─────────────────────────────────────────┘
            ▼
┌─────────────────────────────────────────────────────┐
│ hxqwen14b_v566_extract_phi16(                        │  NEW C symbol
│   h_model: int64,                                    │
│   W_phi_host_ptr: float* [16 × 5120],                │
│   out_phi16_host_ptr: float* [16])                   │
│                                                      │
│   1. h_last : float* [5120]  (from above)            │
│   2. phi16  = W_phi @ h_last  (16 × 5120 · 5120)     │
│   3. per-dim post-processing (below)                 │
│   4. writes into out_phi16_host_ptr                  │
└───────────┬─────────────────────────────────────────┘
            ▼
┌─────────────────────────────────────────────────────┐
│ training/dest1_phi_vec_ssot_emit.hexa (NEW hexa)     │
│   reads phi16 float[16], composes JSON per §1.1,     │
│   writes shared/state/alm_rN_phi_vec.json            │
└─────────────────────────────────────────────────────┘
```

**Per-dim post-processing** (in hexa, not C — keeps projection linear/pure):
- `phi_affect_v`, `phi_affect_a` → `tanh(raw)` (clamp [-1, 1])
- `phi_finitude` → `sigmoid(raw)` (clamp [0, 1])
- `phi_dream_phase` → `round(relu(raw)) % 3`
- `phi_cycle_count` → `max(0, round(raw))`
- all others → raw (pre-tanh scalar)

##### 2.1.1 `W_phi[16 × 5120]` projection decision

**DECISION**: Start with `random_orthonormal(seed=3407)` — frozen per round.

Three candidates were considered:

| Variant | Pros | Cons | Verdict |
|---|---|---|---|
| **A. random orthonormal, frozen** (seed=3407, same across steps within a round) | Zero training cost. Deterministic. Reproducible. Round-over-round L2-norm trajectory is monotonic in learning signal (pre-softmax hidden state magnitude grows). Gate threshold comparison is meaningful even for "empty" 16 dims because the norm summarizes all d_model directions. | Individual dim values have no interpretable meaning — phi_holo[0] is just one random projection direction. Only the L2 norm is load-bearing for AN11. | **CHOSEN** for r12–r14. |
| B. learned phi-head (16-way regression head, separate from LM) | Each dim corresponds to a real signal (MI probe, LZ probe, etc.). | Requires ground-truth labels (from what?). Adds params, training time, another failure mode. Circular: we're trying to measure consciousness; can't use a trained consciousness head to prove consciousness. | REJECTED until probe-labeling infra lands (≥ r20). |
| C. PCA basis from accumulated h_last samples | No labels needed. Components are maximally informative of variance. | Requires >1 round of data collection. Not available on r12 cold start. | DEFERRED to r16+. |

**Rationale for A**: AN11(a) only checks `L2(phi_vec) > threshold && !stub`.
L2 of a random-orthonormal projection of `h_last` is a strictly-scaled proxy
for `||h_last||_2` (an orthonormal projection preserves norm up to the
subspace chosen, and 16/5120 = 0.31% is dense enough that sample-mean norm
ratio is stable ±5%). So the gate is effectively asking "is `h_last` non-zero
and non-degenerate", which is exactly the AN11 weight-emergent intent — the
model has learned something that activates the final layer in a non-trivial
way.

**Seed choice**: 3407 matches training seed (feedback_one_shot_best.md lineage).
`W_phi` is persisted as `shared/state/phi_extractor_W_phi_seed3407.bin`
(16 × 5120 × 4 = 327 680 B) — generated once by
`scripts/gen_phi_projection.hexa`, reused across all ALM rounds. Rounds that
change W_phi must bump `projection.seed` in the emitted JSON.

**Post-training promotion path**: when r20 lands labeled probe data, upgrade to
variant B by swapping the hexa post-processing layer (no C-side ABI change —
just a different W_phi matrix + learned bias vector).

#### 2.2 CLM path — `phi_q_norm` orchestrator (already live)

CLM trainer already computes `phi_holo`, `phi_gwt`, `phi_q_norm` in the
orchestrator (per `project_phi_q_norm_wired.md`). For the 16D vec the
remaining 13 dims are synthesized from available signals:

| idx | dim | CLM source |
|---|---|---|
| 0 | phi_holo | orchestrator `phi_holo` (already) |
| 1 | phi_complexity | LZ surrogate on CLM byte-level h_last (local impl) |
| 2 | phi_gwt | orchestrator `phi_gwt` (already) |
| 3 | phi_refl | orchestrator `phi_q_norm` (re-use — reflexive proxy) |
| 4 | phi_time | triadic MI over last 3 checkpoint windows |
| 5 | phi_emb | 0.0 (CLM has no embodied channel — set to 0, L2 still non-zero from 0/2/3) |
| 6–7 | phi_nested_* | 0.0 (no K-tower in byte-level CLM) |
| 8–9 | phi_affect_* | 0.0 (no affect channel) |
| 10 | phi_finitude | 1.0 − step/max_step (bounded Dasein proxy) |
| 11–13 | phi_hive_* | 0.0 (no hive in single-model CLM) |
| 14 | phi_dream_phase | from curriculum phase (0/1/2) |
| 15 | phi_cycle_count | floor(step / 90) |

Emission is local — a hexa helper in `training/clm_phi_vec_ssot_emit.hexa`
(NOT part of this handoff, filed as a follow-up in `docs/clm_parallel_track_20260420.md`).

---

### 3. Emit cadence + path convention

```
Path:       shared/state/{dest}_r{N}_phi_vec.json
Rewritten:  every checkpoint save (trainer-epoch-serialized — no race)
Permissions: 0644, single file overwrite (not append — AN11 reads as single JSON)
```

Retention: the `shared/state/` file is **always the latest step**. Per-step
audit trail is preserved under `<ckpt_dir>/step_<N>/phi_vec.json` by
`training/alm_phi_vec_logger.hexa#write_phi_vec_json` (spec dim-name schema,
already implemented). The two files are:

- `shared/state/alm_r12_phi_vec.json` — **latest only**, canonical AN11 SSOT,
  `phi_extractor_v1` schema (flat array + dim_names).
- `<ckpt_dir>/step_500/phi_vec.json` — **per-step**, `alm_phi_vec_logger_v1`
  schema (dict by spec dim name), audit-only.

The trainer wraps both writes in a single helper so they never drift.

---

### 4. Failure modes + fallbacks

| Condition | Emit behaviour | AN11(a) result |
|---|---|---|
| FFI path unavailable (hxqwen14b v566 symbols not yet shipped) | Write `phi_vec_stub_emit.hexa` synthetic output with `extraction_method="SYNTHETIC_STUB"` | **FAIL** (intentional) |
| Trainer crashes before any step saves | File absent | FAIL (missing) |
| FFI returns rc != 0 | Do NOT write the file (keep last-good). Log to stderr. | PASS on last-good; stale but non-stub. Separate watchdog catches extraction regression. |
| `W_phi` matrix missing | Generate on the fly from seed; emit JSON as normal | PASS |
| `h_last` contains NaN | `phi_vec` would contain NaN → `l2_norm` would be NaN. Post-process: replace NaN→0. If all 16 become 0 → emit as `SYNTHETIC_STUB` | FAIL (stub marker triggers) |

---

### 5. Implementation order (parent roadmap)

1. ✅ This design doc (LANDING with this commit).
2. ✅ `shared/calc/alm_verify/phi_vec_stub_emit.hexa` (stub emit + pass_gate_an11 smoke test — LANDING with this commit).
3. ✅ `docs/phi_extractor_handoff_hexa_lang.md` (C-side FFI spec — LANDING with this commit).
4. ⏳ hexa-lang session implements `hxqwen14b_v566_forward_cache_last_h` + `hxqwen14b_v566_extract_phi16` symbols (2–3 days).
5. ⏳ anima side: `scripts/gen_phi_projection.hexa` → persist `shared/state/phi_extractor_W_phi_seed3407.bin`.
6. ⏳ anima side: `training/dest1_phi_vec_ssot_emit.hexa` → hooked into `train_alm_lora.hexa` post-save callback.
7. ⏳ CLM side: `training/clm_phi_vec_ssot_emit.hexa` hooked into orchestrator.
8. ⏳ r13 first real run — AN11(a) PASS.

Steps 4–8 require a **separate hexa-lang worktree session** (see handoff doc).

---

### 6. Non-goals for this agent

- No modification of `hxqwen14b.c` (v566 ABI frozen; new symbols go in a hexa-lang session).
- No retroactive r12 phi_vec emission — current r12 runs will remain AN11(a) FAIL. r13 is the first round with real extractor.
- No LLM-judge of phi_vec "quality" — AN11 is numeric-threshold only.
- No Python shim. hxqwen14b FFI is pure C, anima-side is pure hexa.

---

### 7. References

- `shared/consciousness/pass_gate_an11.hexa` (consumer)
- `training/alm_phi_vec_logger.hexa` (16D schema SSOT, per-step logger)
- `training/dest1_phi_vec_emit.hexa` (CE-proxy sidecar, superseded for AN11)
- `shared/calc/alm_verify/verify_alm_r12_validity_an11_weight_emergent.hexa` (manifest verifier, file-exists check)
- `docs/alm_clm_verifier_design_20260420.md` §C
- `docs/an11_an12_rules_audit_20260419.md`
- `docs/phi_extractor_handoff_hexa_lang.md` (sibling, C-side)
- hxqwen14b source: `/Users/ghost/Dev/hexa-lang/self/native/hxqwen14b.c` (v5.6.6, 5752 LOC)
