# drill_breakthrough Minimal-Surface Angle — 2026-04-21

**Scope:** design analysis only. Target: minimize LoC/deps/concepts of
`tool/drill_breakthrough_runner.hexa` while preserving the operational
meaning of "T3 85% -> T4 95% breakthrough" decidability.

**SSOT inputs:**
- `tool/drill_breakthrough_runner.hexa` (stub, exit 2 — 38 LoC)
- `shared/bench/drill_breakthrough_criteria.json` (thresholds — 20 LoC)
- `shared/bench/drill_seed_set.jsonl` (4 seeds: positive / negative / closure / diagonal)

**Constraint:** deterministic only (no LLM judge). Certificate JSON written
to `shared/state/{dest}_r{N}_drill_breakthrough.json`.

---

## 1. Current (full-surface) complexity

Per `criteria.json` `substrate`: **"5-module lens + DFS depth>=3 + absorption/saturation auto-classify"**.

| Axis        | Item                                | Cost (est.) |
|-------------|-------------------------------------|-------------|
| modules     | 5 lenses (ALM/CLM/EEG/physics/body) | 5 visitors  |
| graph       | DFS depth>=3                        | recursion + visited-set |
| classify    | absorption vs saturation automaton  | 2-state FSA × edge weight |
| seeds       | 4 kinds (pos/neg/closure/diagonal)  | 4 fixtures  |
| thresholds  | absorption_max + saturation + depth_min + coverage + diagonal_agreement | 5 dials |

**Full-surface LoC estimate (if realized):** ~380 LoC hexa.
- 5-module visitor dispatch: ~80
- DFS depth>=3 with visited-set: ~60
- absorption/saturation FSA: ~70
- seed loader (JSONL, 4 kinds): ~40
- threshold eval + cert JSON write: ~80
- arg parse + I/O plumbing: ~50

**Deps (semantic):** 5 (modules) + DFS (graph) + FSA (classify) + 5-dial thresholds + JSONL parser + cert-write = **6 concept clusters**.

---

## 2. Reduction options

### Option A — closure-only (single-module)
**Sacrifice:** 5/5 module coverage. Only ask "did the seed produce a
closure token in the fixpoint test"? The 5-lens diagonal becomes a
single projection.

- **LoC:** ~60
- **Deps:** 1 (closure) + seed loader
- **Pros:** matches P5 precedent (v2==v3 idempotence is closure).
- **Cons:** silently drops `module_coverage: 5/5` guarantee —
  idiosyncratic-domain pass becomes invisible.
- **Ratio:** **6.3x shrink**, but breaks one criterion.

### Option B — fixpoint-as-absorption (P5 pattern)
Replace the absorption/saturation automaton with a fixpoint iteration:
run the seed through the judge twice; if `out₁ == out₂` (byte-level),
declare **saturation**; else **absorption**. This is the same trick
`fixpoint_v3_v4.hexa` uses for compiler self-host.

- **LoC:** ~45 (replaces 70 of FSA)
- **Deps:** 1 (byte-eq), no FSA, no edge weights.
- **Pros:** zero new concept — reuses P5 closure idiom battle-tested
  in `tool/fixpoint_v3_v4.hexa`, `verify_fixpoint.hexa`, `meta2_verify.hexa`.
- **Cons:** loses `absorption_rate_max: 0.3` granularity (binary vs
  ratio). Mitigation: run N seeds, compute rate = (non-fixpoint)/N.
- **Ratio:** **1.5x on this axis**, preserves semantic.

### Option C — 1-pass iter instead of DFS
Replace DFS depth>=3 with a 3-step linear unroll: `step1 = judge(seed);
step2 = judge(step1); step3 = judge(step2)`. Saturation iff
`step2 == step3`. Depth is now a constant, not a graph property.

- **LoC:** ~20 (replaces 60 of DFS + visited-set)
- **Deps:** zero graph primitives.
- **Pros:** trivially deterministic, no stack, no cycle detection.
- **Cons:** drops branching evidence — DFS depth>=3 was meant to
  **falsify** deep structure, 1-pass cannot falsify width.
- **Ratio:** **3x on graph axis**, loses width-falsification.

### Option D — 2-seed minimum (pos+neg only)
Drop `closure` and `diagonal` seeds. Rationale: `closure` duplicates
the fixpoint test itself; `diagonal` is a robustness check that
`diagonal_agreement_min: 0.8` encodes — but with 1 positive seed, there
is nothing to rephrase against.

- **LoC:** -10 (seed loader simpler, no `diagonal_agreement` math)
- **Deps:** no change in kind, but threshold count 5 -> 3.
- **Pros:** covers the only two decisions that matter (does positive
  pass? does negative fail?).
- **Cons:** loses idiosyncrasy guard (`diagonal_agreement`) and
  self-witness (`closure`).
- **Ratio:** **1.2x**, acceptable trade if paired with Option B fixpoint
  (fixpoint itself witnesses closure).

### Option E — JSONL-as-hexa-literal
Inline the 2 remaining seeds as a hexa array literal. Remove JSONL
parser entirely. Criteria likewise inlined as 3 constants.

- **LoC:** -30 (no JSONL parser, no criteria file read)
- **Deps:** -2 (no parser, no file I/O for config)
- **Pros:** eliminates a whole subsystem (text parsing).
- **Cons:** threshold changes now require source edit — but thresholds
  rarely change (they are operational invariants, not tunables).
- **Ratio:** ~1.4x, removes the JSONL concept cluster.

---

## 3. Recommended minimum (composition B+C+D+E)

**Stack:** fixpoint-as-absorption (B) + 1-pass iter (C) + 2-seed
(D) + inline literals (E).

**Sacrifice (explicit):**
1. No 5-module dispatch. Saturation is measured on the **aggregate**
   judge output, not per-lens. (Coverage becomes an assertion of the
   judge's own internal breadth, not a runtime check.)
2. No DFS-width falsification. Only depth-3 linear unroll.
3. No `diagonal_agreement` — relies on fixpoint self-witness instead.
4. No JSONL parsing — 2 seeds hardcoded.

**Preserved (operational meaning):**
1. T3->T4 breakthrough ≡ "positive seed fixpoints AND negative seed
   does NOT fixpoint under the same 3-step unroll".
2. Deterministic (no LLM).
3. Certificate JSON unchanged in shape — downstream consumers
   (shared/state readers) untouched.

**Target LoC:** **~70 LoC hexa** (vs ~380 full-surface).
**Ratio:** **~5.4x shrink**, **6 concept clusters -> 2** (fixpoint + cert-write).

**Failure modes this accepts:**
- False-positive if an idiosyncratic seed fixpoints for trivial reasons
  (mitigated: negative seed MUST diverge — it is the structural
  oracle).
- No early-warning on module-specific regressions — relegated to a
  separate `drill_module_coverage.hexa` verifier (future, orthogonal).

---

## 4. Prototype

See `tool/drill_minsurface_proto.hexa` — ~70 LoC, core logic only,
not wired to a real judge (illustrative).

## 5. Escape hatch

If the 5-module coverage turns out to be load-bearing operationally,
Option A+B+E (keeping 5-module dispatch but dropping DFS + JSONL)
lands at ~180 LoC (**2.1x shrink**) — still meaningful, semantically
complete.
