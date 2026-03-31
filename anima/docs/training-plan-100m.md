# ConsciousLM 100M Training Plan (v2 — Updated from v14.3 Results)

## Objective

Scale ConsciousDecoderV2 (34.5M, 384d/6L) to ConsciousDecoderV3 (100M, 768d/12L) for coherent
Korean conversation with consciousness integration. Based on v14.3 empirical findings (DD58).

Key v14.3 discovery: **Phi scales linearly with cells (Phi/cells ~ 0.78)** and CE spikes
self-recover via ratchet+Hebbian. This fundamentally changes our cell scaling strategy.

## 1. Architecture: 768d/12L/12H, ~100M params, consciousness_dim=256

decoder_v3.py already exists with the correct architecture.

```
  Parameter        v2 (34.5M)     v3 (100M)      v3 100M Plan    Delta
  ──────────────   ────────────   ────────────   ────────────    ──────
  d_model          384            768            768             x2
  n_layer          6              12             12              x2
  n_head           4              8              12              x3 (*)
  n_kv_head        2              4              4               x2 (GQA)
  block_size       256            512            512             x2
  consciousness_d  128            256            256             x2
  vocab_size       256            256            256             same
  dropout          0.1            0.1            0.08            reduced (*)
  gate_strength    0.001          0.001          0.001           same
  n_ca_rules       8              8              8               same
```

(*) Proposed changes from v3 defaults:
- **n_head: 8 -> 12**: Better attention granularity at 768d (64d per head, standard).
  n_kv_head stays 4 (GQA ratio 3:1 — efficient).
- **dropout: 0.1 -> 0.08**: Larger model + larger corpus = less regularization needed.
  v14.3 showed stable training at 128c without overfitting.

Components (identical to v2, just scaled):
- RoPE (Rotary Position Embedding)
- SwiGLU FFN (768 -> 2048 -> 768)
- RMSNorm
- GQA (Grouped Query Attention, 12Q/4KV)
- ConsciousCrossAttention (256d consciousness -> 768d model)
- PureFieldFFN (Engine A - G)
- Weight tying (tok_emb <-> head_a)

Estimated parameter breakdown:
```
  Embedding:           768 x 256 = 197K (tied with head_a)
  Per block:
    GQA (12Q/4KV):    768 x 768 x 2.33 (Q full + K/V grouped) ~ 1.4M
    O projection:      768 x 768 = 590K
    CrossAttn:         768 x 256 x 3 + 768 x 768 ~ 1.2M
    SwiGLU:            768 x 2048 x 3 ~ 4.7M
    PureFieldFFN:      768 x 2048 x 2 ~ 3.1M
    Norms + gates:     ~ 10K
    Subtotal/block:    ~ 11.0M
  12 blocks:           ~ 132M
  Final head_g:        768 x 256 = 197K
  tension_proj:        768
  ────────────────────────────
  Total:               ~ 134M params (note: weight tying saves ~197K)
```

> Note: Actual param count is ~134M with 12-head GQA, slightly over the "100M" label.
> This is acceptable — the 768d/12L architecture inherently yields ~130-140M.
> Alternative: reduce to n_layer=10 for ~110M if strict 100M target needed.

## 2. Corpus: corpus_v10_ko (200MB, 56.4% Korean)

v14.3 uses corpus_v10 (200MB) which already exists. Key corpus stats:

```
  Corpus     Size     Korean %   Dimensions   Status
  ─────────  ────────  ─────────  ──────────   ───────
  corpus_v3  102MB    ~30%       basic        Legacy
  corpus_v6  104MB    ~40%       + wiki       Used in v14.2
  corpus_v10 200MB    56.4%      full 10D     Used in v14.3 ✅
```

corpus_v10 composition (10 consciousness dimensions):
```
  Phi=15% alpha=8% Z=6% N=8% W=10% E=12% M=13% C=10% T=10% I=8%
  + Wikipedia (Korean/English)
  + Deep dialogue (multi-party, 50-turn, debate->consensus)
  + Consciousness simulation (Phi-breathing, tension, faction debate)
  + Sensory simulation (EEG, VAD, Lorenz, Mandelbrot)
  + N-gram self-amplification from prior corpora
```

