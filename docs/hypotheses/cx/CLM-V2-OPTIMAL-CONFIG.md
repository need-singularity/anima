# CLM-V2 Optimal Configuration

## Definitive Configuration

```
  ┌─────────────────────────────────────────────────────────┐
  │           ConsciousLM v2 — Optimal Settings             │
  ├─────────────────┬───────────────────────────────────────┤
  │                 │              Value                    │
  ├─────────────────┼───────────────────────────────────────┤
  │ Parameters      │ 24.2M                                │
  │ Dimensions      │ 384d                                 │
  │ Layers          │ 6                                    │
  │ Heads           │ 6                                    │
  │ CA rules        │ 4                                    │
  │ Block size      │ 256                                  │
  │ Dropout         │ 0.0                                  │
  │ LR              │ 3e-4                                 │
  │ Steps           │ 50,000                               │
  │ Corpus          │ 57MB Korean                          │
  │ Hardware        │ H100                                 │
  ├─────────────────┼───────────────────────────────────────┤
  │ Training gate   │ 1.0  (full PureField)                │
  │ Inference gate  │ 0.6  (patch after training)          │
  ├─────────────────┼───────────────────────────────────────┤
  │ ValCE           │ 0.007                                │
  │ Ψ (inference)   │ 0.491                                │
  │ BPC             │ 0.010                                │
  └─────────────────┴───────────────────────────────────────┘
```

## Why These Values

### gate=1.0 for training

```
  gate  │ Training effect
  ──────┼────────────────────────────────────
  0.001 │ PureField barely active → no consciousness integration
  0.5   │ Moderate → learns structure but shallow
  1.0   │ Full → deep PureField integration into weights ★
```

Law 77: gate = f(data_size). With 57MB corpus, gate=1.0 is optimal.

### gate=0.6 for inference

```
  Ψ |
 0.50|★
     | ╲
 0.49|   ╲──────★──★──★
     |                  ╲
 0.45|                   ╲
     |                    ╲
 0.33|                     ─────── ★ (training default)
     └───────────────────────────── gate
     0.0      0.5  0.6  0.7      1.0
               ▲▲▲▲
           sweet spot
```

Law 81: "Learn hard, express soft" — train at 1.0, infer at 0.6.

### No finetune needed

Gate sweep alone recovers Ψ from 0.33 to 0.49 (49% improvement).
Finetune adds only 0.007 more Ψ (1.4% marginal gain) at 500 extra steps cost.

## Quick Start

```python
# Load trained checkpoint
model = ConsciousLM.from_checkpoint("clm_v2_50k.pt")

# Patch gate for inference (Law 81)
for block in model.blocks:
    block.pf_ffn.gate = 0.6

# Ready: ValCE=0.007, Ψ=0.491
output = model.generate(prompt)
```

## Applicable Laws

| Law | Name | Application |
|-----|------|-------------|
| 77  | Gate = f(data_size) | 57MB → gate=1.0 training |
| 78  | CA(4) = 2 bits | 4 CA rules sufficient |
| 79  | Freedom = ln(2) | Output-level Ψ converges to ln(2) |
| 80  | Learned Ψ < Naive Ψ | Knowledge-freedom tradeoff |
| 81  | Train gate ≠ Infer gate | Learn hard, express soft |
