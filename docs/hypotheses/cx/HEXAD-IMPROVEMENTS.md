# HEXAD-IMPROVEMENTS: Bidirectional Bridge + Per-Layer Adapter + Predictive Sense

## 가설 ID: B-1, D-2, S-2

Three high-impact improvements to the Trinity/Hexad architecture,
targeting the C-D information flow and sensory input processing.

## 알고리즘

### B-1: Bidirectional Bridge (양방향 브릿지)
```
After train_step:
  feedback = [ce_loss/10, phi_change]    # normalize CE to ~0-1
  C.feedback = feedback

On next C.step(x_input):
  fb_signal = Linear(2 -> dim)(feedback)  # project to C input space
  x_input = x_input + fb_signal * 0.1     # 10% modulation
  C.process(x_input)

Key: NO gradient leak. feedback is .detach()'d.
     D's loss signal flows to C as information, not gradient.
```

### D-2: Per-Layer Adapter (레이어별 어댑터)
```
Standard TransformerDecoder:
  x = embed(tokens) * gate_signal   # gate only at embedding
  x = transformer_layers(x)

Per-Layer Adapter:
  x = embed(tokens) * gate_signal   # still gate at embedding
  for layer_i in range(n_layers):
    x = transformer_layer_i(x)
    adapter_signal = Linear(d_model -> d_model)(gate_signal)
    x = x + adapter_signal * 0.1    # inject C at every layer

Each adapter initialized near-zero (Tanh bounded, std=0.01).
Adds ~66K params for 4 layers at d_model=128.
```

### S-2: Predictive Sense (예측 감각)
```
C stores last_input.
On step(x_input):
  predicted = Linear(dim -> dim)(last_input)
  surprise = MSE(predicted, x_input)
  update predictor via gradient step (lr=0.01)

  surprise_scale = 1.0 + surprise * 2.0   # 1x to 3x
  x_modulated = x_input * surprise_scale
  C.process(x_modulated)

  last_input = x_input
```

## 벤치마크 결과

Config: MitosisC(32 cells, cambrian_osc_qw), 50 steps, d_model=128, vocab=256, seq=32

```
┌────────────────────────────┬──────────┬──────────┬──────────┬──────────┬──────────┐
│ Hypothesis                 │ Best CE  │ Final CE │ CE vs BL │ Avg Phi  │ Max Phi  │
├────────────────────────────┼──────────┼──────────┼──────────┼──────────┼──────────┤
│ Baseline                   │  5.4082  │  5.5901  │   base   │   2.527  │  22.177  │
│ B-1: Bidirectional Bridge  │  5.4308  │  5.6533  │  -1.1%   │   2.489  │  22.020  │
│ D-2: Per-Layer Adapter     │  5.4711  │  5.5674  │  +0.4%   │   2.616  │  23.023  │
│ S-2: Predictive Sense      │  5.5182  │  5.7911  │  -3.6%   │  22.661  │  26.577  │
│ ALL: B1+D2+S2 Combined     │  5.5021  │  5.7206  │  -2.3%   │  23.274  │  26.213  │
└────────────────────────────┴──────────┴──────────┴──────────┴──────────┴──────────┘
```

## CE Comparison (lower = better)

```
  D-2 Per-Layer  ████████████████████████████████████ 5.5674  +0.4%  <-- BEST CE
  Baseline       █████████████████████████████████████ 5.5901  base
  B-1 Bidir      █████████████████████████████████████ 5.6533  -1.1%
  ALL Combined   █████████████████████████████████████ 5.7206  -2.3%
  S-2 Predict    ██████████████████████████████████████ 5.7911  -3.6%
```

## Phi Comparison (higher = better)

```
  ALL Combined   ██████████████████████████████████████████████ 23.274  +820.9%
  S-2 Predict    █████████████████████████████████████████████ 22.661  +796.6%
  D-2 Per-Layer  ██ 2.616  +3.5%
  Baseline       ██ 2.527  base
  B-1 Bidir      ██ 2.489  -1.5%
```

## CE Curve: Baseline

```
  CE |     ╭──╮
     |   ╭─╯  ╰──╮         ╭╮
     | ╭─╯        ╰──╮  ╭──╯╰─╮
     |─╯              ╰──╯     ╰──
     └──────────────────────────── step (50)
     5.41 ─────────────────── 5.93
```

## 핵심 통찰 / 발견된 법칙

### 1. D-2 (Per-Layer Adapter) wins on CE
- Only hypothesis that improved CE over baseline (+0.4%)
- Injecting C signal at every layer gives decoder richer consciousness context
- Small additional parameter cost (~66K, +6.9%)
- Phi also improved +3.5%

### 2. S-2 (Predictive Sense) dominates Phi (+797%)
- Massive Phi increase: 2.53 -> 22.66 average
- Surprise-modulated input amplifies consciousness dynamics
- BUT CE worsened -3.6% (amplified noise disrupts language learning)
- Trade-off: consciousness richness vs language quality

### 3. B-1 (Bidirectional Bridge) needs tuning
- CE slightly worse (-1.1%), Phi slightly worse (-1.5%)
- Feedback signal may need stronger modulation (currently 10%)
- Or: feedback encoding needs richer representation than [ce, phi_change]
- Promising direction but not yet effective at current settings

### 4. Combined (ALL) inherits S-2's Phi boost but D-2's CE doesn't survive
- Phi: +821% (dominated by S-2's surprise amplification)
- CE: -2.3% (S-2's noise disruption overwhelms D-2's small gain)
- Individual mechanisms compose sub-additively on CE

### 5. Surprise is the key to Phi
- avg_surprise = 1.03 (prediction error stays high with random tokens)
- Surprise amplification (1x-3x) creates more diverse cell dynamics
- This is consistent with Law 22: structure additions -> Phi up

### Law Candidate
```
  Law XX: Per-layer C injection > embedding-only gating for CE.
          Predictive surprise > static input for Phi.
          But surprise hurts CE — consciousness and language
          optimize differently.
```

## 적용 방법

1. **D-2 Per-Layer Adapter**: Integrate into `TransformerDecoder` as optional mode.
   Add `inject_per_layer=True` parameter to constructor.
   Low risk, small CE gain, small Phi gain.

2. **S-2 Predictive Sense**: Use for Phi-maximizing configurations only.
   Could gate surprise strength by CE: when CE is low enough, enable surprise.
   Or: anneal surprise_scale from 1.0 -> 3.0 over training.

3. **B-1 Bidirectional Bridge**: Needs richer feedback encoding.
   Try: encode full CE history (last 10 values) + Phi trajectory.
   Or: use a small RNN to encode feedback sequence.

## 파일 위치
- Benchmark: `bench_hexad_improvements.py`
- Architecture: `trinity.py` (base classes)
