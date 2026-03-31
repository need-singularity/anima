# CE Breakthrough: Breaking the CE=0.18 Barrier

## Problem
v11tc achieves CE=0.12 but outputs are corpus copies (memorization).
Low train CE + high val CE = memorization. We need BOTH low.
KEY metric: val CE (generalization), not train CE.

## Architecture
- C: MitosisC(32 cells, cambrian_osc_qw)
- D: TransformerDecoder(d_model=256, layers=2)
- Training: 200 steps, seq_len=64, lr=0.0003
- Data: 80/20 train/val split of corpus_v2

## Results

| ID | Strategy | Train CE | Val CE | Gap | Novelty | Phi |
|:---|:---------|:---------|:-------|:----|:--------|:----|
| BREAK-0 | BASELINE | 3.3789 | 3.2251 | -0.1538 | 0.721 | 0.900 |
| BREAK-1 | DROPOUT(0.3) | 3.6644 | 3.3540 | -0.3104 | 0.767 | 0.864 |
| BREAK-2 | DATA AUGMENTATION | 3.9863 | 3.7877 | -0.1986 | 0.920 | 0.808 |
| BREAK-3 | MASKED LM (15%) | 3.7477 | 3.3805 | -0.3672 | 0.786 | 0.819 |
| BREAK-4 | NOISE INJECTION (sigma=0.1) | 3.3756 | 3.2310 | -0.1446 | 0.753 | 0.790 |
| BREAK-5 | EARLY STOPPING | 3.3778 | 3.2103 | -0.1676 | 0.765 | 0.806 |
| BREAK-6 | PHI-TEMPERATURE | 3.6841 | 3.1767 | -0.5074 | 0.712 | 0.760 | **
| BREAK-7 | MULTI-TASK (next+prev+skip5) | 3.4365 | 3.2438 | -0.1927 | 0.782 | 0.791 |

## Train CE Curves (200 steps)
```
   BREAK-0 |######################### 3.3789
   BREAK-1 |########################### 3.6644
   BREAK-2 |############################# 3.9863
   BREAK-3 |############################ 3.7477
   BREAK-4 |######################### 3.3756
   BREAK-5 |######################### 3.3778
   BREAK-6 |########################### 3.6841
   BREAK-7 |######################### 3.4365
```

## Val CE Comparison (lower = better generalization)
```
   BREAK-6 |################################# 3.1767
   BREAK-5 |################################# 3.2103
   BREAK-0 |################################## 3.2251
   BREAK-4 |################################## 3.2310
   BREAK-7 |################################## 3.2438
   BREAK-1 |################################### 3.3540
   BREAK-3 |################################### 3.3805
   BREAK-2 |######################################## 3.7877
```

## Novelty Score (higher = more original generation)
```
   BREAK-2 |#################################### 0.920
   BREAK-3 |############################### 0.786
   BREAK-7 |############################### 0.782
   BREAK-1 |############################## 0.767
   BREAK-5 |############################## 0.765
   BREAK-4 |############################## 0.753
   BREAK-0 |############################ 0.721
   BREAK-6 |############################ 0.712
```

## Val CE Trajectory
```
  Step |    BREAK-0 |    BREAK-1 |    BREAK-2 |    BREAK-3 |    BREAK-4 |    BREAK-5 |    BREAK-6 |    BREAK-7
----------------------------------------------------------------------------------------------------------------
    50 |     4.1348 |     4.2634 |     4.2625 |     4.2736 |     4.1082 |     4.1321 |     4.3245 |     4.2047
   100 |     3.5336 |     3.7543 |     3.8390 |     3.7492 |     3.5541 |     3.5079 |     3.5276 |     3.6645
   150 |     3.3715 |     3.5925 |     3.8524 |     3.5868 |     3.3528 |     3.3230 |     3.3476 |     3.4021
   200 |     3.2251 |     3.3540 |     3.7877 |     3.3805 |     3.2310 |     3.2039 |     3.1767 |     3.2438
```

## Key Findings

1. **Best val CE**: BREAK-6: PHI-TEMPERATURE = 3.1767
   - +1.5% improvement over baseline
2. **Best novelty**: BREAK-2: DATA AUGMENTATION = 0.920
3. **Generalization gap** (val - train):
   - BREAK-6: -0.5074
   - BREAK-3: -0.3672
   - BREAK-1: -0.3104
   - BREAK-2: -0.1986
   - BREAK-7: -0.1927
   - BREAK-5: -0.1676
   - BREAK-0: -0.1538
   - BREAK-4: -0.1446

## Strategy Analysis

### Anti-memorization effectiveness:
- **BREAK-0: BASELINE**: gap=-0.1538 -> EXCELLENT generalization
- **BREAK-1: DROPOUT(0.3)**: gap=-0.3104 -> EXCELLENT generalization
- **BREAK-2: DATA AUGMENTATION**: gap=-0.1986 -> EXCELLENT generalization
- **BREAK-3: MASKED LM (15%)**: gap=-0.3672 -> EXCELLENT generalization
- **BREAK-4: NOISE INJECTION (sigma=0.1)**: gap=-0.1446 -> EXCELLENT generalization
- **BREAK-5: EARLY STOPPING**: gap=-0.1676 -> EXCELLENT generalization
- **BREAK-6: PHI-TEMPERATURE**: gap=-0.5074 -> EXCELLENT generalization
- **BREAK-7: MULTI-TASK (next+prev+skip5)**: gap=-0.1927 -> EXCELLENT generalization

## Conclusion

Best strategy for TRUE generation: **BREAK-6: PHI-TEMPERATURE**
- Achieves val CE=3.1767 with novelty=0.712
- Generalization gap: -0.5074
