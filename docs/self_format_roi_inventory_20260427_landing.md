# Self-Format Family ROI Inventory — Omega-Saturation Cycle Landing (2026-04-27)

**Cycle topic:** ROI prioritization for the 12-member self-format family (`.raw` / `.own` / `.roadmap` / `.ext` / `.guide` / `.workspace` / `.turn` / `.end` / `.meta` / `.command` / `.chain` / `HXC` / `.convergence`) covering migration, tooling-gap closure, and cross-repo propagation.

**Trigger:** User directive 2026-04-28 (Korean preserved verbatim) — `자체양식 반영 ROI 목록 서브에이전트 kick`. Cumulative directives: `raw level 허용`, `hexa-lang 개선가능 kick`, `keep going kick`. raw 105 ai-cli-kick-autonomous + raw 100 line 2423 kick-infra-fallback engaged after 9/9 nexus kick FAIL session-cumulative.

**Witness JSON:** `/Users/ghost/core/anima/state/design_strategy_trawl/2026-04-27_self_format_roi_inventory_omega_cycle.json`

---

## 1. Family Inventory (12 Self-Formats)

| Format | Role | Hive Lines | Lint Tool | Lint Status | Cross-Repo Reach |
|---|---|---|---|---|---|
| `.raw` | universal rules SSOT (raw 2 grammar) | 4077 | `raw_cli.hexa#verify` | live | hive + hexa-lang + nexus + n6 (anima absorbed-to-`.own`, airgenome absent) |
| `.own` | project-local rules | 31 | `own_lint.hexa` (hexa-lang) | live | hive + hexa-lang(46L) + anima(181L) + nexus(120L) + n6(319L); airgenome absent |
| `.roadmap` | timeline ledger / P-version system | 1739 | `roadmap_multi_goal_lint` + `roadmap_progress_check` | live | all 6 super-bundle repos covered |
| `.ext` | external resource SSOT (raw 14) | 121 | `ext_lint.hexa` (hexa-lang) | live | hive + nexus + n6 only — anima / hexa-lang / airgenome MISSING |
| `.guide` | cold-entry navigation (raw 0 triad) | 77 | `guide_lint.hexa` | live | hive + nexus only — anima / hexa-lang / airgenome / n6 MISSING |
| `.workspace` | super-bundle topology (raw 14) | 213 | `workspace_sync.hexa` | live | single instance at `/Users/ghost/core/.workspace` (canonical) |
| `.turn` | per-turn policy (raw 89, FORWARD-SPEC) | 66 | `turn_lint.hexa` | live (impl ramp) | hive-only (5 sister repos absent) |
| `.end` | META-composition (raw 90, FORWARD-SPEC) | 77 | `end_composition_check.hexa` | live | hive-only (5 sister repos absent) |
| `.meta` | engine surface (raw 43) | 209 | `meta_lint.hexa` | live | hive-only |
| `.command` | engine surface (raw 43) | 405 | `command_lint.hexa` | live | hive-only |
| `.chain` | engine surface (raw 43) | **0 — ABSENT** | **MISSING** | **MISSING** | **NO repo has `.chain`; raw 43 7-engine completeness violated** |
| `HXC` | wire/storage canonical (raw 92) | spec 141L | `hxc_lint` + `hxc_convert` + `hxc_pilot` | live (90d ramp from 2026-04-27) | hive only (3 sample witnesses); 5 sister repos in 90d migration window |
| `.convergence` | super-bundle timeline events | 58 (hive) | implicit (no dedicated lint) | implicit | super-bundle-root + hive + airgenome + nexus(5 streams); anima / hexa-lang / n6 absent |

---

## 2. Measured Evidence (raw 91 Honest Baseline)

- HXC saving: **27.7%** on JSONL with schema repetition (Pilot B 2026-04-26, 8 rows × 2 schemas, 3002B → 2171B).
- HXC saving: **0.25%** on already-canonical `.raw` (no-op — correctly OUT OF SCOPE per raw 92 header).
- HXC small-N edge case: **negative saving** on 3-row fixture (header overhead > schema-repetition saving). Preserved as counter-evidence per raw 106 multi-realizability.
- raw 95 organic compliance: **2/84 = 2.4%** baseline; D+2 of D+30 falsifier window; 60% target.
- Kick infrastructure: **9/9 FAIL** session-cumulative (rc=3 docker port-bind / rc=0 ai_err_exit witness-not-captured / rc=76 container-no-node). raw 100 line 2422 falsifier 0.20-threshold breached at session level (5x).
- Anima JSONL ledgers: **30 files**, top 5 by size = `alm_r13_4gate_pass_subset.jsonl 960K` / `corpus_tier_tier1_low.jsonl 956K` / `atlas_convergence_witness.jsonl 148K` / `asset_archive_log.jsonl 36K` / `log_rotation_zstd_log.jsonl 12K`.
- Nexus kick witnesses: **124 files** at `/Users/ghost/core/nexus/design/kick/` — single-schema dominance, highest cross-repo HXC migration volume.
- Anima cycle-JSON corpus: **5 files**, 16-40KB each, schema=`omega_cycle.witness_v1` universal — high HXC ROI candidate.

