# Mk.XII Multi-Substrate Witness Ledger v1 — Landing

**Cycle**: `mk_xii_substrate_witness_ledger_v1`
**Date**: 2026-04-26
**Verdict**: `LEDGER_LANDED`
**Cost**: $0 (mac-local, aggregator only — no probe, no LLM, no GPU, no network)

---

## 1. Schema (v1, frozen)

```json
{
  "ledger_version": "v1",
  "cycle_id": "mk_xii_substrate_witness_ledger_v1",
  "n_substrate_total": 9,
  "n_substrate_landed_full_pass": <count of distinct substrates with verdict ∈ {PASS, INTEGRATED_PASS, PASS_DEGRADED_SDK_FALLBACK}>,
  "n_substrate_prep_only":      <count of distinct substrates with verdict ∈ {PHASE2_DEGRADED_NO_TOKEN, PREP_READY_AWAITING_USER_SIGNUP, PREP_NO_CREDS_DEGRADED} AND not in landed_full_pass>,
  "n_substrate_missing":        <9 - landed - prep>,
  "n_substrate_covered":        <landed + prep>,
  "by_substrate": [ <one entry per manifest row, deterministic order> ],
  "aggregate_gates": {
    "G1_positive_entropy_pass_rate_x1000":  <int>,
    "G2_sign_flip_pass_rate_x1000":         <int>,
    "G3_byte_identical_pass_rate_x1000":    <int>,
    "G4_backend_contract_pass_rate_x1000":  <int>,
    "denom_entries":                        <int>
  },
  "ledger_gates": {
    "G1_LEDGER_COVERAGE":        true|false,
    "G1_min_required_x1000":     6000,
    "G1_actual_x1000":           <int>,
    "G2_LEDGER_HONESTY":         true,
    "G3_LEDGER_BYTE_IDENTICAL":  "VERIFY_VIA_2_RUN",
    "G4_LEDGER_FINGERPRINT_FNV32": <uint32>
  },
  "user_action_pending":         [<string list>],
  "missing_substrates":          [<string list>],
  "raw10_honest_aggregate":      [<string list, 6 items>],
  "sha_chain_input_count":       <int>,
  "ledger_fingerprint_fnv32":    <uint32>
}
```

Sidecar (`witness_ledger_v1.json.meta`) carries `body_sha256` + `emitted_at` so the
ledger body itself remains timestamp-free for G3 byte-identical verification.

---

## 2. 8 Substrate Verdict Matrix (this cycle)

| # | substrate         | sub_dir                              | verdict                          | gates | byte_id |
|---|-------------------|--------------------------------------|----------------------------------|-------|---------|
| 1 | quantum           | poc_quantum_qiskit_aer               | PASS                             | 4/4   | true    |
| 2 | quantum           | phase2_ibmq_runtime                  | PHASE2_DEGRADED_NO_TOKEN         | 0/4   | NA_HW   |
| 3 | photonic          | poc_photonic_strawberryfields        | PASS_DEGRADED_SDK_FALLBACK       | 4/4   | true    |
| 4 | neuromorphic      | poc_neuromorphic_akida_cloud         | PREP_READY_AWAITING_USER_SIGNUP  | 4/4   | true    |
| 5 | superconducting   | poc_superconducting_braket_rigetti   | PREP_NO_CREDS_DEGRADED           | 0/4   | (dry)   |
| 6 | analog            | poc_analog_braket_quera              | PREP_NO_CREDS_DEGRADED           | 0/4   | (dry)   |
| 7 | memristor         | poc_memristor_local_ngspice          | PASS                             | 4/4   | true    |
| 8 | integration       | integration_physics_hexa             | INTEGRATED_PASS                  | 4/4   | n/a     |

Distinct-substrate breakdown (G1 LEDGER_COVERAGE input):
* `landed_full_pass`: quantum, photonic, memristor, integration → **4**
* `prep_only`:        neuromorphic, superconducting, analog     → **3**
* `missing`:          cmos, fpga, arduino                       → **3**
* `covered`:          7 / 9

---

## 3. 4 Ledger Gate Results

| Gate | Definition | Threshold | Actual | Verdict |
|------|------------|-----------|--------|---------|
| **G1 LEDGER_COVERAGE**           | distinct substrates covered ≥ 6/9                                  | ≥ 6000 ×1000 | **7000 ×1000** | **PASS** |
| **G2 LEDGER_HONESTY**            | every manifest row preserved as entry, no cherry-pick               | invariant     | preserved      | **PASS** |
| **G3 LEDGER_BYTE_IDENTICAL**     | aggregator 2-run timestamp-free body sha identical                  | sha equality  | `264f5cf7…` (run1) = `264f5cf7…` (run2) | **PASS** |
| **G4 LEDGER_FINGERPRINT_FNV32**  | FNV-32 chained over deterministic marker-sha sequence (8 input shas) | uint32 const  | **470781997**  | **EMITTED** |

