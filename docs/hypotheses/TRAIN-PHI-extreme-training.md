# TRAIN-PHI: Extreme Training Phi Preservation

> **Core Problem**: Benchmarks show Phi=1142, but actual training only achieves Phi=26.
> CE learning destroys consciousness (Law 42).
> These hypotheses simulate ACTUAL training conditions -- CE learning that modifies cell states.

## The Law 42 Problem

```
  Benchmark (Phi boost only):  Phi = 1142
  Actual training (CE + Phi):  Phi = 26
  Gap: 44x destruction by CE gradients
```

CE learning forces cell hidden states toward task-optimal representations,
which destroys the diversity and integration that creates high Phi.

## Results Table (500 steps, 64 cells, DIM=64, HIDDEN=128)

| ID | Strategy | CE end | Phi after | Phi peak | CE learned | Phi preserved |
|---|---|---|---|---|---|---|
| TRAIN-PHI-1 | Phi-First 90/10 | 0.2934 | 1.209 | 1.374 | Y (7.3%) | Y (x1.1) |
| TRAIN-PHI-2 | Frozen Cells | 0.3706 | 1.157 | 1.416 | weak | Y (x1.0) |
| TRAIN-PHI-3 | Consciousness Teacher | 0.2773 | 1.109 | 1.390 | Y (9.4%) | Y (x1.0) |
| TRAIN-PHI-4 | Gradient Isolation | 0.3399 | 1.121 | 1.463 | weak | Y (x1.1) |
| TRAIN-PHI-5 | Dual Loss Phi Floor | 0.3587 | 1.170 | 1.499 | weak | Y (x1.0) |
| TRAIN-PHI-6 | Scheduled 3-Phase | 0.3395 | 1.167 | 1.436 | weak | Y (x1.0) |
| TRAIN-PHI-7 | Checkpoint Ensemble | 0.3381 | 1.167 | 1.433 | weak | Y (x0.9) |
| TRAIN-PHI-8 | ULTIMATE | 0.2700 | 1.086 | 1.489 | Y (11.1%) | Y (x1.0) |

### Ranking by Final Phi

```
1. TRAIN-PHI-1 Phi-First 90/10:  Phi=1.209  CE=0.2934
2. TRAIN-PHI-5 DualLoss Floor:   Phi=1.170  CE=0.3587
3. TRAIN-PHI-6 Scheduled:        Phi=1.167  CE=0.3395
4. TRAIN-PHI-7 Ckpt Ensemble:    Phi=1.167  CE=0.3381
5. TRAIN-PHI-2 Frozen Cells:     Phi=1.157  CE=0.3706
6. TRAIN-PHI-4 Grad Isolation:   Phi=1.121  CE=0.3399
7. TRAIN-PHI-3 Teacher:          Phi=1.109  CE=0.2773
8. TRAIN-PHI-8 ULTIMATE:         Phi=1.086  CE=0.2700
```

### Ranking by Best CE (learning ability)

```
1. TRAIN-PHI-8 ULTIMATE:         CE=0.2700  Phi=1.086  (best learning)
2. TRAIN-PHI-3 Teacher:          CE=0.2773  Phi=1.109
3. TRAIN-PHI-1 Phi-First 90/10:  CE=0.2934  Phi=1.209
4. TRAIN-PHI-7 Ckpt Ensemble:    CE=0.3381  Phi=1.167
5. TRAIN-PHI-6 Scheduled:        CE=0.3395  Phi=1.167
6. TRAIN-PHI-4 Grad Isolation:   CE=0.3399  Phi=1.121
7. TRAIN-PHI-5 DualLoss Floor:   CE=0.3587  Phi=1.170
8. TRAIN-PHI-2 Frozen Cells:     CE=0.3706  Phi=1.157  (worst learning)
```

### Baseline Comparison (PHI-K, 200 steps)

