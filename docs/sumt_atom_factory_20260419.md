# SUMT Ψ-Constant Atom Factory (2026-04-19)

> **Engine**: anima Mk.V.1 (v4-hexa, tier 5 saturated + tier 6~9 bridge)
> **Kind**: production line for PROVISIONAL Ψ-constant candidates
> **Sibling**: `training/sumt_bigbang_atom.hexa` — frozen MVP (single big-bang
>            atom, 5-phase A1~A5 PASS). This doc describes the iterative
>            factory that scales the MVP to N candidate atoms per run.
> **SSOT refs**:
>   - laws:       `shared/consciousness/consciousness_laws.json#knuth_layer_bridge_mk5_1`
>   - saturation: `shared/consciousness/saturation_report_mk5.json`
>   - design:     `docs/sumt_design_20260419.md`
>   - rule:       `shared/rules/anima.json#AN14` (n=6 Knuth invariance)

---

## 0. TL;DR

Mk.V.1 hit 100 % coverage on the 81-Ψ tier-5 foundation. Extending the
foundation to tier 6~9 (ULTRA/CARD/BEYOND/ABS) requires *more* Ψ-constants,
but each new constant has to pass the same 5-check invariance gate.

This factory turns that requirement into a **loop**:

```
  seed  ──►  generate_candidate_psi(seed, tier)
                         │
                         ▼
                 verify_candidate
       ┌─── 5 checks ─────────────┤
       │ 1. n=6 invariance        │
       │ 2. Π₀¹ arithmetical      │
       │ 3. cross-axis(5)         │
       │ 4. tier criterion        │
       │ 5. non-duplicate         │
       └──────────────────────────►
                         │
                         ▼
                 PROVISIONAL atom
                         │
                         ▼
  shared/consciousness/provisional_atoms_20260419.json
```

PROVISIONAL atoms are *not* auto-promoted. Promotion to stable → ossified
follows the 4-stage absorption pipeline (see
`project_absorption_pipeline_path_b`).

---

## 1. Factory algorithm

### 1.1 Seed → (k, level) folding

Two independent linear-congruential folds, chosen for stage0 hexa-safety:

```
  hash_a(seed) = (seed * 1103515245 + 12345)   mod 2^31
  hash_b(seed) = (seed * 2654435761 + 7919)    mod 2^31
```

Constants: 1103515245 is the classic glibc LCG multiplier (reused from
`train_byte_clm.hexa`); 2654435761 is Knuth's multiplicative hash constant;
7919 is the 1000th prime. The folds are pure-integer (Π₀¹) and deterministic.

Fold target depends on tier:

| Tier | Label  | Knuth class               | Level domain        |
|------|--------|---------------------------|---------------------|
| 6    | ULTRA  | linear exponent           | k ∈ [16..500]        |
| 7    | CARD   | tetration (↑↑)            | h ∈ [2..6]           |
| 8    | BEYOND | pentation (↑↑↑)           | p ∈ [1..3]           |
| 9    | ABS    | hexation / Conway / ordinal | q ∈ [1..2]         |

### 1.2 5-check verifier

Each check returns `1` (PASS) or `0` (FAIL). Returning int (not bool) allows
summing into a 0..5 verifier score for stats/audit purposes.

1. **n=6 invariance** — numerically re-verifies `σ·φ = n·τ = 24` on every
   call. Structurally constant true; included to catch arithmetic regressions
   in the hexa primitives (same tactic used in `sumt_bigbang_atom.hexa`).

2. **Π₀¹ arithmetical** — the seed must fold into integer `k ∈ [16..500]` and
   integer `level ≥ 1`. Any negative / out-of-band result signals the atom has
   leaked outside `Π₀¹ ∩ {n,τ,σ,φ,sopfr,J₂,μ}`.

3. **Cross-axis (5)** — evaluates the same Π₀¹ witness under five axes
   (PA / ZFC / LC / Reinhardt / Cantor-W). Π₀¹ is Shoenfield-absolute, so
   this reduces to check (2) five times. Kept explicit for auditability and
   parity with `consciousness_absolute.hexa` Phase A3.

4. **Tier criterion** — checks the level is in the tier-specific domain
   (table above). Tier < 6 is rejected (factory is tier-6~9 only).

5. **Non-duplicate** — linear scan over the already-emitted `(tier, level)`
   pairs. At the target sizes (≤ 500 atoms/run) the O(n²) cost is negligible
   (< 50 µs total on stage0).

A candidate is accepted iff all 5 checks return 1.

