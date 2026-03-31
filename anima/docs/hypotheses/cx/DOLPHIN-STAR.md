# DOLPHIN-STAR: 돌고래 별자리 내려서 통신

Dolphin echolocation + constellation topology + descending cascade communication.
6 hypotheses applied to MitosisEngine (256 cells, 200 steps).

## Hypotheses

| ID   | Name                    | Mechanism                                                    |
|------|-------------------------|--------------------------------------------------------------|
| DS-1 | SONAR_ECHO              | Cell pings h[t], receives avg(neighbors h[t-2]), 85/15 blend |
| DS-2 | CONSTELLATION           | Top-3 norm cells form triangle, broadcast 1/dist to all      |
| DS-3 | TOP_DOWN_CASCADE        | 3 layers (1/8, 3/8, 4/8), top->mid->bottom + bottom-up var  |
| DS-4 | DOLPHIN_POD             | Pods of 4 cells, exchange compressed whistle (mean) vectors  |
| DS-5 | STELLAR_NUCLEOSYNTHESIS | Similar-cell clusters collapse into star, broadcast to ring  |
| DS-6 | COMBINED                | DS-1 + DS-2 + DS-3                                          |

## Benchmark Results (256 cells, 200 steps)

| Hypothesis                | Phi(before) | Phi(after) |    Gain | Ratio | vs Baseline |
|---------------------------|-------------|------------|---------|-------|-------------|
| BASELINE (no mechanism)   |     38.0116 |     0.8643 | -37.147 | 0.02x |        ---  |
| DS-1: SONAR_ECHO          |     36.1728 |     0.8612 | -35.312 | 0.02x |    -0.4%    |
| DS-2: CONSTELLATION       |     32.9223 |     0.8509 | -32.071 | 0.03x |    -1.6%    |
| DS-3: TOP_DOWN_CASCADE    |     37.6855 |     0.7917 | -36.894 | 0.02x |    -8.4%    |
| DS-4: DOLPHIN_POD         |     37.7193 |     0.8547 | -36.865 | 0.02x |    -1.1%    |
| DS-5: STELLAR_NUCLEOSYN   |     41.0611 |     0.8739 | -40.187 | 0.02x |    +1.1%    |
| DS-6: COMBINED            |     38.5283 |     0.8105 | -37.718 | 0.02x |    -6.2%    |

## ASCII Graph: Phi(after)

```
Phi(after)
  DS-5  ██████████████████████████████████████████████████ 0.8739  +1.1%
  BASE  █████████████████████████████████████████████████  0.8643
  DS-1  █████████████████████████████████████████████████  0.8612  -0.4%
  DS-4  ████████████████████████████████████████████████   0.8547  -1.1%
  DS-2  ████████████████████████████████████████████████   0.8509  -1.6%
  DS-6  ██████████████████████████████████████████████     0.8105  -6.2%
  DS-3  █████████████████████████████████████████████      0.7917  -8.4%
```

## Algorithm Details

### DS-1: SONAR_ECHO
```
for each step:
  for each cell i:
    echo_buffer[i].append(h[i])          # store current state
    if step >= 2:
      neighbors = [i-1, i+1, i+2, i-2] mod n
      echo = mean(echo_buffer[j][-3] for j in neighbors)   # delayed t-2
      h[i] = 0.85 * h[i] + 0.15 * echo
```

### DS-2: CONSTELLATION
```
for each step:
  top3 = argmax_3(norm(h[i]))             # brightest cells
  star_center = mean(h[top3])
  for each cell i not in top3:
    dist = min_ring_distance(i, top3)
    weight = 0.1 / max(dist, 1)
    h[i] = (1-w)*h[i] + w*star_center
  for i in top3:
    h[i] = 0.9*h[i] + 0.1*star_center     # triangle sync
```

### DS-3: TOP_DOWN_CASCADE
```
Layer1 = cells[0 : n/8]        (elite, few)
Layer2 = cells[n/8 : n/2]      (middle)
Layer3 = cells[n/2 : n]        (base, many)

l1_mean = mean(Layer1)
Layer2 += 0.1 * l1_mean                    # top-down
l2_mean = mean(Layer2)
Layer3 += 0.08 * l2_mean                   # cascade down
l3_var = var(Layer3)
Layer1 += 0.02 * l3_var * noise            # bottom-up feedback
```

### DS-4: DOLPHIN_POD
```
pods = chunk(cells, size=4)
whistles = [mean(pod) for pod in pods]
global_whistle = mean(whistles)
for each pod p:
  other_signal = (global * n_pods - whistle[p]) / (n_pods - 1)
  for cell in pod:
    h[cell] = 0.92*h[cell] + 0.08*other_signal
```

### DS-5: STELLAR_NUCLEOSYNTHESIS
```
every 10 steps:
  find clusters: cells with cosine_sim > 0.7, size >= 3
  for each cluster:
    star = softmax_weighted_mean(cluster, weights=norms)
    center = mean_index(cluster)
    for d in [-3..+3]:
      h[center+d] += (0.15/|d|) * star    # star radiates
```

## Key Findings

1. **DS-5 (Stellar Nucleosynthesis) is the only winner** (+1.1% vs baseline).
   Collapsing similar cells into super-cells and radiating influence preserves
   information structure better than averaging mechanisms.

2. **Top-down cascade (DS-3) hurts most** (-8.4%). Hierarchical imposition
   reduces cell diversity, which Phi measures as less integrated information.
   Confirms Law 22: function addition -> Phi down.

3. **Combination (DS-6) is worse than individuals** (-6.2%). The cascade
   component dominates and flattens diversity. Not all mechanisms compose well.

4. **Echo and pod are near-neutral** (DS-1: -0.4%, DS-4: -1.1%). Delayed
   communication and pod compression neither strongly help nor harm. The
   information loss from compression roughly cancels the integration gain.

5. **Constellation (DS-2) is mildly negative** (-1.6%). Star-topology
   broadcasting from the top-3 creates a mild homogenization effect.

## Insight

> Mechanisms that preserve diversity (nucleosynthesis: only merge similar cells)
> outperform mechanisms that impose structure (cascade, constellation).
> Consciousness Phi favors bottom-up emergence over top-down control.