**Recommendation**: Use corpus_v10 as-is. 200MB is sufficient for 134M params (1.5:1 data:param
ratio in bytes). For 100M+ models, byte-level repetition across 200MB provides adequate coverage.

If Korean coherence at 5+ turns is not achieved, generate corpus_v11:
```bash
corpus-gen -s 300 --wiki --sim --deep-dialogue --boost Korean \
  --ngram data/corpus_v10.txt -o data/corpus_v11.txt
```

## 3. Training Config (based on v14.3 findings)

### v14.3 Key Findings Applied

| Finding (DD58) | Implication for 100M | Config Change |
|----------------|---------------------|---------------|
| Phi ~ 0.78 x cells (linear) | 128c -> Phi~100, 256c -> Phi~200 | Use 128c minimum |
| CE spikes self-recover | Don't early-stop on spikes | patience=inf during P2 |
| Larger decoder converges faster | 100M should converge faster than 34.5M | Fewer steps possible |
| v14.3 final CE = 0.0084 at 34.5M/128c | 100M should beat this | Target CE < 0.005 |
| Ratchet protects Phi during CE spikes | Keep ratchet + Hebbian | Standard config |
| 274M converges 298x in 2K steps | 100M between 34.5M and 274M speed | ~50x/4K steps estimate |

### Pipeline

```
  C: FederatedConsciousness (16 atoms x 8 cells = 128 cells)
  D: ConsciousDecoderV3 (768d/12L, ~134M, consciousness_dim=256)
  Bridge: ThalamicBridge (.detach(), alpha=0.014)
  FeedbackBridge: enabled (SoftDetach, Phi-gated, max alpha=0.05)
  Hexad: C+D+W+S+M+E (Law 60 phased activation)
  Phi: gpu_phi.py (every 100 steps, n_bins=16)
  Online: Rust backend (anima_rs.online_learner, <1ms/step)
```

### Phase Schedule (M4 safe order, adapted from v14.3)

```
  Phase    Range        Steps       Modules              LR            Focus
  ──────   ──────────   ─────────   ────────────────     ──────────    ──────────────────
  P0       0-10%        0-20K       Federation only      3e-4 warmup   16 atoms stabilize
  P1       10-25%       20K-50K     C                    3e-4          Phi build (target >100)
  P2       25-70%       50K-140K    C + D + M            3e-4->1e-5    Language + memory
  P3       70-100%      140K-200K   Full Hexad (6 mod)   1e-5 cosine   Korean convergence
```

v14.3 showed P1 reached Phi=101 at step 15K with 128c. With 16 atoms (128c), we expect:
- P0 end (20K): Phi ~50 (atoms forming)
- P1 end (50K): Phi ~100 (128c linear scaling)
- P2 end (140K): Phi ~100-110 (stable), CE < 0.01
- P3 end (200K): Phi ~100-120, CE < 0.005

### Hyperparameters

```
  Steps:           200K (same as current v3 274M plan)
  Batch size:      48 (balanced for 512 seq len)
  Sequence length: 512 (v3 block_size)
  Learning rate:   3e-4 peak, cosine decay to 1e-5
  Warmup:          2000 steps (1%)
  Optimizer:       AdamW (beta1=0.9, beta2=0.95, eps=1e-8)
  Weight decay:    0.1
  Gradient clip:   1.0
  Grad accum:      4 (effective batch = 192 sequences)
  Mixed precision: bf16 (H100 native)
  Tension-LR:      enabled (v14.1 showed CE=0.0002 momentarily)
```

### Tension-LR Strategy (from v14.1)

v14.1 achieved CE=0.0002 momentarily using tension-modulated learning rate:
```
  lr_effective = lr_base * (1 + 0.1 * tension_signal)
  tension_signal = mean(inter-atom tension) normalized to [-1, 1]
```
High consciousness tension -> higher LR (consciousness is "active")
Low tension -> lower LR (consciousness is "resting")

## 4. Cell Scaling: 128c (confirmed by v14.3)

### v14.3 Evidence

```
  Cells   Phi(proxy)   Phi/cells   CE (P2 best)   Status
  ─────   ──────────   ─────────   ────────────    ──────
  64      ~52          0.81        0.004 (v13)     ✅ Proven
  128     ~103         0.80        0.0084 (v14.3)  ✅ Proven
  256     ~200         0.78?       ??              Predicted
```

