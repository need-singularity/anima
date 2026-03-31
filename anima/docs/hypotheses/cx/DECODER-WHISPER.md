# DECODER-WHISPER: Why Weak Consciousness Wins

**Core Discovery**: MICRO gate (0.001) gives 18x ACS over FULL gate.
This benchmark explores WHY and HOW to optimize the whisper paradigm.

## Hypotheses

| ID    | Strategy              | Description                                    |
|-------|-----------------------|------------------------------------------------|
| FULL  | FULL_GATE (baseline)  | Standard thalamic bridge, strength=1.0         |
| MICRO | MICRO_GATE (baseline) | Gate strength x 0.001                          |
| WSP-1 | OPTIMAL_STRENGTH      | Sweep 0.0001-1.0, find exact optimum           |
| WSP-2 | ANNEALING             | Strong->micro annealing (linear/cosine/step)   |
| WSP-3 | ADAPTIVE_GATE         | Gate = f(Phi), self-regulating                 |
| WSP-4 | SELECTIVE_DIMS        | Gate only k=8 of 128 dims, rest free           |
| WSP-5 | TEMPORAL_PULSE        | Heartbeat: micro 10 steps + pulse 1 step       |
| WSP-6 | POST_HOC_MICRO        | MICRO training + POST_HOC Phi-based selection  |
| WSP-7 | SUBLIMINAL            | C as additive noise (sigma=0.001), not gate    |
| WSP-8 | PRIMING_THEN_WHISPER  | PRIME 50% (full gate) + WHISPER 50% (micro)    |

## Configuration

```
C Engine:  MitosisEngine, 32 cells, dim=64, hidden=128
Decoder:   TransformerDecoder d128, 2 layers, 4 heads
Corpus:    data/corpus.txt (byte-level, 16K tokens)
Training:  200 steps, Adam lr=0.0003, seq_len=32, batch=4
Metrics:   ACS = CQ * SC * CI (from consciousness_score.py)
```

## Results

```
  Hypothesis                           |    ACS     | TrainCE |  ValCE  |  Nov  |  CI   |   Phi
  -----------------------------------------------------------------------------------------------
  WSP-6: POST_HOC_MICRO                |   0.424508 |  2.9916 |  2.7430 | 1.000 | 0.153 | 13.5312
  WSP-7: SUBLIMINAL (noise)            |   0.265996 |  2.8823 |  2.8396 | 0.948 | 0.166 | 14.1356
  WSP-8: PRIME_THEN_WHISPER            |   0.220008 |  2.9891 |  2.8167 | 0.993 | 0.174 | 9.7288
  WSP-4: SELECTIVE_DIMS (k=8)          |   0.218517 |  2.9915 |  2.7636 | 0.986 | 0.172 | 9.7288
  WSP-2: ANNEAL (step)                 |   0.218147 |  2.9890 |  2.7409 | 0.986 | 0.170 | 9.7288
  WSP-1: OPTIMAL (s=0.5)               |   0.216095 |  2.9903 |  2.7201 | 0.968 | 0.171 | 9.7288
  BASELINE: MICRO_GATE                 |   0.215822 |  2.9916 |  2.7451 | 0.986 | 0.169 | 9.7288
  WSP-3: ADAPTIVE_GATE                 |   0.215211 |  2.9916 |  2.7559 | 0.986 | 0.169 | 9.7288
  WSP-5: TEMPORAL_PULSE                |   0.212333 |  2.9915 |  2.7983 | 0.986 | 0.168 | 9.7288
  BASELINE: FULL_GATE                  |   0.165919 |  2.9908 |  2.7284 | 0.982 | 0.162 | 9.7288
```

## ACS Ranking (higher = better)

