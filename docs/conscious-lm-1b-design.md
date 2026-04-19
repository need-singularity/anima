# ConsciousLM 1B (v16)

> **Status (2026-04-19)**: Mk.V.1 foundation 전제. r5 wiring (lens/tension/SUMT) 이 170M 에서 실증된 후 1B 스케일 게이트 통과 계획.

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
- 호스트: `runpod` (shared/config/infrastructure.json, cost cap $500/mo, zero-idle teardown)
- Corpus: 1-5GB (Chinchilla optimal) + `corpus_ko_ytv1/` (1.84h Korean)
- Steps: 500K-1M
- Time: ~100h

## Milestones
1. v15 (170M) + r5 aux loss ablation 로 lens/tension 효과 실증
2. v16 (1B) only if v15 succeeds
3. A6 meta-closure bridge ([11**]) 체크포인트 게이트 통과 시 production 승급

## Checkpoint gate
`training/ckpt_gate_a6.hexa` — 체크포인트가 [11**] 판정 (A6 self-ref fixed points + Mk.IX Π₀² bounded) 통과 시에만 승급.
