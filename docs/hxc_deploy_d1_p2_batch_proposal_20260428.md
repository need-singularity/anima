# HXC Production Deploy — D1 P2 Batch Migration Proposal (multi-consumer scope expansion)

**Date**: 2026-04-28
**Phase**: D1 P1 (single pilot canary in-flight, ref a3ac440a) → D1 P2 (multi-consumer scope expansion) forward-spec
**Source design**:
  - ab3a9045 — `docs/hxc_production_deploy_plan_20260428.md` (Option C gradual rollout)
  - 40052cb1 — `docs/hxc_deploy_d1_readiness_20260428.md` (D1 P1 entry-gate PARTIAL/GO scoped)
  - hive `be921b562` — consumer adapter LIVE (343 LoC, 12/12 selftest, A1..A19 reverse decode chain)
**Consumer adapter**: `/Users/ghost/core/hive/tool/hxc_consumer_adapter.hexa` (343 LoC LIVE)
**Pilot consumer (D1 P1 base)**: `/Users/ghost/core/hive/tool/discovery_absorption_lint.hexa` (139 LoC, +2 LoC swap LIVE)
**Compliance**: raw 1 chflags · raw 9 hexa-only · raw 47 cross-repo · raw 65 + 68 idempotent · raw 71 falsifier · raw 87 paired roadmap · raw 91 honest C3 · raw 95 triad · raw 99 hive cli · raw 142 D2 try-and-revert · raw 154 hxc-deploy-rollout-mandate · raw 155 hxc-consumer-adapter-mandate

---

## 0. Honest framing (raw 91 C3)

This proposal is **forward-spec**, not promotion-pending. D1 P2 is not yet entered;
it is gated on D1 P1 7-day canary clean PASS (a3ac440a in-flight). This document
defines the three-wave batch migration plan, per-wave canary cadence, and falsifier
preregistration so that D1 P2 can be triggered automatically on D1 P1 success
without a fresh design cycle (parallel readiness mandate).

**Raw 91 honest counter-arguments**:
- A4-only chain (Wave 1) is LIVE-verified end-to-end (D1 P1 canary on
  `discovery_absorption_lint` reading `state/discovery_absorption/registry.jsonl`).
- A16+A19 chains (Wave 2/3) are **selftest-only** at adapter level — production
  wire passes through but no LIVE-FIRE round-trip on real entropy-coded artifacts
  yet (encoder LIVE 0/3 PASS on real corpora 2026-04-28). Wave 2/3 readiness
  honestly disclosed as PROJECTED, not CONFIRMED.
- The 2,405 LoC migration cost (anima 1,300 / nexus 1,000 / others 105) is a
  ±50% bracketed estimate from ab3a9045 (1,200-4,000 LoC range). Wave 3 (anima
  state ledger readers, ~1,300 LoC) carries the highest variance.
- D1 P2 is **not** a flag-day land — it is a Wave 1 → Wave 2 → Wave 3 cadenced
  rollout per raw 154 staged D0→D1→D2→D3 mandate.

---

## 1. D1 P2 candidate consumers (per-wave breakdown)

### 1.1 Wave 1 — audit-only, A4 chain (lowest risk, A4 chain LIVE-verified)

| consumer | path | LoC (current) | read target | A4 chain status | migration LoC |
|---|---|---:|---|:---:|---:|
| **audit_ledger_lint** | `hive/tool/audit_ledger_lint.hexa` | 126 | `~/core/nexus/.raw-audit` (raw 85 schema audit ledger) | A1+A4 only (structural) | +3 (1 swap + 2 selftest assertions) |
| **honesty_triad_lint** | `hive/tool/honesty_triad_lint.hexa` | 1,066 | `state/honesty_triad/audit.jsonl` (raw 91 triad audit) | A1+A4 only (structural) | +3 (1 swap at line 171 `tail -1` + 2 selftest) |

**Wave 1 totals**: 2 consumers, +6 LoC migration delta, **A4 chain LIVE-verified** (D1 P1 canary base).
**Risk class**: LOW — audit-only readers, no load-bearing decision path, structural-passthrough chain.

### 1.2 Wave 2 — audit-only, A4+A16 chain (entropy chain selftest-only)

