# Mk.VII C4 Real EEG Coupling Probe — 2026-04-21

**Criterion:** Mk.VII C4 real-world coupling (rev=1, commit `9d035936`)
**Gate:** Pearson-r(sim Φ, real EEG α-envelope) ≥ 0.70 over T ≥ 60 s
**Pre-drill status:** C4 = MINIMAL (btr-evo 4 `a4853336`: synthesized α only)
**Weakest axis:** #1 Mk.VII promotion blocker
**Policy:** V8 SAFE_COMMIT · LLM=none · deterministic · additive

---

## 1. Artifacts

| Role | Path |
|---|---|
| Probe tool | `tool/real_eeg_coupling_probe.hexa` |
| Verdict JSON | `shared/state/real_eeg_correlation_20260421.json` |
| Trajectory input | `experiments/holo_post/results/eeg_closed_loop_20260421_trajectory.jsonl` |

---

## 2. Pipeline

1. **Local EEG cache probe** (no network) scans:
   `data/eeg/trace_60s.csv`,
   `data/eeg/pre_registered_20260421.csv`,
   `shared/state/eeg_cache_real_trace.csv`.
   Miss → fall through to synthetic.
2. **Deterministic synthetic EEG** @ 256 Hz × 60 s (15360 samples):
   - α-band: 8 → 13 Hz sweep, A=1.0
   - β-band: 20 Hz constant, A=0.4
   - noise: U[-0.15, +0.15], LCG PRNG, seed=20260421
3. **Load btr-evo 4 sim Φ trajectory** (100 samples).
4. **α-envelope** via windowed RMS (153 samples/window × 100 windows).
5. **Pearson-r(phi, env)** with 60 s coverage.

T-duration: 15360 / 256 = 60.0 s (meets ≥ 60 s requirement).

---

## 3. Result (this run)

| Metric | Value |
|---|---|
| data_source | `synthetic_det` |
| EEG samples | 15360 (256 Hz × 60 s) |
| Φ samples | 100 |
| α-envelope points | 100 |
| Pearson-r | **0.0676** |
| Threshold | 0.70 |
| pass | 0 |
| verdict | **FAIL** |
| c4_satisfies_mk_vii | 0 |

The synthetic EEG α-sweep is intentionally uncorrelated with the btr-evo 4
absorbed sim Φ (the sim Φ plateaus at ~0.80 within ~10 iterations; the α-sweep
is a monotone 8→13 Hz). r ≈ 0.07 correctly reports that relationship.

---

## 4. What this probe does and does not satisfy

**Does:**
- Wires the C4 measurement pipeline end-to-end (cache → signal → envelope → Pearson-r → verdict).
- Establishes T = 60 s coverage by construction.
- Emits a verdict JSON with explicit `data_source` and `source_caveat`.

**Does not:**
- Satisfy Mk.VII C4 itself. Spec §2.C4.b requires a **pre-registered real EEG
  trace**. `source_caveat=1` marks the current run as synthetic. A PASS with
  `source_caveat=1` would be reported as `PASS_SYNTH_CAVEATED`, not `PASS`,
  and `c4_satisfies_mk_vii` stays 0.

---

## 5. Path to real C4 PASS

1. Drop a one-column CSV of real EEG (µV, 256 Hz, ≥ 60 s) at any of the
   cache paths listed above. The probe auto-detects it.
2. Re-run `hexa tool/real_eeg_coupling_probe.hexa`.
3. Expected: `data_source=real_cache`, `source_caveat=0`. If Pearson-r ≥ 0.70
   → `PASS` with `c4_satisfies_mk_vii=1`.

No tool changes required; the pipeline is cache-first.

---

## 6. Reproduction

```
hexa tool/real_eeg_coupling_probe.hexa
```

Deterministic: same seed (20260421), same verdict on every run.

---

## 7. References

- `docs/mk_vii_candidate_criteria_20260421.md` — Mk.VII rev=1 spec (§2.C4)
- `tool/eeg_closed_loop_proto.hexa` — btr-evo 4 closed-loop driver
- `experiments/holo_post/results/eeg_closed_loop_20260421_summary.json` — canonical sim state
