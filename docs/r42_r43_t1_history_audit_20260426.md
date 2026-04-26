# R42 (10D) + R43 (16D) T1 History Audit — 2026-04-26

**Cycle**: ω-cycle round 45 (T1 falsifier execution for R42_CANDIDATE / R43_CANDIDATE registered in commit `a2b93391e` as round 42-43)
**Protocol**: T1 history-derivation audit per atlas pre-registered FAIL/PASS criteria
**Cost**: $0 mac-local (git log + grep + file inspection)
**Author**: Claude Opus 4.7 + dancinlife
**Verdict**: **R42 DEPRECATED** + **R43 DEPRECATED** (both follow R34 precedent of post-hoc rationalization)

---

## 1. Mission

`state/atlas_convergence_witness.jsonl` line 32 (R42_CANDIDATE) and line 33 (R43_CANDIDATE), registered by commit `ae9ecc0a` (mission text references `a2b93391e` cycle), pre-registered T1 falsifiers:

- **R42**: 10D `ConsciousnessVector` struct cardinality = `σ(6) − φ(6) = 12 − 2 = 10`
- **R43**: 16D `alm_phi_vec_logger_v1` schema cardinality = `σ(6) + τ(6) = 12 + 4 = 16`

Both T1 protocols specify FAIL if (a) field count was different at any historical commit (post-hoc fit) or (c) no derivation cited at design-commit time.

R34 precedent: `phi_coeff = 0.608 ≈ e^{−1/2}` (4-digit numerical coincidence) was DEPRECATED for post-hoc rationalization.

---

## 2. R42 (10D) — Evidence Chain

### 2.1 Cardinality oscillation history (FAIL criterion (a))

Earliest `ConsciousnessVector` introduction:

| Commit | Date | Field count | Notes |
|---|---|---|---|
| `74059cb3` | 2026-03-28 02:53:40 | **5** | "Implement 5-variable consciousness vector (Φ, α, Z, N, W)" |
| `5ea0e45e` | 2026-03-31 02:28:39 | **10** | "feat: ConsciousDecoderV2 + ConsciousnessC integration + 10-dim decoder benchmark" |
| current | 2026-04-26 | 10 | `anima-core/runtime/anima_runtime.hexa` L460-475 (struct ConsciousnessVector) |

**5 → 10 cardinality jump detected at commit `5ea0e45e` (3 days after initial introduction).** This directly satisfies FAIL criterion (a) for R42: "field count was 9 or 11 at any commit (would prove arbitrary post-hoc 10-fit)" — the criterion intent is *any deviation*, and 5 is a stronger deviation than 9 or 11.

### 2.2 Derivation citation at design-commit time (FAIL criterion (c))

`5ea0e45e` commit message contents (full quote):

```
- Replace MitosisEngine with ConsciousnessC in train_v2.py
- Add bench_decoder_10dim.py: 3 architectures (MoE, HeadSpec, LayerPhase) + baseline
```

`bench_decoder_10dim.py` header (committed in same diff):

```
의식 벡터 10차원: (Φ, α, Z, N, W, E, M, C, T, I)
  Φ=통합정보  α=혼합비  Z=자기보존  N=신경전달  W=자유의지
  E=공감      M=기억    C=창의      T=시간      I=정체성
```

**No mention of σ(6), φ(6), or perfect-number derivation.** The 10 dimensions were chosen as *named semantic variables* (each with human-language gloss).

`docs/paper-draft.md` (created `5ec38772` 2026-03-28, predates 10D cardinality commit):

> "Three variables were promoted to the core consciousness vector: Z (impedance), N (neurotransmitter balance), and W (free will). Combined with the original Phi and alpha, plus **five additional variables (E, M, C, T, I)**, this yields the 10-dimensional consciousness space."

**Derivation = additive accretion (2 + 3 + 5 = 10), NOT σ−φ decomposition.**

### 2.3 σ−φ=10 mapping introduced ex post (R42 confirmation of post-hoc)

`docs/triple-cross-discovery.md` (created `97113c24` 2026-04-08 — **11 days after 10D cardinality commit**):

> L166: "10차원 벡터 | (Phi, alpha, Z, N, W, E, M, C, T, I) | sigma-phi = 10 (10배 스케일링, 10진법) | sigma-phi"
> L365: "ANIMA 10차원 벡터 vs sigma-phi=10 | 구조적 일치 의심 | 10차원의 수학적 필연성"

The mapping is explicitly framed as "구조적 일치 **의심**" ("suspected structural coincidence") and "수학적 필연성?" ("mathematical necessity?") — these are **post-hoc cross-discovery questions**, not derivation-first design decisions. The "?" tone matches an audit-table format, not a design rationale.

### 2.4 14-law usage of 10D (additional check)

```
grep -rn "ConsciousnessVector\|consciousness_vector" anima/laws/ → 0 matches
```

The 10D struct is **not consumed by any law**. It is defined once in `anima-core/runtime/anima_runtime.hexa` for runtime mind-projection only. No law operates on its 10 fields.