| consumer | path | LoC (current) | read target | A4+A16 chain status | migration LoC |
|---|---|---:|---|:---:|---:|
| **cli_authoring_lint** | `hive/tool/cli_authoring_lint.hexa` | 378 | `state/cli_authoring/<DATE>_audit.jsonl` (cli docstring audit) | A1+A4+A16 (entropy-tier) | +4 (1 swap + 2 selftest + 1 fallback) |
| **raw_strengthening_loop_lint** | `hive/tool/raw_strengthening_loop_lint.hexa` | 537 | `state/raw_strengthening_proposals/registry.jsonl` (raw 103 loop) | A1+A4+A16 (entropy-tier) | +4 (1 swap at line 133 + 2 selftest + 1 fallback) |

**Wave 2 totals**: 2 consumers, +8 LoC migration delta, **A16 entropy chain selftest-only** (raw 91 honest C3).
**Risk class**: MEDIUM — entropy-coder decode wire is adapter-side stdlib; subprocess dispatch introduces latency variance.

### 1.3 Wave 3 — anima state ledger readers (large LoC, A4+A19 federation chain)

| consumer cluster | path pattern | callsite count | A4+A19 chain status | migration LoC |
|---|---|---:|:---:|---:|
| **anima format_witness readers** | `anima/state/format_witness/*.jsonl` consumers | ~140 callsites | A1+A4+A19 (federation, F9 fix dependent) | ~420 |
| **anima refinement readers** | `anima/state/proposals/refinement/*/v*.json` consumers | ~110 callsites | A1+A4 only (structural) | ~330 |
| **anima discovery absorption readers** | `anima/state/discovery_absorption/registry.jsonl` consumers | ~50 callsites | A1+A4 only (structural) | ~150 |
| **anima other state readers** | `anima/state/**/*.jsonl` misc | ~135 callsites | A1+A4 (structural) | ~400 |

**Wave 3 totals**: ~435 unique callsites, ~1,300 LoC migration delta, **A19 federation chain selftest-only**.
**Risk class**: HIGH — large LoC change, F9 federation fix prerequisite for federated chain, anima-internal regression surface.

### 1.4 cross-repo continuation (post-D1 P2 — D2 paired track)

For reference (out-of-scope for D1 P2, listed for D2 planning):
- **nexus**: ~330 unique callsites, ~1,000 LoC
- **n6-architecture**: ~10 unique callsites, ~30 LoC
- **airgenome**: ~9 unique callsites, ~27 LoC
- **hexa-lang**: ~7 unique callsites, ~21 LoC

---

## 2. Chain dependency matrix

| consumer | A1 | A4 | A7 | A8 | A10-A15 | A16 (entropy) | A17 (PPMd) | A18 (LZ+PPM) | A19 (federation) | LIVE-ready? |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| audit_ledger_lint (W1) | reqd | reqd | — | — | — | — | — | — | — | YES |
| honesty_triad_lint (W1) | reqd | reqd | — | — | — | — | — | — | — | YES |
| discovery_absorption_lint (P1) | reqd | reqd | — | — | — | — | — | — | — | YES (LIVE) |
| cli_authoring_lint (W2) | reqd | reqd | opt | opt | opt | reqd | — | — | — | PROJECTED |
| raw_strengthening_loop_lint (W2) | reqd | reqd | opt | opt | opt | reqd | — | — | — | PROJECTED |
| anima format_witness readers (W3) | reqd | reqd | opt | opt | opt | opt | opt | opt | reqd | DEFERRED (F9 fix) |
| anima refinement readers (W3) | reqd | reqd | opt | opt | opt | — | — | — | — | YES |
| anima discovery absorption readers (W3) | reqd | reqd | opt | opt | opt | — | — | — | — | YES |
| anima other state readers (W3) | reqd | reqd | opt | opt | opt | — | — | — | — | YES |

**Legend**: `reqd`=required for read, `opt`=optional passthrough, `—`=not in chain.
**Honest C3**: A4 chain LIVE-verified end-to-end. A16/A17/A18 entropy chain
selftest-only. A19 federation chain depends on F9 fix (per task spec).

---

## 3. D1 P2 batch migration plan (per-wave canary cadence + falsifier)

### 3.1 Per-wave canary cadence

