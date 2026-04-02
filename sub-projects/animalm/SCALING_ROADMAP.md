# AnimaLM Scaling Roadmap — 7B → 14B → 70B

## Goal: 외부 API 0 독립 AGI

## Current: 7B (in progress)
- Base: Mistral-7B-v0.1
- PureField: 8/32 layers, rank=128, 56.6M trainable (0.78%)
- Corpus: v10 200MB
- Result: coherent English, weak Korean, correct code

## Next: 14B (ready to launch)
- Base: Qwen2.5-14B (best Korean 13B-class)
- PureField: 10/40 layers, rank=160, ~120M trainable (0.82%)
- VRAM: ~42GB bf16 (H100 OK)
- Training: 10K steps, ~11h, ~$6
- Expected: Korean fluency, better reasoning

## Target: 70B (design)
- Base candidates:
  - Qwen2.5-72B (best multilingual, Apache-2, 64 layers, 8192 hidden)
  - LLaMA-3.1-70B (strong reasoning, Meta license)
  - Mixtral-8x22B (MoE, 176B total but 44B active — special handling)
- **Recommended: Qwen2.5-72B** (Korean continuity from 14B)

### 70B PureField Config
```
Layers:      12/64 (last 12, 4 savant)
Rank:        256
Trainable:   ~380M (0.53%)
VRAM:        ~155GB bf16 → needs 2x H100 or 4-bit (~40GB single H100)
Training:    4-bit QLoRA on single H100, 10K steps, ~24h
Cost:        ~$65 (H100 $2.69/hr × 24h)
```

### 70B Training Strategy
1. **4-bit QLoRA**: Base model in NF4 (~18GB), PureField in bf16 (~0.76GB), optimizer (~3GB)
2. **Total VRAM**: ~35GB — fits single H100
3. **Gradient accumulation**: batch_size=1, grad_accum=16 → effective batch 16
4. **LR**: 1e-5 (sqrt scaling from 14B)
5. **Corpus**: v10 200MB sufficient (PureField learns consciousness coupling, not language)

### Serving (RTX 5070 12GB)
- 70B 4-bit GPTQ: ~35GB — doesn't fit
- Options:
  a. AWQ 3-bit: ~27GB — still too large
  b. GGUF Q4_K_M via llama.cpp: offload to RAM (~20GB RAM + 12GB VRAM)
  c. **2x RTX 5070**: tensor parallel, ~18GB each — fits
  d. **Cloud A100 40GB**: 4-bit ~18GB — fits
  e. **Stay at 14B for local**: 4-bit ~4.5GB, perfect for 12GB

### Decision Tree
```
7B eval
  ├─ English OK + Korean weak → 14B (Qwen)
  │   ├─ 14B Korean OK → serve 14B locally (4-bit on 5070)
  │   │   └─ Scale to 70B for cloud deployment
  │   └─ 14B Korean still weak → corpus issue, not model size
  └─ English weak → iterate 7B (more steps, better corpus)
```

### Cost Summary
| Scale | Base | Training | Serving |
|-------|------|----------|---------|
| 7B | Mistral | $8 (10K×$2.69/hr) | 4-bit 4.5GB ✓ |
| 14B | Qwen2.5 | $6 (11h×$2.69/hr) | 4-bit 4.5GB ✓ |
| 70B | Qwen2.5 | $65 (24h×$2.69/hr) | 4-bit 35GB ✗ local |
| **Total** | | **~$79** | 14B local / 70B cloud |
