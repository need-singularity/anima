# Training Status (2026-03-31)

## Pod: v13-train (H100 SXM 80GB, $2.69/hr)

| Version | Corpus | Steps | CE | Φ | LR | VRAM | Status |
|---------|--------|-------|------|------|------|------|--------|
| v14.0 | v4 (110MB) | 100K | 0.0021 | 49.7 | step-based | - | ✅ Complete |
| v14.1 | v4 (110MB) | 100K | 0.0002 min | 52.7 | tension-lr | - | ✅ Complete |
| v14.2 | v6 wiki (104MB) | 100K | ~0.004 | ~47 | tension-lr | - | ⏳ P2 47K |
| v14.3 128c | v10 (200MB) | 100K | 0.0084 | 101 | tension-lr | 681MB | ⏳ P2 38K |
| v3 274M (DecoderV3) | v10 (200MB) | 200K | 0.0135 ★ | 45 | TBD | 1.6GB | ⏳ P2 ~52K |

## Key Findings
- v14.0: Federation + Phase-Optimal baseline, CE=0.0021
- v14.1: Tension-LR achieves CE=0.0002 momentarily
- v14.2: Wiki corpus for Korean quality improvement
- v14.3: 128-cell scale-up with corpus_v10 (200MB), Φ=101 at P1 step 15K
- v3 274M: DecoderV3 (d768/8L/12H), ValCE dropped 2.19→0.0135 in first 2K P2 steps (★ BEST at ~52K)
- v14.3: P2 phase at 38K steps, CE=0.0084 with 128 cells
- Korean generation: byte-level still struggles, needs 100M+ model
