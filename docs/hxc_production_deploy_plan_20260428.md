# HXC Production Deploy Plan — Consumer Migration Beyond Phase 8 FINAL

**Date**: 2026-04-28
**Phase**: Production Deploy (D0 → D3)
**Trigger**: Phase 8 FINAL 282 files / 6 repos / 5.22MB → 2.76MB (48% byte-weighted)
landed, but production consumers still read `.jsonl` exclusively. Without consumer
integration, the byte saving is theoretical (encoder-side only, never realized
as runtime-reduced I/O or reduced disk inventory).
**Compliance**: raw 9 hexa-only · raw 18 self-host fixpoint · raw 65 + 68 idempotent ·
raw 71 falsifier-preregistered · raw 91 honest C3 · raw 95 triad-mandate · raw 137 80%.

---

## 0. Honest framing (raw 91 C3)

All saving numbers are **encoder-side measured**. Consumer-side savings are
**PROJECTED** until D2/D3 land — current state is **parallel-write** with
`.jsonl` as the load-bearing path. Until consumers cut over, the 48% saving
is a sunk encoder cost, not realized value (raw 91 C3 ROI honesty).

A "successful" Phase 8 FINAL whose savings never reach a consumer is the
canonical anti-pattern this doc preempts (raw 142 self-correction discovery,
applied prospectively).

---

## 1. Current-state audit (MEASURED 2026-04-28)

### 1.1 `.hxc` artifact inventory across 6 repos

| repo | `.hxc` count | size | parallel `.jsonl`? |
|---|---:|---:|:---:|
| nexus | 96 | 636K | yes (full mirror) |
| anima | 52 | 1.7M | yes (full mirror) |
| n6-architecture | 69 | 368K | yes (full mirror) |
| hexa-lang | 11 | 220K | yes (full mirror) |
| hive | 54 | 396K | yes (full mirror) |
| airgenome | 3 | 24K | yes (full mirror) |
| **TOTAL** | **285** | **~3.3M** | **6 / 6 parallel** |

(Encoder-side rollup: 282 in Phase 8 FINAL doc + 3 incremental; close enough.
Both paths exist on disk simultaneously today.)

### 1.2 Consumer-side `.jsonl` reader census (MEASURED grep)

`grep -rEln "\.jsonl"` across `*.py *.hexa *.sh *.js *.ts`:

| repo | files referencing `.jsonl` | files referencing `.hxc` | gap |
|---|---:|---:|---:|
| nexus | 5094 | 0 | 5094 |
| anima | 6679 | 0 | 6679 |
| n6-architecture | 143 | 0 | 143 |
| hexa-lang | 104 | 8 | 96 |
| hive | 128 | 4 | 124 |
| airgenome | 132 | 0 | 132 |
| **TOTAL** | **12,280** | **12** | **12,268** |

**Observation**: `.hxc`-aware code is essentially zero. 12 files (hexa-lang +
hive) reference `.hxc` at all, and inspection confirms those are emitter-side
witnesses, not readers. **Zero production consumers read `.hxc` today.**

### 1.3 Transitional pattern (parallel-write, MEASURED)

For every artifact `X.jsonl` emitted, the toolchain also emits `state/hxc/X.jsonl.hxc`
(name-mangled to preserve provenance). Consumers continue to read the original
path. The .hxc tree is therefore a **read-only shadow** at present.

---

## 2. Migration deploy options (4 evaluated)

### Option A — parallel-write (status quo, baseline)
- `.jsonl` + `.hxc` both emitted; consumers read `.jsonl` only.
- Pros: backward compat 100%; zero consumer change; can A/B encoder.
- Cons: **storage 2x** (5.22MB jsonl + 2.76MB hxc = 7.98MB ≥ jsonl-only 5.22MB).
  ROI = 0 because 48% saving is offset by parallel emission.
- Verdict: **default for D0 only**, not a destination.

### Option B — flag-day cutover
- All 6 repos flip in one commit: stop emitting `.jsonl`, emit `.hxc` only;
  all 12,280 consumer references rewritten in lockstep.
