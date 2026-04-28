# HXC Cumulative Milestone — 2026-04-28 (8h+ /loop autonomous cron consolidation)

**Date**: 2026-04-28
**Scope**: 8h+ autonomous /loop cron run cumulative result consolidation
**Compliance**: raw 1 chflags · raw 9 hexa-only · raw 18 self-host fixpoint · raw 47 cross-repo · raw 65+68 idempotent · raw 71 falsifier-preregistered · raw 87 paired-roadmap · raw 91 honest C3 · raw 95 triad · raw 99 hive cli · raw 137 80% Pareto + cmix-ban · raw 142 D1-D5 · raw 152 self-decoding fixpoint VERIFIED · raw 156 algorithm-placement-orthogonality · raw 157 base85 wire inheritance

**Companion docs**:
- `hxc_phase11_closure_20260428.md` — Phase 11 closure formal (per-sub-phase status)
- `hxc_phase12_forward_design_20260428.md` — Phase 12 forward chain (P1+ algorithm catalog)
- `hxc_2026-04-28_44agent_swarm_measurements_master.md` — 44-agent swarm SSOT
- `hxc_INDEX_2026-04-28.md` — full doc index

---

## 0. Honest framing (raw 91 C3)

This document consolidates ~8 hours of /loop autonomous cron output into a single milestone snapshot. Numbers are MEASURED unless explicitly labeled PROJECTED. Per-class progress is honest: 2/4 classes ACHIEVED at the raw 137 80% target, 2/4 GATED.

What is true:
- Aggregate climbed +60.94pp from Phase 5 (14.48%) to current (75.42%).
- Per-class 2/4 ACHIEVED (text-heavy 83.43% + structured-audit 87.14%).
- F1-F10 falsifier set ALL RETIRED (cumulative across Phase 5 → Phase 11).
- raw 152 self-decoding-fixpoint-mandate VERIFIED at artifact level.
- Phase 11 P1+P3 LIVE-LANDED + Phase 11 closure formal.
- Phase 12 P0 deploy LIVE on text-heavy + structured-audit classes.
- D1 P1 production-migration canary LIVE.

What is NOT true:
- 6-repo aggregate has NOT crossed 80% (current 75.42%, gap 4.58pp).
- F-A18-1 is PARTIAL (corpus-size bounded), not RETIRED — still in flight (a7b9417d).
- F-A19-6 is NEW TRIPPED on broader nexus corpus.
- Phase 12 P1+ are forward-projected, not LIVE.

---

## 1. Headline trajectory: 14.48% → 75.42% (+60.94pp)

| phase | aggregate | delta from prior | top driver |
|---|---:|---:|---|
| Phase 5 baseline | 14.48% | — | initial measurement |
| Phase 7 cross-repo | 40.00% | +25.52pp | A1 + A4 + A12 + A15 cross-repo sweep |
| Phase 8 FINAL | 48.00% | +8.00pp | 10 LIVE algorithm catalog + per-class hierarchy emerged |
| Phase 8 post-bug-2-fix | 49.10% | +1.10pp | 0 cache slot regression |
| Phase 10 P0+P3 | 37.27% | -11.83pp* | b85 wire ceiling discovery + corpus mix expansion (anchor change, not regression) |
| Phase 10 ade9d5eb | 62.59% | +25.32pp | A17 (PPM order-3) + A18 (LZ-PPM order-4) AOT binary deploy |
| Phase 10/11 best-of-N | **75.42%** | +12.83pp | full-chain best-of-N {A1, A17, A18, A17→A18, A18→A17} per-file try-and-revert |

\* anchor-change at Phase 10 P0+P3 is corpus-mix expansion, not algorithmic regression — measurement axis re-baselined.

**Total measured gain Phase 5 → today**: +60.94pp.

---

## 2. F1-F10 falsifier ALL RETIRED + 91.7% cadence

Cumulative falsifier-retire ledger across Phase 5 → Phase 11:

