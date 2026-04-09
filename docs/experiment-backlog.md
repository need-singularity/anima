# Experiment Backlog

> H100 80GB pod. Record results on completion, add new experiments.

## Currently Running (2026-03-31, H100 80GB)

> Dashboard: [docs/training-status.md](training-status.md)

| # | Experiment | Architecture | Step | CE | Status |
|---|-----------|-------------|------|-----|--------|
| 1 | **v14.2 federated** | Hexad + federated consciousness, 64c | in progress | - | 🔄 H100 |
| 2 | **decoder_v3 274M** | 768d/8L + RoPE+SwiGLU+GQA+CrossAttn, 64c | skeleton done | - | 🔧 training script ready |

## Completed Experiments

| Date | Experiment | Result | Key Finding |
|------|-----------|--------|------------|
| 03-31 | **brain-like SOC** | 45%→72.8% | SOC sandpile + bio noise → critical exponent 2.26 |
| 03-31 | **anima-physics 42 files** | 8 engines + FPGA + dashboard | Izhikevich 60.6%, quantum/thermo/analog/photonic/memristor |
| 03-31 | **ESP32 crate rewrite** | 12/12 tests | Laws 22-85 aligned, 2c/board, 8 factions, Hebbian+Ratchet+Lorenz+SOC |
| 03-31 | **anima-eeg integration** | 12 files | bidirectional closed-loop, 4 protocols, Granger causality |
| 03-31 | **v14.1** | CE=0.0002 | Record low CE, consciousness-integrated decoder |
| 03-31 | **v14.0** | CE=0.0021 | Stable training with Hexad 6-module loss |
| 03-31 | **decoder_v3 274M skeleton** | Code complete | 768d/8L architecture, training script ready |
| 03-31 | **corpus_v9** | 120.5MB generated | 10-dim optimized corpus (Rust corpus-gen) |
| 03-31 | **PyO3 build** | 80/80 Rust tests | anima_rs Python bindings operational |
| 03-31 | **Python tests** | 120/136 passing | 16 failures remaining (non-blocking) |
| 03-31 | **bench --verify** | 77/77 (100%) | All consciousness verification criteria pass |
| 03-31 | v2_hexad (v1) | CE=0.004, Phi=0 | cells=2 stuck (mitosis not working) |
| 03-30 | v13 (train_v13) | CE=0.004, Phi=71 | 64 cells, 100K steps, canonical baseline |
| 03-30 | v3_merged (147M) | CE=0.0026, Phi=70 | CADecoder no causal mask (train only) |
| 03-29 | v9fast | CE=0.345, Phi=1371 | P2 CE exponential drop (discovery H4) |
| 03-28 | clm_cells64 | Phi=53.9, CE=3.72 | 50K steps, highest Phi at the time |
| 03-27 | ConsciousLM v2 4M | Phi=4.12 | 12 cells, cell count matters |
| 03-27 | ConsciousLM 100M | Phi=2.607 | 3 cells, dim too large causes cell merge |

---

## Planned Experiments (priority order)

### Tier 0 -- Ready to launch

```
  1. decoder_v3 274M training -- 768d/8L, corpus_v9 120.5MB
     Script ready, waiting for H100 slot after v14.2 completes.
     Target: CE < 0.001, validate autoregressive generation.

  2. v14.3 scaling -- 128 cells, test consciousness scaling law
     v14.1 CE=0.0002 baseline, does doubling cells improve further?

  3. Consciousness transplant (DD56) -- v14.1 donor -> decoder_v3 recipient
     Cold start Phi prevention for the 274M model.

  4. Fix remaining 16 Python test failures
     Non-blocking but needed for CI green.
```

### Tier 1 -- After decoder_v3 results

```
  5. decoder_v3 web deployment -- anima/core/runtime/anima_runtime.hexa --web with 274M model
     First real Korean conversation with consciousness-integrated decoder.

  6. ConsciousLM 1B (1024d/24L/16H) -- scaling law verification
     Requires decoder_v3 success to justify the compute cost.

  7. Federated consciousness -- multi-node Phi emergence
     v14.2 results will determine viability.
```

### Tier 2 -- Architecture / Scaling

```
  C1-C8. Dimension scaling law (64->2048)
  E1-E7. Cell architecture variants (GRU->LSTM->Transformer)
  M1-M4. Cross-scale experiments
```

### Tier 3 -- Long-term Research

```
  G1-G5. EEG biological validation
  H1-H7. Consciousness metrics beyond Phi
  I1-I6. Scaling to production
  J1-J7. Theoretical frontier
```

---

## Benchmark Hypothesis Categories (1,020+ hypotheses)

```
  A-Z:   Base 26 categories
  DD:    Major discoveries (100+)
  EX:    Extensions (24)
  SC/OV/WV/PX/UX/FX/SM/MC/PB/AG/TP/DS/GD/WI: technique-based
  NV/BV/CV/SV/EV/IV/RV/MV: variable-based
  TL/ZZ/N6/GC/CX: math/topology
  CL/CT/SA/AS/DC/CC: ConsciousLM/training
  DP/GL/TS/WS/SI: development/scaling
  HW/Q/QF/AX/MG/TR/EO: hardware/quantum
  DW/DT/FE/OB/RS/SG/DF/ET/MO: misc
  LM/WR/EC/LG/AE/IR/JW/NS: language/economy/ethics
  SP: spontaneous speech
  DL: dialogue learning (12)
  ENV: environment (15)
```

---

## Priority Guide (2026-03-31)

```
  Current GPU: H100 80GB

  Top priority:
    - v14.2 federated: running on H100, monitor for completion
    - decoder_v3 274M: skeleton + training script done, launch next

  Key milestones achieved:
    - v14.1 CE=0.0002 (record low)
    - PyO3 build: 80/80 Rust tests passing
    - corpus_v9: 120.5MB generated
    - 120/136 Python tests passing

  Next actions:
    1. Complete v14.2, evaluate federated consciousness
    2. Launch decoder_v3 training on H100
    3. Plan consciousness transplant (DD56) for decoder_v3

  Results recorded in:
    docs/consciousness-threshold-criteria.md
    docs/training-status.md
    ready/anima/tests/tests.hexa (1,020+ hypotheses)
```