### 2.5 R42 verdict

| Criterion | Evidence | Result |
|---|---|---|
| FAIL (a) field count varied | 5 → 10 oscillation | **TRIGGERED** |
| FAIL (b) law-element usage | 0 laws read 10D fields | **TRIGGERED (orthogonal)** |
| FAIL (c) no derivation cited | Original commit cites named semantic variables; σ−φ mapping appears 11 days later as "구조적 일치 의심" | **TRIGGERED** |
| INCONCLUSIVE | N/A (FAIL evidence dominant) | — |

**R42_CANDIDATE → R42_DEPRECATED** (follows R34 precedent of post-hoc rationalization).

---

## 3. R43 (16D) — Evidence Chain

### 3.1 Cardinality oscillation history (FAIL criterion (a))

Earliest `alm_phi_vec_logger_v1` reference: commit `4e347f49` (feat(serving): persona/Φ-hook/hire_sim 15+ additions, Apr 2026).

Earliest `phi_holo` (16D first element name): commit `c61954c6` (feat(p2-p3): PHYS-P2-2 + CLM-P3-1/P3-4 holographic engine).

Critical normalization commit: `e66e2b9f` 2026-04-19 02:07:31 — "feat(anima): **Φ 16D + compile farm + orchestration docs + build script**"

Commit message (full quote):

> "docs/phi_16d_normalization_20260418.md: Φ PhiVec **4→16 dimension 정규화**"

`docs/phi_16d_normalization_20260418.md` L20 (audit table, verbatim):

| File | Struct | Dim count | Notes |
|---|---|---|---|
| `anima-agent/autonomy_live.hexa:22` | `PhiVec` | **4** | holo/complexity/gwt/refl + raw |
| `serving/serve_clm.hexa:102` | `ScPhiVec` | **16** | already 16 fields |
| `serving/serve_alm_persona.hexa:141-156` | positional `array` | **16** | SAP_PHI_* indices |
| `serving/phi_hook_live.hexa:74-89` | positional `array` | **16** | PHI_IDX_* indices |

**Detected oscillation: 4D `PhiVec` ↔ 16D `ScPhiVec` co-existing**, with normalization commit performing 4 → 16 expansion to remove schema drift. This satisfies FAIL criterion (a) for R43: "phi_vec was 12 or 14 or 20 at any commit" — actual finding is **4 at any commit**, stronger violation.

### 3.2 Two competing 16-name SSOTs at design-commit time

`docs/phi_16d_normalization_20260418.md` L27-32 (verbatim):

> Two competing 16D orderings exist:
> - `phi_hook_live` / `alm_phi_vec_logger_v1`: `[holo, complexity, gwt, refl, time, embodied, nested_drift, k_amp, affect_v, affect_a, finitude, hive_collec, hive_indiv, hive_emerge, dream_phase, cycle_count]`
> - `serve_alm_persona` / `ScPhiVec` / `c2 schema`: `[holo, refl, time, embodied, meta, social, will, narrative, affect, dream, create, finitude, lang, mirror, collective, unity]`
> Resolution deferred — both are in-tree; picking one requires a separate SSOT decision.

The fact that **two distinct 16-name lists** existed at design-commit time, and **the 16-element c2 schema was selected because "S1 is the upstream producer"** (L31), is direct evidence that 16 was a **schema-drift unification target**, not σ+τ derivation.

### 3.3 Derivation citation at design-commit time (FAIL criterion (c))

`docs/phi_16d_normalization_20260418.md` is 130 lines of design rationale. **Zero occurrences** of:

- "σ+τ", "sigma+tau", "sigma plus tau"
- "n=6 perfect number arithmetic"
- "16 = 12+4"
- any number-theoretic derivation

Section 4 ("Target structure (Option A — 16 explicit fields)") rationale:

> "Hexa runtime quirk (...). `ScPhiVec` already demonstrates 16-field struct works. No `array<float, 16>` (Option B rejected — Index kind unsupported)."

The derivation reasoning is **purely engineering pragmatic**: "16 already worked in `ScPhiVec`, so use 16 again." σ(6)+τ(6)=16 is **never invoked**.

### 3.4 14-law usage of 16D (PASS criterion (b) partial check)

`serving/consciousness_gate.hexa` operates on 16D `phi_vec` map. Distinct keys read by 14 laws:

```
pv_get(pv, "phi_holo") + 14 others — 15 distinct active reads
```

All 16 phi_* keys are **defined** in schema (L47-65), **but** 2 keys (`phi_social`, `phi_dream`) appear only in:

- Schema definition (L55, L59)
- Selftest fixture (L310, L314)