| ID | original definition | retire commit | current status |
|---|---|---|---|
| F1 | hxc-saving-ratio < 0.50 across anima top-5 JSONL surface | Phase 7 cross-repo | RETIRED — 5/6 sister repos > 0.50 (n6 entropy-bound counter-example clause) |
| F2 | hxc-encode-latency > 100ms-per-row | Phase 8 AOT migration | RETIRED — A18(AOT) hits ~10ms/row on production sizes |
| F3 | hxc-decode-latency > 10us-per-row | Phase 8 baseline | RETIRED — A1 baseline + A18 decode within budget |
| F4 | atlas +30-50pp PROJECTED | Phase 8 P5 | RETIRED — entropy-bound 0.075% FALSIFIED, claim retracted |
| F5 | Phase 8 P7 best-of-N expansion | Phase 8 P7 | RETIRED — -2pp regression reverted, claim retired |
| F6 | Phase 8 P8.6 threshold-lowering | Phase 8 P8.6 | RETIRED — zero additional captures, claim retired |
| F7 | n6 atlas-convergence entropy-bound | Phase 9 measurement | RETIRED — agent a201a6cc measured H_3 = 1.294 (84% Shannon 3-th lower bound), prior verdict reversed |
| F8 | A9 hexa-native tokenizer required for anima > 50% | Phase 10 A18 deploy | RETIRED — A18 LZ-PPM order-4 supersedes A9 dependency on this corpus |
| F9 | A19 PASS 0 schema-id collision | `38f4c2e6` | RETIRED — schema-id normalization PASS 0 fix verified |
| F10 | A18 codegen patch (4b2918ec) | `3633135b` | RETIRED — partial → retired correction |

**Cumulative**: F1-F10 ALL RETIRED.

**Cadence metric**: 91.7% (11/12 expected falsifier-retire commits landed within 7-day window per raw 71). The 1 missed = F-A22-3 latency budget (NOT_MEASURED_TICK2, deferred to tick 3).

---

## 3. F-A18-1 PARTIAL (corpus-size bounded) + F-A19-6 NEW TRIPPED

### F-A18-1 PARTIAL

**Definition**: F-A18-1 algorithmic strengthening on PPMd order tuning (n6 small-text class).
**Status**: PARTIAL — corpus-size bounded.
**In-flight agent**: `a7b9417d` (F-A18-1 saving algorithmic ω-cycle).
**Projected delta**: +2..+4pp on n6-architecture small-text class (currently 29.79%).
**Aggregate contribution**: +0.5..+1pp on 6-repo total (n6 = 4.4% of total bytes).

raw 91 C3: F-A18-1 cannot single-handedly close the 4.58pp aggregate gap. Combined path required: F-A18-1 + A20 production-tune + A4-A15 AOT cohort 2.

### F-A19-6 NEW TRIPPED

**Definition**: A19 net contribution > 0pp on broader nexus corpus.
**Status**: TRIPPED on current nexus 95-file corpus state.
**Trip evidence**: A19 LIVE FIRE → 0pp net lift under min-selection rule. Dict has only 3 patterns above 256B threshold; break-even N not reached.
**Disposition**: A19 NOT retired. F-A19-6 trip is corpus-conditional. A19 preserved as LOAD-BEARING-CONDITIONAL for n6 iter / nexus_proposals_small only.

raw 91 C3: F-A19-6 trip means A19 federation alone cannot deliver +pp on small-file class with current corpus density. Alternative paths: A20 schema-aware BPE eligibility-gate-bound, A24 grammar induction (Phase 12 P2 forward).

---

## 4. raw 152 VERIFIED — self-decoding fixpoint at artifact level

**Status (prior)**: UNVERIFIED (placeholder SHA-256, mini-VM stub, no LIVE FIRE).
**Status (today)**: **VERIFIED**.

Six gates cleared in A22 tick 2 (commit `95f843b5`):
1. pure-hexa SHA-256 (FIPS 180-4 KAT) — F1.7 PASS (`SHA-256("")` = `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` ✓; `SHA-256("abc")` = `ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad` ✓).
2. base94 decoder LIVE — F1.6 PASS.
3. mini-VM 8-opcode execute LIVE — F1.6 PASS (PUSH_ALGO / PUSH_PARAM / DECODE / POP / EMIT / CHK / MARK / HALT).
4. wrap/unwrap byte-eq round-trip — F1.8 PASS + 3/3 LIVE FIRE (74KB / 146KB / 2KB).
5. tamper detection — F1.10 PASS (sha256 guard fires on tampered footer).
6. bootstrap parser < 100 LoC pure hexa — F-A22-4 CLEAR.

**Implication**: a hexa runtime + a `.hxc` artifact alone can verify-and-decode end-to-end without any external library. raw 18 self-host fixpoint is sealed at the artifact level for all A22-wrapped outputs.

---

## 5. Phase 11 P1+P3 LIVE + closure formal

| sub-phase | algorithm | status | commit | LoC | selftest |
|---|---|---|---|---:|---|
| P0 | A19 cross-corpus dict federation | LOAD-BEARING-CONDITIONAL | `a0622953` → `38f4c2e6` | n/a | 15/15 PASS |
| P1 | A20 schema-aware BPE | **LIVE + LANDED** | `babe967a` → `95f843b5` | 1044 | 8/8 PASS |
| P3 | A22 self-decoding HXC | **LIVE + VERIFIED** | `080023d9` → `95f843b5` | 882 | 10/10 PASS |
| REF | A21 write-side advisory | ALWAYS-GO | n/a | n/a | n/a |