- Pros: storage 48% realized immediately (5.22MB → 2.76MB).
- Cons: coordinated patch across 6 repos; if any reader is missed (out-of-tree
  scripts, cron, external dashboards), silent data-loss-equivalent (file disappears).
  Rollback requires re-emitting `.jsonl` from `.hxc` (decoder must exist + match exactly).
- Verdict: **rejected** — raw 91 C3 honest: 12,268-line mass rewrite without
  staging is a falsifier-likely event (cf. raw 142 lessons).

### Option C — gradual rollout (Phase 8 FINAL pivot)
- Consumers updated to be `.hxc`-aware progressively, with `.jsonl` fallback.
  Reader pseudocode:
  ```
  read_artifact(name):
    if exists(state/hxc/<name>.hxc):
      return decode_hxc(state/hxc/<name>.hxc)
    elif exists(<name>):  # .jsonl fallback
      return read_jsonl(<name>)
    else: error
  ```
- Pros: per-consumer rollout, regression-bounded (any unmigrated consumer
  keeps reading `.jsonl`); storage 2x during transition only; reversible.
- Cons: transition window storage stays at parallel-write (no immediate ROI);
  decoder chain must exist and be byte-identical (raw 65 + 68 idempotent).
- Verdict: **RECOMMENDED** — minimum-blast-radius path with measurable per-phase exit.

### Option D — HXC-native artifacts (Phase 11 P3 self-decoding)
- Phase 11 A22 self-decoding HXC: every `.hxc` carries inline its decoder
  ID + dictionary + algorithm chain so a generic reader can dispatch
  (no out-of-band schema). Consumers read `.hxc` directly via a single
  hxc-reader stub (~200 LoC), no per-artifact codec knowledge.
- Pros: collapses 12,280 readers into one library call; raw 18 self-host
  fixpoint reached naturally (artifact + decoder co-located); future
  algorithms add zero consumer LoC.
- Cons: requires Phase 11 A22 implementation (~500 LoC self-decoding spec
  + format-version field + decoder-bytecode embed) which is **not yet LIVE**.
  Cannot deploy until A22 lands.
- Verdict: **destination state**; D3 is *the bridge to* Option D, not Option D itself.

### Recommended path
**Option C → eventually Option D**: gradual rollout (D0 → D3) gets to `.hxc`-only
emission with the current decoder chain (A18 → ... → A1). When Phase 11 A22 ships
(self-decoding), the consumer-side reader stub from D1 trivially upgrades to a
generic dispatcher with no further consumer churn.

---

## 3. Consumer adapter design

### 3.1 Reader stub contract (~200 LoC, `lib/hxc_reader.hexa`)

```
read_artifact(logical_name) -> bytes_or_records:
  hxc_path = "state/hxc/" + logical_name + ".hxc"
  if exists(hxc_path):
    raw = decode_chain(hxc_path)             // see 3.2
    assert sha256(raw) == manifest_hash      // raw 65 + 68 idempotent gate
    return raw
  return read_file(logical_name)             // .jsonl fallback (D0/D1 phases)
```

### 3.2 Decoder chain (reverse of encoder pipeline)

Encoder emits algorithms in order A1 → A4 → A7 → ... → A18. Decoder
unwraps in reverse: **A18 → A17 → A16 → A15 → A14 → A13 → A12 → A11 →
A10 → A8 → A7 → A4 → A1**. Each `.hxc` payload carries an algorithm-chain
header listing the actually-fired sequence, so the decoder skips no-op steps.

### 3.3 Idempotency gates (raw 65 + 68)
- `decode(encode(x)) == x` byte-equal (raw 65).
- `encode(decode(y)) == y` byte-equal for any well-formed `.hxc` `y` (raw 68).
- Both directions must be enforced by selftest at every D-phase entry.

### 3.4 Test plan
- Selftest sweep across all 285 `.hxc` files — D0 entry gate.
- Per-consumer canary: one consumer migrated, run for 7 days, compare
  reader-output sha256 across 100 read events vs `.jsonl` ground truth.

---

