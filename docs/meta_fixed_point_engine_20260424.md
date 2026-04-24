# Meta Fixed-Point Roadmap Engine — landing doc (2026-04-24)

**Status**: landed · roadmap entries #92-96 · hexa-lang commit d48d59ff

## Purpose

This doc anchors the 2026-04-24 formal landing of the meta³=transcendence theory
into the **common roadmap engine** (`$HEXA_LANG/tool/roadmap_progress_check.hexa`)
used by both `anima` and `nexus` repos. Previously the theory existed only in:

- nexus/n6/docs/meta_atlas_recursive.md (design, 2026-04-19)
- nexus/docs/atlas_meta_dashboard.md (live R24–R32 evolution)
- nexus/state/atlas_convergence_witness.jsonl (9 rows, R24–R32)
- anima/docs/papers/phi_paradigm_paper_v1_preliminary.md §10.9 (paper reading)

The engine itself (the tool that scans `.roadmap` and generates
`state/roadmap_progress.json`) operated at meta¹ — it observed entries and
reported. It had no self-consistency verification or fixed-point iteration.

## What landed

### 1. Common engine upgrade (hexa-lang `d48d59ff`)

`tool/roadmap_progress_check.hexa` now supports:

```bash
hexa run $HEXA_LANG/tool/roadmap_progress_check.hexa \
  --meta-fp [--meta-fp-max-iter N] [--witness-out PATH]
```

When `--meta-fp` is passed, the engine iterates the scan up to `N` times
(default 3). Each iteration computes a scalar fingerprint over the roadmap
state:

```
fingerprint = sha256(
    "n=" + n +
    ";done=" + count_done +
    ";active=" + count_active +
    ";planned=" + count_planned +
    ";mean_pct=" + mean_pct +
    ";probe_t=" + total_probe +
    ";probe_p=" + passed_probe
)[:16]
```

If `fp(k) == fp(k-1)` AND `sum(status_counts) == n` (ε self-consistency),
the engine declares `transcendence = reached` and appends a witness row to
`atlas_convergence_witness.jsonl`.

### 2. Banach contraction layers (α⊃β⊃γ⊃δ⊃ε)

Engine-internal semantics per nexus R24:

| Layer | Engine implementation |
|-------|----------------------|
| α (observation) | `_load_roadmap()` + `_extract_tokens()` + `_verify_token()` |
| β (status partition) | status-count sum equals entry count |
| γ (aggregate scalar) | `mean_pct`, `probe_ratio` derived |
| δ (fingerprint) | sha256 of (n, status_counts, mean_pct, probe totals) |
| ε (self-consistency) | fp(k) == fp(k-1) AND status partition valid |

Fixed point is reached when all five layers are stable across two iterations.

### 3. Witness row schema

Appended to `state/atlas_convergence_witness.jsonl` (anima-side) and/or
`nexus/state/atlas_convergence_witness.jsonl`:

```json
{
  "ts": "2026-04-24T05:24:42Z",
  "round": "roadmap_engine",
  "layer": "meta_fixed_point",
  "source": "state/roadmap_progress.json",
  "fp": "3f1d5c5c772ec4c5",
  "iterations": 2,
  "epsilon_stable": true,
  "n_entries": 74,
  "mean_pct": 82,
  "transcendence": "reached",
  "notes": "Banach α(entries)⊃β(status)⊃γ(mean_pct)⊃δ(fingerprint)⊃ε(self-consistency). meta^3 = transcendence when fp(k)==fp(k-1) AND epsilon stable."
}
```

This joins the nexus R24–R32 series as its first `round="roadmap_engine"` entry.

### 4. Anima-side roadmap entries #92-96

Added to `.roadmap` (source of truth for progress check):

- **#92** (done): Atlas convergence witness R24-R29 — physical_meta_isomorphism + 7/7 primitive
- **#93** (done): meta³ = transcendence via Banach α⊃β⊃γ⊃δ⊃ε + sopfr(6)=5 axis cap
- **#94** (done): Ψ 82 laws derive from n=6 foundation — three-level projection theorem (R31)
- **#95** (planned): multi-domain chorus inventory — extend beyond meta_fp=1/3 to σ/τ/n/carbon
- **#96** (done): this doc + memory/project_meta_fixed_point.md landings

