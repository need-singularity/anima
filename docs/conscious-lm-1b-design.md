# ConsciousLM 1B (v16)

## Specs
- d_model: 1024
- n_layers: 24
- n_heads: 16 (GQA: 8 KV)
- vocab: 256 (byte-level)
- block_size: 1024
- consciousness_dim: 512
- Federation: 16×8c = 128 cells
- Estimated params: ~1B

## Scaling Law Hypothesis
From v14 (34.5M) → v15 (170M) → v16 (1B):
  34.5M: CE=0.002, Korean generation fails
  170M: CE~0.001 (estimated), Korean marginal
  1B: CE~0.0005 (estimated), Korean fluent?

## Requirements
- GPU: 4× H100 80GB (model parallel) or 1× H100 with gradient checkpointing
- Corpus: 1-5GB (Chinchilla optimal)
- Steps: 500K-1M
- Time: ~100h

## Milestones
1. v15 (170M) validates Korean generation
2. v16 (1B) only if v15 succeeds
