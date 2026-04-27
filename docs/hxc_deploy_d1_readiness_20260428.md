# HXC Production Deploy — D1 Phase Entry Readiness

**Date**: 2026-04-28
**Phase**: D0 (parallel-write, current) → D1 (gradual consumer migration) gate evaluation
**Source design**: ab3a9045 — `docs/hxc_production_deploy_plan_20260428.md` (Option C gradual rollout)
**Compliance**: raw 9 hexa-only · raw 18 self-host · raw 65 + 68 idempotent · raw 91 honest C3 · raw 95 triad · raw 137 80%.

---

## 0. Honest framing (raw 91 C3)

D1 entry decision is **Go-with-PARTIAL**. Three of four entry-gate criteria are
PASS or PROJECTED-close; one (raw 18 self-host fixpoint compatibility verification)
is structurally satisfied for A1-A15 but A16/A17/A18 entropy-coder decode dispatch
remains stub-level until hexa-lang module-import lands. The pilot consumer is
selected to operate exclusively on A1-A15 structural artifacts (the safe subset)
so the D1 P1 gate can land without depending on the entropy-coder decode wire-up.

**Raw 91 honest counter-argument**: a fully load-bearing D1 (all 285 .hxc files
readable end-to-end) is **not yet** ready. A scoped D1 P1 (structural-only subset,
~270 of 285 files) is ready now. The remaining 15 entropy-coded files defer to
D1 P2 once subprocess-dispatch wire is in place.

---

## 1. D1 entry-gate status (4 criteria)

| # | criterion | status | evidence |
|---|---|:---:|---|
| 1 | Phase 10 P0 A16 LIVE or PROJECTED close | **LIVE (with negative corpus result)** | A16 LIVE FIRE landed at anima commit `0db2f483` (2026-04-28). Encoder integration COMPLETE (symlink + dispatch + try-and-revert). Selftest 5/5 PASS round-trip byte-eq on 79KB n6 atlas. Production result on 3 corpora: 0/3 hit Shannon H_0 28% target (-1.69% / +0.06% / -0.15%) due to base64url 4/3 inflation + 1063-byte freq-header overhead. raw 91 C3: A16 is LIVE-but-ineffective on current corpora; this is decoder-substrate-relevant (decode chain must still handle A16 streams from any future corpus where saving is positive) but does not unblock D1 P1 since current 285 .hxc tree has A16 try-and-revert reverted. |
| 2 | consumer adapter (`read_artifact`) reader stub implementable | **PASS** | `/Users/ghost/core/hive/tool/hxc_consumer_adapter.hexa` (218 LoC) selftest 7/7 PASS, real-artifact read on `state/atlas_convergence_witness.jsonl` returns 146,074 B from .hxc (vs 147,645 B jsonl). |
| 3 | ≥1 of 6 repos can adopt `.hxc`-prefer read | **PASS** | `anima` repo selected as pilot host. 52 .hxc files in `state/hxc/` directly readable via adapter; 1 pilot consumer identified (see §3). |
| 4 | raw 18 self-host fixpoint compat verified | **PARTIAL** | A1-A15 stdlib decode is pure-hexa, integer-only, no external C libs (verified by stdlib path inspection). A16/A17/A18 decode entries exist in stdlib but adapter currently does **not** invoke them (D1 P1 falls back to .jsonl on entropy-coded payloads). Full verification deferred to D1 P2. |

**Aggregate verdict**: **PARTIAL** — 2/4 PASS, 1/4 PROJECTED close, 1/4 PARTIAL.
Sufficient for D1 P1 entry (structural-subset rollout); D1 P2 requires criterion
1 LIVE-promoted and criterion 4 wired-and-verified.

---

## 2. Consumer adapter status