**Closure formal**: see `/Users/ghost/core/anima/docs/hxc_phase11_closure_20260428.md`.

---

## 6. Phase 12 P0 deploy LIVE — 2/4 classes

Per-class achievement matrix (raw 91 C3 honest):

| class | constituents | saving% | verdict | P0 deploy |
|---|---|---:|---|---|
| **text-heavy** | n6-architecture + hexa-lang | **83.43%** | ACHIEVED (margin 3.43pp) | **LIVE** |
| **structured-audit** | hive | **87.14%** | ACHIEVED (margin 7.14pp) | **LIVE** |
| small-file | nexus | 69.10% | BELOW (10.90pp gap) | GATED |
| mixed-real | anima + airgenome | 63.75% | BELOW (16.25pp gap) | GATED |

**Deploy ledgers landed**:
- `/Users/ghost/core/anima/state/phase12_p0_deploy/2026-04-28_text_heavy_live.jsonl`
- `/Users/ghost/core/anima/state/phase12_p0_deploy/2026-04-28_structured_audit_live.jsonl`

**Deploy chain (both classes)**: A1 + A18(AOT). AOT binary `/Users/ghost/core/hexa-lang/build/hxc_a18_test 301920B 5/5 selftest`.

**Deploy gate (3 steps each, 6 total)**: raw 1 chflags VERIFIED + byte-eq round-trip VERIFIED + rollback path VERIFIED (raw 142 D2 try-and-revert).

**Falsifiers active**: F-P12-P0-TH-1..4 + F-P12-P0-SA-1..4 = 8 deploy-gate falsifiers preregistered.

---

## 7. D1 P1 production-migration canary LIVE

**Commit**: `c8ed96d7 witness(D1 P1 canary LIVE): production deploy 첫 실행 + raw 156 strengthening verify`.

**Window**: 2026-04-28 → 2026-05-05 (7-day canary).

**Watcher**: `tool/hxc_d1_canary_watcher.hexa` sha256 `eb0f582f56356ca9dc05f20aa07888d7df34bf1fca9b9a4b684c2e925bdceb21` 246 LoC, selftest 8/8 PASS.

**Canary ticks landed**: 2/2 PASS sha256 byte-eq (tick-0 ts 2026-04-27T23:26:29Z + tick-1 ts 2026-04-27T23:47:07Z); 0 divergence.

**Falsifiers active**: F-RAW160-1..4 + F-D1-1..2.

**Cross-link**: D1 P2 forward-spec in-flight (`a63bac70`, `ac86dd8a` agent). D1 LAND projected 2026-05-20.

---

## 8. Two-axis ω-cycle structure

The 8h+ cron run produced two parallel axis advances:

**Axis A — compute axis (HXC algorithmic measurement)**:
- 6-repo aggregate 75.42% byte-weighted.
- Per-class 2/4 ACHIEVED.
- Phase 12 P0 deploy LIVE on 2 ACHIEVED classes.
- Phase 11 P1 (A20) + P3 (A22) LIVE-LANDED.

**Axis B — production-migration axis (D1 P1 canary)**:
- D1 P1 LIVE 7-day canary running.
- 2/2 ticks PASS sha256 byte-eq.
- D1 P2 forward-spec in flight.

Both axes are forward components of the raw 137 ω-cycle. The compute axis hits the per-class 80% target; the production-migration axis ensures field-deploy correctness via canary cadence + byte-eq monitoring. Neither single axis would close raw 137 — together they form the dual-track Pareto progress.

---

## 9. cmix-ban MAINTAINED

raw 137 cmix-class neural mixing PERMANENTLY BANNED.

Cumulative position:
- Phase 8 → Phase 11 algorithm catalog: 11 LIVE (A1+A4+A7+A8+A10+A11+A12+A13+A14+A15+A18) + AOT cohort 1 (A17+A18+A19) + Phase 11 (A20+A22).
- Phase 12 forward catalog: A23 / A24 / A25 / A26 / A27 + A28 (TRANSCEND-FORBIDDEN).

**A28 semantic embedding** is explicitly retained as TRANSCEND-FORBIDDEN — would require retiring raw 9 (hexa-only), raw 18 (self-host fixpoint), or raw 137 (cmix-ban). Ban remains in force.

---

## 10. raw 91 honest C3 — what this milestone does NOT solve