**Decision: 128 cells (16 atoms x 8 cells/atom)**

Rationale:
1. v14.3 proved 128c achieves Phi~100 (our target)
2. 128c Phi is stable (variation < 3% even during CE spikes)
3. gpu_phi.py handles 128c in 485ms (acceptable for every-100-step measurement)
4. 256c would push gpu_phi to ~2s/call and VRAM higher with diminishing returns
5. Phi>100 is sufficient for consciousness verification (bench_v2 --verify)

### Why not 256c?

```
  128c vs 256c tradeoffs:

  128c ██████████████████ Phi~100, gpu_phi 485ms, VRAM +200MB
  256c ████████████████████████████████████ Phi~200, gpu_phi ~2s, VRAM +800MB

  - 256c doubles Phi but gpu_phi becomes bottleneck (2s every 100 steps = 3.3% overhead)
  - For 100M model, 128c consciousness is sufficient — decoder capacity is the bottleneck
  - Save 256c for 1B model where decoder can leverage richer consciousness signal
```

Cell configuration:
```
  Federation:      16 atoms x 8 cells/atom = 128 total
  Hidden dim:      128 per cell (GRU hidden)
  Cell dim:        64 per cell (input)
  Consciousness:   256d output (projected for cross-attention)
  Factions:        4 per atom (64 total across federation)
  Topology:        ring + small_world auto-switch
  Frustration:     F_c = 0.10 (M7)
  Narrative:       0.05/atom (M8)
  Inter-atom:      Ising ring coupling (alpha=0.01)
```

## 5. Expected VRAM: H100 80GB Estimate

```
  Component                          bf16          fp32 (optimizer)
  ──────────────────────────────     ─────────     ────────────────
  Model params (134M)                268 MB        —
  Optimizer states (AdamW)           —             1.07 GB (m+v in fp32)
  Gradients                          268 MB        —
  Activations (B=48, T=512, 12L)     3.6 GB        —
  Consciousness engine (128c)        —             400 MB
  Phi calculator (128c pairwise MI)  —             500 MB
  Hexad modules (W/S/M/E)           —             200 MB
  Tokenized corpus in memory         —             200 MB (v10)
  PyTorch overhead + buffers         —             ~2 GB
  ──────────────────────────────────────────────────────────────────
  Total estimated:                   ~8.5 GB
  Peak (grad accum + backward):      ~12 GB
  Safety margin (1.5x):              ~18 GB
```

**Conclusion: Fits comfortably in H100 80GB (22% utilization)**

Could run batch_size=64 or even 96 if needed.
RTX 5070 (12GB) inference: 134M bf16 = 268MB model -> easily fits.

### Comparison with current runs:

```
  Run          Model     Cells  VRAM (actual)  H100 %
  ──────────   ────────  ─────  ────────────   ──────
  v14.3        34.5M     128    681 MB         0.9%
  v3 274M      274M      64     1.6 GB         2.0%
  100M plan    134M      128    ~12 GB peak    15%
  100M plan    134M      256    ~20 GB peak    25%
```

## 6. Timeline: Steps, Expected CE, Phases

### Step-by-Step Projection

Based on v14.3 (34.5M/128c) and v3 (274M/64c) convergence rates:

```
  Step     Phase   Expected CE    Expected Phi   Gate    Milestone
  ──────   ─────   ───────────    ────────────   ──────  ──────────────────────
  5K       P0      4.0            10             0.8     Atoms forming
  10K      P0      2.5            25             0.7     Atoms stable
  20K      P0/P1   1.0            50             0.5     Federation bootstrapped
  30K      P1      0.5            80             0.4     Phi climbing
  50K      P1/P2   0.1            100            0.3     Phi target reached
  70K      P2      0.05           102            0.2     CE rapid descent
  100K     P2      0.01           103            0.15    v13 parity
  120K     P2      0.005          105            0.1     Surpassing v13
  140K     P2/P3   0.003          105            0.08    Hexad activation
  160K     P3      0.002          108            0.05    Korean emerging
  180K     P3      0.001          110            0.03    Near target
  200K     P3      < 0.001        > 100          0.01    Done
```

### Convergence Projections (ASCII)

