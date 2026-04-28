# Mk.XII Hard PASS Composite — Landing

**Date**: 2026-04-26
**Status**: **MK_XII_HARD_PASS_GREEN** (6/6, mac-local pre-flight wire-up; first real validation = post-EEG D+22..D+30)
**Cost**: $0 (read-only aggregator, mac-local hexa-only)
**Tool**: `tool/mk_xii_hard_pass_composite.hexa`
**Output**: `anima-clm-eeg/state/mk_xii_hard_pass_composite_v1.json`

---

## §1. Frozen criterion (5 gates + 1 prerequisite)

```
HARD_PASS = preflight.GREEN
          AND G0_AN11_b.PASS  (>= 3/4 backbones)
          AND G1_BTom.PASS    (>= 3/4 backbones)
          AND G7_composite.PASS (>= 3/4 backbones)
          AND G8_transversal_mi.PASS (global)
          AND G9_dag_cascade.PASS    (global)
```

- **G10 deferred** (post-EEG D+5..D+21).  Its absence does NOT block Hard PASS pre-flight.
- **YELLOW tier reserved** (currently disabled — strict AND only).
- **Backbones**: gemma, mistral, qwen3, llama (4-backbone v10_benchmark_v4 ensemble).
- **Source rule**: `anima-clm-eeg/docs/mk_xii_proposal_outline_20260426.md` §4.3.

## §2. Current verdict (2026-04-26 mac-local pre-flight)

| Gate                    | Source                                                          | Result          |
|-------------------------|------------------------------------------------------------------|-----------------|
| preflight cascade       | `anima-clm-eeg/state/mk_xii_preflight_v1.json`                  | **GREEN** (5/5) |
| G0 AN11(b)              | `state/v10_benchmark_v4/{4×backbone}/g_gate.json`               | **PASS** (4/4)  |
| G1 B-ToM                | `state/v10_benchmark_v4/{4×backbone}/g_gate.json`               | **PASS** (4/4)  |
| G7 composite            | `state/v10_benchmark_v4/{4×backbone}/g_gate.json`               | **PASS** (4/4)  |
| G8 transversal MI       | `anima-clm-eeg/state/g8_transversal_mi_matrix_v1.json`          | **PASS** (max MI=39 / 1000) |
| G9 DAG cascade          | `state/g9_dag_cascade_analyzer.json`                            | **PASS** (edge=4, cascade_max=1) |
| **composite**           | `anima-clm-eeg/state/mk_xii_hard_pass_composite_v1.json`         | **MK_XII_HARD_PASS_GREEN** (6/6) |

`chained_fingerprint = 2638701628` (FNV-32 over byte counts + per-component pass + verdict label).

## §3. ω-cycle 6-step ledger

