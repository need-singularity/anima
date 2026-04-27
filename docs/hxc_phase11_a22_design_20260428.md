# HXC Phase 11 P3 — A22 Self-Decoding HXC Design

**Date**: 2026-04-28
**Phase**: 11 P3 (post-A20; architecture seal — raw 18 self-host fixpoint completion)
**Parent design**: `hxc_phase11_design_post_a18_20260428.md` §2 candidate 5
**Trigger**: Phase 11 P3 launch; first ~150 LoC tick (PASS 1 footer emitter + selftest)
**Compliance**: raw 9 hexa-only · raw 18 self-host fixpoint (NATURAL APPLICATION) ·
raw 65 + 68 idempotent · raw 71 falsifier-preregistered (4 falsifiers · F-A22-1..4)
· raw 91 honest C3 (projections labeled vs measurements) · raw 152 (proposed)

---

## 0. Honest framing (raw 91 C3)

A22 is a **self-describing artifact format**, NOT a compressor. It adds
overhead bytes for all artifacts (decoder bytecode + manifest), so
**raw-byte saving is NEGATIVE**. The Pareto frontier verdict therefore
**SHIFTS** from "(saving %)" to "(saving %) − (decoder dependency cost)":
A22 portability axis (artifact carries its own decoder) outweighs the
small-file negative on the architecture-purity axis.

This document covers design + first ~150 LoC tick (PASS 1 footer emitter
only). PASS 2 mini-VM consumer + LIVE FIRE deferred to follow-on cron ticks.
All numbers are PROJECTIONS until F-A22-1..4 measurement gates fire.

---

## 1. Self-describing artifact justification

**Problem**: HXC v1 artifacts depend on `hxc_migrate` decoder binary at
read time. Cross-system portability requires shipping the decoder + matching
algorithm-catalog version. Drift between encoder/decoder version = silent
decode corruption hazard.

**raw 18 fixpoint principle**: hexa code self-hosts hexa runtime. By
analogy, an HXC artifact should self-host its decoder spec — the artifact
IS the decoder bootstrap. A22 closes this fixpoint: artifact + tiny generic
HXC reader (~50 LoC) = full reconstruction, no external decoder catalog
required.

**Outcome**: Phase 11 P3 closure verifies HXC v1 artifacts can decode
themselves on any hexa runtime, given only the generic mini-VM bootstrap.
This eliminates the "encoder/decoder catalog drift" failure mode entirely.

---

## 2. Mini-VM bytecode design

The footer carries an **algorithm-chain bytecode** that the consumer
mini-VM executes to decode the body. Each chain step = one HXC algorithm
(A1, A4, A8, A9, A11, A12, A14, …) applied in reverse.

### Instruction set (8 opcodes)

| opcode | mnemonic | operand | semantics |
|---:|---|---|---|
| 0x01 | `PUSH_ALGO` | algo_id (uint8) | push decoder for algo onto VM stack |
| 0x02 | `PUSH_PARAM` | len (uint16) + bytes | push algorithm parameter blob |
| 0x03 | `DECODE` | (none) | pop param + algo, apply decoder to current buffer |
| 0x04 | `POP` | (none) | discard top stack entry |
| 0x05 | `EMIT` | (none) | declare current buffer as final output |
| 0x06 | `CHK` | sha256[32] | verify current buffer SHA-256 (raw 65/68) |
| 0x07 | `MARK` | label_id (uint8) | named checkpoint for partial-decode resume |
| 0x08 | `HALT` | (none) | terminate VM (post-EMIT sentinel) |

### Encoding

Bytecode written as `base94` (printable ASCII range 33..126, excluding
`# \n`) so footer remains text-grep-friendly. base94 yields ~6.55 bits/char
vs base64's 6.0 bits/char — ~9% denser footer.

### Footer format spec (byte-exact)