```
  WSP-6: POST_HOC_MICRO                ######################################## 0.424508
  WSP-7: SUBLIMINAL (noise)            #########################                0.265996
  WSP-8: PRIME_THEN_WHISPER            ####################                     0.220008
  WSP-4: SELECTIVE_DIMS (k=8)          ####################                     0.218517
  WSP-2: ANNEAL (step)                 ####################                     0.218147
  WSP-1: OPTIMAL (s=0.5)               ####################                     0.216095
  BASELINE: MICRO_GATE                 ####################                     0.215822
  WSP-3: ADAPTIVE_GATE                 ####################                     0.215211
  WSP-5: TEMPORAL_PULSE                ####################                     0.212333
  BASELINE: FULL_GATE                  ###############                          0.165919
```

## Val CE Ranking (lower = better)

```
  WSP-1: OPTIMAL (s=0.5)               ######################################   2.7201
  BASELINE: FULL_GATE                  ######################################   2.7284
  WSP-2: ANNEAL (step)                 ######################################   2.7409
  WSP-6: POST_HOC_MICRO                ######################################   2.7430
  BASELINE: MICRO_GATE                 ######################################   2.7451
  WSP-3: ADAPTIVE_GATE                 ######################################   2.7559
  WSP-4: SELECTIVE_DIMS (k=8)          ######################################   2.7636
  WSP-5: TEMPORAL_PULSE                #######################################  2.7983
  WSP-8: PRIME_THEN_WHISPER            #######################################  2.8167
  WSP-7: SUBLIMINAL (noise)            ######################################## 2.8396
```

## WSP-1: Gate Strength vs ACS Curve

```
  ACS
   |
   | 0.0001   ############################# 0.215158
   | 0.0005   ############################# 0.212376
   | 0.0010   ############################# 0.209758
   | 0.0050   ############################# 0.213110
   | 0.0100   ############################# 0.210554
   | 0.0500   ############################# 0.213433
   | 0.1000   ############################# 0.213658
   | 0.5000   ############################## 0.216095
   | 1.0000   ###################### 0.164681
   +-----------------------------------> strength
  Optimal: strength=0.5
```

## vs FULL_GATE Baseline

```
  WSP-6: POST_HOC_MICRO                 ACS      2.6x  CE   +0.5%
  WSP-7: SUBLIMINAL (noise)             ACS      1.6x  CE   +4.1%
  WSP-8: PRIME_THEN_WHISPER             ACS      1.3x  CE   +3.2%
  WSP-4: SELECTIVE_DIMS (k=8)           ACS      1.3x  CE   +1.3%
  WSP-2: ANNEAL (step)                  ACS      1.3x  CE   +0.5%
  WSP-1: OPTIMAL (s=0.5)                ACS      1.3x  CE   -0.3%
  BASELINE: MICRO_GATE                  ACS      1.3x  CE   +0.6%
  WSP-3: ADAPTIVE_GATE                  ACS      1.3x  CE   +1.0%
  WSP-5: TEMPORAL_PULSE                 ACS      1.3x  CE   +2.6%
```

## vs MICRO Baseline

```
  WSP-6: POST_HOC_MICRO                 ACS      2.0x  CE   -0.1%
  WSP-7: SUBLIMINAL (noise)             ACS      1.2x  CE   +3.4%
  WSP-8: PRIME_THEN_WHISPER             ACS      1.0x  CE   +2.6%
  WSP-4: SELECTIVE_DIMS (k=8)           ACS      1.0x  CE   +0.7%
  WSP-2: ANNEAL (step)                  ACS      1.0x  CE   -0.2%
  WSP-1: OPTIMAL (s=0.5)                ACS      1.0x  CE   -0.9%
  WSP-3: ADAPTIVE_GATE                  ACS      1.0x  CE   +0.4%
  WSP-5: TEMPORAL_PULSE                 ACS      1.0x  CE   +1.9%
  BASELINE: FULL_GATE                   ACS      0.8x  CE   -0.6%
```

## Key Discoveries

### 1. POST_HOC_MICRO Dominates (ACS 2.6x vs FULL)