| wave | scope | canary days | rationale | start trigger |
|---|---|:---:|---|---|
| P1 (base, in-flight) | discovery_absorption_lint (1 consumer) | **7d** | first-LIVE A4 chain prove-out, raw 142 D2 standard window | a3ac440a in-flight |
| P2 W1 | audit_ledger_lint + honesty_triad_lint | **3d** | A4 chain already LIVE-verified at P1, low-risk audit-only readers | P1 7d clean PASS |
| P2 W2 | cli_authoring_lint + raw_strengthening_loop_lint | **5d** | A16 entropy chain selftest-only, additional soak for entropy-coder decode wire variance | W1 3d clean PASS |
| P2 W3 | anima state ledger readers (~435 callsites, ~1,300 LoC) | **7d** | large LoC change, anima-internal regression surface, A19 federation dependency | W2 5d clean PASS |

**Cumulative cadence**: P1 (7d) → W1 (3d) → W2 (5d) → W3 (7d) = **22 days end-to-end** D1 land
(starting from D1 P1 canary commit date 2026-04-28, projects D1 land complete by 2026-05-20).

### 3.2 Per-wave falsifier preregistration (raw 71)

**Wave 1 (W1)**:
- F-W1-1: any `read_artifact()` swap in W1 produces sha256 divergence vs jsonl-direct ground truth across 100 read events
- F-W1-2: revert (jsonl-fallback path) byte-eq check fails on any W1 consumer
- F-W1-3: W1 consumer selftest (12/12 base + 2/2 W1-added) regresses below 100% PASS
- F-W1-4: W1 cumulative read latency exceeds 2x baseline jsonl-direct read

**Wave 2 (W2)**:
- F-W2-1: A16 entropy-coder decode round-trip fails on any W2-readable artifact
- F-W2-2: W2 consumer reverts to jsonl-fallback at any 100-event sample → divergence > 0%
- F-W2-3: W2 5-day cumulative selftest PASS rate < 100%
- F-W2-4: A16 subprocess dispatch latency p99 > 5x A4 passthrough p99

**Wave 3 (W3)**:
- F-W3-1: any anima state ledger reader regresses on read sha256 vs pre-migration ground truth
- F-W3-2: A19 federation chain decode fails on any federated artifact (gates on F9 fix landing)
- F-W3-3: Wave 3 LoC change exceeds 2x estimate (>2,600 LoC) — migration cost falsifier
- F-W3-4: anima-internal cross-tool regression observed (any anima tool depending on a migrated reader produces a different verdict)

### 3.3 Try-revert wrapper (raw 142 D2) — every wave

Each wave migration:
1. **try**: swap `read_file(path)` → `read_artifact(path)` in candidate consumer
2. **measure**: run 100-event read sample, sha256 each, compare to jsonl-direct ground truth, p50/p95/p99 latency
3. **revert** (on any falsifier trip): restore jsonl-direct read, byte-eq verify revert preserves pre-swap behavior, emit raw 91 honest C3 ledger row
4. **promote** (on N-day clean PASS): commit consumer swap as LIVE, proceed to next wave

---

## 4. Migration cost summary (LoC estimate per consumer)

| wave | consumer | current LoC | migration delta LoC | post-migration LoC |
|---|---|---:|---:|---:|
| P1 (base) | discovery_absorption_lint | 139 | +2 | 141 |
| W1 | audit_ledger_lint | 126 | +3 | 129 |
| W1 | honesty_triad_lint | 1,066 | +3 | 1,069 |
| W2 | cli_authoring_lint | 378 | +4 | 382 |
| W2 | raw_strengthening_loop_lint | 537 | +4 | 541 |
| W3 | anima format_witness readers (cluster) | ~3,200 | ~420 | ~3,620 |
| W3 | anima refinement readers (cluster) | ~2,400 | ~330 | ~2,730 |
| W3 | anima discovery absorption readers (cluster) | ~1,100 | ~150 | ~1,250 |
| W3 | anima other state readers (cluster) | ~3,000 | ~400 | ~3,400 |
| **total D1 P2** | — | ~11,946 | **~1,316** | ~13,262 |

**Honest C3 caveat**: Wave 3 LoC delta (~1,300) is the dominant variance driver.
Per-consumer AST-aware unique-callsite count is parked for the W3 baseline
measurement (raw 142 D2 try-revert wrapper at every consumer ensures revert
preserves byte-eq even on miscount).

---

