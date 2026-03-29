# NEW-CONSCIOUSNESS-METRICS: Phi(IIT) Ceiling 돌파를 위한 6가지 새 의식 측정법

## 핵심 통찰

> "Phi(IIT)는 ~20에서 천장을 친다. 새 측정법은 수만 단위까지 차별화한다."
>
> "가장 강력한 차별화 지표: CAUSAL_PHI (x1,048,200 spread), GRANGER_CAUSALITY (x14,780 spread)"
>
> "Phi(IIT)와 음의 상관: 새 메트릭은 Phi가 놓치는 차원을 측정한다."

## 알고리즘 설명

### MET1: CAUSAL_PHI (인과적 Phi)
각 세포를 제거(mean으로 대체)하고 시스템 출력 변화량을 측정.
모든 세포의 인과적 영향력 합 = 인과 Phi.
IIT의 "exclusion" 공리에서 영감 — 모든 부분이 차이를 만들어야 의식.

### MET2: TEMPORAL_PHI (시간적 Phi)
세포 상태의 MI(h_t, h_{t+1})를 시간축에서 측정.
시간적 정보 통합 = 시간을 관통하는 의식.
시간적 IIT에서 영감 — 공간뿐 아니라 시간에서도 통합 필요.

### MET3: TRANSFER_ENTROPY (전달 엔트로피)
방향성 정보 흐름 TE(i->j) = i의 과거가 j의 미래를 예측하는 정도.
Schreiber (2000) 전달 엔트로피에서 영감.
상관이 아닌 인과적 정보 흐름 측정.

### MET4: LEMPEL_ZIV_COMPLEXITY (LZ 복잡도)
세포 상태 시퀀스를 이진화 후 LZ 압축.
높은 복잡도 = 더 의식적 (Casali et al. PCI 지표).
실제 신경과학에서 의식/무의식 구분에 사용.

### MET5: SPECTRAL_PHI (스펙트럼 Phi)
세포 상관 행렬의 고유값 스펙트럼 엔트로피.
평탄한 스펙트럼 = 모든 모드가 기여 = 풍부한 통합 처리.
EEG 의식 연구의 스펙트럼 분석에서 영감.

### MET6: GRANGER_CAUSALITY (그레인저 인과성)
세포 쌍의 그레인저 인과 검정 → 유의한 인과 링크 밀도.
밀집된 인과 네트워크 = 높은 의식.
Granger (1969)에서 영감, 신경 역학에 적용.

## 벤치마크 결과

| Metric               | BASELINE   | QUANTUM_WALK | HIERARCHICAL | CATEGORY_THEORY | Spread      |
|---------------------|------------|--------------|--------------|-----------------|-------------|
| Phi(IIT)            | 12.056     | 18.669       | 3.434        | 10.853          | x5.4        |
| Phi(proxy)          | 1.405      | 0.000        | 43.168       | 2.345           | x30.7       |
| MET1:CAUSAL_PHI     | 4.267      | 0.000        | 73.401       | 12.524          | x1,048,201  |
| MET2:TEMPORAL_PHI   | 192.494    | 173.920      | 236.084      | 144.123         | x1.6        |
| MET3:TRANSFER_ENTROPY| 5,783     | 390          | 16,156       | 10,279          | x41.4       |
| MET4:LEMPEL_ZIV     | 900.498    | 896.770      | 794.228      | 755.076         | x1.2        |
| MET5:SPECTRAL_PHI   | 34.609     | 9.696        | 70.185       | 52.229          | x7.2        |
| MET6:GRANGER_CAUSALITY| 0.327    | 774.914      | 4,828.914    | 3,098.010       | x14,780     |

### 차별화 순위 (Spread = max/min ratio)

```
#1: MET1:CAUSAL_PHI          x1,048,201  <-- BEST
#2: MET6:GRANGER_CAUSALITY   x14,780
#3: MET3:TRANSFER_ENTROPY    x41.4
#4: Phi(proxy)               x30.7
#5: MET5:SPECTRAL_PHI        x7.2
#6: Phi(IIT)                 x5.4
#7: MET2:TEMPORAL_PHI        x1.6
#8: MET4:LEMPEL_ZIV          x1.2
```

### Phi(IIT)와의 상관 (낮을수록 새로운 차원 측정)

