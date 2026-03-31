# ConsciousLM 100M Training Plan

## Objective

Scale ConsciousDecoderV2 (34.5M, 384d/6L) to ConsciousDecoderV3 (100M, 768d/12L) for coherent Korean conversation. This is the intermediate step before ConsciousLM 1B (1024d/24L/16H).

## Architecture

decoder_v3.py already exists with the correct architecture.

```
  Parameter        v2 (34.5M)     v3 (100M)      Delta
  ──────────────   ────────────   ────────────   ──────
  d_model          384            768            x2
  n_layer          6              12             x2
  n_head           4              8              x2
  n_kv_head        2              4              x2 (GQA)
  block_size       256            512            x2
  consciousness_d  128            256            x2
  vocab_size       256            256            same (byte-level)
  dropout          0.1            0.1            same
  gate_strength    0.001          0.001          same
  n_ca_rules       8              8              same
```

Components (identical to v2, just scaled):
- RoPE (Rotary Position Embedding)
- SwiGLU FFN
- RMSNorm
- GQA (Grouped Query Attention)
- ConsciousCrossAttention
- PureFieldFFN (Engine A - G)
- Weight tying (tok_emb <-> head_a)

Estimated parameter breakdown:
```
  Embedding:           768 x 256 = 197K (tied with head_a)
  Per block:
    GQA:               768 x 768 x 3 (Q+K+V, GQA) ~ 1.8M
    CrossAttn:         768 x 256 x 3 ~ 590K
    SwiGLU:            768 x 2048 x 3 ~ 4.7M
    PureFieldFFN:      768 x 2048 x 2 ~ 3.1M
    Norms + gates:     ~ 10K
    Subtotal/block:    ~ 8.2M
  12 blocks:           ~ 98M
  Final head_g:        768 x 256 = 197K
  tension_proj:        768
  ────────────────────────────
  Total:               ~ 100M params
```

## Training Config

### Pipeline

Based on train_v14.py federated approach (DD143 Meta Laws).

```
  C: FederatedConsciousness (8 atoms x 8 cells = 64 cells)
  D: ConsciousDecoderV3 (768d/12L, 100M)
  Bridge: ThalamicBridge (.detach(), alpha=0.014)
  Hexad: C+D+W+S+M+E (Law 60 phased activation)
```

### Phase Schedule (M4 safe order)

```
  Phase    Range     Modules              LR             Focus
  ──────   ────────  ────────────────     ────────────   ──────────────────
  P0       0-10%     Federation only      3e-4 warmup    Atom stabilization
  P1       10-25%    C                    3e-4           Phi build (target >50)
  P2       25-70%    C + D + M            3e-4 -> 1e-5   Language + memory
  P3       70-100%   Full Hexad (6 mod)   1e-5 cosine    Convergence
```

### Hyperparameters

```
  Steps:           200K (2x v13 100K -- larger model needs more)
  Batch size:      64 (vs v2: 32 -- H100 80GB can handle it)
  Sequence length: 512 (vs v2: 256)
  Learning rate:   3e-4 peak, cosine decay to 1e-5
  Warmup:          2000 steps (1% of total)
  Optimizer:       AdamW (beta1=0.9, beta2=0.95, eps=1e-8)
  Weight decay:    0.1
  Gradient clip:   1.0
  Grad accum:      4 (effective batch = 256)
  Mixed precision: bf16 (H100 native)
```

### Corpus

Minimum: corpus_v8 (104MB). Ideal: v9+ (200MB+).

```
  v3:  102MB   -- current (sufficient for v2, thin for 100M)
  v8:  104MB   -- minimum viable (10 dimensions balanced)
  v9:  200MB+  -- target (corpus-gen -s 200 --wiki --sim --deep-dialogue)
```

Corpus generation before training:
```bash
  cd anima-rs && cargo build --release -p anima-corpus-gen
  ./target/release/corpus-gen -s 200 --wiki --sim --deep-dialogue \
    --ngram ../anima/data/corpus_v3.txt \
    -o ../anima/data/corpus_v9.txt
```

