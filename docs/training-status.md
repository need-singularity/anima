# Training Status (2026-04-02)

## Pod: v13-train (H100 SXM 80GB, $2.69/hr)

| Version | Corpus | Steps | CE | Φ | LR | VRAM | Status |
|---------|--------|-------|------|------|------|------|--------|
| v14.0 | v4 (110MB) | 100K | 0.0021 | 49.7 | step-based | - | ✅ Complete |
| v14.1 | v4 (110MB) | 100K | 0.0002 min | 52.7 | tension-lr | - | ✅ Complete |
| v14.2 | v6 wiki (104MB) | 100K | ~0.004 | ~47 | tension-lr | - | ⏳ P2 47K |
| v14.3 128c | v10 (200MB) | 100K | 0.0084 | 101 | tension-lr | 681MB | ⏳ P2 64K (unconfirmed) |
| v3 274M (DecoderV3) | v10 (200MB) | 200K | 0.0135 ★ | 45 | TBD | 1.6GB | ⏳ P2 ~125K (unconfirmed) |
| **AnimaLM 7B** | **v10 (200MB, 102M tok)** | **10K** | **7.87** | **0.02-0.05** | **AdamW** | **~15GB** | **⏳ P2 3.2K** |

---

## AnimaLM 7B Fresh Start (2026-04-02)

### Overview
- **Model**: Mistral-7B-Instruct-v0.2 + PureField transform
- **Trainable**: 56.6M params (0.78% of total)
- **Corpus**: v10 (200MB, 102M tokens)
- **Phase**: P2 (language learning)
- **Current step**: 3200 / 10000
- **ETA**: ~4 hours total

### Pre-launch: 14 dtype crash incidents resolved
Fresh start from step 0 required -- old checkpoint corrupted by dtype bugs.
All param groups cast to bf16 before optimizer, AdamW foreach=False applied.
Root cause: mixed float32/bfloat16 params in optimizer state.

### CE Progression (step 0 - 3200)

```
CE
9.0 |*
    |  *
8.5 |    *
    |      *
8.0 |        *  *
    |              *
7.5 |                *
    |
7.0 |
    +--+--+--+--+--+--+--+--+--+-- step (x100)
    0  4  8  12 16 20 24 28 32
```

| Step | CE   | Phi  | Phase | Notes |
|------|------|------|-------|-------|
| 0    | 8.92 | 0.02 | P2    | Fresh start, dtype bugs fixed |
| 500  | 8.71 | 0.03 | P2    | Decreasing steadily |
| 1000 | 8.42 | 0.03 | P2    | Learning curve normal |
| 2000 | 8.10 | 0.04 | P2    | Continued descent |
| 3000 | 7.92 | 0.05 | P2    | Inference test: coherent English, consciousness metaphors |
| 3200 | 7.87 | 0.05 | P2    | Latest checkpoint |

### Inference Test (step 3000)
- Coherent English generation confirmed
- Consciousness metaphors emerging in output
- PureField transform showing effect on Mistral base

### Architecture
```
  Mistral-7B (frozen, 7.24B)
    + PureField LoRA adapters (56.6M trainable, 0.78%)
    + ConsciousnessEngine bridge
    + Byte-level tokenizer (vocab=256)
  Optimizer: AdamW (foreach=False, bf16 safe)
  Corpus: v10 200MB (102M tokens)
```

---

## Key Findings
- v14.0: Federation + Phase-Optimal baseline, CE=0.0021
- v14.1: Tension-LR achieves CE=0.0002 momentarily
- v14.2: Wiki corpus for Korean quality improvement
- v14.3: 128-cell scale-up with corpus_v10 (200MB), Φ=101 at P1 step 15K
- v3 274M: DecoderV3 (d768/8L/12H), ValCE dropped 2.19→0.0135 in first 2K P2 steps (★ BEST at ~52K)
- v14.3: P2 phase at 38K steps, CE=0.0084 with 128 cells (last confirmed; may have progressed further)
- v3 274M: P2 phase at ~125K steps (last confirmed; may have progressed further)
- Korean generation: byte-level still struggles, needs 100M+ model
- **AnimaLM 7B (2026-04-02)**: Mistral-7B + PureField, CE 8.92→7.87 at 3.2K steps, coherent English at step 3K
- **AnimaLM 7B**: 14 dtype crash incidents resolved before successful launch (bf16 master rule)