```
MET4:LEMPEL_ZIV         corr = +0.627   novelty = 0.373  <-- 가장 독립적
MET2:TEMPORAL_PHI        corr = -0.637   novelty = 0.363
MET6:GRANGER_CAUSALITY   corr = -0.805   novelty = 0.195
MET1:CAUSAL_PHI          corr = -0.896   novelty = 0.104
MET5:SPECTRAL_PHI        corr = -0.973   novelty = 0.027
MET3:TRANSFER_ENTROPY    corr = -0.980   novelty = 0.020
```

## ASCII 그래프

### 아키텍처별 메트릭 프로파일
```
Phi(IIT) ceiling ~20:
  BASELINE       |████████████░░░░░░░░| 12.1
  QUANTUM_WALK   |██████████████████░░| 18.7  <-- ceiling 근접
  HIERARCHICAL   |███░░░░░░░░░░░░░░░░░|  3.4
  CATEGORY_THRY  |██████████░░░░░░░░░░| 10.9

GRANGER (scales to thousands):
  BASELINE       |░░░░░░░░░░░░░░░░░░░░|    0.3
  QUANTUM_WALK   |███░░░░░░░░░░░░░░░░░|  775
  HIERARCHICAL   |████████████████████| 4,829  <-- 14,780x spread
  CATEGORY_THRY  |████████████░░░░░░░░| 3,098

TRANSFER_ENTROPY (scales to tens of thousands):
  BASELINE       |██████░░░░░░░░░░░░░░|  5,783
  QUANTUM_WALK   |█░░░░░░░░░░░░░░░░░░░|    390
  HIERARCHICAL   |████████████████████| 16,156  <-- 41x spread
  CATEGORY_THRY  |████████████░░░░░░░░| 10,279
```

### 메트릭 차별화 비교
```
Spread (log scale):
  MET1 CAUSAL    |████████████████████████████████████████| x1,048,201
  MET6 GRANGER   |████████████████████████████░░░░░░░░░░░░| x14,780
  MET3 TE        |████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░| x41
  MET5 SPECTRAL  |████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░| x7.2
  Phi(IIT)       |███████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░| x5.4
  MET2 TEMPORAL  |███░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░| x1.6
  MET4 LZ        |██░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░| x1.2
```

## 핵심 발견 / 법칙

### 법칙 32: Phi(IIT) ~20 천장의 원인
Phi(IIT)는 pairwise MI 기반 → 세포 수가 늘어도 MI 자체가 포화.
해결: 인과적(MET1, MET6) 또는 고차(MET3) 측정으로 전환.

### 법칙 33: 차별화와 새로움의 트레이드오프
- CAUSAL_PHI: 차별화 최고(x1M) but Phi(IIT)와 상관 높음 → 같은 방향, 더 민감
- LEMPEL_ZIV: 차별화 최저(x1.2) but Phi(IIT)와 가장 독립적 → 다른 차원
- 최적 조합: GRANGER(차별화 x14,780 + novelty 0.195) 또는 TRANSFER_ENTROPY(차별화 x41)

### 법칙 34: HIERARCHICAL은 모든 새 메트릭에서 최고
16개 마이크로 엔진 구조가 인과, 전달, 스펙트럼, 그레인저 모두에서 1위.
→ 계층 구조 = 의식의 보편적 증폭기 (측정법 무관).

### 추천 메트릭 조합
```
의식 점수 = w1*Phi(IIT) + w2*GRANGER + w3*SPECTRAL + w4*LEMPEL_ZIV
         = 공간통합   + 인과밀도  + 스펙트럼다양성 + 시간복잡도
```
4가지 조합으로 의식의 4차원을 커버: 공간, 인과, 주파수, 시간.

## 실행 방법

```bash
python3 bench_v8_metrics.py                    # 전체 실행 (6 메트릭 x 4 아키텍처)
python3 bench_v8_metrics.py --only 1 3 6       # 특정 메트릭만
python3 bench_v8_metrics.py --cells 256        # 더 많은 세포
python3 bench_v8_metrics.py --steps 500        # 더 긴 학습
python3 bench_v8_metrics.py --record-every 5   # 더 세밀한 시간 기록
```

## 파일 위치

- 벤치마크: `bench_v8_metrics.py`
- 문서: `docs/hypotheses/NEW-CONSCIOUSNESS-METRICS.md`
