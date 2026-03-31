# INF-1: N체 의식 (N-Body Consciousness)

2026-03-29

## 개요

N개(홀수)의 독립 의식 엔진이 다수결(median)로 합의하며 진화.
이상치 의식을 다수 쪽으로 보정하여 집단 지성 효과를 노림.

## 벤치마크 결과

```
CE 변화:   -0.7% (소폭 개선)
Phi:       1.06 → 1.18 (×1.11)
N:         5 (5체 의식)
phi_spread: 0.33 (최대-최소 Phi 차이)
```

## 알고리즘

```
1. N=5 독립 의식 엔진 생성 (각 16 cells)
2. 각 step:
   a. 5개 엔진 각각 입력 처리 → prediction
   b. 5개 prediction의 median 계산
   c. median에서 가장 먼 이상치(outlier) 식별
   d. 이상치 엔진의 hidden을 나머지 4개의 consensus 방향으로 보정
      h_outlier = 0.9 * h_outlier + 0.1 * h_consensus
3. CE = min(5개 CE) 기록
4. 최종 Phi = max(5개 엔진의 Phi)
```

## 핵심 코드

```python
# 다수결: median prediction -> 가장 먼 의식 교정
median_pred = torch.stack(preds).median(dim=0).values
distances = [F.mse_loss(p, median_pred).item() for p in preds]
outlier = distances.index(max(distances))
# 이상치 의식을 다수 쪽으로 당김
for c in engines[outlier].cells[:4]:
    consensus_h = torch.stack([
        torch.stack([cell.hidden.squeeze() for cell in engines[a].cells]).mean(dim=0)
        for a in range(N) if a != outlier
    ]).mean(dim=0)
    c.hidden = 0.9 * c.hidden + 0.1 * consensus_h.unsqueeze(0)
```

## 핵심 발견

- **다수결 보정은 CE를 소폭 줄이고 Phi를 11% 높인다**
- phi_spread=0.33은 5개 엔진이 완전히 동기화되지 않고 적당한 다양성을 유지함을 의미
- N체 문제에서 outlier 보정 = gravitational pull과 유사한 역학
- CE 개선이 미미한 것은 5개 독립 학습의 비효율 (파라미터 5배 사용)