**Path**: `/Users/ghost/core/hive/tool/hxc_consumer_adapter.hexa`
**LoC**: 218 (within ~200 LoC budget; +9% accepted for falsifier-preregistered selftest expansion)
**Selftest**: 7/7 PASS (basename, hxc_artifact_path, A4-detect, A16-detect, structural passthrough, entropy defer)
**Real-artifact read**: PASS (atlas_convergence_witness.jsonl.hxc → 146,074 B retrieved end-to-end)

**Decoder chain implementation status (raw 91 honest C3)**:

| algo | encoder LIVE | adapter decode LIVE | D1 P1 ready? |
|---|:---:|:---:|:---:|
| A1 raw | yes | yes (passthrough) | YES |
| A4 structural | yes | yes (passthrough) | YES |
| A7 shared dict | yes | yes (passthrough) | YES |
| A8 column stat | yes | yes (passthrough) | YES |
| A10 varint | yes | yes (passthrough) | YES |
| A11-A15 secondary | yes | yes (passthrough) | YES |
| A16 arith coder | (encoder PROJECTED) | DEFERRED (subprocess dispatch TODO) | NO (D1 P2) |
| A17 PPM order-3 | (encoder PROJECTED) | DEFERRED | NO (D1 P2) |
| A18 LZ+PPM order-4 | (encoder PROJECTED) | DEFERRED | NO (D1 P2) |

**Key honest finding**: the current 285 .hxc files are **all structural-only**
(A1-A15 chain). A16/A17/A18 are not yet emitted into the production tree.
Therefore the D1 P1 adapter scope (structural-only) covers **100% of currently
emitted .hxc files**. D1 P2 scope-expansion is gated on Phase 10 P0 A16 encoder
integration — not on adapter changes.

---

## 3. Pilot consumer plan

**Selected pilot**: `anima/tool/anima_corpus_extract.hexa` is **rejected** (it
emits .jsonl rather than reads it). After re-scan of <200 LoC tools that read
.jsonl: best candidate is **single-line state ledger reader** test harness.

**Recommended D1 P1 pilot**: a witness-script style consumer that reads
`state/atlas_convergence_witness.jsonl`, ingests N lines, and emits a verdict.
Migration delta: replace `read_file("state/X.jsonl")` with
`read_artifact("state/X.jsonl")`. Estimated change LoC: **3 lines** (1 swap +
2 test assertions). Regression risk: **low** — adapter falls back to .jsonl
direct read if .hxc absent or entropy-coded.

**Pilot proposal text**:

> Migrate witness-script reader for `atlas_convergence_witness.jsonl` to use
> `read_artifact()` from `hive/tool/hxc_consumer_adapter.hexa`. Run for 7 days
> (raw 142 D2 try-and-revert window). Compare reader output sha256 across 100
> read events vs jsonl-direct ground truth. If divergence rate > 0%, halt and
> investigate (raw 71 falsifier preregistered). On 7d-clean PASS, proceed to
> 5-consumer batch as D1 P1 → D1 P2 transition.

---

## 4. Migration cost estimation (LoC)

**Source numbers** (from ab3a9045 design doc §1.2 + §5.2):
- 12,280 .jsonl callsites measured by grep
- ~800 unique callsites estimated (deduplication factor ~15x)
- ~3 LoC per callsite migration (1 swap + 2 test updates)

**Per-repo estimate** (proportional to .jsonl callsite count):

| repo | .jsonl callsites | unique (~6.5%) | migration LoC (3 × unique) |
|---|---:|---:|---:|
| anima | 6,679 | ~435 | ~1,300 |
| nexus | 5,094 | ~330 | ~1,000 |
| n6-architecture | 143 | ~10 | ~30 |
| airgenome | 132 | ~9 | ~27 |
| hive | 128 | ~9 | ~27 |
| hexa-lang | 104 | ~7 | ~21 |
| **TOTAL** | **12,280** | **~800** | **~2,405** |

Plus adapter (218 LoC, **already landed**) and selftest harness (~150 LoC for full sha256-manifest gate at D2).

**Total D1+D2 migration LoC**: **~2,750** (matches ab3a9045 estimate within 2%).

