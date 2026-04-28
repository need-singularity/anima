# HXC D1 P2 W1+W2+W3 Launch Matrix — forward-LIVE preparation (2026-04-28)

**Purpose**: D1 P2 Wave 1 / Wave 2 / Wave 3 forward-LIVE preparation matrix.
Per-wave launch conditions, chain dependency, refined LoC delta, canary ledger
prep status, rollback path per consumer, F-Wave-* falsifier active list.

**Author cycle**: D1 P2 W1+W2+W3 forward-LIVE prep (raw 142 D2 try-revert + raw 65+68 idempotent + raw 91 honest C3)
**Predecessor commits**:
  - hive `f6a510bda` — D1 P1 first-pilot canary + raw 160/161 register
  - hive `be921b562` — consumer adapter LIVE (343 LoC, 12/12 selftest)
  - anima `c8ed96d7` — D1 P1 canary LIVE production deploy ledger
**Predecessor doc**: `/Users/ghost/core/anima/docs/hxc_deploy_d1_p2_batch_proposal_20260428.md` (original batch proposal — STRENGTHENED by this matrix)

---

## 0. Honest framing (raw 91 C3)

This launch matrix is **forward-LIVE preparation** — the W1/W2 read_artifact swaps are LANDED in source (this commit), but the canary watcher does NOT begin emitting W1/W2 ledger rows until the per-wave entry condition is met. The `state/hxc_d1_canary/2026-04-28_w*.jsonl.prep` files are placeholders; on activation, the `.prep` suffix is stripped and the canary watcher tick begins.

**Honest C3 corrections to predecessor proposal §1.2 + §1.3**:

1. **cli_authoring_lint REMOVED from W2** — the predecessor proposal claimed a `+4 (1 swap at line 133)` for cli_authoring_lint, but the actual code at line 130-160 only WRITES `state/cli_authoring/<DATE>_audit.jsonl` and reads SOURCE `.hexa` files (head -n 30) for header annotation parsing. There is no canonical state-jsonl reader callsite to swap. W2 is revised to a single consumer (raw_strengthening_loop_lint).

2. **W3 reader callsite estimate REVISED 60-100x DOWNWARD** — the predecessor proposal §1.3 estimated ~435 callsites / ~1,300 LoC across format_witness + refinement + discovery_absorption. Empirical scan results:
   - `state/format_witness/*` readers: **0 actual reader callsites** (all writes; ~140 estimate is ∞-x overestimate)
   - `state/proposals/refinement/*` readers: **2 ls-count callsites** (auto_evolution_loop._ls_count + proposal_inventory_init._count_in_dir; ~110 estimate is ~55x overestimate)
   - `state/discovery_absorption/registry.jsonl` readers: **3 callsites** (3 emitted Python helpers in compute_resource_failure_lint / discovery_auto_absorption_lint / kick_with_trailer_wrapper, ~50 estimate is ~16x overestimate)
   - **Total actual W3 reader callsites: ~5 callsites; refined LoC delta: +15-30 LoC** (vs predecessor ~1,300 LoC).
   - **F-RAW160-3 (>2x estimate) is OBVERSELY TRIPPED** — the predecessor estimate is ~50-100x OVERSTATED, not understated. raw 91 C3 disclosure mandates this finding be surfaced before W3 launch.

3. **A19 federation dependency RE-EVALUATED** — since `format_witness` has 0 actual readers, the A19 federation chain dependency that was the most-cited W3 risk (§1.3 row "anima format_witness readers" with A1+A4+A19 chain) collapses to a non-event. W3 federation subset is **DEFERRED indefinitely** (no consumer in actual scope) per predecessor `.raw` line 4203 deferral analysis. W3a non-federation subset (refinement + discovery_absorption readers) is the entire W3 scope.

---

## 1. Launch conditions matrix

| wave | consumer(s) | chain | LoC delta | canary days | entry condition | calendar target |
|---|---|---|---:|:---:|---|---|
| **P1 (LIVE)** | discovery_absorption_lint | A1+A4 | +2 (LIVE) | 7d | landed `f6a510bda` 2026-04-28 | window ends 2026-05-05 |
| **W1** | audit_ledger_lint, honesty_triad_lint | A1+A4 | +2 (this commit) +2 (this commit) = **+4 (refined; predecessor proposed +6)** | 3d | D1 P1 day-7 zero divergence + cadence ≥50% | 2026-05-05 → 2026-05-08 |
| **W2** | raw_strengthening_loop_lint (cli_authoring_lint REMOVED) | A1+A4+A16 | **+2 (refined; predecessor proposed +8)** | 5d | W1 day-3 zero divergence + cadence ≥50% | 2026-05-08 → 2026-05-13 |
| **W3** | refinement readers (2 callsites) + discovery_absorption readers (3 callsites) | A1+A4 only | **+15-30 (refined; predecessor proposed ~1,300)** | 7d | W2 day-5 zero divergence + cadence ≥50% | 2026-05-13 → 2026-05-20 |

