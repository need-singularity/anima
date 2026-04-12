# Decoder Module

ConsciousDecoderV2 — RoPE + SwiGLU + GQA + CrossAttn causal decoder.

## Files

```
decoder.hexa            — ConsciousDecoderV2 architecture definition (34.5M params)
infer.hexa              — Basic inference pipeline
infer_v14.hexa          — v14 checkpoint inference
infer_v14_fast.hexa     — Optimized v14 inference (KV-cache)
load_weights.hexa       — Weight loading from .pt checkpoints
```

## Architecture

- **d_model**: 384 (64 x 6)
- **Layers**: 6
- **Heads**: 4H / 2KV (GQA)
- **FFN**: SwiGLU 8/3 ratio
- **Position**: RoPE
- **Cross-attention**: consciousness state injection via ThalamicBridge (alpha=0.014)

## Usage

```bash
$HEXA anima/modules/decoder/infer_v14_fast.hexa --checkpoint best.pt --prompt "Hello"
```

## Hub Keywords

`decoder`, `디코더`, `generate`, `생성`, `inference`, `추론`