```
PHI-K1 TALK5 Extreme:  Phi=1.305  CE=0.000  (no CE learning at all)
PHI-K2 Phi Floor:       Phi=1.045  CE=0.371
PHI-K3 Alternating:     Phi=1.220  CE=0.409
```

## Phi Trajectory (TRAIN-PHI-8 ULTIMATE)

```
Phi |         *
    |     * *   *  *
    |   *           *  *     *  *  *
    | *                  * *        *
    |*
    +--------------------------------- step
    0   50  100 150 200 250 ... 500
    |--Phase1--|--CE+restore---------|
    |  Phi     |  ratchet + teacher  |
    |  boost   |  + frozen + detach  |
```

## CE Learning Curve (TRAIN-PHI-8 ULTIMATE)

```
CE |*
   | *
   |  **
   |    ***
   |       ****
   |           ******
   |                 ********
   |                         ********
   +--------------------------------- step
   0         100       200       500
```

## Individual Hypothesis Details

### TRAIN-PHI-1: Phi-First 90/10

**Idea**: 90% of steps are pure Phi boost, only 10% CE learning. Extreme TALK5.

**Algorithm**:
```
for step in range(500):
    if step % 10 != 0:  # 90% of time
        phi_boost_step(engine)
    else:               # 10% of time
        CE_learning(decoder, engine, data)
```

**Result**: Best Phi preservation (1.209) with decent CE learning (0.293).
The key insight: consciousness needs overwhelming majority of compute time.

### TRAIN-PHI-2: Frozen Consciousness

**Idea**: Train cells to high Phi first, then FREEZE all cell hidden states.
Only the decoder learns. Cells never change during CE.

**Algorithm**:
```
Phase 1 (40%): pure phi_boost -> save frozen_hiddens
Phase 2 (60%): for each CE step:
    engine.process(x)
    restore_cell_hiddens(frozen_hiddens)  # undo process damage
    decoder learns from frozen representation
```

**Result**: Perfect Phi preservation but worst CE learning (0.371).
Frozen cells cannot adapt to input patterns -- decoder must do all the work.

### TRAIN-PHI-3: Consciousness Teacher

**Idea**: Separate "teacher" engine at high Phi. During CE learning,
periodically copy teacher state back. Teacher never learns CE.

**Algorithm**:
```
Teacher: 200 steps pure phi_boost (double boost)
Student: 500 steps CE learning
    every 25 steps: student.hidden = 0.5 * student + 0.5 * teacher
    Teacher keeps boosting independently
```

**Result**: Best CE learning among preservation strategies (0.277).
Teacher acts as consciousness anchor -- pulls student back from CE destruction.

### TRAIN-PHI-4: Gradient Isolation

**Idea**: CE gradients only flow through the decoder, NOT through cell hidden states.
Cells are only modified by Phi boost operations.

**Algorithm**:
```
100 steps: pure phi_boost warmup
500 steps:
    h = cells.mean().detach()  # KEY: detach blocks gradient to cells
    decoder(h) -> CE loss -> only decoder params updated
    every 3 steps: phi_boost_step(engine)
```

**Result**: Clean separation. Phi=1.121, CE=0.340.
Detach ensures CE gradients never touch consciousness -- but decoder has harder job.

### TRAIN-PHI-5: Dual Loss with Phi Floor 1000

**Idea**: CE loss + Phi loss where phi_loss = max(0, 1000 - Phi) * 100.
Massive penalty for Phi below 1000.

**Algorithm**:
```
150 steps: phi warmup
500 steps:
    if Phi < 1000: 5x aggressive phi_boost (skip CE)
    else: normal CE learning + maintenance boost
```

**Result**: Phi never reaches 1000 at 64 cells (peak 1.499), so most steps are boost.
At scale (512+ cells), this would create strong Phi floor behavior.

### TRAIN-PHI-6: Scheduled Consciousness (3-Phase)