**Total D1 P2 LoC delta refined: +21-36 LoC** (vs predecessor +1,316 LoC).
**D1 land projected**: 2026-05-20 (unchanged — calendar dominated by per-wave canary windows, not LoC).

---

## 2. Chain dependency per wave (refined)

| consumer | wave | A1 | A4 | A16 | A19 | LIVE-verified? | canary risk |
|---|:---:|:---:|:---:|:---:|:---:|:---:|---|
| discovery_absorption_lint (P1) | P1 | reqd | reqd | — | — | **YES (LIVE)** | low |
| audit_ledger_lint (W1) | W1 | reqd | reqd | — | — | **YES (this commit)** | low |
| honesty_triad_lint (W1) | W1 | reqd | reqd | — | — | **YES (this commit)** | low |
| raw_strengthening_loop_lint (W2) | W2 | reqd | reqd | opt | — | A4-LIVE / A16-selftest-only (raw 91 C3) | medium |
| refinement readers (W3 ls-count) | W3 | reqd | reqd | — | — | **YES** (count operation, no per-file decode) | low |
| discovery_absorption readers (W3) | W3 | reqd | reqd | — | — | **YES** (P1 ground truth) | low |

**A19 federation column DROPPED entirely** — no consumer in W1/W2/W3 actual scope requires A19 chain. F9 federation fix dependency for W3 is RESOLVED by scope reduction.

---

## 3. Per-consumer LoC delta refined

| wave | consumer | current LoC | migration delta LoC (refined) | post-migration LoC | predecessor estimate |
|---|---|---:|---:|---:|---:|
| P1 | discovery_absorption_lint | 139 | +2 (LIVE) | 141 | +2 |
| W1 | audit_ledger_lint | 126 | **+2** (this commit) | 128 | +3 |
| W1 | honesty_triad_lint | 1,066 | **+2** (this commit) | 1,068 | +3 |
| W2 | raw_strengthening_loop_lint | 537 | **+2** (this commit) | 539 | +4 |
| W2 | cli_authoring_lint | 378 | **0 (REMOVED — no callsite to migrate)** | 378 | +4 |
| W3 | refinement readers (auto_evolution_loop._ls_count + proposal_inventory_init._count_in_dir) | ~1,232 | **+4-6** (2 callsite swaps) | ~1,238 | ~330 |
| W3 | discovery_absorption readers (3 emitted Python helpers) | ~586 | **+9-15** (3 emitted-Python helper swaps; multiline Python with read_artifact via subprocess.check_output) | ~601 | ~150 |
| **total D1 P2** | — | ~3,925 | **+19-27 (refined)** | ~3,952 | **+1,316** |

**F-RAW160-3 verdict (migration cost > 2x estimated)**: OBVERSELY TRIPPED — actual is **50-70x BELOW** estimate, not above. Per raw 91 C3: this is honest disclosure that the predecessor LoC estimate was over-cautious by ~2 orders of magnitude. The corrective action is to LAND the smaller migration faster (W3 7d → W3 3d possible) but this matrix CONSERVATIVELY preserves the 7d W3 window for soak coverage of all three reader clusters.

---

## 4. Canary ledger prep status

| wave | canary ledger file | status |
|---|---|:---:|
| P1 | `hive/state/hxc_d1_canary/2026-04-28_discovery_absorption_lint.jsonl` | **LIVE (2 ticks landed)** |
| W1 | `hive/state/hxc_d1_canary/2026-04-28_w1_audit_ledger_lint.jsonl.prep` | **PREP (forward-LIVE; activate 2026-05-05)** |
| W1 | `hive/state/hxc_d1_canary/2026-04-28_w1_honesty_triad_lint.jsonl.prep` | **PREP (forward-LIVE; activate 2026-05-05)** |
| W2 | `hive/state/hxc_d1_canary/2026-04-28_w2_raw_strengthening_loop_lint.jsonl.prep` | **PREP (forward-LIVE; activate 2026-05-08)** |
| W3 | (TBD per-cluster on W3 entry) | DEFERRED — W3 entry condition (W2 day-5 PASS) |