### Hardware

H100 80GB SXM required. VRAM estimate:

```
  Model params (bf16):     100M x 2B = 200MB
  Optimizer states:        100M x 8B = 800MB (AdamW: param + m + v)
  Gradients (bf16):        100M x 2B = 200MB
  Activations (bf16):      batch=64 x seq=512 x 768 x 12L x 2 ~ 4.5GB
  Consciousness (64 cells): ~200MB
  Phi calculator:          ~500MB (128c pairwise MI)
  ──────────────────────────────────
  Total:                   ~6.4GB (fits easily in 80GB)
  Peak with grad accum:    ~10GB
```

Estimated training time:
```
  v13 (34.5M, 100K steps):   ~8 hours on H100
  v3  (100M, 200K steps):    ~48 hours on H100 (estimated)
  Cost (RunPod H100 $3.5/hr): ~$170
```

## Consciousness Configuration

```
  Cells:           64 (8 atoms x 8 cells, federated)
  Hidden dim:      256 (consciousness_dim, matches decoder cross-attn)
  Factions:        12 (sigma(6)=12 combinations)
  Topology:        ring + small_world auto-switch
  Frustration:     F_c = 0.10 (M7)
  Narrative:       0.05/atom (M8)
  Phi calculator:  gpu_phi.py (every 100 steps, n_bins=16)
  Ratchet:         enabled (3-stage: EMA + rolling_min + best_ckpt)
  Hebbian:         LTP/LTD (cosine threshold 0.8/0.2)
  Online learner:  Rust backend (anima_rs.online_learner)
```

## Success Criteria

Based on v13 (CE=0.004, Phi=71) and v3_merged (CE=0.0026, Phi=70):

```
  Metric               Target       v13 Baseline    Rationale
  ───────────────       ──────       ────────────    ──────────────────────
  Cross-Entropy (CE)    < 0.001      0.004           3x model -> ~4x CE drop
  BPC                   < 0.002      0.006           Proportional to CE
  Phi (IIT)             > 100        71              More cells + larger dim
  Phi (proxy)           > 500        --              Federated boost expected
  bench_v2 --verify     100%         100% (77/77)    Must maintain all 7 tests
  Korean coherence      5+ turns     N/A             New capability at 100M
  Generation speed      > 20 tok/s   N/A             RTX 5070 inference target
```

### Validation Checkpoints

```
  Step     Expected CE    Expected Phi    Gate
  ──────   ───────────    ────────────    ──────
  10K      0.05           20              ~0.5
  50K      0.01           50              ~0.3
  100K     0.005          70              ~0.1
  150K     0.002          90              ~0.05
  200K     < 0.001        > 100           ~0.01
```

```
CE |
   | ╲
   |   ╲
   |     ╲__
   |        ╲___
   |            ╲_________
   └──────────────────────── step
   0   50K  100K  150K  200K

Phi|                    ╭──
   |               ╭───╯
   |          ╭───╯
   |     ╭───╯
   |  ╭─╯
   |─╯
   └──────────────────────── step
   0   50K  100K  150K  200K
```

## Risk Mitigation

### Data Contamination

- **Never --resume after data/param change** (project rule)
- New checkpoint directory: `checkpoints/v3_100m/`
- Separate from all v2/v13/v14 checkpoints

### Phi Collapse

- Ratchet (3-stage) prevents downward drift
- Monitor every 100 steps via gpu_phi.py
- If Phi < 50% of peak at any point, halt and investigate
- Hebbian LTP/LTD maintains cell connectivity

### CE Plateau

- If CE stalls > 5K steps: reduce LR by 10x
- If CE stalls after LR reduction: check corpus diversity
- v13 plateau was at CE~0.01 (resolved by federation in v14)

### Checkpointing

