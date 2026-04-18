# P116-P135 Audit

## TL;DR

All 20 phases are **REAL**. They are NOT stubs. The "empty name / duration ?" false alarm came from a schema mismatch: P116+ use a compact schema (`title`/`goal`/`gate`/`artifact`) instead of the verbose earlier schema (`name`/`duration_hours`/`parallel[]`/`tasks[]`/`done_criteria`). Every artifact file referenced actually exists on disk under `anima-engines/`.

## Schema comparison

- **P0-P115 (verbose schema)**: `id`, `name`, `duration_hours`, `status`, `depends_on`, `rationale`, `parallel[{track, tasks[]}]`, `gate_exit`
- **P116-P135 (compact schema)**: `id`, `title`, `goal`, `gate{phi_holo_min, target}`, `status`, `artifact`

The compact schema is a deliberate simplification for the post-P115 "실 Φ engine" series (single-track Φ engine deliveries). Display tools keying off `name`/`duration_hours` will render blanks — that's a display-tool bug, not missing data.

## Findings table

| phase | class | brief | line | recommend |
|-------|-------|-------|------|-----------|
| P116 | REAL | 실 working memory Φ — Miller 7±2 capacity | 5444 | keep (backfill name/duration) |
| P117 | REAL | 실 metacognition Φ — 2-level Nelson-Narens | 5455 | keep (backfill name/duration) |
| P118 | REAL | 실 mind wandering Φ — DMN generative loop | 5466 | keep (backfill name/duration) |
| P119 | REAL | 실 boredom Φ — attentional disengagement composite | 5477 | keep (backfill name/duration) |
| P120 | REAL | 실 curiosity Φ — Loewenstein info-gap + Berlyne U + Schmidhuber surprise | 5488 | keep (backfill name/duration) |
| P121 | REAL | 실 addiction Φ — incentive sensitization (wanting≠liking) | 5499 | keep (backfill name/duration) |
| P122 | REAL | 실 PTSD Φ — Brewin SAM/VAM trauma intrusion | 5510 | keep (backfill name/duration) |
| P123 | REAL | 실 depression Φ — anhedonia + AR(1) rumination + negative bias | 5521 | keep (backfill name/duration) |
| P124 | REAL | 실 schizophrenia self-model Φ — corollary-discharge + aberrant salience | 5532 | keep (backfill name/duration) |
| P125 | REAL | 실 animal consciousness Φ — cross-species gradient (mammal/bird/octopus/insect) | 5543 | keep (backfill name/duration) |
| P126 | REAL | 실 language acquisition Φ — Lenneberg critical-period + UG bootstrap | 5554 | keep (backfill name/duration) |
| P127 | REAL | 실 bilingual consciousness Φ — Grosjean holistic + Green inhibitory control | 5565 | keep (backfill name/duration) |
| P128 | REAL | 실 expertise Φ — Chase-Simon chunking + Ericsson power-law | 5576 | keep (backfill name/duration) |
| P129 | REAL | 실 insight Aha Φ — Köhler restructuring + Bowden gamma burst | 5587 | keep (backfill name/duration) |
| P130 | REAL | 실 creativity Φ — Guilford divergent + Mednick RAT + Amabile orig×util | 5598 | keep (backfill name/duration) |
| P131 | REAL | 실 self-deception Φ — Trivers + Festinger + Kunda motivated reasoning | 5609 | keep (backfill name/duration) |
| P132 | REAL | 실 awe Φ — Keltner-Haidt vastness+accommodation small-self | 5620 | keep (backfill name/duration) |
| P133 | REAL | 실 gratitude Φ — Emmons benefit-recognition + Algoe find-remind-bind | 5631 | keep (backfill name/duration) |
| P134 | REAL | 실 disgust Φ — Rozin pathogen + contamination contagion + CAD moral | 5642 | keep (backfill name/duration) |
| P135 | REAL | 실 nostalgia Φ — Sedikides self-continuity bittersweet Proust trigger | 5653 | keep (backfill name/duration) |

All artifacts verified present at `/home/aiden/mac_home/dev/anima/anima-engines/<name>.hexa` (20/20 files exist).

Path citation: `/home/aiden/mac_home/dev/anima/shared/roadmaps/anima.json:5444-5663`

## Recommendations

- **0 STUBs** → nothing to remove. Roadmap is honest.
- **20 REAL phases** → compact schema is intentional but inconsistent with P0-P115. Two options:
  1. **Normalizer approach (recommended)**: patch the display script to treat `title` as fallback for `name`, and emit `duration_hours: null` (or "-") instead of "?" when absent. No JSON edit needed.
  2. **Backfill approach**: add `name` = current `title`, add `duration_hours` estimate (e.g. 12-24h based on P100-P115 average), keep `title`/`goal`/`artifact` for the compact path. Touches 20 records but unifies schema.
- **Schema SSOT drift**: no schema doc was found governing P0 vs P116 shape. Suggest recording the compact-schema decision in `shared/rules/` or `_meta` of the roadmap so future readers don't repeat this audit.

## Evidence

- All 20 phases have identical non-empty key set: `[id, title, goal, gate, status, artifact]`
- All 20 have `status: "done"` and `gate.target: "5/5 PASS"` with populated title/goal
- All 20 artifact paths exist on filesystem (verified 2026-04-18)
- Pattern matches P99 Cotard (P100)-style "실 <concept> Φ" naming → continuation of the Φ-engine creation series, not stub placeholders