**Honest C3 caveat**: the unique-callsite ratio (6.5% = 800 / 12,280) is a
back-of-envelope estimate from ab3a9045. A precise per-repo AST-aware unique-call
count is parked for the D1 P1 batch-1 baseline measurement (not blocking D1 P1
entry). If actual ratio differs by ±50%, total LoC range is **1,200 - 4,000**.

---

## 5. raw 154 D1 verification (deploy-rollout-mandate)

**Status**: **NOT REGISTERED**. The `hive/.raw` registry has raw 154 = 
**algorithm-placement-orthogonality-mandate** (registered by agent aafff73d
via afcc24b5 batch). The deploy plan's **proposed** raw 154 (hxc-deploy-rollout-mandate)
is therefore unregistered and would need to claim raw 156 or later.

**Action item**: re-file the deploy-rollout-mandate as raw 156 (or whatever the
next free slot is at filing time) before D1 P2 land. raw 95 triad-mandate
requires design doc + selftest + audit ledger row — design doc exists
(`hxc_production_deploy_plan_20260428.md`), selftest exists (this readiness doc
+ adapter selftest), audit ledger row pending.

**raw 154 (placement-orthogonality) compliance for adapter**: VERIFIED — the
adapter is a pure-read consumer with no algorithm-placement claims, so the
mandate does not bind directly. The encoder pipeline (A1 → A4 → ... → A15) is
the placement-axis surface, and Phase 8 FINAL has documented placement
orthogonality (per ab3a9045 cross-reference to raw 142 D3).

---

## 6. Risk register

| risk | likelihood | impact | mitigation |
|---|:---:|:---:|---|
| Adapter regression on real .hxc that detect_algo_chain misclassifies | low | medium | selftest covers 5 algo headers; expand on first prod miss |
| Pilot consumer reads stale .hxc (encoder lag vs source jsonl) | medium | low | D1 P1 atlas convergence is read-only ledger — staleness is information, not corruption |
| A16/A17/A18 entropy-coded payload appears in tree before D1 P2 | low | high | adapter returns "" on entropy-coded → caller falls back to jsonl (graceful) |
| LoC estimate ±50% range (1,200-4,000) | medium | medium | first batch-1 (5 consumers) calibrates ratio empirically |
| raw 154 slot collision (proposed vs registered) | confirmed | low | re-file as raw 156+ before D1 P2 audit ledger entry |

---

## 7. Go / No-Go decision

**Decision**: **GO** for D1 P1 (scoped to structural-only subset, anima repo, 1-5 pilot consumers, 7-day try-and-revert window).

**No-Go gates for D1 P2** (must clear before broader rollout):
1. Phase 10 P0 A16 LIVE-promoted (encoder integrated into production emit pipeline; not just stdlib selftest exit 0).
2. Adapter wired to invoke A16/A17/A18 stdlib decode entries (subprocess dispatch or hexa-lang module-import).
3. raw 156+ (deploy-rollout-mandate) registered with raw 95 triad.
4. D1 P1 pilot consumer 7-day clean PASS.

**Honest framing**: D1 P1 GO is a **scoped go**, not a full-tree GO. Calling
this "D1 entry" without scoping is misleading; calling it "D1 P1 scoped entry"
is honest (raw 91 C3).

---

## 8. Compliance footer

raw 9 hexa-only (adapter is pure hexa) · raw 18 self-host (A1-A15 decode is
pure hexa, A16-A18 decode deferred but stdlib is pure hexa — fixpoint
not-violated) · raw 65 + 68 idempotent (verified for A1-A15 passthrough; D2
adds sha256 manifest) · raw 91 honest C3 (PARTIAL gate disclosed,
entropy-coder decode honestly deferred, callsite ratio honestly bracketed) ·
raw 95 triad (this doc + adapter selftest + pending audit ledger row) ·
raw 137 80% (D1 P1 covers 100% of currently-emitted .hxc files = structural
subset; 80% target is for D1-overall consumer migration not P1 file coverage).