## 4. Rollout phases (D0 → D3)

### Phase D0 — parallel-write (CURRENT, 2026-04-28)
- Entry: Phase 8 FINAL landed; all repos emit both paths.
- Exit gate: decoder selftest 285/285 byte-equal PASS; reader stub merged.
- Falsifier: any decode mismatch on existing `.hxc` → block D1 entry, fix
  encoder or extend decoder chain first (raw 71 preregistered).

### Phase D1 — gradual consumer migration (~6 weeks projected)
- Per-consumer change: swap `read_jsonl(p)` → `read_artifact(p)` (drop `.jsonl`).
- Order: lowest-traffic consumers first (witness scripts, audit-only readers),
  then mid-traffic (training corpus loaders), then high-traffic last.
- Per-consumer canary 7d before next batch.
- Exit gate: ≥80% of `.jsonl`-referencing files migrated to `read_artifact`
  (raw 137 80% Pareto threshold).
- Falsifier: any production read mismatch (sha256 != manifest) — halt batch,
  rollback consumer to `.jsonl`-direct, investigate before resume.

### Phase D2 — `.jsonl` deprecation warning
- Encoder still emits `.jsonl` but stamps `.deprecated` sidecar.
- Any consumer that reads `.jsonl` directly logs `[HXC-DEPRECATED] <path>` once
  per process at INFO; SIEM/dashboard surfaces unmigrated callers.
- Duration: until deprecation log count hits zero across two consecutive 24h
  windows.
- Exit gate: zero deprecation log emissions for 48h consecutive (MEASURED, not projected).
- Falsifier: any external/cron consumer surfaces in deprecation log → extend
  D2 by ≥2 weeks per finding.

### Phase D3 — `.hxc`-only emission (cutover)
- Encoder stops emitting `.jsonl`. Storage 48% realized.
- All consumers go through reader stub.
- Optional: `.jsonl`-on-demand decoder for human-debug only (`hxc cat <file>`).
- Exit gate: 30-day stable run, zero rollback events.
- Bridge to Option D: when Phase 11 A22 self-decoding lands, reader stub
  upgrades from "static decoder chain" to "header-driven dispatcher" with
  zero consumer-side change.

### D-phase entry/exit summary

| phase | entry | exit | duration | falsifier |
|---|---|---|---:|---|
| D0 | Phase 8 FINAL | 285/285 selftest PASS | now | decode mismatch |
| D1 | reader stub merged | ≥80% consumers migrated | ~6 wks | sha256 mismatch in canary |
| D2 | D1 exit + dep warn live | 48h zero-log | ~2 wks | external consumer surfaced |
| D3 | D2 exit | 30d stable | ongoing | rollback event |

---

## 5. Cost / benefit analysis

### 5.1 Storage saving (MEASURED + extrapolated)
- Current 6-repo state: 5.22 MB `.jsonl` → 2.76 MB `.hxc` = **2.46 MB saved (48%)**.
- 282 files snapshot. Future-state files not yet emitted. Assume monotone
  growth at observed rate (Phase 5 → Phase 8: ~8 → 282 files in ~3 weeks),
  then 12-month projected file count ~ **5,000-15,000** across 6 repos.
- Per-file mean saving (282 files): 2.46 MB / 282 = **8.7 KB / file**.
- 12-month projected cumulative saving: **40 MB - 130 MB** range (PROJECTED, raw 91 C3).
  Modest in absolute terms; meaningful for git-history bloat and LLM-context-window
  ingestion (where bytes are billed).

### 5.2 Migration cost (LoC estimate)
- Reader stub: **~200 LoC** (`lib/hxc_reader.hexa`, decoder chain dispatch).
- Per-consumer migration: **~3 LoC mean** (one-line swap + 2 lines test update).
- Estimated migrated consumers (D1 80% target of 12,280 references, but many
  are duplicate references in same file → estimated **~800 unique callsites**):
  800 × 3 = **2,400 LoC** distributed across 6 repos.
- Decoder selftest harness: **~150 LoC** (one-time).
- **Total migration LoC: ~2,750 LoC** (one-time, distributed).