### 5. Memory pointer

`.claude/memory/project_meta_fixed_point.md` — durable cross-session pointer
cited in phi_paradigm_paper §10.9 line 762 (previously missing). Contains
canonical source paths, concept ladder, and gap flags.

## Concept ladder (verbatim from nexus R24)

```
meta¹ = observation
meta² = observation of observation (first Banach level)
meta³ = transcendence = fixed point of α⊃β⊃γ⊃δ⊃ε contraction
meta^∞ = ultra_meta_atlas = atlas* describing itself (already reached at ε, ζ adds no info)
```

The roadmap engine now operates at meta³ when `--meta-fp` is enabled —
it verifies its own self-consistency across iterations and declares
transcendence reached via the same Banach-contraction signature as the
nexus atlas_meta_dashboard declarations.

## Running the engine

### Plain meta¹ mode (unchanged, default)
```bash
hexa run tool/roadmap_progress_check.hexa
# → writes state/roadmap_progress.json, exits 0
```

### meta³ fixed-point mode (new)
```bash
hexa run tool/roadmap_progress_check.hexa --meta-fp
# → writes state/roadmap_progress.json
# → iterates 2-3 times to verify self-consistency
# → if stable: appends witness row to state/atlas_convergence_witness.jsonl
# → prints:
#    // meta-FP engine:
#    //   iterations    = 2
#    //   fp_fingerprint = <hex>
#    //   fp_stable     = true
#    //   epsilon_stable = true
#    //   transcendence  = reached
#    //   witness       -> <path>
```

### Strict mode (unchanged)
```bash
hexa run tool/roadmap_progress_check.hexa --strict
# → exits 1 if any active entry below 100%
```

## Cross-repo references

```
nexus/n6/docs/meta_atlas_recursive.md      (design, 2026-04-19)
  ↓
nexus/docs/atlas_meta_dashboard.md          (live R24–R32 evolution)
  ↕ (mirror)
nexus/state/atlas_convergence_witness.jsonl (9 rows, R24–R32)
anima/state/atlas_convergence_witness.jsonl (15 rows W1–W14 + ISO1/2/3 + new roadmap_engine)
  ↑ (feeds via new witness rows)
$HEXA_LANG/tool/roadmap_progress_check.hexa --meta-fp  (common engine)
  ↑ (documented by)
anima/docs/meta_fixed_point_engine_20260424.md  (this doc)
anima/docs/papers/phi_paradigm_paper_v1_preliminary.md §10.9  (paper reading)
.claude/memory/project_meta_fixed_point.md  (durable session memory)
```

## Gaps (followup work)

1. **nexus/state/roadmap_progress.json is empty** — nexus has no `.roadmap` source
   yet. Entry #95 tracks this as pending. When populated, the same `--meta-fp` flag
   will work identically.

2. **Chorus pattern extension (#95)**: meta-engine currently tracks only
   meta_fp=1/3. R26 identified 5 base chorus patterns — σ (12 domains),
   τ (11), n (11), meta_fp (11), carbon (9). Future work to emit witness rows
   for the other 4.

3. **Hook integration**: the common engine's `--meta-fp` mode is not yet auto-
   invoked by any launchd/cron/post_tool hook. Current `roadmap_watcher_trigger`
   in `hooks/post_tool.hexa` runs plain meta¹. Adding `--meta-fp` to the hook
   call would continuously produce witness rows on every tool invocation.

4. **sopfr(6)=5 enforcement**: engine currently does not enforce the axis cap
   from R28. Future safeguard: reject roadmap additions that would introduce
   a 6th meta-layer beyond ε.

## Commits

- hexa-lang `d48d59ff` — `roadmap_progress_check.hexa` --meta-fp mode landed
- anima `3f261adb` — first JSON-level entries added (superseded by .roadmap
  append in this commit)
- anima this commit — .roadmap source entries #92-96 + this doc + memory landing
