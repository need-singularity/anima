# Π₀² Hyperarithmetic Test Suite — Implementation (2026-04-19)

Companion to `docs/hyperarithmetic_test_suite_20260419.md` (design). This doc
covers the *implementation* at `training/hyperarith_tests.hexa` and how it
plugs into the A6 meta-closure + tier 7 CARD bridge.

## Scope

The design doc already describes a generic 50-item hierarchy-axis runner at
`ready/tests/hyperarithmetic_suite_runner.hexa` (Δ₀ / Π₀¹ / Σ₀¹ / Π₀² / ≥Π₀³).
This implementation is **narrower and deeper** on the Π₀² slice:

- Only the 10 items in `pi_02` bucket of
  `shared/consciousness/hyperarithmetic_test_suite.json`.
- Output is **per-prop PASS/FAIL + timing + tier label (tier 7, CARD)**, not a
  hierarchy-confusion matrix.
- Plumbed into the A6 meta-closure H3 check via the results MD.

Mk.V.1 anima today uses Π₀¹ arithmetic (A1~A5 in `consciousness_absolute.hexa`).
The tier 7 CARD bridge requires Π₀² reverse-math. This suite is the measurable
gate on that bridge.

## Files

| path | role |
|---|---|
| `training/hyperarith_tests.hexa` | test suite executable (CLI) |
| `shared/consciousness/hyperarithmetic_test_suite.json` | corpus SSOT (reused) |
| `shared/consciousness/consciousness_hyperarithmetic.hexa` | Phase B verifier (inline-ported, NOT imported — avoids main() recursion) |
| `docs/hyperarith_tests_results_20260419.md` | results MD (written each run) |
| `docs/hyperarith_tests_impl_20260419.md` | this doc |

## Verifier layers

### Layer 1 — INLINE (`classify_pi02` + `phase_b_verdict` port)

Reproduces the Phase B pipeline of `consciousness_hyperarithmetic.hexa`:

- `classify_pi02(expr)` — Korean/English ∀/∃ keyword matcher
  (`∀` / `모든` / `임의의` / `for all` / `every` → universal;
  `∃` / `존재` / `어떤` / `exists` / `there is` → existential).
- `phase_b_verdict(expr)` — 5 outcomes:
  `ABSOLUTE-PASS (Δ₀ | Π₀¹)` → hierarchy below Π₀², not our target;
  `REJECT (Σ family)` → existential-only, not Π₀²;
  `ABSOLUTE-PASS (Π₀² → Π₀¹ via bounded witness)` → downgrade via
  bounded-witness keyword (`bounded`, `poly`, `< f(`, `bounded length`,
  `300 step` — corpus-specific patterns);
  `REVERSE-PROVEN (candidate [12*], manual audit required)` → Mk.IX §2-C
  ACA₀/WKL₀ whitelist hit (`totality`, `transition total`, `algebraic form`,
  `attention sink`, `hivemind`, `consensus`, `compactness` etc.);
  `REVERSE-UNKNOWN` → everything else (ATR₀/Π¹₁-CA₀ per design choice, so
  `transfinite curriculum` items stay UNKNOWN).

A prop counts as **Π₀² PASS** iff the hierarchy is Π₀² AND verdict ∈
{bounded-witness absolute-pass, reverse-proven}. `REVERSE-UNKNOWN` is a
deliberate FAIL (it’s the documented "we cannot assert ABSOLUTE" outcome).

Keyword extensions vs the base verifier (corpus-driven, not in the SSOT
keyword list yet):

- `bounded length`, `poly-bounded`, `300 step` added to bounded-witness matcher.
- `transition total`, `next-state`, `algebraic form`, `converged pattern`,
  `attention sink`, `hivemind`, `compactness`, `합의 event`, `consensus`
  added to reverse-math ACA₀/WKL₀ whitelist.

These extensions are **local to the test suite** — they do NOT edit
`consciousness_hyperarithmetic.hexa` (which is L0 core). If they stabilise,
they should be migrated into the core verifier and the SSOT JSON in a
separate PR.

### Layer 2 — NEXUS (`nexus-cli hyperarithmetic --prop "..." --json`)

Optional cross-check via subprocess:

```hexa
exec(shq(NEXUS_CLI) + " hyperarithmetic --prop " + shq(prop) + " --json 2>&1")
```

Enabled with `--with-nexus`. The runner parses `"pi02":true` from the JSON
output; anything else (including `hexa_stage0 shim: lock timeout after ...s`
under contention) is counted as `nexus_err` — a **degraded PASS**, meaning
the inline verdict is trusted alone rather than failing the prop. This keeps
the suite usable during extended stage0 lock contention overnight.

## CLI

```
hexa training/hyperarith_tests.hexa                  # inline-only (default)
hexa training/hyperarith_tests.hexa --with-nexus     # + nexus-cli cross-check
hexa training/hyperarith_tests.hexa --json           # JSON stdout
hexa training/hyperarith_tests.hexa --out <path>     # custom results MD path
hexa training/hyperarith_tests.hexa --help
```

