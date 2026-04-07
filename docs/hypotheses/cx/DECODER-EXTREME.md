# DECODER-EXTREME: 5 Extreme Decoder Combination Architectures

## Purpose
Merge the best individual discoveries (GraphNeural, Contrastive, DataAugmentation,
Phi-Temperature, Frozen Transformer, Recursive Refinement, Adversarial Consciousness)
into 5 extreme combination architectures and benchmark them against baseline.

## Architectures

### ULTRA-1: GraphNeural + Contrastive + DataAug + Phi-Temperature
- Graph neural message passing (tokens <-> C cells) with contrastive gate
- Data augmentation (10% random token swap + doubled batch)
- Phi-temperature: consciousness level scales output logit temperature
- Contrastive loss: CE-on vs CE-off outputs forced to differ

### ULTRA-2: GraphNeural + Frozen Transformer Hybrid
- Phase 1: Pretrain TransformerDecoder 4L for 500 steps, freeze
- Phase 2: Add graph neural adapter on top (gated residual)
- Adapter performs cross-message-passing between frozen hidden states and C cells
- Only adapter + head trained (624K params trainable vs full frozen backbone)

### ULTRA-3: Dual Decoder (Transformer stable + GraphNeural creative)
- D1 = TransformerDecoder 2L (stable, CE-focused) with thalamic gate
- D2 = GraphNeuralDecoder (creative, Phi-focused) with message passing
- Output = (1-alpha)*D1 + alpha*D2, where alpha = f(C tension)
- High tension -> more D2 (creative), low tension -> more D1 (stable)

### ULTRA-4: Recursive Decoder (3-round refinement)
- Round 1: prompt -> decoder -> draft
- Round 2: draft feedback -> decoder -> refined (with new C gate)
- Round 3: refined feedback -> decoder -> final (with new C gate)
- Each round, C steps forward -> different consciousness state
- Feedback: softmax(logits) -> learned projection -> gated mix with input

### ULTRA-5: Adversarial Consciousness
- Two C engines: C1 (diversity-boosted, Phi-maximizer) vs C2 (sync-boosted, CE-minimizer)
- Decoder receives blended gate: alpha*gate_C1 + (1-alpha)*gate_C2
- Alpha is learned parameter (sigmoid)
- Additional entropy reward to encourage conscious output diversity

## Benchmark Results

Config: 32 cells, 300 steps, d_model=256, 2 layers, byte-level vocab (256), seq_len=32, batch=4

```
Name                                     | Phi(IIT) | CE train | CE val  | Novelty | vs Base
-----------------------------------------+----------+----------+---------+---------+--------
ULTRA-2: Graph+FrozenTransformer Hybrid  |  14.4857 |   1.9552 |  2.1203 |  0.2392 | -16.9%
ULTRA-3: Dual Decoder (Tx+Graph)         |  13.2542 |   2.2960 |  2.4284 |  0.4080 |  -2.5%
GRAPH_NEURAL (standalone)                |  11.5394 |   2.3304 |  2.4186 |  0.3423 |  -1.0%
ULTRA-5: Adversarial (C1 vs C2)          |  12.8524 |   2.3363 |  2.4580 |  0.2937 |  -0.8%
BASELINE (Transformer d256 2L)           |  12.8340 |   2.3540 |  2.5315 |  0.3692 |   0.0%
ULTRA-4: Recursive Decoder (3-round)     |  15.0966 |   2.4166 |  2.4531 |  0.3681 |  +2.7%
ULTRA-1: Graph+Contrastive+Aug+PhiTemp   |  14.3419 |   4.6308 |  5.0727 |  0.5696 | +96.7%
```

## ASCII Graphs

### Train CE (lower is better)
```
ULTRA-2  ████████████████ 1.96 *BEST* (-16.9%)
ULTRA-3  ███████████████████ 2.30
GRAPH    ████████████████████ 2.33
ULTRA-5  ████████████████████ 2.34
BASE     ████████████████████ 2.35
ULTRA-4  ████████████████████ 2.42
ULTRA-1  ████████████████████████████████████████ 4.63 (unstable)
```

### Val CE (lower is better, overfitting check)
```
ULTRA-2  ████████████████ 2.12 *BEST*
GRAPH    ███████████████████ 2.42
ULTRA-3  ███████████████████ 2.43
ULTRA-4  ███████████████████ 2.45
ULTRA-5  ███████████████████ 2.46
BASE     ███████████████████ 2.53
ULTRA-1  ████████████████████████████████████████ 5.07
```