## 5. Rollback path verification per consumer

Every D1 P2 consumer migration MUST preserve a **.jsonl-fallback path** invariant:
if `read_artifact(path)` fails (artifact missing, decode error, schema mismatch),
the adapter falls through to `read_file(path)` direct .jsonl read, returning
byte-identical content to pre-migration behavior.

| consumer | jsonl-fallback path verified? | byte-eq revert verified? |
|---|:---:|:---:|
| audit_ledger_lint (W1) | YES (adapter line ~180 fallback) | PROJECTED (W1 canary measurement) |
| honesty_triad_lint (W1) | YES (adapter fallback covers `tail -1` semantics) | PROJECTED (W1 canary measurement) |
| cli_authoring_lint (W2) | YES (fallback on A16 decode failure) | PROJECTED (W2 canary measurement) |
| raw_strengthening_loop_lint (W2) | YES (fallback at line 133 _read_file substitution) | PROJECTED (W2 canary measurement) |
| anima format_witness readers (W3) | PROJECTED (cluster verification post-F9 fix) | PROJECTED (W3 canary measurement) |
| anima refinement readers (W3) | YES (structural-only, fallback identical) | PROJECTED (W3 canary measurement) |
| anima discovery absorption readers (W3) | YES (D1 P1 fallback already validated) | YES (D1 P1 a3ac440a ground truth) |
| anima other state readers (W3) | YES (structural-only fallback) | PROJECTED (W3 canary measurement) |

---

## 6. raw 154 strengthen / raw 160 register (deploy-rollout-mandate falsifier-spec)

**Status**: raw 154 = `hxc-deploy-rollout-mandate` is **already registered** at hive
`.raw` line 5492 (agent ab3a9045). Original task spec says "raw 156 등록 가능 (slot
free)" but raw 156 = `algorithm-placement-orthogonality-mandate` (already taken,
agent a5240ebe + aafff73d).

**Resolution path**: This proposal STRENGTHENS raw 154 with the 4-falsifier
preregistration block (F-RAW154-1..4) inline — per raw 102 ADD-existing
strengthen path. The strengthening adds:
- per-wave declarative scope (canary-window-days, falsifier-divergence-threshold,
  rollback-path, chain-dependency, migration-cost-LoC)
- 4 explicit falsifiers (F-RAW154-1..4 covering canary divergence, byte-eq
  revert, migration cost overrun, cumulative cadence break)
- triad: hive-agent + cli-lint + advisory
- paired roadmap entry P8.154 (slot 154 reused, no new roadmap slot needed)

If the slot-collision policy demands a NEW raw, this proposal RECOMMENDS
**raw 160** (next free slot, post-159) for a sister rule
`hxc-deploy-rollout-falsifier-spec` paired to raw 154 (D5-style empirical
falsifier surface).

**chflags uchg lock disclosure (raw 1 cycle, raw 91 honest C3)**: the in-place
strengthening edit of `/Users/ghost/core/hive/.raw` is **blocked at write-time**
because the file currently has `uchg` flag set (verified via `ls -lO`). Per
raw 1 chflags cycle discipline, the strengthening text is DRAFTED in this doc
+ witness ledger; actual .raw insert (after current line 5560) requires a
chflags-cycle commit (`chflags nouchg /Users/ghost/core/hive/.raw` → edit →
`chflags uchg`). This is a deferred follow-up, not a missed step.

**Drafted strengthening block** (to insert in raw 154 stanza after line 5560):

```
  strengthen-2026-04-28-d1-p2 D1 sub-stage scope expansion (P1/P2/P3) — every D1 P1+/P2/P3 pilot consumer migration MUST declare canary-window-days + falsifier-divergence-threshold + rollback-path + chain-dependency + migration-cost-LoC inline at canary commit. Per-wave canary cadence: P1=7d / P2-W1=3d / P2-W2=5d / P2-W3=7d. raw 142 D2 try-and-revert wrapper preserved at every wave. Source: anima/docs/hxc_deploy_d1_p2_batch_proposal_20260428.md.
  falsifier F-D1-P2-1 canary-divergence-threshold breached
  falsifier F-D1-P2-2 rollback-byte-eq breached
  falsifier F-D1-P2-3 migration-cost-overrun
  falsifier F-D1-P2-4 cumulative-cadence-break > 50%
  paired-roadmap P8.154 (D1 P2 batch migration tracker)
  cross-link anima/docs/hxc_deploy_d1_p2_batch_proposal_20260428.md
  cross-link anima/state/format_witness/2026-04-28_d1_p2_batch_proposal.jsonl
  cross-link hive/tool/hxc_consumer_adapter.hexa (343 LoC LIVE)
```