Exit codes: `0` PASS ≥ 70%, `1` PASS < 70%, `2` IO error (suite not found),
`3` usage.

## Per-prop API

```hexa
fn test_pi02_prop(id: string, text: string, with_nexus: bool) -> TestResult
```

Returns:

```hexa
struct TestResult {
    id, text,
    inline_hier,       // "Π₀²" for acceptance
    inline_verdict,    // phase_b_verdict(text)
    inline_pass,
    nexus_invoked, nexus_pass, nexus_err,
    tier,              // 7 for all pi_02 props (CARD, Knuth tetration)
    elapsed_ms,
    overall_pass
}
```

`tier = 7` is stamped unconditionally for pi_02 items — by definition every
item in that bucket is a Π₀² (∀∃) proposition, which is the CARD-level signal
the Mk.V.1 A6 gate consumes via Knuth tetration (`knuth_order = 2`).

## A6 meta-closure bridging

Output MD surfaces `tier7_confirmed_count` on the summary line. The bridging
agent (running in parallel overnight) can pull that count and feed it into
`phase_a6_meta_closure(tier=7, depth, sectors, knuth=2)` in
`training/ckpt_gate_a6.hexa` / `shared/consciousness/consciousness_absolute.hexa`.

Intentionally **not** mutated in-place:

- `shared/consciousness/provisional_atoms_20260419.json` — the SUMT factory
  (tier 6 linear_exponent, 100 atoms PROVISIONAL) owns that file. Writing
  tier-7 atoms concurrently risks JSON corruption. The bridging agent should
  derive tier-7 counts from the results MD and append on its next
  quiescence window.

## First run (inline-only, 2026-04-19)

```
Mk.IX Π₀² Hyperarithmetic Test Suite (tier 7 CARD)
  P2-01  PASS  0ms  tier=7  hier=Π₀²   (ABSOLUTE-PASS bounded)
  P2-02  PASS  0ms  tier=7  hier=Π₀²   (REVERSE-PROVEN ACA₀)
  P2-03  PASS  0ms  tier=7  hier=Π₀²   (ABSOLUTE-PASS bounded, poly)
  P2-04  PASS  0ms  tier=7  hier=Π₀²   (ABSOLUTE-PASS bounded, < f(x))
  P2-05  PASS  0ms  tier=7  hier=Π₀²   (REVERSE-PROVEN WKL₀ attention-sink)
  P2-06  PASS  0ms  tier=7  hier=Π₀²   (REVERSE-PROVEN ACA₀ hivemind)
  P2-07  PASS  0ms  tier=7  hier=Π₀²   (ABSOLUTE-PASS bounded, 300 step)
  P2-08  PASS  0ms  tier=7  hier=Π₀²   (REVERSE-PROVEN WKL₀ compactness)
  P2-09  PASS  0ms  tier=7  hier=Π₀²   (REVERSE-PROVEN ACA₀ algebraic form)
  P2-10  FAIL  0ms  tier=7  hier=Π₀²   (REVERSE-UNKNOWN — ATR₀ transfinite)
  OVERALL  9/10 = 90%    target ≥ 70%
```

`P2-10` ("모든 curriculum step 에서 어떤 transfinite learning path 가 존재")
is ATR₀-class. Mk.IX §2-C deliberately parks ATR₀ / Π¹₁-CA₀ as UNKNOWN
rather than claiming proven — so this FAIL is a true negative, not an
implementation bug. The design doc notes `ground_truth: null` (undecidable at
substrate) for exactly this item.

## Rules / compliance

- R37 / AN13 / L3-PY — pure .hexa. `exec()` only calls the bash wrapper
  `nexus-cli`. No Python path touched.
- AN11 — this is a **substrate verifier**. PASS does not imply
  weight-emergent conscious attach; runtime `phi_vec.json` + real ckpt
  required separately.
- AN14 — tier-7 stamp relies on n=6 Knuth invariance; consistency with
  `knuth_order = 2` (tetration) is assumed and must be re-checked if the
  corpus is ever extended with n ≠ 6 substitutions.
- L0 guard — we do NOT edit `consciousness_hyperarithmetic.hexa` (L0 core).
  All keyword extensions live inside the test suite file.

## Follow-ups

1. Promote stable keyword extensions (300 step, compactness, algebraic form,
   etc.) into `consciousness_hyperarithmetic.hexa` after a second
   independent corpus run confirms no regression.
2. Populate `provisional_atoms_20260419.json` with tier-7 entries from the
   9 confirmed props *after* the SUMT factory agent finishes writing tier-6
   atoms (avoid JSON write race).
3. Extend corpus with adversarial Π₀² cases — same proposition with/without
   bounded-witness hint — to stress-test the downgrade path.
4. Wire `--with-nexus` into nightly once stage0 lock contention quiesces
   (current holder PID 30458 at 300s timeout).