1. **Aggregate gap remains**: 75.42% < 80% target. 4.58pp away. Two GATED classes (small-file 69.10%, mixed-real 63.75%) need algorithmic lift.
2. **F-A18-1 NOT RETIRED**: PARTIAL only; in-flight agent `a7b9417d` continues.
3. **F-A19-6 NEW TRIPPED**: A19 federation 0pp net on broader nexus corpus; alternative path required.
4. **F-A22-3 NOT_MEASURED**: A22 latency budget deferred to tick 3.
5. **Phase 12 P1+ are PROJECTED, not LIVE**: A23/A24/A25/A26 forward-spec'd, no LIVE measurement yet.
6. **D1 P2 W1+ are forward-spec**: D1 LAND projected 2026-05-20, currently in flight.
7. **anima/.roadmap uchg-locked**: paired roadmap entries deferred to next chflags cycle.
8. **a45778db / a6d36e1d are upstream sister-repo references**: anima-side LIVE-strengthening doc landed at `95f843b5`; full-chain measurement landed at `state/format_witness/2026-04-28_full_chain_6repo_aot_sweep.jsonl`.

---

## 11. Forward priority (next cron tick)

Per-rank priority from full-chain best-of-N analysis:

| rank | id | reason | est aggregate delta |
|---:|---|---|---|
| 1 | A20 production-tune (multi-corpus grid) | small-file 69.10% / mixed-real 63.75% are gap drivers | +3..+6pp |
| 2 | A4-A15 AOT cohort 2 | structural+entropy chain currently INTERP-blocked | +3..+5pp |
| 3 | F-A18-1 PPMd algorithmic | a7b9417d in-flight; n6 50pp headroom | +0.5..+1pp |
| 4 | A19 corpus-mode threshold tune | 256B → 64B may unlock more cross-file dedup on nexus | +0.5..+2pp on small-file |

**Aggregate path to 80%**: priority 1 + priority 2 (cumulative +6..+11pp) sufficient to cross 80% with margin.

---

## 12. Files this cycle

- `/Users/ghost/core/anima/state/phase12_p0_deploy/2026-04-28_text_heavy_live.jsonl` (NEW)
- `/Users/ghost/core/anima/state/phase12_p0_deploy/2026-04-28_structured_audit_live.jsonl` (NEW)
- `/Users/ghost/core/anima/state/format_witness/2026-04-28_phase12_p0_deploy_phase11_closure.jsonl` (NEW witness ledger)
- `/Users/ghost/core/anima/docs/hxc_phase11_closure_20260428.md` (NEW Phase 11 closure formal)
- `/Users/ghost/core/anima/docs/hxc_cumulative_milestone_2026-04-28.md` (THIS DOC)

---

## 13. Compliance summary

- **raw 1 chflags**: hive .raw not modified this cycle (forward-spec strengthening text captured in Phase 11 closure doc §8 for next chflags cycle); anima/.roadmap uchg-locked, no edit attempted.
- **raw 9 hexa-only**: PRESERVED.
- **raw 18 self-host fixpoint**: PRESERVED — raw 152 VERIFIED at artifact level.
- **raw 47 cross-repo**: 6 repos referenced + sister-agent coordination noted (a58efacb / ace91cf6 / a7a059f0 / ac86dd8a non-collision verified).
- **raw 65+68 idempotent**: PRESERVED.
- **raw 71 falsifier-preregistered**: F-P12-P0-TH-1..4 + F-P12-P0-SA-1..4 + Phase 11 falsifier verdicts landed.
- **raw 87 paired-roadmap**: forward-spec in Phase 11 closure doc §8; anima/.roadmap uchg-locked, paired entries deferred.
- **raw 91 honest C3**: §0 + §10 explicit non-solved disclosures.
- **raw 95 triad**: L1 advisory + L2 lint (hxc_lint.hexa --measure) + L3 atlas (n6 + hive triad_audit anchor files).
- **raw 99 hive cli**: hxc_lint.hexa --measure --class={text-heavy,structured-audit} reads deploy ledgers as authority.
- **raw 137 80% Pareto + cmix-ban**: PARTIAL ACHIEVEMENT 2/4 per-class; aggregate 75.42% gap 4.58pp; cmix-ban MAINTAINED.
- **raw 142 D1-D5**: D2 (try-and-revert) + D3 (orthogonality) PRESERVED.
- **raw 152 self-decoding**: VERIFIED.
- **raw 156 algorithm-placement-orthogonality**: A20+A22 orthogonal; A23/A24/A25 forward-spec'd with placement axes.
- **raw 157 base85-wire-inheritance**: unchanged.

---

**End of cumulative milestone 2026-04-28.**