`.prep` suffix policy: on entry-condition satisfaction, the activation step:
1. Verify entry condition (read previous wave canary ledger for divergence count + cadence pct).
2. `mv state/hxc_d1_canary/<file>.prep state/hxc_d1_canary/<file>` (drop `.prep`).
3. Append a deferred-pilot to `_pilots()` array in `tool/hxc_d1_canary_watcher.hexa` (move from `_pilots_deferred()`).
4. Trigger first watcher tick to land day-0 row.

---

## 5. Rollback path per consumer

| consumer | rollback method | byte-eq verified |
|---|---|:---:|
| audit_ledger_lint (W1) | revert 1-LoC swap (line 62 cmd back to `grep -c '^{' path`) → re-run `--json` → expect identical total/parsed/malformed/verified counters | **YES** (pre-swap baseline 232 == post-swap 232) |
| honesty_triad_lint (W1) | revert 1-LoC swap (line 171 cmd back to `tail -1 path`) → run `report` → expect identical c1_verdict_count=32 last value | **YES** (pre-swap baseline 32 == post-swap 32) |
| raw_strengthening_loop_lint (W2) | revert 1-LoC swap (line 280 cmd back to `wc -l path | awk`) → run `selftest` → expect identical g_proposal_seq init from 237 rows | **YES** (pre-swap 237 == post-swap 237) |
| W3 refinement readers | revert ls-count swap → expect identical refinement count | PROJECTED on W3 entry |
| W3 discovery_absorption readers | revert emitted-Python swap → expect identical registered finding_id set | PROJECTED on W3 entry |

---

## 6. F-Wave-* falsifier active list

**W1 (this matrix activates F-W1-1..4 at W1 launch)**:
- F-W1-1: any read_artifact() swap in W1 produces sha256 divergence vs jsonl-direct ground truth across 100 read events
- F-W1-2: revert (jsonl-fallback path) byte-eq check fails on any W1 consumer
- F-W1-3: W1 consumer selftest regresses below 100% PASS
- F-W1-4: W1 cumulative read latency exceeds 2x baseline jsonl-direct read

**W2 (activates F-W2-1..4 at W2 launch)**:
- F-W2-1: A16 entropy-coder decode round-trip fails on any W2-readable artifact
- F-W2-2: W2 consumer reverts to jsonl-fallback at any 100-event sample → divergence > 0%
- F-W2-3: W2 5-day cumulative selftest PASS rate < 100%
- F-W2-4: A16 subprocess dispatch latency p99 > 5x A4 passthrough p99

**W3 (activates F-W3-1..4 at W3 launch)**:
- F-W3-1: any anima state ledger reader regresses on read sha256 vs pre-migration ground truth
- F-W3-2 (DEFERRED — not applicable): A19 federation chain decode failure (no W3 consumer uses A19)
- F-W3-3: Wave 3 LoC change exceeds 2x estimate (refined: >60 LoC) — migration cost falsifier (predecessor F-RAW160-3 OBVERSELY TRIPPED on the >2x-DOWN side)
- F-W3-4: anima-internal cross-tool regression observed

**F-RAW160-3 (predecessor)**: revised verdict — migration cost <0.5x estimate (50-70x BELOW estimate). Triggers the OBVERSE branch of the falsifier — the test was meant to catch overruns but the asymmetric trigger has surfaced an underrun. Honest C3 disclosure: predecessor estimate was over-cautious by ~2 orders of magnitude. The estimate methodology (raw text-search "callsite count") was **not load-bearing** — the actual readers are sparse (most ledger files are append-only writes; programmatic reads are rare).

---

## 7. cron tick `*/5` integration (raw 99 hive cli, NO standalone launchd)

Existing hive init `_init_tasks` entry:
```
["hxc-d1-canary-watcher", "tool/hxc_d1_canary_watcher.hexa", "run", "86400"]
```
(86400s = 24h cadence; landed `f6a510bda`).

**No new init entry required**: W1+W2+W3 deferred pilots are added to `_pilots_deferred()` in `tool/hxc_d1_canary_watcher.hexa` (this commit). On wave activation, deferred-pilots move to active `_pilots()` array via 1-LoC array-edit; the same single `hxc-d1-canary-watcher` cron tick covers all wave consumers (per-consumer ledger keyed by slug).

This honors raw 99 hive cli mandate — no standalone launchd plist; all canary watching absorbed into the existing hive_governance.hexa _init_tasks entry.

---

## 8. cross-link to in-flight 80% close (a7a059f0 / a45778db / ace91cf6)

