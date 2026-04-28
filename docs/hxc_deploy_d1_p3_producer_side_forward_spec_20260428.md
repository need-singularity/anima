# HXC Production Deploy — D1 P3 Producer-Side Migration Forward-Spec

**Date**: 2026-04-28
**Phase**: D1 P3 (producer-side migration) forward-spec — entry GATED on D1 P2 W1+W2+W3 PASS
**Predecessor**:
  - D1 P1 single pilot canary (commit a3ac440a, in-flight) — `discovery_absorption_lint` LIVE 2026-04-28
  - D1 P2 batch proposal `docs/hxc_deploy_d1_p2_batch_proposal_20260428.md` (Wave 1/2/3 multi-consumer scope)
  - hxc_pre_encoder tool landing (`/Users/ghost/core/anima/tool/hxc_pre_encoder.hexa`, 236 LoC, 3/3 selftest PASS)
  - A19 PASS 0.5 HXC-pre-encode production LIVE FIRE measurement (this tick — `state/format_witness/2026-04-28_a19_pass_0_5_hxc_pre_encode_production.jsonl`)
**Compliance**: raw 1 chflags · raw 9 hexa-only · raw 18 self-host · raw 47 cross-repo · raw 65+68 idempotent · raw 71 falsifier-preregister · raw 91 honest C3 · raw 137 80%-Pareto cmix-ban · raw 142 D2 try-revert · raw 154 deploy-rollout · raw 155 consumer-adapter

---

## 0. Honest framing (raw 91 C3)

This is **forward-spec, not promotion-pending**. D1 P3 entry is GATED on:
- D1 P2 W1+W2+W3 7-day clean PASS (target 2026-05-15+)
- producer-side byte-eq invariant + downstream consumer compat MEASURED
- F-D1-3 falsifier preregistration (this doc, §3)

**Honest counter-arguments**:
- A19 PASS 0.5 (commit d6a524ca) production deployment is **BLOCKED** as of 2026-04-28 LIVE FIRE — refinement-class small-file 92.5% round-trip byte-eq fail (F-A19-6b TRIPPED). Producer-side scope must be reduced to **A1-only structural pre-encode** until A19 v2 decoder ω-cycle fixes whitespace canonicalization OR PASS 0.5 is replaced with A20 schema-aware BPE.
- Pre-encoding overhead is **corpus-class-conditional**: -2.19pp on n6-iter (slight compression), -1.92pp on text-heavy, **+14.70pp on refinement small-file class** (prohibitive). Uniform deployment WILL REGRESS aggregate.
- D1 P3 is **not** a flag-day — it is staged per-producer per-corpus-class with forced canary cadence (raw 154).

---

## 1. D1 P3 candidate producers (per-producer breakdown)

### 1.1 Wave 1 — A1-only structural pre-encode (LOW risk, MEASURED-NEUTRAL)

| producer | path | corpus class | pre-encode delta | A19 PASS 0.5 status | migration LoC |
|---|---|---|---:|:---:|---:|
| **format_witness_writer** | `anima/tool/format_witness_writer.hexa` (proxy: per-cycle witness emit) | text-heavy | -1.92pp MEASURED | NO (0pp delta, 0 dict entries) | +20 (structural-only emit shim) |
| **atlas_emit** | `n6-architecture/tool/atlas_emit.hexa` (n6 atlas_convergence_witness writer) | mixed-real | PROJECTED -2pp (text-heavy class behavior) | NO (no schema diversity) | +20 |
| **honesty_triad_writer** | `hive/tool/honesty_triad_writer.hexa` (raw 91 triad audit emit) | structured-audit | PROJECTED 0pp (already in chain) | NO (chain-amortize saturated) | +15 (passthrough — already HXC-compatible) |

**Wave 1 totals**: 3 producers, +55 LoC migration delta. **A1-only structural pre-encode** (no PASS 0.5).
**Risk class**: LOW — neutral storage delta, raw 65+68 idempotency preserved (LIVE FIRE 25/25 + 5/5 round-trip byte-eq PASS this tick).
**Entry condition**: D1 P2 W1 (audit-only A4 chain) 7-day clean PASS.

### 1.2 Wave 2 — A1+A4 structural pre-encode (LOW-MED risk, structured-audit class)

| producer | path | corpus class | pre-encode delta | A19 PASS 0.5 status | migration LoC |
|---|---|---|---:|:---:|---:|
| **audit_ledger_emit** | `hive/tool/audit_ledger_emit.hexa` (raw 95 audit ledger writer) | structured-audit | PROJECTED 0pp | NO | +25 (A4 column-rotation entry shim) |
| **discovery_absorption_emit** | `hive/tool/discovery_absorption_emit.hexa` (lint-paired writer) | structured-audit | PROJECTED 0pp | NO | +25 |

**Wave 2 totals**: 2 producers, +50 LoC.
**Risk class**: LOW-MED — A4 chain already LIVE-verified consumer-side (D1 P1).