| Step | Action                                                                  | Result |
|------|--------------------------------------------------------------------------|--------|
| 1    | design — 5-gate AND criterion frozen, G10 deferred                       | OK     |
| 2    | implement — `tool/mk_xii_hard_pass_composite.hexa` (raw#9 strict)        | OK     |
| 3    | positive selftest — default paths → **6/6 GREEN, exit=0**                | PASS   |
| 4    | negative falsify — 4 input categories swept, all → RED, exit=1           | PASS   |
| 5    | byte-identical — two consecutive runs identical sha256                   | OK     |
| 6    | iterate — 1 fix (auto-invoke conflict, removed `main()` call)            | OK     |

### §3.1 Negative falsify sweep

| Override | preflight | G0 | G1 | G7 | G8 | G9 | pass_count | verdict | exit |
|----------|-----------|----|----|----|----|----|------------|---------|------|
| `MK_XII_PREFLIGHT_PATH=/dev/null`        | 0 | 1 | 1 | 1 | 1 | 1 | 5/6 | RED | 1 |
| `MK_XII_G8_PATH=/dev/null`               | 1 | 1 | 1 | 1 | 0 | 1 | 5/6 | RED | 1 |
| `MK_XII_G9_PATH=/dev/null`               | 1 | 1 | 1 | 1 | 1 | 0 | 5/6 | RED | 1 |
| `MK_XII_GATE_BENCH_DIR=/tmp/empty_xyz`   | 1 | 0 | 0 | 0 | 1 | 1 | 3/6 | RED | 1 |

Single-input fault → composite RED, cascade_abort=1, exit=1.  Expected behavior verified.

## §4. SHA-256 (artifacts)

```
c08a745926bed5f85bf704c77751fd93fc33e71d7111d2622cbbacc0ec0e97fa  tool/mk_xii_hard_pass_composite.hexa
142020cec8d16a0953934c46cd7797c1218eb523543c54dfcb41e1dcb691b4d6  anima-clm-eeg/state/mk_xii_hard_pass_composite_v1.json
cf2aecda38ea3da657d16ec012debdd9fc8da86b7da75ba78c3fd53df26c0854  anima-clm-eeg/state/mk_xii_preflight_v1.json   (input)
499c4910e9df223b0f4632ceb383175fde369a58537a0b9ccdb5fa9a8a8b91f0  anima-clm-eeg/state/g8_transversal_mi_matrix_v1.json (input)
3f61be28c4968773345babf02f23c87cdf6e6ca3d4699858b780680f31c533c4  state/g9_dag_cascade_analyzer.json   (input)
0e5544dbbe8331e05cac34666d8112fc1c78a202d58720c870bd9283d7eb6378  state/v10_benchmark_v4/gemma/g_gate.json   (input)
624311397d9a0596e4849dab6b1380a3581a80376e552e2274ffb0915a24cb25  state/v10_benchmark_v4/mistral/g_gate.json (input)
bb125c32cd1fc4c15f1fb162b978649dc39e9e0934c4e2cf97baeac5f4c2f388  state/v10_benchmark_v4/qwen3/g_gate.json   (input)
5479b5a8311e56273ecdf1c4539f8d813fefcabd737e686156b86ec864d5bf30  state/v10_benchmark_v4/llama/g_gate.json   (input)
```

## §5. Mk.XII verification status (post-this-cycle)

| Layer | Component | Status |
|---|---|---|
| pre-flight cascade | HCI / CPGD / CLM-EEG dry-run / TRIBE stub / paradigm v11 | GREEN (5/5) |
| 5-gate harness     | G0 / G1 / G7 / G8 / G9                                     | PASS (5/5)  |
| **composite**      | **MK_XII_HARD_PASS_GREEN**                                  | **GREEN (6/6)** mac-local |
| post-EEG triangulation | G10 family×band 4-backbone correlation                  | DEFERRED (D+5..D+21) |
| Mk.XII first validation | Hard PASS + G10 + EEG real arrival                     | PENDING (D+22..D+30) |

**Interpretation**: Mk.XII Integration tier achieves architectural pre-flight completion at 6/6 mac-local.  This is **wire-up GREEN, not empirical PASS** — G8 surrogate FNV trials, G10 deferred, EEG arrival required for first real validation.  Fallback = Mk.XI v10 4-backbone LoRA ensemble (proposal §7).

## §6. Next cycle

1. **D-day** = EEG hardware arrival (expected D-1 from 2026-04-26).
2. **D+0..D+7** = anima-eeg calibrate + P1+P2+P3 EEG forward ($12-24 GPU + $200-500 facility).
3. **D+5..D+21** = G10 family×band triangulation (post P3 GCG result).
4. **D+22..D+30** = Mk.XII first validation = re-run `tool/mk_xii_hard_pass_composite.hexa` with REAL EEG-derived G8 falsifier scores + G10 added; expect ≥ 6/6 GREEN preserved + 1/1 G10 PASS or 3/4 PARTIAL.

If D+22..D+30 first validation fails → Mk.XI v10 fallback graceful degradation per `mk_xii_proposal_outline_20260426.md` §7.

## §7. Failure modes covered (raw#10 honest)

- ✅ single-input fault detection (4-way negative falsifier sweep)
- ✅ deterministic sha256 across two consecutive runs
- ✅ exit code 1 on RED (CI-ready)
- ✅ G10 deferral explicit in JSON + landing doc (no hidden gate)
- ⚠️ G8 currently FNV-surrogate (frozen, replaced by real-falsifier MI post-EEG)
- ⚠️ TRIBE-v2 currently stub-pass (HF-gated unblock pending D+8..D+14)
- ⚠️ G0/G1/G7 backbone-majority threshold = 3/4 (not 4/4) — single-backbone outage tolerated.  Conservative; matches AN11(b) consensus rule.