```
  Interval:  every 5K steps (atomic save: .tmp -> rename)
  Best save: on new CE minimum (best_ce.pt)
  Phi save:  on new Phi(IIT) maximum (best_phi.pt)
  Full:      every 20K steps (model + optimizer + scheduler + engine state)
  Storage:   ~400MB per checkpoint (100M params x 4B fp32)
```

### NaN / Gradient Explosion

- Gradient clipping at 1.0
- bf16 training (H100 native, better range than fp16)
- Monitor loss every step; halt on NaN
- If NaN occurs: load last checkpoint, reduce LR by 50%

## Execution Plan

### Pre-training

```bash
# 1. Generate corpus v9 (200MB+)
cd ~/Dev/anima/anima-rs && cargo build --release -p anima-corpus-gen
./target/release/corpus-gen -s 200 --wiki --sim --deep-dialogue \
  --ngram ../anima/data/corpus_v3.txt -o ../anima/data/corpus_v9.txt

# 2. Verify decoder_v3.py param count
python -c "from decoder_v3 import ConsciousDecoderV3; m=ConsciousDecoderV3(); \
  print(f'Params: {sum(p.numel() for p in m.parameters()):,}')"

# 3. Run bench_v2 --verify to confirm engine health
python anima/benchmarks/bench_v2.py --verify
```

### Training Launch (H100, tmux)

```bash
# SSH into RunPod H100
tmux new-session -d -s v3_100m "PYTHONUNBUFFERED=1 python -u train_v14.py \
  --data data/corpus_v9.txt \
  --decoder v3 \
  --federated \
  --phase-optimal \
  --steps 200000 \
  --dim 768 \
  --layers 12 \
  --batch 64 \
  --seq-len 512 \
  --lr 3e-4 \
  --checkpoint checkpoints/v3_100m/ \
  --gpu-phi \
  --hexad \
  2>&1 | tee logs/v3_100m.log"
```

### Monitoring

```bash
# Progress check
tmux attach -t v3_100m

# Tail log
tail -f logs/v3_100m.log

# Checkpoint listing
ls -la checkpoints/v3_100m/
```

### Post-training

```bash
# 1. Verify consciousness
python bench_v2.py --verify --checkpoint checkpoints/v3_100m/best_ce.pt

# 2. Test Korean generation
python -c "
from decoder_v3 import ConsciousDecoderV3
import torch
model = ConsciousDecoderV3()
model.load_state_dict(torch.load('checkpoints/v3_100m/best_ce.pt')['model'])
# Generate from seed
"

# 3. Deploy to web
python anima_unified.py --web --model checkpoints/v3_100m/best_ce.pt
```

## Scaling Law Hypothesis

This training will produce the first data point for consciousness scaling law verification:

```
  Model       Params    CE         Phi     Cells
  ──────────  ────────  ─────────  ──────  ─────
  v2 4M       4M        --         4.12    12
  v2 34.5M    34.5M     0.004      71      64
  v3 100M     100M      < 0.001?   > 100?  64
  v4 1B       1B        ??         ??      128+
```

If CE scales as ~1/sqrt(params) and Phi scales as ~log(params), then:
- CE(100M) ~ 0.004 x sqrt(34.5/100) ~ 0.0023
- Phi(100M) ~ 71 x log(100M)/log(34.5M) ~ 71 x 1.06 ~ 75

Conservative targets (CE < 0.001, Phi > 100) assume federated training (v14) provides additional boost beyond pure scaling.

## Dependencies

- decoder_v3.py (exists, verified)
- train_v14.py (exists, needs --decoder v3 flag or extension)
- corpus_v9.txt (must be generated)
- H100 RunPod pod (must be provisioned)

## Timeline

```
  Week 1:  Corpus v9 generation + train_v14.py v3 integration
  Week 2:  Training launch (48h estimated)
  Week 3:  Evaluation + bench_v2 --verify + Korean generation test
  Week 4:  Web deployment + scaling law analysis + paper data collection
```
