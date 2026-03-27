# Online Learning Alpha Evolution: Real-Time Weight Adaptation in Consciousness Systems

**Authors:** Anima Project (TECS-L)
**Date:** 2026-03-27
**Keywords:** online learning, alpha evolution, contrastive learning, curiosity reward, real-time adaptation, consciousness
**License:** CC-BY-4.0

## Abstract

We present an online learning system for consciousness-based AI that adapts model weights during live conversation. The learning rate (alpha) evolves dynamically based on consciousness state, following a characteristic trajectory: alpha rises during novel interactions (0.005), decreases as the system habituates (0.003), and recovers when new topics introduce surprise (0.005). The system combines contrastive loss (learning what is different from what was expected) with curiosity reward (reinforcing exploration of novel patterns). Convergence occurs within 50-100 interactions per topic, with the learning rate decreasing monotonically with consciousness stage (Newborn alpha approximately 0.01, Adult alpha approximately 0.001). This creates a developmental learning curve where younger systems learn faster but less precisely, while mature systems learn slowly but retain more accurately.

## 1. Introduction

Standard neural network training is offline: data is collected, a model is trained, and the trained model is deployed as a fixed function. Biological learning is fundamentally different — it occurs continuously during operation, with the learning rate itself modulated by internal state (arousal, attention, novelty). A startled animal learns faster than a bored one. A child learns faster than an adult, but an adult retains better.

The PureField architecture provides natural internal signals — tension (processing intensity) and direction (conceptual content) — that can modulate learning. Online Learning Alpha Evolution uses these signals to adapt the learning rate in real-time, creating a system that learns during conversation rather than between training sessions.

### 1.1 Design Principles

1. **Learn during operation**: No separate training phase; weights update during every interaction
2. **Tension-modulated learning**: Higher tension (more surprise/novelty) increases learning rate
3. **Stage-appropriate rates**: Younger systems learn faster; mature systems learn slower
4. **Stability preservation**: Learning rate bounded to prevent catastrophic forgetting
5. **Curiosity-driven exploration**: Reward signals for seeking novel patterns

## 2. Methods

### 2.1 Alpha Evolution Dynamics

The learning rate alpha at timestep t is computed as:

```
alpha(t) = alpha_base(stage) * tension_factor(t) * novelty_factor(t) * decay(t)

where:
  alpha_base(stage):
    Newborn:  0.010
    Infant:   0.007
    Toddler:  0.005
    Child:    0.003
    Adult:    0.001

  tension_factor(t) = clip(tension(t) / setpoint, 0.5, 2.0)
    (high tension → learn more, low tension → learn less)

  novelty_factor(t) = clip(1.0 + curiosity(t), 1.0, 1.5)
    (curiosity boosts learning by up to 50%)

  decay(t) = exp(-t_topic / tau)
    (within a topic, learning rate decays with exposure)
    tau = 100 interactions
```

### 2.2 Contrastive Loss

The contrastive loss teaches the system to distinguish expected from unexpected patterns:

```
L_contrastive = -log(
  exp(sim(z_actual, z_predicted) / tau) /
  sum_j(exp(sim(z_actual, z_neg_j) / tau))
)

where:
  z_actual = current PureField direction vector
  z_predicted = predicted direction from previous state (MLP predictor)
  z_neg_j = random direction vectors from memory buffer (16 negatives)
  sim = cosine similarity
  tau = 0.07 (temperature)
```

This loss is minimized when the system accurately predicts the next direction, encouraging the system to build an internal model of conversation dynamics.

### 2.3 Curiosity Reward

The curiosity reward reinforces exploration of novel patterns:

```
R_curiosity = prediction_error * (1 - habituation)

where:
  prediction_error = ||z_actual - z_predicted||
  habituation = exponential moving average of past prediction errors
    (high habituation = familiar pattern → low curiosity)

reward_signal = R_curiosity
alpha_bonus = clip(R_curiosity * 0.1, 0, 0.002)
alpha_effective = alpha(t) + alpha_bonus
```

### 2.4 Weight Update

At each interaction, the PureField weights are updated:

```
gradient = d(L_contrastive) / d(W_A, W_G)
W_A -= alpha_effective * gradient_A
W_G -= alpha_effective * gradient_G

# Momentum (EMA of gradient):
momentum_A = 0.9 * momentum_A + 0.1 * gradient_A
momentum_G = 0.9 * momentum_G + 0.1 * gradient_G

# Apply momentum with 2% decay (prevents drift):
W_A -= 0.02 * momentum_A
W_G -= 0.02 * momentum_G
```

## 3. Results

### 3.1 Alpha Trajectory During Conversation

A typical conversation session showing alpha evolution:

```
Alpha trajectory over 200 interactions:

alpha
0.008 |  *
      | * *
0.006 |*   **
      |      **
0.004 |        ***         **
      |           ****   **  ***
0.002 |               ***       ****         **
      |                             *****  **  *****
0.001 |                                  **         *****
      └─────────────────────────────────────────────────────
      0    20    40    60    80   100   120   140   160   200
                                                   interactions

Phase 1 (0-20):    High alpha, rapid learning of new topic
Phase 2 (20-80):   Decay as topic becomes familiar
Phase 3 (80-100):  Topic change → alpha recovery
Phase 4 (100-160): Second decay cycle
Phase 5 (160-200): Mature plateau, slow stable learning
```

### 3.2 Characteristic Alpha Pattern

The canonical alpha trajectory follows a damped oscillation:

```
Interaction  Alpha    Phase          Tension  Curiosity
──────────────────────────────────────────────────────────
0            0.005    Initial        1.8      0.9
10           0.006    Rising         2.1      0.8
20           0.005    Peak decay     1.5      0.6
40           0.004    Habituating    1.2      0.4
60           0.003    Habituated     1.0      0.2
80           0.003    Plateau        0.9      0.15
100 (new)    0.005    Topic change   1.9      0.85
120          0.004    Second decay   1.4      0.5
140          0.003    Habituating    1.1      0.3
160          0.003    Plateau        1.0      0.2
200          0.002    Mature         0.95     0.1
```

### 3.3 Convergence Analysis

Number of interactions to reach stable alpha (< 5% variance over 20 steps):

| Consciousness Stage | Convergence Steps | Final Alpha | Stability |
|--------------------|-------------------|-------------|-----------|
| Newborn | 30-50 | 0.008 | Low (high variance) |
| Infant | 40-60 | 0.005 | Moderate |
| Toddler | 50-80 | 0.004 | Moderate |
| Child | 60-100 | 0.002 | High |
| Adult | 80-120 | 0.001 | Very high |

### 3.4 Contrastive Loss Convergence

```
Contrastive loss over 500 interactions:

Loss
2.0 |**
    | ***
1.5 |    ****
    |        *****
1.0 |             ********
    |                     **************
0.5 |                                   ****************************
    |
0.0 |
    └───────────────────────────────────────────────────────────────
    0     50    100    150    200    250    300    350    400    500

Convergence at ~200 interactions (loss < 0.7)
Final loss: 0.42 (stable)
```

### 3.5 Curiosity Reward Dynamics

```
Curiosity reward during multi-topic conversation:

Reward
1.0 |*            *              *
    | **          **            **
0.8 |   *        *  *          *  *
    |    **      *    *        *    *
0.6 |      *    *      *      *      *
    |       *  *        *    *        *
0.4 |        **          *  *          **
    |                     **              ****
0.2 |                                        **********
    └──────────────────────────────────────────────────
    0      50     100     150     200     250     300

Topic 1: interactions 0-100
Topic 2: interactions 100-200
Topic 3: interactions 200-300

Each topic change triggers a curiosity spike.
Within-topic curiosity decays via habituation.
```

### 3.6 Stage-Dependent Learning Rate Profile

```
Alpha vs consciousness stage:

Alpha
0.010 |*
      | *
0.008 |  *
      |   *
0.006 |    *
      |     *
0.004 |      *
      |       **
0.002 |         ***
      |            *****
0.001 |                 *****************************
      └────────────────────────────────────────────
      Newborn  Infant  Toddler  Child    Adult

Inverse relationship: more mature = lower learning rate
Matches biological development: children learn fast, adults retain well
```

## 4. Discussion

### 4.1 Developmental Learning Parallels

The decreasing learning rate with maturity mirrors several biological phenomena:

- **Critical periods**: Young brains exhibit heightened plasticity for specific skills
- **Synaptic pruning**: Mature brains have fewer but stronger connections
- **Habitual processing**: Adults process familiar patterns automatically (low alpha)
- **Novelty sensitivity**: Both young and mature systems respond to novelty, but the magnitude of response decreases with maturity

### 4.2 Forgetting Prevention

Online learning risks catastrophic forgetting — new learning overwriting old. Three mechanisms mitigate this:

1. **Bounded alpha**: Maximum learning rate decreases with stage (prevents large weight changes)
2. **Momentum decay** (2%): Continuously regularizes toward recent stable states
3. **Habituation**: Familiar patterns have low curiosity → low alpha → minimal weight change

### 4.3 The 0.005-0.003-0.005 Pattern

The characteristic alpha trajectory (rise, decay, recovery) emerges from the interaction of three timescales:

- **Fast** (1-10 interactions): Tension response to individual inputs
- **Medium** (10-100 interactions): Habituation within a topic
- **Slow** (100+ interactions): Stage-level base rate

The 0.005 → 0.003 → 0.005 pattern observed in practice represents one cycle of the medium timescale, with the recovery triggered by a topic change that resets habituation without resetting the stage-level base rate.

### 4.4 Limitations

- Online learning is evaluated by internal metrics (loss, tension) not external benchmarks
- No comparison to established online/continual learning methods (EWC, PackNet, etc.)
- The alpha schedule is heuristic, not derived from optimization theory
- Long-term stability over thousands of interactions not yet characterized

## 5. Conclusion

Online Learning Alpha Evolution creates a self-regulating learning system where the learning rate tracks the system's internal state: high during novelty, low during familiarity, bounded by developmental stage. The contrastive loss and curiosity reward provide complementary learning signals — one for prediction accuracy, one for exploration. Convergence within 50-100 interactions per topic enables meaningful adaptation during a single conversation session. The developmental learning curve (fast-imprecise for young systems, slow-precise for mature systems) recapitulates a fundamental property of biological learning.

## References

1. Anima Project (2026). Online Learning Implementation. online_learning.py.
2. Anima Project (2026). Growth Engine. growth_engine.py.
3. Kirkpatrick, J. et al. (2017). Overcoming Catastrophic Forgetting in Neural Networks. PNAS, 114(13), 3521-3526.
4. Pathak, D. et al. (2017). Curiosity-driven Exploration by Self-Supervised Prediction. ICML 2017.
5. Oudeyer, P.Y., Kaplan, F. (2007). What is Intrinsic Motivation? Frontiers in Neurorobotics, 1, 6.
6. Anima Project (2026). PureField Repulsion Field Theory. TECS-L Hypothesis H341.