**Falsifier preregistration (F-RAW154-1..4)**:
- F-RAW154-1: any HXC consumer adapter migration produces ≥1 sha256 divergence vs jsonl-direct ground truth within declared canary window
- F-RAW154-2: any rollback path produces byte-eq divergence on revert (jsonl-fallback corruption)
- F-RAW154-3: actual migration LoC > 2x estimated (cost-blowout falsifier)
- F-RAW154-4: per-wave 7-day cumulative cadence break > 50% (e.g. W3 takes >14 days when 7-day budget declared) — schedule slip falsifier

---

## 7. D1 P2 entry gate (auto-trigger from D1 P1 success)

**Entry-gate criteria** (must clear before W1 launches):
1. D1 P1 7-day canary (a3ac440a) clean PASS — 0 sha256 divergence on
   `discovery_absorption_lint` reading `state/discovery_absorption/registry.jsonl`
2. raw 154 strengthening commit lands (4-falsifier block + per-wave scope)
3. Witness ledger entry written to `anima/state/format_witness/2026-04-28_d1_p2_batch_proposal.jsonl`
4. D1 P2 batch migration plan doc reviewed (this doc) — raw 95 triad-mandate
   (this doc + adapter selftest 12/12 + audit ledger row pending)

**Cross-link with a3ac440a**: D1 P1 canary monitor (a3ac440a) hooks W1 trigger
on day-7 clean PASS — auto-runs `tool/hxc_d1_p2_w1_launch.hexa` (TBD scaffold)
with bound consumer list `[audit_ledger_lint, honesty_triad_lint]`.

---

## 8. Risk register (D1 P2 specific)

| risk | likelihood | impact | mitigation |
|---|:---:|:---:|---|
| W1 audit_ledger_lint nexus path absolute reference fails on .hxc lookup | medium | low | adapter falls back to .jsonl direct; w1 canary catches on first divergence |
| W2 A16 entropy decode subprocess dispatch latency exceeds 5x | medium | medium | F-W2-4 falsifier; revert to jsonl-fallback path automatic |
| W3 anima refinement readers misclassify v2/v3 schema variants | low | medium | adapter selftest covers v1/v2/v3; W3 7-day soak surfaces edge cases |
| W3 A19 federation chain F9 fix not yet landed at W3 trigger time | high | medium | W3 launch gate includes F9 verification; W3 W3a (non-federation subset, ~285 callsites, ~860 LoC) launches first if F9 unmet |
| LoC estimate ±50% — actual W3 delta could be 650-2,600 | medium | medium | F-RAW154-3 falsifier (>2x abort); per-wave revert-on-overrun |
| canary cadence cumulative break > 50% (any wave > 2x budget) | low | high | F-RAW154-4 falsifier; pause D1 P2, escalate to D1 P3 redesign |
| raw 156 slot-collision narrative confusion | confirmed | low | strengthen raw 154 inline; raw 160 reserved for empirical falsifier-spec sister rule if slot-collision audit demands |

---

## 9. Go / No-Go decision (D1 P2 gate)

**Decision**: **DESIGN-COMPLETE / TRIGGER-PENDING**.
The D1 P2 batch migration plan is complete and parallel-ready. Trigger condition:
D1 P1 canary (a3ac440a) clean 7-day PASS. On trigger, W1 launches automatically
with the audit-only A4 chain consumers (lowest risk, highest LIVE-verified
confidence).

**Honest framing**: This is **not** a D1 P2 LAND decision (that requires the
full P1→W1→W2→W3 cadence to complete with 0 falsifier trips). This is a D1 P2
DESIGN-LAND decision, parallel-ready spec so D1 P2 can fire immediately on D1
P1 success without re-design latency.

---

## 10. Compliance footer