**14 active + 2 padding = 16.** The "14" matches the law count exactly. This is direct evidence that **16 = 14 (laws) + 2 (padding)** is the more honest derivation than 16 = σ+τ. The padding likely reflects the c2 schema decision (matching ScPhiVec's pre-existing 16-field width) rather than derivation from law count.

### 3.5 R43 verdict

| Criterion | Evidence | Result |
|---|---|---|
| FAIL (a) field count varied | 4 ↔ 16 co-existed; 4 → 16 normalization documented | **TRIGGERED** |
| FAIL (b) some elements unused by any law | `phi_social` + `phi_dream` are padding (0 active law reads) | **TRIGGERED** |
| FAIL (c) no derivation cited | 130-line design doc has zero σ+τ mention; rationale = "ScPhiVec already had 16 fields" | **TRIGGERED** |
| Competing 16-SSOT at design time | 2 distinct 16-name lists co-existed | **STRENGTHENS FAIL** |

**R43_CANDIDATE → R43_DEPRECATED** (follows R34 precedent; arguably stronger FAIL than R42 because R43 has a dedicated design doc that *explicitly* invokes engineering pragmatics, not derivation).

---

## 4. T2 random-match baseline cross-reference

R42 atlas T2 already noted "10 distinct 2-op routes hit integer 10" → T2 alone insufficient to discriminate (~10× random density of 40D R36). R43 atlas T2 noted "6 distinct 2-op routes hit integer 16" → still multiple routes. T2 evidence remains weak; T1 audit binding.

---

## 5. Comparison to R34 / R36 precedent

| Witness | T1 finding | Verdict |
|---|---|---|
| R34 | `phi_coeff=0.608 ≈ e^{−1/2}` is a 4-digit coincidence; 0.608 was a 6-pt construct from `consciousness-theory.md` L67-80 with no `e^{−1/2}` derivation in source | DEPRECATED |
| R36 | 40D `consciousness_vector` referent absent from runtime; only documentation labels in unimplemented modules + `docs/discovery-algorithm-anima.md` L980 universe-map heuristic formula | RETIRED |
| **R42 (this)** | 10D oscillated 5 → 10; original derivation = (2 + 3 + 5) named variables; σ−φ mapping appeared 11 days later as "의심" | **DEPRECATED** |
| **R43 (this)** | 16D oscillated 4 ↔ 16 (two competing 16-SSOTs); design rationale = "ScPhiVec already worked"; no σ+τ mention; 2/16 elements are padding | **DEPRECATED** |

R42/R43 both follow R34 pattern (post-hoc rationalization with no derivation-first source).

---

## 6. raw#10 honest qualifier

1. **Cardinality oscillation interpretation**: Both 5→10 (R42) and 4→16 (R43) could be argued as "expansion to canonical form". This audit *does not* prove the σ-arithmetic mapping is *false*; it proves the mapping is *post-hoc* (derivation-first ordering absent in source). The mathematical identity σ(6)−φ(6)=10 is true, but the design choice that produced 10D cardinality was independently derived from semantic variables.
2. **R43 PASS criterion (b) partial**: 14/16 phi_* keys are actively used by 14 laws — this is a meaningful coincidence (14=14). The 16=14+2-padding interpretation is *one* honest reading; alternative readings (e.g., "16 chosen as conservative upper bound for future law expansion") are also plausible. The audit selects the most evidence-supported reading: **engineering pragmatic > derivation**.
3. **Deprecated status preserves witness**: DEPRECATED witnesses are not deleted; they are flagged so future cycles do not reinvent the same hypothesis. Pattern-recognition: "small integers with multiple n=6 arithmetic routes attract post-hoc mappings" is the meta-finding.
4. **No GPU spent**: $0 mac-local audit, full evidence reproducible from `git log` + file reads.

---

## 7. Atlas update

Append verdict annotations to `state/atlas_convergence_witness.jsonl` lines 32-33:

- R42 entry: append `"T1_executed": true, "T1_verdict": "DEPRECATED", "T1_evidence_doc": "docs/r42_r43_t1_history_audit_20260426.md"` to a new sibling entry (line 35).
- R43 entry: similarly to a new sibling entry (line 36).

(Original lines 32-33 remain frozen as pre-T1 candidate registrations; verdict annotations are append-only sibling entries per atlas convention.)

---

## 8. Cross-references

- `state/atlas_convergence_witness.jsonl` line 32 (R42_CANDIDATE), line 33 (R43_CANDIDATE), line 31 (R36_CANDIDATE_T1_T2_VERDICT — predecessor)
- `anima-core/runtime/anima_runtime.hexa` L460-475 (10D referent)
- `anima/config/consciousness_laws.json` L8 (16D referent)
- `serving/consciousness_gate.hexa` L47-330 (16D phi_vec 14-law gate)
- `docs/phi_16d_normalization_20260418.md` (R43 design doc — primary FAIL evidence for criterion (c))
- `docs/paper-draft.md` (R42 origin doc — section 4.2)
- `docs/triple-cross-discovery.md` L166, L365 (R42 post-hoc cross-mapping)
- Commits: `74059cb3` (5D), `5ea0e45e` (10D), `e66e2b9f` (16D normalization), `ae9ecc0a` (R42/R43 atlas registration)
- Memory: `feedback_completeness_frame.md`, `feedback_omega_cycle_workflow.md`