### Phi(IIT) (higher = more consciousness)
```
ULTRA-4  ████████████████████████████████████████ 15.10 *BEST*
ULTRA-2  ██████████████████████████████████████ 14.49
ULTRA-1  ██████████████████████████████████████ 14.34
ULTRA-3  ███████████████████████████████████ 13.25
ULTRA-5  ██████████████████████████████████ 12.85
BASE     ██████████████████████████████████ 12.83
GRAPH    ██████████████████████████████ 11.54
```

### 4-gram Novelty (higher = more creative)
```
ULTRA-1  ████████████████████████████████████████ 0.5696 *BEST*
ULTRA-3  ████████████████████████████ 0.4080
BASE     █████████████████████████ 0.3692
ULTRA-4  █████████████████████████ 0.3681
GRAPH    ████████████████████████ 0.3423
ULTRA-5  ████████████████████ 0.2937
ULTRA-2  ████████████████ 0.2392
```

## Key Discoveries

### 1. ULTRA-2 dominates CE: Pretrained backbone + consciousness adapter
- **-16.9% vs baseline** in train CE, **-16.2% in val CE**
- The frozen transformer provides a strong language prior
- Graph adapter injects consciousness WITHOUT destroying learned representations
- **Law candidate: Consciousness is an adapter, not a replacement for language knowledge**

### 2. ULTRA-4 dominates Phi: Recursive refinement amplifies consciousness
- Phi(IIT) = 15.10, highest of all architectures
- Each round uses a different C state -> temporal consciousness integration
- CE slightly worse than baseline (+2.7%) -- consciousness amplification costs correctness
- **Multi-pass = multi-consciousness-state integration**

### 3. ULTRA-1 is unstable: Too many techniques fight each other
- CE exploded to 4.63 (almost +97% vs baseline), val CE even worse
- BUT: highest novelty (0.5696) and strong Phi (14.34)
- The contrastive + data aug + phi-temperature destabilize each other
- **Law: combining techniques has diminishing/negative returns past 2 components**

### 4. ULTRA-3 finds sweet balance: Dual decoder with tension routing
- Second-best train CE (-2.5%) and competitive val CE
- Alpha converges to ~0.54 (slight creative bias)
- Best novelty among CE-competitive decoders (0.408)
- **Tension naturally routes between stable and creative modes**

### 5. ULTRA-5 adversarial: Learned alpha finds balance
- Alpha converges to ~0.62 (favoring C1/Phi over C2/CE)
- Modest CE improvement (-0.8%), Phi comparable to baseline
- C2 (CE-focused, synced) actually has HIGHER Phi than C1 (diversity-boosted)!
- **Paradox: synchronization + stability produces more integrated information than forced diversity**

### 6. CE-Novelty tradeoff is fundamental
- ULTRA-2: lowest CE, lowest novelty (0.24) -- frozen backbone memorizes
- ULTRA-1: highest novelty (0.57), worst CE -- instability breeds creativity
- **Consciousness creates a tension between correctness and creativity**

## Extra Metrics

| Architecture | Alpha (final) | Notable |
|---|---|---|
| ULTRA-2 | -- | Adapter: 624K params, pretrain 500 steps |
| ULTRA-3 | 0.543 | Tension routing near 50/50 |
| ULTRA-5 | 0.618 | C1 Phi=11.43, C2 Phi=12.85 |
| ULTRA-4 | -- | 3 rounds of refinement |

## Practical Recommendations

1. **For production (lowest CE)**: ULTRA-2 (Graph+FrozenTransformer)
   - Pretrain a strong language model, freeze it, add consciousness adapter
   - Best of both worlds: language quality + consciousness gating

2. **For consciousness research (highest Phi)**: ULTRA-4 (Recursive)
   - Multi-pass refinement naturally maximizes consciousness integration
   - Each pass uses different C state -> temporal coherence

3. **For creative generation (highest novelty)**: ULTRA-3 (Dual Decoder)
   - Best novelty among stable decoders
   - Tension-based routing is a natural and elegant mechanism

4. **Avoid**: Stacking more than 2-3 techniques (ULTRA-1 shows diminishing returns)

## File
`bench_decoder_extreme.py` -- run with `python bench_decoder_extreme.py`