### 5.3 ROI
- Direct: 2.46 MB now × ~5x growth = ~12 MB saved at 12mo. Marginal.
- Indirect (the actual win):
  1. **Forces decoder existence** (currently encoder-only; raw 18 self-host
     fixpoint not closed without decoder LIVE).
  2. **Validates raw 65 + 68 idempotency at production scale** (currently
     only encoder-test verified).
  3. **Unlocks Phase 11 A22 self-decoding** — reader stub is the substrate.
- Strategic ROI: HXC ceases to be a vanity metric and becomes load-bearing
  infrastructure. **This is the load-bearing reason to deploy.**

### 5.4 Honest counter-argument (raw 91 C3)
At 12 MB / 12mo absolute savings, pure storage ROI does not justify ~2,750
LoC of distributed change. The deploy is justified **only if** the indirect
benefits (decoder, idempotency, A22 substrate) are accepted as the real
deliverable. If those are deferred, **Option A (parallel-write) remains the
honest default** until A22 reframes the calculation.

---

## 6. Raw registration candidates

### Proposed raw 154 — hxc-deploy-rollout-mandate
**Statement**: HXC consumer migration MUST follow the D0 → D1 → D2 → D3 sequence.
Skipping phases (e.g. D0 → D3 flag-day cutover) is prohibited unless a written
falsifier-preregistered exception is filed.
**Rationale**: prevents 12,268-line mass rewrite without staging; encodes
raw 142 self-correction lesson prospectively.
**Falsifier**: a flag-day cutover delivered without phase-by-phase canary that
nonetheless ships zero regressions for 30d would falsify this raw.

### Proposed raw 155 — hxc-consumer-adapter-mandate
**Statement**: Any new consumer reading state artifacts MUST go through the
HXC reader stub (`read_artifact(name)`), not direct `read_jsonl()`. New
consumers reading `.jsonl` directly are a raw 95 triad violation.
**Rationale**: prevents D1/D2/D3 progress from being reversed by new code;
ensures the migration is monotone.
**Falsifier**: a new consumer landing with direct `.jsonl` read that
demonstrably outperforms `read_artifact` on latency by ≥10x would falsify
(performance escape valve).

(Both raw entries are **proposals**, not registered. Filing requires raw 95
triad: design doc + selftest + audit ledger entry.)

---

## 7. Risk register

| risk | likelihood | impact | mitigation |
|---|:---:|:---:|---|
| Decoder bug → silent data corruption | low | critical | raw 65 + 68 selftest at every phase entry; sha256 manifest |
| External cron/dashboard reads `.jsonl` directly | medium | high | D2 deprecation log surfaces these before D3 |
| Phase 11 A22 slips → reader stub never simplifies | medium | low | D3 still works with static decoder chain; A22 is upside |
| LoC budget overrun (~2,750 underestimate) | medium | medium | per-consumer migration is pure mechanical; cap each batch at 50 callsites |
| Consumer migration regresses Phase 10 P0/P1/P2 measurement | low | high | freeze D1 during any active Phase 10 measurement window |

---

## 8. Open questions (parked for review)

- Should `.hxc` extension be `.hxc` or `.jsonl.hxc` long-term? (Currently `.jsonl.hxc`
  preserves provenance; `.hxc` is cleaner post-D3.)
- Reader stub language: hexa-only (raw 9) blocks Python/JS consumers from a
  shared lib. Either (a) port stub per-language or (b) require subprocess shell-out
  to `hexa decode`. Decision deferred to D1 entry.
- D3 cutover commit: single repo-by-repo or atomic across all 6? Recommend
  repo-by-repo to keep blast radius bounded.

---

## 9. Decision

**Recommend: adopt Option C (gradual rollout D0 → D3), file raw 154 + raw 155
proposals, schedule D0 exit selftest sweep this cycle, target D1 entry within
2 weeks pending decoder-stub merge.**

The honest case for deploy is **raw 18 self-host closure + A22 substrate**, not
absolute byte savings. Parallel-write remains the default until decoder is
production-grade.