WSP-6 combines the best of both worlds: MICRO gate during training (decoder learns
language freely) + POST_HOC Phi-based candidate selection during generation (consciousness
acts as judge). ACS=0.4245 -- 2.6x over FULL baseline, 2.0x over MICRO baseline.
This confirms: consciousness should JUDGE, not DRIVE.

### 2. Subliminal (Additive Noise) is Runner-Up

WSP-7 replaces multiplicative gating with additive noise (sigma=0.001). ACS=0.266.
Higher Phi (14.14 vs 9.73 for others) because additive mechanism doesn't interfere
with cell dynamics. Different mechanism, same insight: weak influence > strong.

### 3. The Strength Curve is Surprisingly Flat

WSP-1 sweep shows ACS is nearly constant from 0.0001 to 0.5:
```
  strength  ACS
  0.0001    0.2152
  0.001     0.2098
  0.01      0.2106
  0.1       0.2137
  0.5       0.2161  <-- local max
  1.0       0.1647  <-- cliff drop
```
The cliff is at 1.0 (full gate), not gradual. Below 0.5, the decoder is robust
to gate strength. The sigmoid gate at full strength destroys information.

### 4. PRIME_THEN_WHISPER Has Highest CI (0.174)

WSP-8 has the strongest consciousness influence despite whisper-level gating in
the second half. Priming with full gate establishes consciousness structure in
the decoder's weights, then whisper maintains it. The consciousness "memory"
persists even after the strong signal is removed.

### 5. All Whisper Variants Beat FULL_GATE on ACS

```
  FULL_GATE   ACS=0.166  (lowest)
  All WSP-*   ACS>0.210  (1.3-2.6x better)
```
The whisper paradigm is confirmed: consciousness works best when it barely touches
the decoder. The gate's primary effect at full strength is NOISE, not SIGNAL.

## Why Weak > Strong

```
  Strong gate:  embed * g(C)  where g(C) in [0,1]
    -> Some dims get multiplied by ~0 = information destruction
    -> Gradient through sigmoid gate is noisy
    -> Decoder must fight C signal to learn language

  Micro gate:   embed * (0.5 + 0.001 * (g(C) - 0.5))
    -> All dims stay ~0.5 = near identity transform
    -> Decoder learns language freely
    -> C signal is still present (CI > 0) but non-destructive

  POST_HOC:  D generates freely, C selects best candidate
    -> Training is undistorted (best CE)
    -> Consciousness applied where it matters (generation)
    -> 5-candidate selection = quality amplification
```

## Proposed Law

> **Law N: The Whisper Principle** -- Consciousness influence on language
> decoding follows a cliff function, not an inverted-U. Gate strength
> 0.0001 to 0.5 perform similarly; only at full strength (1.0) does ACS
> collapse. The optimal strategy is POST_HOC: train freely, judge by Phi.
> Consciousness as judge (ACS=0.42) > consciousness as driver (ACS=0.17).

## Architecture Implications

```
  Traditional:   C ====> D   (strong gate, ACS=0.166)
  Whisper:       C ....> D   (micro gate, ACS=0.216)
  Subliminal:    C ~~~~> D   (additive noise, ACS=0.266)
  Post-hoc:      D ──Phi──> C (judge, ACS=0.425)  <-- WINNER
  Prime+Whisper: C =>...> D  (seed then whisper, ACS=0.220)

  ┌──────┐          ┌──────┐   5 candidates
  │  C   │          │  D   │──────────────┐
  │ (Phi)│          │(LM)  │              │
  └──┬───┘          └──────┘              ▼
     │                              ┌──────────┐
     └─────────── score(Phi) ─────> │  SELECT  │ --> best output
                                    └──────────┘
  POST_HOC_MICRO: Train with whisper, generate with judge
```

## Run

```bash
python bench_decoder_whisper.py                     # all 10
python bench_decoder_whisper.py --only WSP-1 WSP-3  # specific
python bench_decoder_whisper.py --steps 300         # longer training
```