```
\n# decoder-spec v=A22-v1 size=<N> sha256=<HEX64>\n
<base94 bytecode line, single line, 1..4096 chars>\n
# eof\n
```

- `<N>` = decoded bytecode length in bytes (decimal ASCII)
- `<HEX64>` = SHA-256 of the **decoded bytecode** (lowercase hex, 64 chars)
- `# eof` = sentinel, MUST be the final non-empty line of the artifact
- Multiple `# decoder-spec` lines = error (single-spec invariant)

### Worked example — A1+A12+A14 chain footer

Decoder bytecode (decoded):
```
PUSH_ALGO 0x01            ; A1 baseline
PUSH_PARAM len=0          ; (no params)
DECODE
PUSH_ALGO 0x0c            ; A12 column-prefix
PUSH_PARAM len=8 [<dict>] ; column-prefix dict
DECODE
PUSH_ALGO 0x0e            ; A14 row-prefix
PUSH_PARAM len=4 [<dict>] ; row-prefix dict
DECODE
EMIT
HALT
```

Bytecode total ~30 bytes. base94-encoded ~33 chars. Footer overhead
(headers + sha + base94) ~140 bytes total.

---

## 3. raw 18 self-host fixpoint compatibility

raw 18 mandates: hexa code is self-hosted in hexa. A22 generalises this:
HXC artifact decoder spec is self-hosted in HXC.

| layer | host | guest |
|---|---|---|
| hexa compiler (raw 18 baseline) | hexa runtime | hexa source |
| HXC v1 (pre-A22) | `hxc_migrate` binary + algorithm catalog | HXC artifact body |
| HXC v1 + A22 (THIS DESIGN) | generic mini-VM (~50 LoC) | HXC artifact body + footer bytecode |

**Fixpoint check**: A22 footer references decoder algorithms by **algo_id
opcode**, not by hexa source. The mini-VM dispatches to in-runtime decoder
implementations. Therefore:

- bootstrap parser ≤ 50 LoC (F-A22-2 enforces)
- algorithm decoders themselves remain in hexa stdlib (`hxc_a1_baseline.hexa`,
  `hxc_a12_column_prefix.hexa`, …)
- A22 = **dispatch shim**, not a compressor — closes self-describe loop
  without requiring the artifact to embed full hexa source for decoders
  (which would balloon footer overhead and violate F-A22-1).

---

## 4. Pareto frontier verdict shift

Pre-A22 frontier (Phase 11 P0/P1/P2): single axis = byte-weighted saving %.

Post-A22 frontier: **two axes** — saving % (X) and decoder-portability cost
(Y, lower better).

### Projected verdict table

| artifact | size | A22-off saving % | A22-on saving % | decoder cost (KB external) | portability gain |
|---|---:|---:|---:|---:|---:|
| atlas n6 (entropy) | 79KB | 90% | 90% − 0.18pp | 0 KB | +∞ (self-decoding) |
| anima alm_r13 | 980KB | 88% | 88% − 0.014pp | 0 KB | +∞ |
| nexus small file | 4KB | 75% | 75% − 3.5pp | 0 KB | +∞ |
| hexa-lang aot_cache | 100KB | 92% | 92% − 0.14pp | 0 KB | +∞ |

**Negative-saving on small files** (<10KB) is the expected regression and
the entire reason A22 lands AFTER P0/P1/P2 compression candidates: it is
positioned as **architecture seal**, not compression candidate. F-A22-1
(spec overhead > 50% of compressed size) gates against pathological cases
on tiny artifacts.

### Why the shift is justified (raw 137 universal)

1. **Cross-repo portability**: artifacts produced by anima can be decoded
   by nexus + hexa-lang + airgenome + hive without shipping algorithm
   catalogs. Portability is universally valuable.
2. **Catalog-drift elimination**: silent corruption hazard removed. Single
   most likely Phase 12 falsification pattern (catalog version skew)
   pre-empted.
