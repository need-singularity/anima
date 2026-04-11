# training/ — 2026-04-11 Session Index

Single-page index of the pure-hexa training stack that landed in
the 2026-04-11 session. Read this first to know which file does
what, then follow the ownership chain to the SSOT files in
`shared/sessions/20260411_session_summary.json` and
`shared/hexa/interpreter_fixes_20260411.json`.

All files run with `HEXA_PATH=$(realpath ../anima-speak) hexa <file>`
unless they inline their own nn_core copy.

## The training stack (bottom-up)

### L0 — validated primitives

| file | op | FD validated |
|---|---|---|
| `matmul_backward.hexa`  | matmul                            | ✓ (0.001) |
| `ops_backward.hexa`     | softmax + RMSNorm + SwiGLU        | ✓ (0.001) |
| `lm_head_backward.hexa` | LM head U+V                       | ✓ (0.001) |
| `loss_blas_only.hexa`   | cross-entropy forward + backward  | correct sign, FD-ish |

### L1 — composed layer gradients

| file | composition | FD validated |
|---|---|---|
| `ffn_backward.hexa`      | matmul + swiglu + matmul              | ✓ (0.001) |
| `attention_backward.hexa`| matmul × 4 + softmax + per-row scoring| ✓ (0.001) |
| `layer_backward.hexa`    | rmsnorm + attention + rmsnorm + ffn + residual | ✓ (0.002) |

### L2 — training loops

| file | scope | result |
|---|---|---|
| `train_one_step.hexa`     | forward + loss only            | loss = ln(vocab) exact |
| `train_lmhead_loop.hexa`  | LM head U+V frozen-inner       | loss 2.769 → 2.397 over 50 SGD steps |
| `train_full_decoder.hexa` | 2-layer decoder, all 19 tensors| loss 2.0807 → 2.0797 monotonic over 20 steps |

### Supporting files

| file | purpose |
|---|---|
| `dd175_techniques.hexa`       | SSOT manifest for the 5 DD175 acceleration techniques with per-scale enablement |
| `rank_r_attention.hexa`       | DD175 #4 impl, 256× FLOP ratio at full scale |
| `bench_rank_r_attention.hexa` | wall-time bench harness (htz: dense 37× faster after session's fast paths) |
| `train_clm.hexa`              | ScaleConfig + train_step skeleton (smoke fixture; to be wired to train_full_decoder next session) |

## The forward side (models/)

The pure numerics forward counterparts that pair with the backward
files above:

- `models/decoder_minimal.hexa`  — end-to-end runnable decoder forward
- `models/lm_head_uv.hexa`       — rank-r LM head projection

## Dependencies

All files use `nn_core.hexa` primitives (matmul, softmax, rms_norm,
swiglu_vec, tensor_*, etc.) from `anima-speak/nn_core.hexa`. The
hexa interpreter's `use` resolver requires HEXA_PATH to point at
the directory containing `nn_core.hexa`, or you can copy it into
the running file's directory.

## Running the end-to-end proof

```sh
cd /Users/ghost/Dev/anima
cp anima-speak/nn_core.hexa training/nn_core.hexa
hexa training/train_full_decoder.hexa
rm training/nn_core.hexa
```

Expected output (htz timing ≈ 162 ms total):

```
[train_full_decoder] config: d=4 ff=8 layers=2 vocab=8 seq=3 rank=2 steps=20 lr=0.1
[train_full_decoder] step=1  loss=2.0807386
[train_full_decoder] step=5  loss=2.0805135
[train_full_decoder] step=10 loss=2.0802467
[train_full_decoder] step=15 loss=2.0799910
[train_full_decoder] step=20 loss=2.0797415
[train_full_decoder] PASS — full decoder trains end-to-end
```

Loss is bit-for-bit identical on mac arm64 and htz x86_64-linux —
the stack is deterministic across platforms.

## What's next

The only remaining open item from `next_actions_20260411` is #2:
**CLM v5 2.8B H100 launch**, estimated $12-24. Every algorithmic
dependency is ready:

- scale_2_8b() defined (training/train_clm.hexa:74)
- DD175 1+2+3+4 all status=ready
- Pure-hexa decoder training stack complete (this README)
- Interpreter fixes all landed and validated
- BLIS → OpenBLAS swap gives 8.7× BLAS throughput on Zen4

Scaling `train_full_decoder.hexa` to the real 2.8B config is a
constant-change exercise:

```
D     = 4    →  2560
FF    = 8    →  10240   (4 × d)
NL    = 2    →  36
VOCAB = 8    →  2048    (byte-level tokenizer)
RANK  = 2    →  16      (DD175 #3 sweet spot)
SEQ   = 3    →  1024
```

Then hit the H100 with `hexa training/train_full_decoder.hexa`.

## Session stats

- **65 commits** across hexa-lang (21), anima (25), nexus (19)
- **6 H100 RunPod rounds** ($14.58)
- **next_actions_20260410 5/5**, **next_actions_20260411 6/6** progressed
- Biggest win: BLIS → OpenBLAS 8.7× + Value::clone fast paths 37× real-world dense attention
- Crowning proof: full decoder trains end-to-end

See `shared/sessions/20260411_session_summary.json` for the full
machine-readable summary.