---

## 3. ROI Matrix — Top 10 High-ROI Items

| Rank | ID | Format | Target | Tier | Expected Saving | Cost (h) | Disposition |
|---|---|---|---|---|---|---|---|
| 1 | T-A-1 | HXC | anima/state/design_strategy_trawl/*.json (5 files, 152KB) | A | 28% / ~42KB | 1.5 | autonomous |
| 2 | T-A-2 | HXC | nexus/design/kick/*.json (124 files) | A | 27% | 3.0 | autonomous |
| 3 | T-B-1 | `.chain` ADD-new | hive `.chain` SSOT + `chain_lint.hexa` | B-pending | correctness | 4.0 | pending-review |
| 4 | T-A-3a | `.guide` | anima/.guide creation | A | cold-entry win | 0.5 | autonomous |
| 5 | T-A-3b | `.guide` | hexa-lang/.guide creation | A | cold-entry win | 0.5 | autonomous |
| 6 | T-A-4a | `.ext` | anima/.ext (RunPod / IonQ / H100 catalog) | A | SSOT canonicalize | 1.0 | autonomous |
| 7 | T-A-1+ | HXC | anima/state/*.jsonl top-5 (~2.1MB) | A | 25% / ~525KB | 2.0 | autonomous |
| 8 | T-B-2 | `.turn` x-repo | 5 sister repos forward-spec | B-pending | parity | 5.0 | pending-review |
| 9 | T-A-3c | `.guide` | airgenome / n6 .guide creation | A | cold-entry win | 1.0 | autonomous |
| 10 | T-B-3 | `.end` x-repo | 5 sister repos META-composition | B-pending | parity | 5.0 | pending-review |

---

## 4. Tier Classification (raw 102 Disposition)

**Tier-A (autonomous, STRENGTHEN-existing, 1-3h budget):** T-A-1, T-A-1+nexus, T-A-2, T-A-3a, T-A-3b, T-A-3c, T-A-4a — 7 items. All STRENGTHEN existing format-on-existing-artifacts; raw 92 strengthening 2026-04-27 already mandates JSONL/cycle-JSON HXC adoption; cross-repo `.guide` / `.ext` propagation strengthens raw 14 ext-ssot + raw 0 cold-entry triad.

**Tier-B (medium, ADD-new pending-review, 4-6h):** T-B-1 `.chain` SSOT creation (raw 43 cross-engine 7-engine completeness — 6/7 surfaces present, `.chain` is the absent 7th), T-B-2 `.turn` cross-repo propagation, T-B-3 `.end` cross-repo propagation, T-B-4 raw note structured-keys conversion (117 entries remaining from P-101.1 commit `c2cb01d99` 7-entry pattern).

**Tier-C (large redesign, 8-24h, deferred):** T-C-1 HXC tokenizer-aware A3 algorithm impl (requires cl100k tokenizer integration), T-C-2 HXC content-address subtree A4 (requires merkle-DAG), T-C-3 `.meta` / `.command` cross-repo propagation (5 sister repos engine-surface parity, requires per-repo command catalog audit), T-C-4 HXC small-N edge case scope retraction or sharpening per raw 91 C3.

---

## 5. Tooling Gap Inventory

**With lint (11 of 13):** `.raw`, `.own`, `.roadmap`, `.ext` (hexa-lang side), `.guide`, `.workspace`, `.turn`, `.end`, `.meta`, `.command`, HXC (`hxc_lint` + `hxc_convert` + `hxc_pilot`).

**Missing lint (2 gaps):**
- `.chain` — NO `.chain` SSOT in any repo, NO `chain_lint.hexa`. raw 43 cross-engine completeness violation (6/7 engine surfaces present). HIGH priority gap.
- `.convergence` — implicit timeline event grammar only; no dedicated lint. LOW priority (event-driven semantics absorbed by readers).

---

## 6. Cross-Repo Propagation Map

| Format | hive | hexa-lang | anima | nexus | n6 | airgenome |
|---|---|---|---|---|---|---|
| `.raw` | live (4077L) | live | absorbed→.own | live | live | absent |
| `.own` | live (31L) | live (46L) | live (181L) | live (120L) | live (319L) | absent |
| `.roadmap` | live (1739L) | live (944L) | live (3785L) | live (168L) | live (10L) | live (280L) |
| `.ext` | live (121L) | absent | **MISSING** | live (177L) | live (39L) | **MISSING** |
| `.guide` | live (77L) | **MISSING** | **MISSING** | live (53L) | **MISSING** | **MISSING** |
| `.turn` | live forward-spec | absent | absent | absent | absent | absent |
| `.end` | live forward-spec | absent | absent | absent | absent | absent |
| `.meta` | live (209L) | absent | absent | absent | absent | absent |
| `.command` | live (405L) | absent | absent | absent | absent | absent |
| `.chain` | **ABSENT** | absent | absent | absent | absent | absent |
| HXC | live (3 witnesses) | absent | absent | absent | absent | absent |
| `.convergence` | live (58L) | absent | absent | live (5 streams) | absent | live |

**Propagation priority order:**
1. `.guide` (4 repos missing) — cold-entry hostility = biggest UX gap.
2. `.ext` (3 repos missing) — external-resource SSOT gap; anima-side esp critical (RunPod / IonQ / H100 currently undeclared).
3. HXC (5 repos absent) — 90d ramp from 2026-04-27; STRENGTHEN track.
4. `.turn` / `.end` (5 repos absent) — engine-surface parity, forward-spec.
5. `.chain` — ALL repos absent, ADD-new track requires raw 43 schema design.

---

## 7. Raw 87 Paired-Roadmap Candidates

- **P-format-1** HXC migration: anima cycle-JSON + state JSONL (Tier-A, 3.5h, falsifier: byte saving < 20% over N>=5).
- **P-format-2** HXC migration: nexus design/kick (124 files; Tier-A, 3h, falsifier: < 22% over N>=20).
- **P-format-3** `.chain` SSOT + chain_lint creation (Tier-B-pending, 4h, falsifier: schema overlap with `.meta`/`.command` > 0.7 → retire).
- **P-format-4** `.guide` cross-repo propagation × 4 repos (Tier-A, 2h, falsifier: no cold-entry confusion gain in 30d).
- **P-format-5** `.ext` cross-repo propagation × 3 repos (Tier-A, 1h, falsifier: no canonicality gain in 30d).
- **P-format-6** `.turn` / `.end` / `.meta` / `.command` cross-repo parity (Tier-C, 16h, falsifier: engine-surface SSOTs do not survive sister own-namespace pressure 90d).
- **P-format-7** HXC tokenizer-aware A3 algorithm impl (Tier-C, 12h, falsifier: tokenizer-aware delta < 5pp over A2 baseline).

---

## 8. Five Preregistered Falsifiers (raw 71)

- **F1 — HXC ROI:** Tier-A T-A-1 + T-A-2 actual byte saving < 20% over 30d post-migration → demote raw 92 mandate scope OR retire HXC claim.
- **F2 — Tooling gap:** `.chain` SSOT cannot be defined without semantic overlap > 0.7 with `.meta` + `.command` → retire `.chain` proposal; raw 43 accepts 6/7.
- **F3 — Cross-repo propagation:** `.guide` / `.ext` propagated to <50% of target repos by 60d → demote propagation mandate; declare format hive-internal-only.
- **F4 — Tier classification:** Tier-A items take >2x estimated cost (3h budget item runs 6h+) → rebalance Tier-A/B boundary.
- **F5 — raw 102 disposition:** ADD-new pending-review queue grows >5 entries without user review for 14d → review queue is flow-blocker; promote highest-ROI ADD-new OR retire entry.

---

## 9. Honest Disclosures (raw 91 C3)

- 9/9 nexus kick FAIL session-cumulative; raw 100 line 2423 fallback engaged; this landing is in-context synthesis, NOT kick-emitted.
- HXC small-N edge case (3-row fixture) shows NEGATIVE byte saving — header overhead > schema-repetition saving below ~5 rows; preserved per raw 106 multi-realizability counter-example axis.
- raw 95 organic compliance D+2 of D+30 window — 2.4% baseline far below 60% target; ROI prioritization respects ramp window not optimistic projection.
- ROI byte-saving estimates projected from Pilot B 27.7% baseline — NOT from migration-completion measurement; F1 falsifier preregistered to retire claim if <20% actual.

---

## 10. Omega-Stop Decision

raw 37 fixpoint-convergence: additional ω-cycle on identical self-format inventory yields ZERO net new ROI candidates. Tier-A list saturated at 7 items; Tier-B/C bounded by raw 102 review-queue cardinality. raw 72 tri-axis ordinal-theoretic ceiling = 12 formats × 6 repos × 3 dispositions = 216 cells; populated 78 distinct triples (saturation density 36%). Diagonal-major fill expected from execution of P-format-1..P-format-7. **STOP this cycle.**

---

## 11. Next Actions (Main Thread Decision)

1. Commit witness JSON + this landing doc (no code edits).
2. Execute Tier-A items in rank order: T-A-1 → T-A-3a → T-A-3b → T-A-4a → T-A-3c → T-A-1+nexus → T-A-2 (cumulative ~9.5h).
3. Queue Tier-B items in `state/raw_addition_requests/registry.jsonl` for user review.
4. Defer Tier-C items pending Tier-A measurement evidence (F1 falsifier resolves first).
5. Re-fire kick once nexus infra rc=3 / rc=0 / rc=76 root-cause lands (raw 100 line 2422 D+30 falsifier clock anchored 2026-04-27).