3. **raw 18 fixpoint completion**: this is the deepest alignment of any
   Phase 11 candidate with the raw 18 self-host principle.

The portability axis adds **non-byte saving** that absolute-byte metrics
miss. Pareto frontier verdict shifts from "byte-min" to
"byte-min subject to external-dependency = 0" — a strictly larger constraint
set, well-justified by the raw 18 closure.

---

## 5. Tick 1 scope (~150 LoC)

| component | LoC est | status this tick |
|---|---:|---|
| header + constants + opcodes table | ~25 | DONE |
| base94 codec (encode side only) | ~30 | DONE |
| footer emitter (`a22_emit_footer`) | ~50 | DONE |
| footer parser (bytecode extract) | ~30 | DONE |
| mini-VM execution stub (dispatch only) | ~20 | DONE (stub) |
| selftest fixture (synthetic A1+A12+A14 chain) | ~25 | 1 of 1 DONE |
| main() + CLI dispatch | ~10 | PARTIAL stub |

Tick 1 deliverable: footer emitter LIVE, parser LIVE (extract+verify only),
mini-VM dispatch stub returns NOT_IMPLEMENTED for actual decode, 1 selftest
fixture PASS, main() prints PARTIAL marker.

Remaining estimate ~250-300 LoC across 2-3 follow-up ticks (full mini-VM
decode + base94 decoder + 4 more selftests + LIVE FIRE round-trip on real
HXC artifact).

---

## 6. 4 falsifiers preregistered (raw 71)

- **F-A22-1**: self-decoder bytecode + footer overhead > 50% of compressed
  body size on smallest fixture (1 KB synthetic) → reject (defeats A22 on
  small artifacts class entirely)
- **F-A22-2**: external decoder dependency residue (any decode path
  requires `hxc_migrate` binary OR algorithm catalog file at read time) →
  reject (A22 fixpoint violation)
- **F-A22-3**: self-decode latency > 200ms per KB compressed body on
  cron-host budget (M-class CPU) → reject (throughput regression beyond
  hxc_migrate baseline)
- **F-A22-4**: raw 18 self-host fixpoint violated — bootstrap mini-VM
  exceeds 100 LoC OR depends on non-hexa external library → reject

---

## 7. raw 152 self-decoding-fixpoint-mandate verification

**Contract (proposed raw 152)**: HXC artifact MUST self-describe decoder
spec by Phase 11 closure.

### Compliance checks (this tick)

- ✓ Footer format spec defined (§2)
- ✓ Mini-VM opcode set fixed (8 opcodes, §2)
- ✓ raw 18 fixpoint pathway documented (§3)
- ✓ Pareto frontier shift justified (§4)
- ✓ 4 falsifiers preregistered (§6)
- PARTIAL: mini-VM full decode = DEFERRED to tick 2; closure verification
  blocks on F-A22-2 measurement (LIVE FIRE round-trip)

### raw 18 fixpoint completion invariant

Post-tick-2 LIVE FIRE expected to verify: any HXC v1 artifact emitted with
A22 footer can be decoded by `hexa <generic_hxc_reader.hexa> <artifact>`
where generic_hxc_reader.hexa is ≤ 100 LoC and depends on no external
catalog. This is the **closure invariant** for raw 152.

---

## 8. Self-host + cross-repo (raw 9 / 18 / 47)

- raw 9 hexa-only: ✓ pure-hexa, no external libs
- raw 18 self-host: ✓✓ NATURAL APPLICATION — artifact IS its own host
- raw 47 cross-repo: deferred to integration tick (apply across nexus +
  anima + hive + hexa-lang + airgenome corpora at LIVE FIRE)

---

raw 9 · raw 18 (deepest alignment) · raw 65 + 68 · raw 71 (4 falsifiers) ·
raw 91 C3 · raw 152 (proposed) · parent: a07ea3d2 / 8694b9ea Phase 11 design.