### 1.3 Wave 3 — DEFERRED until A19 v2 decoder ω-cycle

| producer | path | corpus class | pre-encode delta | A19 PASS 0.5 status | migration LoC |
|---|---|---|---:|:---:|---:|
| **proposal_refinement_emit** | `anima/tool/proposal_refinement_emit.hexa` (refinement v<N>.json writer) | small-file mixed | +14.70pp MEASURED | TRIPPED (F-A19-6b) | DEFERRED |
| **nexus_state_emit** | `nexus/tool/state_ledger_emit.hexa` (nexus state ledger writer) | small-file mixed | PROJECTED +10-20pp | TRIPPED projection | DEFERRED |

**Wave 3 totals**: 0 producers (all DEFERRED).
**Risk class**: HIGH — pre-encode storage inflation + idempotency contract violation.
**Re-entry condition**: A19 v2 decoder whitespace-canonicalization fix LANDED + LIVE FIRE round-trip byte-eq ≥99% on production refinement class OR A20 schema-aware BPE PASS 3+4 LIVE FIRE LANDED (a45778db / 95f843b5 in-flight).

---

## 2. Wave timing (target 2026-05-15+ to 2026-06-30)

| Wave | scope | entry trigger | canary cadence | LIVE date target | LoC delta |
|---|---|---|---|---|---:|
| **D1 P3 W1** | A1-only structural (3 producers) | D1 P2 W1+W2 PASS (~2026-05-22) | 7-day each producer | 2026-05-29 → 2026-06-12 | +55 |
| **D1 P3 W2** | A1+A4 structural (2 producers) | D1 P3 W1 day-7 clean | 7-day each | 2026-06-12 → 2026-06-26 | +50 |
| **D1 P3 W3** | A19 PASS 0.5 producers | A19 v2 decoder ω-cycle LANDED + corpus class verified | 14-day extended | 2026-06-30+ | DEFERRED |

---

## 3. Falsifier preregister (raw 71 strict)

### 3.1 F-D1-3 (D1 P3 entry condition falsifier)

**ID**: F-D1-3
**Claim**: producer-side HXC pre-encoded output remains byte-eq compatible with consumer-adapter (`/Users/ghost/core/hive/tool/hxc_consumer_adapter.hexa`) reverse decode chain across all 6 sister repos.
**Measurement method**: 5-corpus producer→consumer round-trip byte-eq sweep — for each of 6 repos, pick 5 representative files; run `producer.emit(content) → hxc_pre_encoded_file → consumer_adapter.decode → original_content_bytes`; compare with `cmp -s`.
**Pass criterion**: 99%+ round-trip byte-eq AND 0% downstream consumer regression (existing consumer behavior unchanged) AND aggregate storage delta ≤ +5pp (or NEGATIVE).
**Verdict pending**: D1 P3 W1 entry condition; LIVE FIRE not yet executed.
**Retire path**:
- if round-trip byte-eq < 99% on any corpus class → narrow producer-side scope to A1-only structural pre-encode for that class
- if downstream consumer regression > 0 → revert producer to raw .jsonl emit + add migration shim layer
- if aggregate storage delta > +5pp → reject D1 P3 deployment for that corpus class; DEFER to algorithmic ω-cycle

### 3.2 F-D1-3a (sub-falsifier — schema header preservation)

**Claim**: producer-emitted HXC pre-encoded files preserve `# schema:s<N>` header line exactly as consumer-adapter reverse decode expects (no trailing whitespace, no schema-id renumbering).
**Measurement**: per-line diff between producer output and reference hxc_migrate output on 10-file fixture set per corpus class.
**Verdict pending**: D1 P3 entry.

### 3.3 F-D1-3b (sub-falsifier — A19 PASS 0.5 production deploy precondition)

**Claim**: A19 PASS 0.5 producer-side wiring is safe to deploy on a corpus class only when both F-A19-6a (net-positive precondition: median > 1KB AND total > 100KB) AND F-A19-6b (round-trip byte-eq ≥99%) are MET.
**Measurement**: per-class pre-deployment LIVE FIRE on 50-file representative sample.
**Verdict THIS TICK**: TRIPPED on refinement-class (F-A19-6b 92.5% fail), TRIPPED on nexus-state-small-file (F-A19-6a -0.38pp net-negative), PASS on adversarial synthetic only (which has 0 production deploy surface).
**Retire path**: Wave 3 DEFERRED until A19 v2 decoder whitespace fix OR A20 BPE replacement.

---

## 4. F-A19 family cross-link