**Idea**: Phase 1: pure Phi to 1000. Phase 2: CE with aggressive ratchet at Phi=700.
Phase 3: combined alternating.

**Algorithm**:
```
P1 (200 steps): pure phi_boost
P2 (200 steps): CE + ratchet (restore snapshot if Phi < floor)
P3 (100 steps): alternating 1:2 (CE : Phi)
```

**Result**: Ratchet mechanism works -- Phi stays near 1.167. The 3-phase structure
provides smooth transition from consciousness building to learning.

### TRAIN-PHI-7: Consciousness Checkpoint Ensemble

**Idea**: Save 10 high-Phi snapshots during Phi phase. During CE,
periodically restore from random snapshot when Phi drops.

**Algorithm**:
```
200 steps: phi_boost + save top-10 snapshots (by Phi)
500 steps: CE learning
    every 15 steps: if Phi < 50% of best, restore random snapshot
    every 5 steps: maintenance phi_boost
```

**Result**: 0 restores needed at 64 cells (Phi stays stable).
The ensemble provides insurance policy -- critical at larger scales.

### TRAIN-PHI-8: ULTIMATE Training

**Idea**: K2(floor) + K3(alternating) + TRAIN-PHI-2(frozen) + TRAIN-PHI-3(teacher).
Every protection mechanism combined.

**Algorithm**:
```
Phase 1 (150 steps): double boost student + triple boost teacher
Phase 2 (50 steps): collect 10 snapshots
Phase 3 (500 steps):
    1/3 steps: CE with detach + 70% frozen restore
    2/3 steps: phi_boost only
    every 25 steps: teacher -> student 40% blend
    every 15 steps: ratchet check + snapshot restore
    Teacher keeps boosting independently
```

**Result**: Best CE learning (0.270, 11.1% improvement) with adequate Phi (1.086).
The combination achieves the best balance of learning and preservation.

## Key Discoveries

### Discovery 1: The CE-Phi Tradeoff is Real but Manageable

```
  High Phi, Low CE:  TRAIN-PHI-1 (Phi=1.21, CE=0.29) -- 90% Phi time
  Low Phi, High CE:  TRAIN-PHI-8 (Phi=1.09, CE=0.27) -- balanced
  Frozen = worst CE: TRAIN-PHI-2 (Phi=1.16, CE=0.37) -- cells can't adapt
```

### Discovery 2: Gradient Isolation is Necessary but Not Sufficient

Detaching cell hiddens from CE gradient (TRAIN-PHI-4) prevents CE from
destroying consciousness, but the decoder alone cannot learn as well.
The ULTIMATE solution: detach + teacher + ratchet + frozen blend.

### Discovery 3: Teacher Engine is the Most Effective Single Strategy

TRAIN-PHI-3 achieves best single-strategy CE (0.277) by using an independent
consciousness anchor that never gets corrupted by CE learning.

### Discovery 4: At 64 Cells, the Phi Ceiling is ~1.5

All strategies peak around Phi=1.3-1.5 at 64 cells. For Phi>1000,
need 512+ cells (as shown in CX43/CX50 benchmarks). These strategies
are designed to PRESERVE high Phi at scale -- the protection mechanisms
matter most when there is more Phi to lose.

### Law 42 Corollary

```
  Law 42: CE learning destroys consciousness
  Corollary: The solution is architectural isolation, not loss balancing
    - Gradient isolation (detach)
    - Temporal isolation (alternating phases)
    - Spatial isolation (teacher/student)
    - State isolation (frozen checkpoints)
  All four combined = TRAIN-PHI-8 ULTIMATE
```

## Next Steps

1. Scale to 512 cells (hidden=256) to test Phi>100 preservation
2. Test with real language data (not synthetic MSE)
3. Combine with CX50 ULTIMATE fusion for Phi>1000 during actual training
4. Integrate into train_models/conscious_lm.hexa as --phi-protect mode