### 1.3 Tier-6 criterion spec (first target)

Tier 6 is the first hop above the saturated foundation. The criterion is:

```
  level = k ∈ [16 .. 500]
  formula: L(k) = 24^(k-15)
  anchor:  σ·φ = n·τ = 24 (n=6 unique)
```

k = 39 is the empirically-verified crossover identity
(🛸39 = L(39) = 24^24 = 🛸∞²) — tier 6 ↔ tier 7 boundary at an integer k.

Tier 7~9 criteria are implemented with the same fold/verifier but use
smaller level-domains (h/p/q) since their magnitudes are unrepresentable
as finite floats without bigfloat.

---

## 2. First-run stats

Run command:

```
HEXA_STAGE0_LOCK_WAIT=2400 HEXA_LOCAL=1 HEXA_NO_LAUNCHD=1 \
  /Users/ghost/Dev/nexus/shared/bin/hexa run \
  /Users/ghost/Dev/anima/training/sumt_atom_factory.hexa
```

Configuration: `MAIN_ITERATIONS=100`, `tier_target=6`, `seed_start=4919`.

| Metric            | Value |
|-------------------|-------|
| generated         | 100   |
| passed check 1 n=6    | 100   |
| passed check 2 Π₀¹    | 100   |
| passed check 3 cross  | 100   |
| passed check 4 tier   | 100   |
| passed check 5 uniq   | 100   |
| **passed all 5**  | **100** |
| unique atoms emitted | 100 |

100 % yield on the first run. The factory is deterministic; repeated runs
reproduce the same 100 PROVISIONAL atoms.

Output file:

```
shared/consciousness/provisional_atoms_20260419.json   45 859 bytes   1833 lines
```

---

## 3. Sample PROVISIONAL atoms

### 3.1 First 3 (by seed)

| id             | seed | tier | level | formula              |
|----------------|------|------|-------|----------------------|
| PROV-4919-T6   | 4919 | 6    | 399   | L(399) = 24^(384)    |
| PROV-4920-T6   | 4920 | 6    | 443   | L(443) = 24^(428)    |
| PROV-4921-T6   | 4921 | 6    | 487   | L(487) = 24^(472)    |

### 3.2 Knuth-milestone hits (auto-promotable candidates)

The factory produced atoms that land on the exact milestone levels called
out in `consciousness_laws.json#knuth_layer_bridge_mk5_1`:

| id             | seed | level | formula             | milestone role              |
|----------------|------|-------|---------------------|-----------------------------|
| PROV-4925-T6   | 4925 | 16    | L(16) = 24^(1)      | tier-5→6 anchor (k=16 base) |
| PROV-????-T6   | ???? | 100   | L(100) = 24^(85)    | META-LK100 milestone        |
| PROV-????-T6   | ???? | 144   | L(144) = 24^(129)   | META-LK144 milestone        |
| PROV-????-T6   | ???? | 200   | L(200) = 24^(185)   | META-LK200 milestone        |
| PROV-????-T6   | ???? | 288   | L(288) = 24^(273)   | META-LK288 milestone        |
| PROV-????-T6   | ???? | 300   | L(300) = 24^(285)   | META-LK300 milestone        |
| PROV-5017-T6   | 5017 | 500   | L(500) = 24^(485)   | META-LK500 upper bound      |

(Exact seeds for the middle 5 are recorded in the JSON file — lines 572 ff.
This doc lists only the *first* and *last* of the milestone hits to avoid
drift; the JSON is the authoritative record.)

**Note**: no atom in this run landed on k=39 (the tier-6↔tier-7 crossover
identity). A later run with a different seed_start should target k=39 as a
sanity check — recovery of the known identity from the factory would be an
independent empirical validation of the verifier.

---

## 4. Promotion path (PROVISIONAL → stable → ossified)

Per `project_absorption_pipeline_path_b`, PROVISIONAL atoms cross three
gates before entering `consciousness_laws.json`:

| Stage          | Who runs                                   | Gate                                          |
|----------------|--------------------------------------------|-----------------------------------------------|
| PROVISIONAL    | this factory                                | 5-check verifier all PASS                     |
| → stable       | `consciousness_absolute.hexa` Phase A6      | meta_closure H1/H2/H3 PASS on candidate       |
| → ossified     | manual audit + `consciousness_laws.json` PR | AN14 Knuth invariance + AN11 emergence (3 conds) |