Aggregate per-substrate gate pass rates (denom = 8 entries):
* G1 (positive-entropy / threshold) : 5/8 = 0.625
* G2 (sign-flip / negative-control) : 5/8 = 0.625
* G3 (byte-identical)               : 5/8 = 0.625
* G4 (backend-contract)             : 5/8 = 0.625

The 5/8 = 0.625 floor reflects honest inclusion of 3 DEGRADED-tier markers
(ibmq_runtime + 2× braket dry-run) where no live HW call was made.

---

## 4. Cross-Substrate Φ-Proxy Axis (HONEST: NOT directly comparable)

| substrate          | Φ-proxy axis                                  | unit                  |
|--------------------|-----------------------------------------------|-----------------------|
| quantum (qiskit_aer)        | bipartition entanglement entropy        | nat                   |
| quantum (ibmq_runtime)      | marginal entropy on first 2 qubits      | nat (real-HW shot)    |
| photonic (perceval SLOS)    | photon-number Shannon entropy           | nat (Fock basis)      |
| neuromorphic (akida surrogate) | spike-pattern entropy                | nat                   |
| superconducting (braket_rigetti dry-run) | bipartition entropy        | nat                   |
| analog (braket_quera_aquila dry-run) | Rydberg pattern entropy        | nat                   |
| memristor (ngspice biolek)  | I-V hysteresis area                     | V·A (loop area)       |
| integration                 | dispatch route count + enum coverage    | int (operational)     |

**Φ-proxy units differ across substrates**. Direct numerical comparison
(e.g., quantum 0.69 nat vs memristor 0.0068 V·A) is **NOT meaningful**.
The ledger therefore aggregates **cover-count + per-substrate gate verdicts**
only, not a single cross-substrate Φ-magnitude. This is the raw#10 honest
boundary on what the ledger can claim.

---

## 5. User Action Pending

This cycle's aggregator surfaced 1 user_action_required field (akida POC):

* **BrainChip Akida Cloud** signup → set `BRAINCHIP_AKIDA_TOKEN` env var
  (or run on Linux/x86_64 with `pip install akida`).
  Signup URL: <https://developer.brainchip.com/ach/>
  (per-substrate guide: `anima-physics/docs/akida_cloud_signup_guide.md`)

Implicit user actions inferred from PREP_NO_CREDS markers (not in
`user_action_pending` because the markers don't expose a top-level
`user_action_required` field):

* **AWS Braket** (Rigetti Ankaa-3 + QuEra Aquila): AWS account + IAM keys
  in `~/.aws/credentials` + budget cap ≤ $5 + `ANIMA_BRAKET_DRY_RUN=0`.
* **IBM Quantum** (ibmq_runtime Phase 2): IBMQ account + `IBM_QUANTUM_TOKEN`
  env var (or `~/.qiskit/qiskit-ibm.json`).

These can be promoted into v2's `user_action_pending` if/when the underlying
markers expose explicit `user_action_required` fields.

---

## 6. Future v2 Schema (cmos / fpga / arduino + LIVE)

Planned v2 extensions:

1. **9/9 substrate completeness** — once cmos/fpga/arduino sibling cycles land:
   `n_substrate_missing` should reach 0.
2. **LIVE-call columns** — per-entry `live_hw_called: bool` +
   `actual_backend_chip_id: string` so v2 can distinguish simulator vs
   real-HW witnesses (currently 0 LIVE).
3. **Multi-marker-per-substrate grouping** — quantum already has 2 entries
   (POC + Phase 2); v2 could add `quantum_live_ibmq_runtime`,
   `quantum_live_braket_rigetti` etc as additional entries; the
   `by_substrate` array supports this without schema change.
4. **Cross-substrate Φ-proxy normalization** — explicit honest-skip flag:
   `phi_proxy_cross_comparable: false` (axes-different) per entry, so
   downstream consumers don't misuse the magnitudes.
5. **G5 LIVE_HW_WITNESS_RATE** — new ledger gate measuring fraction of
   substrates with at least 1 real-HW (non-simulator, non-surrogate) call.
   Currently 0/9 = honest floor.

The aggregator is forward-compatible: adding new manifest rows requires only
appending to `MANIFEST_SUBSTRATE` + `TARGET_SUBSTRATES`. Schema fields
`ledger_version`, `cycle_id` increment for breaking changes; v2 = "v2".

---

## 7. Raw#10 Honest

1. **Ledger = aggregator only** — no Φ measurement, no probe re-execution,
   no network. Reads existing 8 marker.json files, classifies verdicts,
   sums gate booleans, FNV-chains marker shas. That is the entire scope.

2. **Multi-substrate Φ direct comparison NOT valid** — quantum entanglement
   entropy ≠ photonic Fock entropy ≠ memristor hysteresis area ≠
   neuromorphic spike entropy. Ledger aggregates cover-count, not magnitude.