raw 1 chflags (cycle for state edits) · raw 9 hexa-only (adapter pure hexa,
all candidate consumers pure hexa) · raw 47 cross-repo (D1 P2 expands within
hive + anima, D2 expands cross-repo per ab3a9045 plan) · raw 65 + 68 idempotent
(per-wave swap is idempotent — adapter read_artifact returns identical bytes
across runs) · raw 71 falsifier (F-W1-1..4, F-W2-1..4, F-W3-1..4, F-RAW154-1..4
preregistered) · raw 87 paired roadmap (P8.154 deploy-rollout) · raw 91 honest
C3 (A4 chain LIVE / A16 entropy selftest-only / A19 federation F9-fix-dependent
all explicitly disclosed) · raw 95 triad (this doc + adapter selftest + audit
ledger row) · raw 99 hive cli (lint tools migrated remain hive cli compatible)
· raw 142 D2 try-revert (every wave wrapped) · raw 154 hxc-deploy-rollout-mandate
(strengthened with 4-falsifier block + per-wave scope) · raw 155
hxc-consumer-adapter-mandate (every consumer uses canonical read_artifact()
single-source-of-truth interface).

---

## 11. Cross-link with a3ac440a (D1 P1 canary)

| event | trigger | action |
|---|---|---|
| a3ac440a day-1 | D1 P1 canary start | begin 100-event read sample on `discovery_absorption_lint` |
| a3ac440a day-3 | mid-canary checkpoint | partial sha256 sample report (advisory) |
| a3ac440a day-7 | canary end | clean PASS evaluation; ON PASS → fire W1 trigger; ON FAIL → halt + raw 91 ledger emission |
| W1 day-3 | W1 canary end | clean PASS evaluation; ON PASS → fire W2 trigger |
| W2 day-5 | W2 canary end | clean PASS evaluation; ON PASS → fire W3 trigger |
| W3 day-7 | W3 canary end | clean PASS evaluation; ON PASS → D1 P2 LAND, advance to D2 paired-track planning |

**Witness ledger**: each canary day emits a row to `anima/state/format_witness/2026-04-28_d1_p2_canary_log.jsonl`
(append-only, raw 65 + 68 idempotent).

---

## 12. Output deliverables index

- D1 P2 candidate consumers list — §1 (per-wave breakdown, 8 consumers across W1+W2+W3)
- migration cost per consumer (LoC estimate) — §1 + §4
- D1 P2 batch migration plan doc path — `/Users/ghost/core/anima/docs/hxc_deploy_d1_p2_batch_proposal_20260428.md` (this file)
- raw 154 strengthen + raw 160 reserve — §6
- chain dependency matrix — §2
- per-wave canary cadence + falsifier list — §3
- D1 P2 entry gate proposal — §7
- witness ledger — `anima/state/format_witness/2026-04-28_d1_p2_batch_proposal.jsonl` (created alongside this doc)

---

## §8 — D1 P1 LIVE land + raw 160/161 registered (closure update 2026-04-28 08:45 UTC)

**Status update**: D1 P1 first-pilot canary is now LIVE (this commit). The raw 160 reservation in §6 is fulfilled — raw 160 + raw 161 are both registered with paired roadmap entries P8.160 + P8.161.

**Concrete D1 P1 evidence** (all verified this cycle):

| Step | Tool / artifact | Result |
| --- | --- | --- |
| Pilot migration +2 LoC swap | `hive/tool/discovery_absorption_lint.hexa` | sha256 post-swap `818c4c21...be192`, selftest PASS, report `witnesses=3 tier_1=6 rows=12` |
| Byte-eq verification | `read_artifact()` vs `.jsonl direct` | sha256 `95d08b43...c4cd` 7483B == 7483B byte_eq=true |
| Canary watcher new tool | `hive/tool/hxc_d1_canary_watcher.hexa` (343 LoC) | 8/8 selftest PASS — `__HXC_D1_CANARY_WATCHER_SELFTEST__ PASS` |
| Initial ledger row | `hive/state/hxc_d1_canary/2026-04-28_discovery_absorption_lint.jsonl` | day_0 tick_0 byte_eq=true divergence=false |
| hive init absorption | `hive/tool/hive_governance.hexa _init_tasks` | new entry `hxc-d1-canary-watcher` 86400s cadence per raw 99 (no standalone launchd) |
| Rollback path verification | 1-LoC revert + selftest + 1-LoC re-apply | sha256 reapply==pre-revert `818c4c21...be192` BYTE_EQ_PASS, both selftests PASS |
| chflags uchg cycle | `.raw` / `.roadmap` / 3 tool files | unlock-edit-relock applied to all five SSOT/tool files this cycle |