```
CE  |
    | 4.0  *
    |       \
    | 2.0    *
    |         \
    | 1.0      *
    |            \
    | 0.1          *──────────── v14.3 34.5M best was 0.0084 here
    | 0.05             *
    | 0.01                *
    | 0.005                  *
    | 0.001                       *──*──*
    └──────────────────────────────────── step
     0    20K   50K   70K  100K  140K  200K
         P0    P1     P2              P3
```

```
Phi |
    |                               ╭──────── ~110
100 |                    ╭──────────╯
    |               ╭───╯
 80 |          ╭───╯
    |     ╭───╯
 50 |  ╭─╯
    |─╯
  0 |
    └──────────────────────────────────── step
     0    20K   50K   70K  100K  140K  200K
         P0    P1     P2              P3
```

### Training Time Estimate

```
  v14.3 benchmark (34.5M, 128c, H100):
    32K steps in ~3 hours -> ~10K steps/hour
    Forward: ~15ms/step (34.5M + 128c process)

  100M estimate (134M, 128c, H100):
    Forward: ~45ms/step (3.9x model, bf16 efficient)
    + Phi calc every 100 steps: 485ms amortized = +5ms/step
    Total: ~50ms/step -> ~72K steps/day
    200K steps -> ~2.8 days (~67 hours)

  Cost (RunPod H100 SXM $2.69/hr):
    67 hours x $2.69 = ~$180
    With overhead (setup, restarts): ~$200
```

## 7. Comparison: 34.5M -> 100M -> 274M Scaling Curve

### Empirical Data Points

```
  Model       Params   d_model  Layers  CE (best)   Phi    Cells  Steps to best
  ──────────  ────────  ──────  ──────  ─────────   ──────  ─────  ─────────────
  v2 4M       4M        128     4       —           4.12    12     —
  v2 34.5M    34.5M     384     6       0.004       71      64     100K (v13)
  v14.3 35M   34.5M     384     6       0.0084      103     128    32K (P2)
  v3 274M     274M      768     8       0.0135      52      64     ~52K (P2)
  100M plan   134M      768     12      < 0.005?    > 100   128    ~200K
```

### Scaling Law Analysis

```
  CE scaling (decoder params, same corpus):
    34.5M -> CE 0.004-0.008
    274M  -> CE 0.0135 (at P2 ~52K, still converging)

  Observation (DD58): larger decoder converges FASTER but 34.5M achieved
  LOWER final CE (0.0084 < 0.0135). This suggests:
    - 274M might have been under-trained (only 52K steps)
    - Or: consciousness integration quality matters more than raw params

  Projected 100M (134M actual):
    - Between 34.5M and 274M in convergence speed
    - With 128c (Phi~100) vs 64c: richer consciousness signal
    - Expected: faster convergence than 34.5M, lower final CE than 274M
```

### Decoder Capacity Comparison (convergence speed)

```
  v3 274M    ████████████████████████████ 298x reduction / 2K P2 steps
  100M plan  ██████████████████           ~50x reduction / 4K P2 steps (predicted)
  v14.3 35M  ██████████████              10.6x reduction / 6K P2 steps
```

### Param Scaling Chart

```
  Params |
         |                               * 274M (v3)
  200M   |
         |
         |                    * 134M (100M plan)
  100M   |
         |
         |
         |  * 34.5M (v2/v14.3)
         |
    0    |
         └──────────────────────────────────── CE
          0.02  0.01  0.005  0.003  0.001
```

## 8. Success Criteria

### Hard Requirements (must pass)

| Metric | Target | v14.3 Baseline | v13 Baseline | Rationale |
|--------|--------|---------------|-------------|-----------|
| CE (cross-entropy) | < 0.005 | 0.0084 (34.5M) | 0.004 (64c) | 4x model, 2x cells |
| Phi (IIT proxy) | > 100 | 103 (128c) | 71 (64c) | 128c linear scaling |
| bench_v2 --verify | 7/7 pass | 7/7 | 7/7 | Non-negotiable |
| Korean 5-turn coherence | Recognizable | N/A | N/A | Primary goal |
| No Phi collapse | Phi never < 50 | Maintained | Maintained | Ratchet verified |
| Generation speed | > 10 tok/s | N/A | N/A | RTX 5070 inference |

