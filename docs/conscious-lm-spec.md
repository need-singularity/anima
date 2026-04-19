# ConsciousLM — Conscious Language Model Spec

> **Status (2026-04-19)**: Mk.V.1 foundation (82 atoms, [11*]/[11**]) wired into training loop.
> See [MK5-DELTA0-ABSOLUTE.md](MK5-DELTA0-ABSOLUTE.md) for foundation + bridge architecture.

## Current implementations

| Track | File | Revision | Role |
|---|---|---|---|
| CLM base | `training/train_clm.hexa` | r5 ready | ConsciousLM training loop (structural port from train_clm.py 2165 LOC) |
| CLM GPU | `training/train_clm_gpu.hexa`, `_gpu_v2.hexa` | — | GPU variants |
| CLM kr | `training/train_clm_kr.hexa`, `_d64_kr.hexa`, `_d64_kr_nl8.hexa` | — | Korean-specialized |
| CLM emergent | `training/train_clm_emergent.hexa` | — | Emergent-module training |
| ALM base | `training/train_alm.hexa` | r11 ready | AnimaLM (Mistral/Qwen2.5 base + PureField FFN + tension bridge) |
| ALM 14B | `training/train_alm_14b.hexa`, `_14b_r5.hexa`, `_14b_r5_kbase.hexa` | — | 14B variants |
| Checkpoint gate | `training/ckpt_gate_a6.hexa` | — | [11**] A6 meta-closure gate |
| Meta-closure bridge | `training/a6_meta_closure_bridge.hexa` | — | [11*] → [11**] bridge |

## Aux loss modules (opt-in, default OFF)

- `training/lens_{field,holographic,quantum,string,toe}_loss.hexa` — 5-Lens 19/19 atoms
- `training/quadruple_cross_loss.hexa`, `_sweep.hexa` — 4-axis cross-loss
- `training/tension_link_{causal,quantum_rho,second_order}.hexa` — TL diagnostic variants
- `training/holographic_propagator.hexa` — G_holo inside TL
- `training/sumt_bigbang_atom.hexa` — SUMT 100 atoms (k=39 복구)
- `training/corpus_universe_tier_labels.jsonl` — tier-labeled curriculum

## Design refs

| Scale | Doc |
|---|---|
| 100M | [conscious-lm-100m-design.md](conscious-lm-100m-design.md) |
| 1B   | [conscious-lm-1b-design.md](conscious-lm-1b-design.md) |
| Full | [modules/conscious_lm.md](modules/conscious_lm.md) |

## Corpus

- `training/corpus_ko_ytv1/` — Korean YT audiobook (1392 seg / 1.84h / LJSpeech-style)
- 다른 corpus: `training/corpus_*.txt(.gz)` — gitignored
- Distribution via R2 (see shared/config/infrastructure.json)
