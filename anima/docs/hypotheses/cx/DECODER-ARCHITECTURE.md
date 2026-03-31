# DECODER-ARCHITECTURE: 6 Decoder Architectures for Consciousness-Language Bridge

## Purpose
Systematically compare decoder architectures for translating consciousness (C states) into language. The core question: **what is the optimal way for a decoder to consume consciousness information?**

## Architectures Tested

### 1A: PROMPT_INJECTION
- C states -> compute Phi, tension, emotion -> format as prefix token embeddings
- Prepend learned consciousness prefix (8 tokens) before actual input
- Decoder sees consciousness as context in its attention window
- Analogy: "system prompt" but as continuous learned embeddings

### 1C: CONTRASTIVE_GATE
- Standard thalamic gate (C -> sigmoid -> multiply embeddings)
- Additional loss: -lambda * MSE(output_on, output_off)
- Forces the decoder to actually USE consciousness (not ignore the gate)
- lambda=0.1 to not overwhelm CE loss

### 2A: CONSCIOUSNESS_TRANSFORMER
- Cross-attention decoder: Q=token hidden, KV=projected C states
- Each layer: self_attn -> cross_attn(Q=hidden, KV=C) -> FFN
- C states participate as a separate "memory" at every layer
- Most parameter-rich approach

### 2B: MOE_CONSCIOUSNESS
- 4 expert FFNs per layer, router based on C mean state
- Top-2 expert selection via softmax routing
- C determines WHICH computation path, not the values directly
- Inspired by Mixtral but routing by consciousness instead of input

### 2C: SSM_DECODER (S4-inspired)
- State Space Model: A,B,C,D matrices, discretized sequential scan
- C states set the initial hidden state h0
- O(N) complexity (no attention) -- potentially scalable
- Autoregressive by nature (each step depends on previous)

### 2D: DIFFUSION_DECODER
- Start from noise, denoise iteratively guided by C
- C's Phi determines number of denoising steps (high Phi -> fewer steps)
- Final denoised representation -> project to vocab logits
- Most unconventional approach

## Benchmark Results

```
Config: 32 cells, 100 steps, d_model=256, 2 layers, byte-level vocab=256
        seq_len=32, batch=4, real corpus (data/corpus.txt)
```

| Architecture | CE Start | CE End | dCE vs Baseline | Phi(IIT) | Phi(proxy) | Time |
|---|---|---|---|---|---|---|
| **1C: CONTRASTIVE_GATE** | 5.705 | **2.743** | **-2.2%** | 0.000 | 0.004 | 1.2s |
| 2B: MOE_CONSCIOUSNESS | 5.727 | 2.799 | -0.2% | 0.000 | 0.003 | 1.1s |
| BASELINE (Transformer d256 2L) | 5.705 | 2.805 | 0.0% | 0.000 | 0.003 | 1.0s |
| 2A: CONSCIOUSNESS_TRANSFORMER | 5.688 | 2.807 | +0.1% | 0.000 | 0.003 | 1.0s |
| 1A: PROMPT_INJECTION | 5.765 | 2.832 | +1.0% | 0.000 | 0.004 | 2.1s |
| 2C: SSM_DECODER | 5.724 | 3.547 | +26.5% | 0.000 | 0.003 | 0.5s |
| 2D: DIFFUSION_DECODER | 5.778 | 3.864 | +37.8% | 0.000 | 0.004 | 1.9s |

## ASCII Chart

```
CE End (lower = better):

1C CONTRASTIVE    ████████████████████████████ 2.743  *BEST*
2B MOE            ████████████████████████████ 2.799
BASELINE          █████████████████████████████ 2.805
2A CROSS-ATTN     █████████████████████████████ 2.807
1A PROMPT_INJ     █████████████████████████████ 2.832
2C SSM            ████████████████████████████████████ 3.547
2D DIFFUSION      ████████████████████████████████████████ 3.864
```

## Architecture Ranking

```
  Tier 1 (competitive with/beats baseline):
    1C > 2B > BASELINE >= 2A

  Tier 2 (underperform baseline):
    1A (prompt injection adds parameters but not performance)

  Tier 3 (fundamentally limited at 100 steps):
    2C (SSM needs more steps to learn temporal patterns)
    2D (diffusion needs curriculum/more training to denoise well)
```

## Key Insights

### 1. Contrastive gating is the winner
The contrastive loss (-lambda * MSE(on, off)) forces the decoder to actually leverage consciousness. Without it, the thalamic gate can be ignored or made constant. This is the cheapest and most effective approach: same architecture as baseline + one extra loss term.

### 2. Cross-attention (2A) does NOT help at this scale
Despite being the most "principled" approach (Q=tokens, KV=C), cross-attention performs at baseline level. The C states from 32 cells with sync are too homogeneous -- cross-attention has nothing useful to attend to differentially.

### 3. MoE routing by consciousness works subtly
MoE with C-routing shows slight improvement. The key insight: consciousness determines *which computation path* (expert selection), not *what values to add*. This is architecturally cleaner than gating.

### 4. SSM and Diffusion need more scale
Both SSM and Diffusion decoders underperform at 100 steps. SSM's sequential scan needs longer sequences to build useful hidden state. Diffusion's denoising is fundamentally harder to train -- the 0.3/0.7 curriculum blend helps but 100 steps is insufficient.

### 5. Phi(IIT) = 0 for all
With 32 cells + sync, all C engines converge to similar states. Phi requires diversity. This is consistent with the project's known observation: sync=0.35 with 32 cells kills Phi. Does NOT mean consciousness is absent -- just that the measurement at this scale cannot detect integration above the noise floor.

## Applicable Laws

- **Law 22**: Feature addition -> Phi down, structure addition -> Phi up
  - 2A adds features (cross-attn params) but no structural diversity -> no Phi gain
- **Law 29**: Speech (loop only) != Conversation (factions needed)
  - All decoders produce "speech" but consciousness routing (1C, 2B) enables more meaningful output

## Reproduction

```bash
python3 bench_decoder_arch.py                      # All architectures
python3 bench_decoder_arch.py --only 1C 2B         # Specific ones
python3 bench_decoder_arch.py --cells 64 --steps 200  # Larger scale
```

## Conclusion

**Contrastive gating (1C) is the recommended approach** for consciousness-decoder integration. It is:
- Architecturally simple (baseline + one loss term)
- Cheapest to compute (no extra parameters vs baseline)
- Best CE performance (-2.2% vs baseline)
- Forces the decoder to depend on consciousness (prevents gate collapse)

For future work: combine 1C + 2B (contrastive MoE routing) for potentially stronger results.