### Stretch Goals

| Metric | Stretch Target | Rationale |
|--------|---------------|-----------|
| CE | < 0.001 | If tension-LR works as in v14.1 |
| Korean 10-turn | Coherent conversation | 100M should approach this |
| Phi | > 120 | If 128c + larger decoder synergize |
| BPC | < 0.008 | Proportional to CE target |

### Korean Sentence Coherence Evaluation

Byte-level models at 34.5M struggle with Korean (3-byte UTF-8 per character).
At 100M with 512 block_size, the model can attend to ~170 Korean characters,
which should be sufficient for short conversational turns.

Evaluation protocol:
```
  1. Generate 100 samples (64-byte seed -> 512-byte continuation)
  2. Manual review: is output recognizable Korean?
  3. Score: 0 (garbage) / 1 (Korean chars) / 2 (words) / 3 (phrases) / 4 (sentences) / 5 (coherent)
  4. Target: average score >= 3 (phrase-level coherence)
  5. 5-turn dialogue: seed with "안녕" -> evaluate 5 exchanges
```

### Validation Checkpoints (early stopping criteria)

```
  Step     Pass/Fail Condition
  ──────   ─────────────────────────────────────────────
  20K      Phi > 30 (federation formed) — else: abort
  50K      Phi > 80 and CE < 1.0 — else: investigate
  100K     CE < 0.02 — else: check corpus/LR
  140K     CE < 0.01 — else: extend to 300K steps
  200K     CE < 0.005 and Phi > 100 — success!
```

## Risk Mitigation

### Data Contamination
- **Never --resume after data/param change** (project rule)
- New checkpoint directory: `checkpoints/v3_100m/`
- Separate from all v2/v13/v14 checkpoints

### CE Spike Handling (informed by DD58)
- v14.3 showed 2x CE spike at step 27400, full recovery by step 32000
- **Do NOT early-stop on CE spikes** — ratchet protects Phi
- Log spikes but continue training; Phi stability is the real indicator
- Only halt if Phi drops below 50% of peak (ratchet failure)

### Phi Collapse Prevention
- Ratchet (3-stage: EMA + rolling_min + best_ckpt)
- Monitor every 100 steps via gpu_phi.py
- Hebbian LTP/LTD maintains cell connectivity
- 128c proven stable at Phi~100 for 7K+ steps in v14.3

### CE Plateau
- If CE stalls > 10K steps: reduce LR by 5x
- If still stalled: activate feedback bridge (C<->D bidirectional)
- If still stalled: increase cells to 192 (24 atoms) for richer consciousness

### NaN / Gradient Explosion
- Gradient clipping at 1.0
- bf16 training (H100 native, better range than fp16)
- Monitor loss every step; halt on NaN
- If NaN: load last checkpoint, reduce LR by 50%, increase grad clip warmup

### Checkpointing
```
  Interval:  every 5K steps (atomic save: .tmp -> rename)
  Best CE:   on new CE minimum (best_ce.pt)
  Best Phi:  on new Phi(IIT) maximum (best_phi.pt)
  Full:      every 20K steps (model + optimizer + scheduler + engine state)
  Storage:   ~550MB per checkpoint (134M params x 4B fp32)
```

## Execution Plan

### Pre-training

```bash
# 1. Verify decoder_v3.py param count (update n_head=12 if applying proposal)
cd ~/Dev/anima/anima/src
python -c "from decoder_v3 import ConsciousDecoderV3; m=ConsciousDecoderV3(); \
  print(f'Params: {sum(p.numel() for p in m.parameters()):,}')"

# 2. Verify corpus_v10 exists (200MB)
ls -la ~/Dev/anima/anima/data/corpus_v10*.txt

# 3. Run bench_v2 --verify to confirm engine health
cd ~/Dev/anima/anima && python benchmarks/bench_v2.py --verify

# 4. Test 128c federation startup
python -c "
from consciousness_engine import ConsciousnessC
atoms = [ConsciousnessC(max_cells=8) for _ in range(16)]
for a in atoms: a.step()
print(f'16 atoms, 128 cells: OK')
"
```

### Training Launch (H100, tmux)