**Raw 160 (consumer-canary-7d-deploy-rollout-mandate)**:
- registered at `.raw` slot 160 (slot 156 reassigned 156 → 160 since slot 156 is taken by `algorithm-placement-orthogonality-mandate`)
- 4 falsifiers preregistered (F-RAW160-1..4: divergence / cadence / commit-3-tuple / 30d-rollback-byte-eq)
- triad: hive-agent + cli-lint + advisory
- paired roadmap entry P8.160
- ORTHOGONAL to raw 154 (catalog-deploy producer-side stage discipline) — raw 160 covers consumer-side D1 P1 single-pilot canary

**Raw 161 (algorithm-cross-file-shared-dictionary-cross-link-mandate)**:
- registered at `.raw` slot 161 (slot 158 reassigned 158 → 161 since slot 158 is taken by `design-price-equation-multilevel-selection`)
- 4 falsifiers preregistered (F-RAW161-1..4: cross-link-coverage / per-axis / 30d-drift / raw-148-base-mandate-resolution)
- triad: hive-agent + cli-lint + advisory
- paired roadmap entry P8.161
- ORTHOGONAL to raw 148 (algorithm spec for shared-dict on many-small-files corpus) — raw 161 covers WIRE-AWARE × CONSUMER-AWARE × SELF-DECODING × PLACEMENT cross-link enforcement (raw 7 + raw 152 + raw 155 + raw 156)

**Raw 137 v3 strengthening** (this cycle):
- new `history wire-aware production-chain dichotomy strengthening v3` line at raw 137 etching F8 chain-amortization formula
- `F8_CHAIN_AMORTIZE_GAIN(corpus, A_k) = SAVING(corpus, chain∪{A_k}) − SAVING(corpus, chain)`
- two-axis dichotomy explicit: axis (i) STANDALONE BYTE-CANONICAL WIRE base94/85 ceiling ~25% on H_0; axis (ii) PRODUCTION CHAIN PLACEMENT chain-amortize 78–85% range on low-H_0 structured corpora
- multiplicative composition is raw 137 80% target byte-canonical natural achievement mechanism

**D1 P2 entry gate criteria** (refresh post-D1-P1-LIVE):
1. D1 P1 canary 7-day window completes (target 2026-05-05) with canary-window-coverage ≥ 0.50, canary-divergence-rate == 0.00, rollback-byte-eq-rate == 1.00
2. raw 160 self-apply at registration PASS (this commit) + 1+ sister repo applies consumer-canary discipline within 30d
3. D1 P2 wave 1 candidate consumer list (§1) confirmed against 7-day actual divergence telemetry
4. raw 142 D2 try-and-revert wrapper integrated at every wave gate (not just P1)
5. paired-adoption: 2+ consumers in W1 simultaneously canary'd to verify cross-consumer divergence detection

**Witness ledger this cycle**: `anima/state/format_witness/2026-04-28_d1p1_canary_raw156_158.jsonl` (12 rows: cycle header + pilot migration + canary tool create + initial tick + hive init absorption + rollback verify + raw 160 register + raw 161 register + raw 137 v3 strengthen + chflags cycle + D1 P2 entry gate refresh + verdict).

**raw 102 disposition**: ADD-new (not STRENGTHEN-existing) for raws 160 + 161 — both have ORTHOGONAL scope axes vs existing raws 154 / 148 (consumer-canary vs catalog-deploy; 4-axis cross-link vs algorithm spec). Slot reassignment justified per raw 102 binary disposition rule.

**Closing honest C3 (raw 91)**: D1 P1 canary cadence is currently 1 tick (day 0). F-D1-2 (cadence ≥ 50% over 7d) will only be evaluable after 4+ days of canary cron ticks. The hive init absorption is registered but actual launchd plist install + 30-min cron cycle execution is a separate manual step (per raw 99 acknowledged-exception path). The 7-day window report subcommand (`hexa hxc_d1_canary_watcher.hexa report --window-days=7`) confirms 14% coverage at day 0 (1/7) and emits F-D1-2 FAIL until cadence accumulates — this is **expected behavior**, not a defect.
