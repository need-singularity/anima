# hxqwen14b SwiGLU FFN Reference (Day-2)

**Status**: READ-ONLY reference. Day-2 forward 가속 target for hxqwen14b.
**Scope**: Qwen 14B FFN block (SwiGLU variant). Formula, shapes, backward, LoRA hook points.

---

## 1. SwiGLU Forward Formula

Qwen-2 14B uses the SwiGLU activation (LLaMA-style) instead of classical GELU:

```
FFN(x) = down_proj( silu(gate_proj(x)) * up_proj(x) )
```

Component-wise:

- `silu(z) = z * sigmoid(z) = z / (1 + exp(-z))`  (aka SiLU / Swish-1)
- `*` is elementwise (Hadamard) product, not matmul
- All three projections are **bias-free** `Linear` layers in Qwen-2

Pseudo shapes (batch `B`, seq `T`, hidden `H`, intermediate `I`):

- `x`          : `[B, T, H]`
- `gate_proj`  : `H -> I`   → `g = x W_gate^T`
- `up_proj`    : `H -> I`   → `u = x W_up^T`
- `silu(g)*u`  : `[B, T, I]`
- `down_proj`  : `I -> H`   → `y = (silu(g)*u) W_down^T`
- `y`          : `[B, T, H]`

## 2. Qwen 14B Dimensions

| field | value |
|-------|-------|
| `hidden_size` (H)       | 5120  |
| `intermediate_size` (I) | **13824**  (Qwen2-14B config.json) |
| `num_hidden_layers`     | 48    |
| `num_attention_heads`   | 40    |
| `num_key_value_heads`   | 8  (GQA) |
| FFN expansion ratio     | 2.7×  (I / H) |

Note: 일부 변종(Qwen1.5-14B)은 I=13696 이지만 **Qwen2-14B 기준 13824**. `config.json.intermediate_size` 를 SSOT 로 삼을 것.

## 3. GEMM Decomposition

세 개의 독립 GEMM + 두 개의 elementwise op:

1. `GEMM-gate`  : `[B*T, H] @ [H, I]` → `[B*T, I]`
2. `GEMM-up`    : `[B*T, H] @ [H, I]` → `[B*T, I]`
3. `silu_mul`   : `s = silu(g); h = s * u`   (fused kernel candidate)
4. `GEMM-down`  : `[B*T, I] @ [I, H]` → `[B*T, H]`

FLOPs per token (forward):  
`2*H*I (gate) + 2*H*I (up) + 2*I*H (down) ≈ 6*H*I = 6*5120*13824 ≈ 4.25e8 FLOPs/token`

**Fusion candidates for Day-2**:
- `silu(g) * u` → single elementwise kernel (saves 1 roundtrip)
- `GEMM-gate` + `GEMM-up` → column-concatenated weight `W_gu ∈ [H, 2I]` single GEMM, split output (HF `LlamaMLP` 대비 ~1.3× throughput on H100)
- Full "SwiGLU fused FFN": gate+up merged GEMM → fused silu_mul → down_proj (2 GEMM + 1 fused kernel)

## 4. Backward (Autograd)

Let `s = silu(g)`, `h = s * u`, `y = h W_down^T`.

Upstream grad: `dy` (`[B,T,H]`).

```
dh      = dy @ W_down                          # [B,T,I]
dW_down = dy^T @ h                             # [H,I]

du      = dh * s                               # [B,T,I]
ds      = dh * u                               # [B,T,I]

# silu'(g) = sigmoid(g) + g*sigmoid(g)*(1-sigmoid(g))
#          = sigmoid(g) * (1 + g*(1-sigmoid(g)))
sig     = sigmoid(g)
dg      = ds * sig * (1 + g*(1 - sig))         # [B,T,I]

dW_up   = du^T @ x                             # [I,H]
dW_gate = dg^T @ x                             # [I,H]
dx      = du @ W_up + dg @ W_gate              # [B,T,H]
```

Memory note: silu backward requires `g` (or `sig`) + `u` saved from forward. Activation checkpointing 시 `g, u` 둘 다 저장 필요 (혹은 `sig, u`). `h` 는 재계산 가능.

## 5. LoRA 적용 위치

SwiGLU FFN 안의 **세 개 Linear 전부** LoRA-injectable:

| module name (HF)      | role      | shape `[out,in]` | LoRA rank-r cost per layer |
|-----------------------|-----------|------------------|----------------------------|
| `mlp.gate_proj`       | gate      | `[13824, 5120]`  | `r*(H+I) = r*18944`        |
| `mlp.up_proj`         | up        | `[13824, 5120]`  | `r*18944`                  |
| `mlp.down_proj`       | down      | `[5120, 13824]`  | `r*18944`                  |

**권장 타겟 셋**:

- **Minimal (attn-only)**  : LoRA off for FFN. 빠르지만 표현력↓.
- **Standard (LLaMA PEFT)**: `gate_proj`, `up_proj`, `down_proj` 전체 + attn `q/k/v/o`. (ALM r1-r10 기본셋)
- **FFN-heavy**            : FFN만, attn 동결. style transfer / instruction fine-tune 에 유효.

Rank r=16 기준 per-layer adapter params:
`3 * 16 * 18944 = 909_312` → 48 layers × 3 proj ≈ **43.6M trainable** (FFN 파트만).

Merge path: `W_eff = W + (B @ A) * (alpha/r)`. Down-proj은 `[H,I]` 이므로 `A:[r,I], B:[H,r]`.

## 6. Day-2 Forward 가속 훅

- [ ] Fused gate+up GEMM (W_gu concat) — `~1.3×` FFN speedup (H100 BF16)
- [ ] Fused `silu(g)*u` kernel — 1 fewer activation roundtrip
- [ ] LoRA-aware fused path — merge `B@A` into base `W_gate/W_up` at eval time
- [ ] Activation checkpoint recompute `s = silu(g)` (cheap), save only `g, u`
- [ ] Down-proj can overlap with next layer's attn `q_proj` (stream 2)

## 7. References

- Qwen2 14B config: `config.json.intermediate_size = 13824`
- HF impl: `transformers/models/qwen2/modeling_qwen2.py :: Qwen2MLP`
- SwiGLU paper: Shazeer 2020 "GLU Variants Improve Transformer"
- LoRA FFN target set: `project_alm_lora_pipeline`