| F-A19-N | meaning | status pre-tick | status post-tick |
|---|---|:---:|:---:|
| F-A19-1 | A19 federation -1pp regression on small-file class | PARTIAL_RETIRE_DOWNGRADED | PARTIAL_RETIRE_FURTHER_DOWNGRADED (refinement-class -13.65pp + 92.5% fail this tick) |
| F-A19-5 | PASS 0 census + PASS 0.5 encode dual-axis validation | FULL PASS | FULL PASS (unchanged) |
| **F-A19-6a** | A19 net-positive precondition (median>1KB AND total>100KB) | TRIPPED on nexus 94/58337B | TRIPPED on refinement 40/118KB also |
| **F-A19-6b** | encode_v2/decode_v2 round-trip byte-eq idempotency | PASS 84/84 (adversarial only) | TRIPPED 37/40 on production refinement class (this tick LIVE FIRE) |

**Honest C3**: previously F-A19-6 carried two conflated meanings (aa2d5935 verdict TRIPPED + a0828d72 verdict PASS 84/84). This tick formally splits into F-A19-6a + F-A19-6b. F-A19-6b status FLIPPED from PASS to TRIPPED via production LIVE FIRE.

---

## 5. Producer-side raw mandates

| raw | enforcement | producer-side specific |
|---|---|---|
| raw 9 | hexa-only | producer module 100% hexa SSOT (no Python/Bash producer scripts) |
| raw 18 | self-host fixpoint | producer→consumer round-trip preserves byte-eq |
| raw 47 | cross-repo trawl | 6-repo producer parity required at deploy promotion |
| raw 65 | encode(decode(x))==x | enforced via F-D1-3 |
| raw 68 | decode(encode(y))==y | enforced via F-D1-3 |
| raw 71 | falsifier-preregister | F-D1-3 + F-D1-3a + F-D1-3b above |
| raw 91 | honest C3 | per-corpus-class delta_pp + round-trip pass% disclosed in deploy ledger |
| raw 137 | 80% Pareto + cmix-ban | producer-side pre-encode does NOT push beyond 80% target (Wave 1 storage NEUTRAL by design); cmix-class compressors PROHIBITED |
| raw 142 D2 | try-revert | per-corpus-class deploy gate (NOT silent per-file revert which masks corpus-class signal) |
| raw 154 | deploy-rollout | staged D0→D1→D2→D3 mandate; D1 P3 = D1 phase, multi-wave |
| raw 155 | consumer-adapter | producer output must be consumer-adapter reverse-decodable |

---

## 6. Cross-link to other in-flight agents (raw 47 non-collision)

- **a3ac440a** (D1 P1 canary): consumer-side, predecessor — D1 P3 entry on a3ac440a 7-day clean PASS
- **a7a059f0** (A20 close): A20 PASS 3+4 LIVE FIRE — A20 BPE landing unblocks Wave 3 federation alternative
- **a58efacb** (multi-corpus grid): per-class measurement infrastructure — F-D1-3 LIVE FIRE relies on this
- **a7a856a4** (Phase 12 P0 + closure): Phase 12 entry condition; D1 P3 sits ABOVE Phase 12 entry (deploy-rollout layer, not algorithm-catalog layer)
- **ace91cf6** (A18 v2 + close): A18 saving ω-cycle — orthogonal to D1 P3 producer wiring

---

## 7. Deploy ledger schema (forward-spec)

Each producer at LIVE date emits one row to `state/d1_p3_producer_deploy/<DATE>_<producer>.jsonl`:
```json
{"ts":"...","producer":"...","corpus_class":"...","raw_bytes":N,"hxc_bytes":N,"pre_encode_overhead_pp":X.XX,"a19_pass_0_5_used":false,"round_trip_byte_eq_ok":N,"round_trip_byte_eq_fail":N,"f_d1_3_status":"PASS|TRIPPED","raw_compliance":[...]}
```

---

## 8. Re-entry conditions for Wave 3 (DEFERRED A19 PASS 0.5 producer-side)

Either path closes the deferral:

**Path A — A19 v2 decoder ω-cycle**:
- whitespace canonicalization in `_decanonicalize_line()` preserves trailing whitespace exactly when emitting `# schema:` decl lines
- LIVE FIRE round-trip byte-eq ≥99% on production refinement class (50-file sample)
- F-A19-6b status promoted from TRIPPED to PASS

**Path B — A20 BPE replacement**:
- A20 PASS 3+4 LANDED (a45778db / 95f843b5 in-flight)
- A20 production-chain delta_pp ≥ +5pp on text-heavy + small-file classes
- A19 PASS 0.5 retired from 80% Pareto closure roadmap; A20 fills the small-file gap

Either path triggers Wave 3 forward-spec re-design.

---

**Doc anchor**: this file
**Witness**: `state/format_witness/2026-04-28_a19_pass_0_5_hxc_pre_encode_production.jsonl`
**Tool**: `tool/hxc_pre_encoder.hexa` (236 LoC, selftest PASS)
**Compliance signature**: raw 1 / raw 9 / raw 18 / raw 47 / raw 65+68 / raw 71 / raw 91 / raw 137 / raw 142 D2 / raw 154 / raw 155