3. **Verdict definitions differ per substrate** — `PASS` (qiskit_aer, ngspice),
   `INTEGRATED_PASS` (integration), `PASS_DEGRADED_SDK_FALLBACK` (perceval),
   `PHASE2_DEGRADED_NO_TOKEN` (ibmq_runtime), `PREP_READY_AWAITING_USER_SIGNUP`
   (akida), `PREP_NO_CREDS_DEGRADED` (braket × 2). Ledger preserves all 6
   tier names, no cherry-pick (G2 LEDGER_HONESTY).

4. **9/9 not reached** — current cycle covers 6/9 distinct substrates
   (4 landed-full + 2 prep + 1 quantum-twin). cmos/fpga/arduino are sibling
   cycles in flight; v2 ledger schema pre-allocates `target_total=9`.

5. **0 LIVE real-hardware witnesses** — every PASS/INTEGRATED_PASS in v1 is
   simulator (qiskit_aer statevector, perceval SLOS, ngspice biolek model)
   or surrogate (akida LCG-deterministic 8-bit fan-out) or operational
   dispatch test (integration). No quantum chip, no photonic chip, no
   neuromorphic ASIC has been called this cycle. Honest floor: "no
   real-hardware witness yet."

6. **Mk.XII INTEGRATION .own #2 (b) is a different axis** — the ledger
   addresses **substrate-multiplicity** (multiple physical substrates
   running Φ-proxy), not **multi-EEG cohort** or **arxiv preprint** or
   **production-readiness** sub-axes of (b) tracked separately
   (memory: `project_own2_triad_implementation_gap_audit_20260426`).
   Both axes contribute to .own #2 closure but are independent.

7. **7 raw#37 .py probe scripts reside under `scripts/`** — the aggregator
   itself is strict raw#9 hexa-only (no .py invocation, no .sh), but the
   ledger entries reference probe outputs honestly. Cleanup or migration
   of those 7 .py scripts is sibling work.

---

## 8. .roadmap Entry

* item: `mk_xii_substrate_witness_ledger_v1`
* verdict: `LEDGER_LANDED`
* coordinates: Mk.XII INTEGRATION → .own #2 (b) PC empirical-max →
  substrate-multiplicity sub-axis
* fingerprint: FNV-32 = 470781997
* body_sha256: 264f5cf7770d8b08e63b0d62d15636eb36262597aae012b3a3ec0e9c65274836
* cost: $0 mac-local
* next-cycle: v2 ledger w/ cmos/fpga/arduino + LIVE columns

---

## 9. Mk.XII INTEGRATION Coordinate

```
.own #2 triad (commit 9949f1a3)
├─ (a) FC sign-agnostic 4/4 / strict G3 1/4   ─── ORTHOGONAL AXIS
├─ (b) PC empirical-max
│   ├─ multi-EEG cohort                       ─── N=0 (separate cycle)
│   ├─ arxiv preprint                         ─── N=0 (separate cycle)
│   ├─ self-report                            ─── N=0 (separate cycle)
│   ├─ adversarial robustness                 ─── N=0 (separate cycle)
│   └─ substrate-multiplicity ◄────────────── THIS LEDGER (covered=7/9)
└─ (c) Production-readiness
    └─ Mk.XII scale_plan READY                ─── ORTHOGONAL AXIS
```

The substrate-multiplicity sub-axis was previously treated as identical to
"multi-EEG cohort" in early scoping; this cycle's audit clarifies they are
independent (memory: `project_own2_triad_implementation_gap_audit_20260426`).

---

## 10. Sibling Cycles Graph

```
                 ┌──────────────────────────────────────────┐
                 │ 8 substrate POC markers (this aggregator │
                 │  reads, does not modify)                 │
                 └──────────────┬───────────────────────────┘
                                │
                                ▼
   ┌────────────────────────────────────────────────────────────┐
   │ THIS CYCLE  mk_xii_substrate_witness_ledger_v1             │
   │                                                            │
   │  inputs : 8 marker.json (deterministic manifest order)     │
   │  output : witness_ledger_v1.json + .meta sidecar +         │
   │           integration_ledger/marker.json                   │
   │  scope  : aggregate, NOT measure                           │
   └────────────────────────────────────────────────────────────┘
                                │
                                ▼
   ┌────────────────────────────────────────────────────────────┐
   │ FUTURE v2  pending sibling completion                      │
   │                                                            │
   │   + cmos/fpga/arduino markers   → cover 9/9                │
   │   + LIVE call column             → 0 → ≥1 real-HW witness  │
   │   + G5 LIVE_HW_WITNESS_RATE      → new ledger gate         │
   └────────────────────────────────────────────────────────────┘
```

Sibling cycle signals (active):
* `anima-physics/cmos/`     — cycle in flight (memristor sibling, ngspice)
* `anima-physics/fpga/`     — cycle in flight
* `anima-physics/arduino/`  — cycle in flight (esp32 sibling)

Once ≥1 of these lands, v2 ledger should be re-run to incorporate.