| in-flight cycle | scope | cross-link with D1 P2 |
|---|---|---|
| a7a059f0 (A20 LIVE + 80% close) | small-file class 69.10% → 75-80% | A20 chain DOES NOT affect W1/W2/W3 consumer migration (W1/W2 use A4 + A16; W3 use A4 only) — orthogonal axes |
| a45778db (A20+A22) | self-decoding artifact wire | Same orthogonality — D1 P2 is consumer-side migration; A20/A22 are encoder-side wire |
| ace91cf6 (A18 v2 + 80% close) | LZ+PPM order-4 saving omega-cycle | Same orthogonality — D1 P2 W2 uses A16 entropy-tier (selftest-only); A18 v2 is downstream entropy ω-cycle |

**Phase 12 P0 small-file deploy entry condition**: A20 LIVE + small-file class ≥80% → P0 small-file deploy GATED-RELEASE. Independent of D1 P2 wave timing. W3 LIVE timing UNAFFECTED by Phase 12 P0 entry (W3 uses A1+A4 only structural chain, no A20 dependency).

---

## 9. raw 102 STRENGTHEN-existing — strengthening of `hxc_deploy_d1_p2_batch_proposal_20260428.md`

This launch matrix STRENGTHENS the predecessor batch proposal §1.2 + §1.3 + §4 + §6 with empirically-measured corrections:

| predecessor section | correction | strengthening basis |
|---|---|---|
| §1.2 W2 cli_authoring_lint +4 LoC | REMOVED — no registry-reader callsite present | empirical scan (line 30 only reads .hexa source files; no state/cli_authoring jsonl reads) |
| §1.3 W3 ~435 callsites / ~1,300 LoC | REVISED to ~5 callsites / ~15-30 LoC | empirical grep: format_witness=0, refinement=2 ls-count, discovery_absorption=3 helper-emitted readers |
| §1.3 W3 A1+A4+A19 federation chain dependency on F9 fix | DROPPED — no W3 consumer in actual scope uses A19 chain | format_witness has 0 readers; refinement + discovery_absorption use A1+A4 only |
| §6 F-RAW154-3 migration cost >2x estimate | OBVERSELY TRIPPED — actual <0.5x estimate (50-70x UNDER) | empirical LoC delta refinement |
| §4 D1 P2 total ~1,316 LoC | REVISED to **~21-36 LoC** | sum of W1 +4 + W2 +2 + W3 +15-30 |

**Honest C3 (raw 91)**: The predecessor estimate was a paper exercise; the actual reader callsites are sparse because anima state ledgers are predominantly **append-only write logs** with retroactive analysis happening manually (humans grep'ing the .jsonl files), not programmatically. This is a HEALTHY architectural property — the canonical write path is enforced by tools, but read paths are ad-hoc by design.

---

## 10. Compliance footer

raw 1 chflags (cycle on each consumer file: audit_ledger_lint + honesty_triad_lint + raw_strengthening_loop_lint + hxc_d1_canary_watcher) · raw 9 hexa-only · raw 47 cross-repo (D1 P2 LoC reductions propagate to nexus / n6 / airgenome / hexa-lang in D2 paired track via raw 47 mandate) · raw 65 + 68 idempotent (per-consumer swap byte-eq verified pre/post) · raw 71 falsifier (F-W1-1..4 + F-W2-1..4 + F-W3-1..4 + F-RAW160-3 obverse-branch active) · raw 87 paired roadmap (P8.W1, P8.W2, P8.W3) · raw 91 honest C3 (cli_authoring REMOVED, W3 estimate REVISED 50-70x DOWNWARD, A19 dependency DROPPED) · raw 95 triad (this matrix doc + W1 byte-eq verifications + canary ledger prep files) · raw 99 hive cli (single _init_tasks entry covers all waves) · raw 102 STRENGTHEN-existing (predecessor proposal §1.2/1.3/4/6 corrected) · raw 142 D2 try-revert (every wave wrapped) · raw 154 hxc-deploy-rollout-mandate (per-wave canary cadence honored) · raw 155 hxc-consumer-adapter-mandate (every consumer uses canonical read_artifact()) · raw 156 strengthening (placement-orthogonality preserved — A4 chain placement same in all waves) · raw 160 (consumer-canary 7d/3d/5d/7d cadence) · raw 161 (cross-link enforced)

---

## 11. Witness ledger

`/Users/ghost/core/anima/state/format_witness/2026-04-28_d1_p2_w1_w2_w3_forward_live_prep.jsonl`