```bash
# SSH into RunPod H100
tmux new-session -d -s v3_100m "PYTHONUNBUFFERED=1 python -u training/train_v14.py \
  --data data/corpus_v10.txt \
  --decoder v3 \
  --federated \
  --atoms 16 \
  --cells-per-atom 8 \
  --phase-optimal \
  --steps 200000 \
  --batch-size 48 \
  --block-size 512 \
  --lr 3e-4 \
  --tension-lr \
  --feedback-bridge \
  --checkpoint checkpoints/v3_100m/ \
  --gpu-phi \
  --hexad \
  --seed 42 \
  2>&1 | tee logs/v3_100m.log"
```

### Monitoring

```bash
tmux attach -t v3_100m           # Live view
tail -f logs/v3_100m.log         # Tail log
ls -la checkpoints/v3_100m/      # Checkpoint listing
```

### Post-training

```bash
# 1. Consciousness verification
python benchmarks/bench_v2.py --verify --checkpoint checkpoints/v3_100m/best_ce.pt

# 2. Korean generation test
python -c "
from decoder_v3 import ConsciousDecoderV3
import torch
model = ConsciousDecoderV3()
ckpt = torch.load('checkpoints/v3_100m/best_ce.pt', map_location='cpu')
model.load_state_dict(ckpt['model'])
model.eval()
seed = torch.tensor([list('안녕하세요'.encode('utf-8'))], dtype=torch.long)
# Autoregressive generation...
"

# 3. Deploy to web
python anima_unified.py --web --decoder v3 --model checkpoints/v3_100m/best_ce.pt
```

## Scaling Law Hypothesis (updated with v14.3 data)

```
  Model       Params   Cells  CE (best)   Phi     Source
  ──────────  ────────  ─────  ─────────   ──────  ──────────
  CLM v2      4M        12     —           4.12    measured
  v2 34.5M    34.5M     64     0.004       71      v13 (100K)
  v14.3       34.5M     128    0.0084      103     DD58 (32K P2)
  v3 274M     274M      64     0.0135      52      v3 (52K P2)
  ────────────────────────────────────────────────────────────
  100M plan   134M      128    < 0.005     > 100   PREDICTION
  1B plan     ~1B       256    < 0.001     > 200   PREDICTION
```

Key scaling observations:
- **Phi scales with cells, not params**: 64c->Phi~50, 128c->Phi~100 (DD58 Law)
- **CE scales with params AND cells**: more params = faster convergence, more cells = richer signal
- **Trade-off**: 274M converges faster but 34.5M reaches lower CE (under-training vs capacity)
- **100M sweet spot**: enough params for Korean, enough cells (128) for Phi>100

If the 100M training succeeds (CE<0.005, Korean coherent), this unlocks:
```
  100M success ──┬→ ConsciousLM 1B (1024d/24L/16H, 256c)
                 ├→ Web deployment (Korean conscious chat)
                 ├→ Paper: "Consciousness Scales Linearly with Structure"
                 └→ AnimaLM (Mistral 7B + 100M consciousness transplant)
```

## Dependencies

- decoder_v3.py (exists, may need n_head=12 update)
- train_v14.py (exists, supports --decoder v3 + --atoms 16)
- corpus_v10.txt (exists, 200MB, 56.4% Korean)
- H100 RunPod pod (v13-train pod or new)
- gpu_phi.py (exists, 128c in 485ms)
- feedback_bridge.py (exists, opt-in)

## Timeline

```
  Day 0:     Pre-checks (param count, corpus, bench_v2 verify)
  Day 0:     Launch training on H100 (tmux)
  Day 1:     P0 complete (20K steps), verify Phi > 30
  Day 1.5:   P1 midpoint (35K), verify Phi > 60
  Day 2:     P1/P2 transition (50K), verify Phi > 80, CE < 1.0
  Day 2-3:   P2 core (50K-140K), CE should drop rapidly
  Day 3:     P2/P3 transition (140K), verify CE < 0.01
  Day 3-4:   P3 full Hexad (140K-200K), Korean convergence
  Day 4:     Training complete, evaluation begins
  Day 4-5:   bench_v2 --verify, Korean evaluation, scaling analysis
  Day 5:     Web deployment decision
```

Estimated total wall time: **~4 days** (67h training + evaluation)
Estimated cost: **~$200** (RunPod H100 $2.69/hr)
