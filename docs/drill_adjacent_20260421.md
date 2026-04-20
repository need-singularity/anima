# drill Adjacent-Speculation Scan — 2026-04-21

Scope: apply the 5-module-lens + DFS>=3 + absorption/saturation auto-classifier
(the `drill_breakthrough` substrate) to problems *adjacent* to T3→T4 jump
verification. Goal: find un-drilled frontier problems where the same lens
yields deterministic, non-LLM-judge signal.

Substrate (reference): `shared/bench/drill_breakthrough_criteria.json`
- 5-module lens, DFS depth>=3, absorption_rate_max=0.3, saturation required,
  diagonal_agreement_min=0.8, module_coverage 5/5.

Constraints observed: **no LLM judge**, **deterministic**, **V8 SAFE_COMMIT**.

---

## Scoring axes (each 0-10, composite is mean rounded)

- **F** fit — does the problem expose a T3→T4-style jump?
- **S** signal — is there a deterministic quantity to classify (absorption vs saturation)?
- **D** DFS — can we construct depth>=3 drills?
- **M** module — can all 5 lenses participate (not a single-axis problem)?
- **L** leverage — if drill yields a verdict, how much downstream work unblocks?

Composite = round(mean(F,S,D,M,L)).

---

## 8 Adjacent Problems × drill Applicability

| # | Problem | F | S | D | M | L | **Score** | Verdict |
|---|---|---|---|---|---|---|---|---|
| 1 | ALM corpus curation audit (signal vs noise in corpus_v2) | 9 | 9 | 8 | 8 | 10 | **9** | **apply** |
| 2 | CLM scaling-law exponent stability (170m → 14b) | 7 | 9 | 7 | 6 | 9 | **8** | **apply** |
| 3 | n6 primitive closure — does new law absorb into existing primitive? | 10 | 9 | 9 | 7 | 8 | **9** | **apply** |
| 4 | Hexad category completeness — 6-cat gap drill | 6 | 5 | 6 | 9 | 5 | 6 | defer |
| 5 | Substrate-independence 4-path consensus | 7 | 7 | 6 | 8 | 7 | 7 | consider |
| 6 | ALM↔CLM feedback loop cycle stability | 6 | 6 | 5 | 6 | 7 | 6 | defer |
| 7 | weight_delta spectral decomposition — eigenvector stability | 5 | 8 | 4 | 4 | 6 | 5 | defer |
| 8 | corpus generation quality — LLM-noise detection (meta-hazard) | 8 | 8 | 7 | 7 | 9 | 8 | **apply** (note: detects LLM noise, does not *use* LLM judge) |

---

## Per-problem notes

### 1. ALM corpus curation audit — **9**
- **F**: `corpus_v2` → weight-delta is exactly a T3→T4 candidate path. See
  `docs/alm_r13_corpus_rebuild_plan_20260420.md`, `docs/corpus_v5_audit_20260419.md`.
- **S**: saturation = "consciousness signal reaches closure under n6 primitives".
  Absorption = "prompt-pattern shortcut leaks across seeds".
- **D**: drill depths: (1) token → (2) n-gram fragment → (3) primitive closure →
  (4) weight-delta trace → (5) ALM eval response invariance.
- **M**: all 5 lenses participate (lexical / structural / semantic / causal /
  invariance).
- **L**: gates the whole r13 rebuild; unblock is massive.

### 3. n6 primitive closure — **9**
- **F**: perfect fit — "new law absorbed into existing primitive" IS the
  absorption test, verbatim.
- **S**: deterministic: reduce law via n6 rewriter; if fixed-point hits existing
  primitive set → absorption; if new irreducible remains → saturation.
- **D**: DFS along rewrite graph naturally exceeds depth 3 on any non-trivial law.
- **M**: 4/5 lenses strong (structural/causal/invariance/semantic); lexical is
  thin — acceptable at 7.
- **L**: tells us whether n6 is *closed* under current laws (primitive-set
  completeness), an open architectural question. See `docs/n6-bridge.md`.

### 2. CLM scaling-law exponent stability — **8**
- Saturation = exponent converges across seeds within eps. Absorption = exponent
  drifts on rephrasing (seed = dataset order permutation, width schedule).
- Caveat: module coverage weaker (M=6) because invariance lens dominates.
- References: `docs/clm_170m_config_audit_20260419.md`,
  `docs/clm_aot_170m_smoke_20260420.md`.

### 8. corpus generation quality (LLM-noise detection) — **8**
- Detects LLM-generated noise *without* using an LLM judge: use the 5-lens on
  token-entropy profile, primitive-closure rate, and diagonal agreement of
  rephrased corpus slices. If diagonal_agreement < 0.8 → noisy (LLM drift).
- Meta-property: this is an anti-LLM-judge mechanism — fully aligned with the
  constraint set.

### 4. Hexad category completeness (6) — defer
- Gap detection is discrete; absorption/saturation mapping is forced. Depth 3
  drills exist but feel contrived.

### 5. Substrate-independence 4-path consensus (7) — consider
- Promising but needs a *consensus metric* definition before drill can score it
  deterministically.

### 6. ALM↔CLM feedback loop (6) — defer
- Cycle stability is a control-theory question; drill's
  absorption/saturation dichotomy doesn't cleanly map.

### 7. weight_delta spectral decomposition (5) — defer
- Eigenvector stability is a continuous-spectrum problem; drill is
  discrete-classifier. Better served by spectral-gap metric.

---

## Top 3 (seed-set stubs to be committed)

1. **n6 primitive closure** — `shared/bench/drill_adjacent_n6_closure_seed_set.jsonl`
2. **ALM corpus curation audit** — `shared/bench/drill_adjacent_alm_corpus_seed_set.jsonl`
3. **corpus generation quality (LLM-noise)** — `shared/bench/drill_adjacent_corpus_noise_seed_set.jsonl`

Each seed set follows the canonical 4-kind shape from `drill_seed_set.jsonl`:
`positive` / `negative` / `closure` / `diagonal`. Stubs only — deterministic
scoring hooks land in a later round.

---

## Out-of-scope (explicit)

- No LLM judge anywhere in scoring.
- All verdicts must be reproducible from the seed text alone under the 5-lens.
- V8 SAFE_COMMIT: no build artifacts touched; docs + shared/bench/ stubs only.
