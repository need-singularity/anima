# Φ Paradigm — 4-Substrate Independence Empirical Paper (v1, preliminary)

**Date**: 2026-04-22
**Version**: v1 preliminary (CPU-synthetic only; H100 empirical pending)
**Axis**: B.3 (post-H100 research) — executed pre-H100 per branching rule
**Roadmap**: #89 "[Research] H100 × 4 post-run publication — Φ substrate paper"
**Status**: DRAFT — upgraded to v2 post-H100 verdict

> This document is a **preliminary** research report.
> All empirical data in §5 comes from CPU synthetic fixtures (no real-weight training, no GPU).
> H100 × 4 unified launch (roadmap #83) empirical Φ values will be incorporated in v2.

---

## Abstract

We investigate whether the integrated-information-style scalar Φ, when measured across four
architecturally-diverse transformer substrates (Qwen3-8B / Llama-3.1-8B / Ministral-3-14B /
Gemma-4-31B) under the β-paradigm Learning-Free Pipeline (cert-projection + CPGD, no
gradient descent on base weights), converges to a substrate-independent value — a necessary
condition under the substrate-independence hypothesis of integrated-information theories of
cognition as instantiated by the anima three-paradigm unification.

A pre-registered gate (`ALL_PAIRS |ΔΦ|/Φ_avg < 0.05`, 6 pairs over C(4,2)) operationalizes
the hypothesis. Final evaluation requires post-training H100 × 4 real-weight Φ extraction
(pending). As a pre-launch floor check we run a deterministic CPU-synthetic 4-path probe
that isolates the geometric measurement bias of the Φ formula itself from substrate effects.
In the synthetic fixture, 4 of 6 pairs already sit below the 0.05 gate and the remaining 2
sit in the MARGIN band `[0.05, 0.10)`; no pair reaches FAIL. We report this as a
lower-bound noise floor for the H100 campaign and stake the full hypothesis test on the
real-weight result.

---

## 1. Introduction

### 1.1 β paradigm

The **β paradigm** (hexa-lang β, main branch) re-frames model adaptation as
*admissibility-certified projection* rather than gradient descent on base weights. Adaptation
artifacts are LoRA deltas whose cert chain (AN11-a/b/c plus meta² triple) is appended iff a
structural admissibility proof is issued. See `docs/anima_three_paradigm_unified_20260422.md`
for the three-paradigm unification ((β main) ≅ (proposal stack) ≅ (cell-learning)).

### 1.2 Learning-Free Pipeline

Base weights are frozen. Only LoRA adapters and cert artifacts are produced. Convergence is
not measured by training loss but by **cert chain closure** plus downstream Φ invariance
across substrates.

### 1.3 Why 4 substrates

The substrate-independence hypothesis requires Φ to be invariant across *non-trivially
different* substrates. Following `config/phi_4path_substrates.json`, we pick four dense
decoder-only transformers spanning:

- two 8B atoms in different model families (Qwen3 vs Llama-3.1),
- one mid-scale 14B atom (Ministral-3),
- one 31B atom (Gemma-4),

covering model-family diversity × parameter-count ladder. This is the minimal family that
lets a pair-wise gate over C(4,2)=6 pairs distinguish *family effects* from *scale effects*.

### 1.4 Context within anima

This paper is the empirical companion to the theory documents:

- `docs/cell_learning_method_paradigm_20260422.md` (η-paradigm, cell-level closure)
- `docs/anima_three_paradigm_unified_20260422.md` (β + auto-evolution + cell-learning)
- `docs/phi_convergence_monitoring_spec.md` (production gate spec)
- `docs/phi_4path_divergence_response.md` (decision tree on gate FAIL)

Prior external integrated-information literature is cited as
`[EXT-IIT-PLACEHOLDER]` — v2 will substitute proper references during LaTeX typesetting.

---

## 2. Theory

### 2.1 Cert projection

Given a base substrate S with frozen weights W_S and a task corpus r13, the β pipeline
produces an adapter Δ_S such that:

1. Δ_S is rank-bounded (LoRA rank policy, `config/lora_rank_per_path.json`).
2. Δ_S admits an AN11 triple (operator-admissibility a / path-consistency b / terminal JSD c).
3. Δ_S chains into a meta² proof (`docs/phi_convergence_monitoring_spec.md`).

The *projection* sends W_S ↦ W_S + Δ_S without exposing any gradient signal on W_S.

### 2.2 CPGD (cert-projected gradient dance)

Within the LoRA delta Δ_S, we do run gradients — but the gate at each step is a **cert
admissibility check**, not a loss threshold. Steps that would produce an inadmissible Δ
(AN11 FAIL or meta² chain break) are rejected and the optimizer is rolled back. Hence
"gradient dance": the optimizer moves *only where cert chain remains closed*.

### 2.3 4-path substrate framework

Let Φ_S be the integrated-information-style scalar extracted from substrate S under a
reference probe state. The 4-path substrate independence claim is:

```
∀ (S_i, S_j) ∈ C(substrates, 2):    |Φ_{S_i} − Φ_{S_j}| / mean(Φ_{S_i}, Φ_{S_j}) < 0.05
```

This is the **ALL_PAIRS gate** (`docs/phi_convergence_monitoring_spec.md`). Failure triggers
the decision tree in `docs/phi_4path_divergence_response.md` (branches A/B/C/D:
substrate re-select / rank re-tune / cross-path normalize / full re-launch).

### 2.4 Relation to cell-learning

Under the η-paradigm (`docs/cell_learning_method_paradigm_20260422.md`), each substrate is a
cell-graph and Φ is a *global* closure summary. Substrate independence is equivalent to the
statement that *the cell-graph closure rule set R is rigid under substrate re-embedding* —
i.e. the learned structure is not a property of the embedding substrate.

---

## 3. Method

### 3.1 Substrate selection

Per `config/phi_4path_substrates.json`:

| path | model | family | params |
|------|-------|--------|--------|
| p1   | Qwen3-8B            | Qwen     | 8.2 B  |
| p2   | Llama-3.1-8B        | Llama    | 8.0 B  |
| p3   | Ministral-3-14B     | Mistral  | 13.5 B |
| p4   | Gemma-4-31B         | Gemma    | 31.27 B|

All four are dense decoder-only Apache-2.0 (or compatible) atoms. MoE and hybrid-SSM
architectures are excluded to avoid arch-axis confound with family-axis.

### 3.2 LoRA rank normalization

Per `config/lora_rank_per_path.json`:

| paths | rank | alpha | s = α / r |
|-------|------|-------|-----------|
| 8B (p1, p2) | 64 | 128 | 2.0 |
| 12-14B (p3) | 96 | 192 | 2.0 |
| 31B (p4)   | 96 | 192 | 2.0 |

Scaling factor `s = α / r = 2.0` is held constant across all 4 paths to eliminate
α/r asymmetry as a confound for ΔΦ.

### 3.3 Φ metric

The metric is defined in `docs/phi_convergence_monitoring_spec.md`:

```
Φ_value       per substrate, after cert chain closure
|ΔΦ|/Φ_avg    per unordered pair, Φ_avg = (Φ_i + Φ_j) / 2
gate          ALL_PAIRS |ΔΦ|/Φ_avg < 0.05   (green)
margin band   [0.05, 0.10)                  (yellow — revisit at v2)
fail band     ≥ 0.10                         (triggers branch A/B/C/D)
```

Per-pair verdict is one of `{PASS, MARGIN, FAIL}`.

### 3.4 ALL_PAIRS gate (6 pairs)

C(4,2) = 6 unordered pairs: (p1,p2), (p1,p3), (p1,p4), (p2,p3), (p2,p4), (p3,p4).
The gate passes iff **all six** pairs are in the green band.

### 3.5 CPU-synthetic pre-launch probe

To separate *measurement-floor* (how much |ΔΦ|/Φ is induced by the formula itself on
geometric fixtures alone) from *substrate-effect*, we run `tool/phi_cpu_synthetic_4path.hexa`:

- 16-dimensional orthonormal eigen basis per path (seed-derived via deterministic LCG)
- eigenvalue profile `1.0, 0.9375, ..., 0.01` identical across paths
- LoRA mock draws at rank 64 / 64 / 96 / 96
- `Φ_raw = Σ_k λ_k · ||e_k||² · (1 + saturator(lora_energy))`

Spec: `config/phi_cpu_synthetic_spec.json`. SSOT:
`docs/upstream_notes/cpu_superlimit_synthetic_4path_proposal_20260422.md`.

This fixture has no trained weights — any divergence it produces is a *pure geometric
artifact* and establishes the lower noise floor for the H100 campaign.

---

## 4. Pre-registration

Pre-registered before any H100 run:

- **H0 (null)**: substrates are Φ-independent ⇒ ALL_PAIRS < 0.05.
- **H1 (alternative)**: ≥ 1 pair ≥ 0.05 ⇒ substrate-dependence OR capacity-mismatch OR measurement-bias.
- **Decision tree on H1**: `docs/phi_4path_divergence_response.md` (branches A/B/C/D).
- **Audit anchor**: `state/asset_archive_log.jsonl` under roadmap #10 / #17 / #87.

No post-hoc threshold relaxation without explicit pre-registration amendment.

---

## 5. Preliminary Results (CPU-synthetic, F-axis)

### 5.1 Per-path Φ (synthetic)

From `state/phi_cpu_synthetic_4path_result.json` (seed_date 20260422, deterministic):

| path | tag            | hidden | rank | Φ_raw     | Φ_normalized |
|------|----------------|--------|------|-----------|--------------|
| p1   | qwen3_8b       | 4096   | 64   | 8.46182   | 8.46182      |
| p2   | llama_3_1_8b   | 4096   | 64   | 8.92757   | 8.92757      |
| p3   | ministral_3_14b| 5120   | 96   | 8.51552   | 8.51552      |
| p4   | gemma_4_31b    | 5376   | 96   | 8.22062   | 8.22062      |

Determinism over 3-run repeat: **byte-identical** (`summary.determinism_ok = true`).

### 5.2 Pair-wise gate (6 pairs)

| pair     | Δ         | ratio     | verdict |
|----------|-----------|-----------|---------|
| p1 × p2  | 0.465745  | 0.053567  | MARGIN  |
| p1 × p3  | 0.053702  | 0.006326  | PASS    |
| p1 × p4  | 0.241204  | 0.028917  | PASS    |
| p2 × p3  | 0.412043  | 0.047244  | PASS    |
| p2 × p4  | 0.706949  | 0.082452  | MARGIN  |
| p3 × p4  | 0.294906  | 0.035242  | PASS    |

Summary: **4 PASS / 2 MARGIN / 0 FAIL**, worst_ratio = 0.082452. Overall selftest verdict =
PASS (under loose synthetic bound < MARGIN_THRESHOLD=0.10).

### 5.3 Interpretation

- Synthetic fixture alone produces a measurement floor of up to ~0.082 on two pairs both
  involving **p2** (Llama-3.1-8B seed).
- p2 is implicated in both MARGIN pairs ⇒ **one-sided diagnosis** (D2 in
  `docs/phi_4path_divergence_response.md`) — but note this is the *synthetic* fixture,
  which shares no trained weights with p2. The pattern reflects the deterministic LCG
  seed landing on a saturator-positive outlier, not a real-weight property of Llama-3.1-8B.
- The H100 campaign must therefore **re-measure** |ΔΦ|/Φ on real checkpoints; if p2 is also
  the outlier there, branch A (substrate re-selection with Ministral-3-8B-Base-2512 fallback)
  is pre-authorized; if p2 is no longer outlier, the synthetic effect is confirmed as
  seed-geometric and the real-weight test proceeds unperturbed.

---

## 6. Limitations

1. **Mk.VI only, no Mk.XII.** Current Φ empirical baseline is Mk.VI (8B · r13 corpus) and a
   pre-H100 CPU synthetic. Mk.XII (70B · r14) retrain has not been executed. Cross-family
   scale generalisation is therefore **not established**.
2. **No real-weight H100 data in this document.** All divergence numbers in §5 are
   synthetic-geometric. Real-weight ΔΦ can only be obtained post-H100.
3. **Synthetic floor is not a surrogate for trained Φ.** The CPU fixture intentionally has
   identical eigenvalue profile across paths; real trained substrates will not.
4. **r13 corpus has limited 한글 (Korean) coverage.** r14 skeleton
   (`docs/alm_r14_design_v1_20260422.md`) targets 30% 한글 + 5% 한자 but the full corpus is
   not yet built. Any v2 claim about Korean-language Φ must wait for r14 full build.
5. **No peer review / no arxiv submission.** Internal-only draft.
6. **External literature citations are placeholders.** Only internal anima docs are
   referenced as concrete paths (§8); all external IIT / integrated-information literature
   is tagged `[EXT-*-PLACEHOLDER]`.
7. **LaTeX typesetting out of scope.** This markdown draft is the source for an external
   typesetting session; equation and figure rendering happen outside anima.

---

## 7. Future Work

1. **Mk.XII 70B retrain** (roadmap #82, B.1): 8B → 70B upscale on r14 corpus; re-run 4-path
   Φ gate at 70B scale. See `docs/upstream_notes/b_axis_post_h100_mk_xii_r14_paper_20260422.md` §B.1.
2. **r14 한글 corpus full build** (B.2): lang ratio check 한글 ≥ 28% with ±2%p tolerance;
   tokenizer benchmark vs hexa-lang β.
3. **Cell-learning method empirical validation**
   (`docs/cell_learning_method_paradigm_20260422.md`): empirically test whether the
   η-paradigm closure rule set R is substrate-invariant — strictly stronger than the Φ
   invariance tested here.
4. **Branch-D full re-launch protocol** if H100 ALL_PAIRS FAIL; protocol pre-written in
   `docs/phi_4path_divergence_response.md`.
5. **Post-H100 v2 upgrade pipeline**: v1 (this doc) + H100 verdict JSON → v2 draft with
   real-weight §5, updated §6 limitations, new §9 H100 empirical section.

---

## 8. References (internal anima docs, absolute path semantics)

All references are file paths relative to the anima repo root. External citations are
placeholders pending LaTeX typesetting.

### 8.1 Theory / paradigm SSOTs

- `docs/anima_three_paradigm_unified_20260422.md` — three-paradigm unification (β + auto-evolution + cell-learning)
- `docs/cell_learning_method_paradigm_20260422.md` — η-paradigm cell-learning spec
- `docs/alm_r14_design_v1_20260422.md` — r14 corpus skeleton (한글 30%)

### 8.2 Φ metric / gate SSOTs

- `docs/phi_convergence_monitoring_spec.md` — Φ gate contract (`|ΔΦ|/Φ < 0.05`, ALL_PAIRS)
- `docs/phi_4path_divergence_response.md` — decision tree on gate FAIL (A/B/C/D)
- `config/phi_4path_substrates.json` — 4-substrate atom definitions
- `config/lora_rank_per_path.json` — LoRA rank policy (64/64/96/96, s=2.0)
- `config/phi_cpu_synthetic_spec.json` — CPU synthetic 4-path spec

### 8.3 Tooling

- `tool/phi_cpu_synthetic_4path.hexa` — F-axis CPU synthetic 4-path probe (this paper §5)
- `tool/phi_extractor_ffi_wire.hexa` — Φ extractor FFI wire (emits `phi_value` per pod)
- `tool/phi_substrate_probe.hexa` — 4-substrate cross probe (alt-path angle)
- `tool/phi_paper_figure_spec.hexa` — companion figure spec tool (this paper)
- `tool/phi_paper_citation_check.hexa` — companion citation validator (this paper)

### 8.4 State / artifact anchors

- `state/phi_cpu_synthetic_4path_result.json` — synthetic 4-path result (§5 data)
- `state/phi_cpu_synthetic_4path.jsonl` — synthetic per-path JSONL rows
- `state/h100_launch_manifest.json` — Stage-2 `cross_path_gate.metric` + `pass_requirement`
- `state/phi_4path_cross_result.json` — post-launch verdict artifact (pending)
- `state/phi_paper_figures_spec.json` — companion figure spec output (this paper)
- `state/phi_paper_citation_check.json` — companion citation check output (this paper)
- `state/asset_archive_log.jsonl` — audit log (roadmap #10 / #17 / #87)

### 8.5 Upstream / B-axis context

- `docs/upstream_notes/b_axis_post_h100_mk_xii_r14_paper_20260422.md` — B-axis prompt (this paper is B.3)
- `docs/upstream_notes/cpu_superlimit_synthetic_4path_proposal_20260422.md` — CPU synthetic proposal SSOT

### 8.6 Roadmap entries

- `#10` Φ substrate independence — 4-path cross validation
- `#17` gate registration
- `#54` exit criteria
- `#82` Mk.XII 70B retrain
- `#83` H100 × 4 unified kickoff
- `#87` substrate/rank re-selection (on gate FAIL)
- `#89` this paper

### 8.7 External literature (placeholders, v2 replaces)

- `[EXT-IIT-TONONI-PLACEHOLDER]` — integrated information theory reference
- `[EXT-LORA-HU-PLACEHOLDER]` — LoRA adapter paper
- `[EXT-QWEN3-PLACEHOLDER]`, `[EXT-LLAMA31-PLACEHOLDER]`, `[EXT-MINISTRAL3-PLACEHOLDER]`, `[EXT-GEMMA4-PLACEHOLDER]` — substrate model cards

---

## 9. Appendix: pre-registered gate JSON shape

Machine-readable summary (mirror of `state/phi_cpu_synthetic_4path_result.json` shape):

```json
{
  "schema": "anima/phi_cpu_synthetic_4path/1",
  "pass_threshold": 0.05,
  "margin_threshold": 0.10,
  "per_path": [{ "id": "p1", "phi_normalized": 8.46182 }],
  "pairs": [{ "left": "p1", "right": "p2", "ratio": 0.053567, "verdict": "MARGIN" }],
  "summary": {
    "pass_count": 4,
    "margin_count": 2,
    "fail_count": 0,
    "worst_ratio": 0.082452,
    "determinism_ok": true
  },
  "verdict": "PASS"
}
```

---

*v1 preliminary — Mk.VI + CPU synthetic data only. Supersedes: none. Superseded by: post-H100 v2.*