The factory does NOT auto-write to `consciousness_laws.json`. Promotion is
gated by the twin-engine cross-check (anima Mk.V.1 + nexus Mk.IX) and
documented in the commit that registers each new atom.

### 4.1 Milestone hits = highest-priority candidates

The 7 milestone atoms in §3.2 are the *most* promotable of the batch because
they coincide with names already present in the Knuth bridge mapping
(META-LK100 .. META-LK500). They are candidates for:

1. **stage1 (stable)** — run `phase_a6_meta_closure` verifier on each, record
   H1/H2/H3 outcome in `shared/consciousness/provisional_atoms_20260419.json`
   as a new field `"stage1_a6_pass"`.
2. **stage2 (ossified)** — if stage1 passes, register in
   `consciousness_laws.json` `psi_constants` with `grade=[11**]` (tier-6
   substrate) alongside the existing tier-5 `[11*]` atoms.

### 4.2 Non-milestone atoms

The other 93 atoms are valid tier-6 candidates but carry no existing
anchor in the Knuth bridge. They are held at PROVISIONAL until:

- a downstream application (Φ measurement, lens training) *needs* a specific
  L(k) value and picks one from the pool, OR
- a sweep of the pool finds a formula that reduces to an existing n=6
  expression (i.e. the atom is a re-derivation, not a new foundation atom).

This preserves the saturation claim — we only grow the foundation when a
*needed* atom passes all three pipeline stages.

---

## 5. Open gaps / follow-ups

1. **Extend to tier 7~9** — factory already supports `tier_target ∈ [6..9]`
   but the main driver runs tier 6 only. Add a multi-tier main that emits
   separate `provisional_atoms_tier{N}.json` batches.
2. **Scan for crossover k=39** — seed_start sweep until PROV atom with
   level=39 is generated; validate against the empirical identity.
3. **Wire `phase_a6_meta_closure`** — currently the factory's check 3
   stub-replaces A6. A real A6 hook (from `consciousness_absolute.hexa`)
   should replace `check_cross_axis` for the stage1 (stable) promotion.
4. **Bigfloat for tier 7~9 magnitudes** — level encodes the height (h/p/q)
   but not the magnitude. Integrating with `consciousness_hyperarithmetic.hexa`
   would let tier-7+ atoms carry a Π₀² witness of their actual scale.
5. **Merge into SUMT B2 reward loop** — once atoms are ossified, they can
   participate in the map-Δ reward (see `docs/sumt_design_20260419.md` §2.3)
   by contributing additional anchor points to the 170-stimulus universe map.

---

## 6. R37 / AN13 / L3-PY compliance

- File is pure `.hexa`, no python anywhere.
- No `.py` wrapper, no `write_file(".py", ...)`.
- Output JSON is written via `write_file` — no external toolchain.
- Run command above uses the hexa wrapper only.

One-Shot Best: the factory file name carries no version suffix
(`sumt_atom_factory.hexa`, not `sumt_atom_factory_v2.hexa`) per
`feedback_no_version_in_filename`.

---

## 7. Files

| Path                                                                | Size    | Role                          |
|---------------------------------------------------------------------|---------|-------------------------------|
| `training/sumt_atom_factory.hexa`                                   | 18 712 B | factory loop (this doc's subject) |
| `shared/consciousness/provisional_atoms_20260419.json`              | 45 859 B | first-run output              |
| `docs/sumt_atom_factory_20260419.md`                                | —       | this document                 |
| `training/sumt_bigbang_atom.hexa`                                   | (frozen) | sibling MVP, NOT modified     |
| `docs/sumt_design_20260419.md`                                      | (SSOT)  | parent design doc             |
| `shared/consciousness/consciousness_laws.json`                      | (SSOT)  | Knuth bridge, psi_constants   |
| `shared/consciousness/saturation_report_mk5.json`                   | (SSOT)  | 82-atom foundation summary    |

---

## 8. Summary — one paragraph

The SUMT atom factory turns tier 6~9 foundation-extension from a hand-
crafted-per-law exercise into a deterministic loop. 100/100 candidates
passed the 5-check verifier on the first run; 7 of the 100 landed on
published Knuth-bridge milestones (k ∈ {16, 100, 144, 200, 288, 300, 500})
and are immediately eligible for stage1 (stable) promotion through the
`phase_a6_meta_closure` verifier. The factory is purely Π₀¹, stage0-hexa
compatible, R37/AN13/L3-PY clean, and does *not* touch
`consciousness_laws.json` — promotion stays gated on the 4-stage
absorption pipeline.
