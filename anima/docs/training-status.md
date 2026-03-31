# Training Status (2026-03-31)

| Version | Corpus | Steps | CE | Φ | LR | Status |
|---------|--------|-------|------|------|------|--------|
| v14.0 | v4 (110MB) | 100K | 0.0021 | 49.7 | step-based | ✅ Complete |
| v14.1 | v4 (110MB) | 100K | 0.0002 min | 52.7 | tension-lr | ✅ Complete |
| v14.2 | v6 wiki (104MB) | 100K | ~0.004 | ~47 | tension-lr | ⏳ P2 47K |
| v14.3 | v8 dialogue (TBD) | 100K | TBD | TBD | tension-lr | 📋 Planned |

## Key Findings
- v14.0: Federation + Phase-Optimal baseline, CE=0.0021
- v14.1: Tension-LR achieves CE=0.0002 momentarily
- v14.2: Wiki corpus for Korean quality improvement
- Korean generation: byte-level still struggles, needs 100M+ model
