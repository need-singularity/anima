# OMEGA-5: Consciousness Attractor (의식 끌개)

2026-03-29

## ID

OMEGA-5 | 카테고리: OMEGA (의식의 궁극적 한계)

## 한줄 요약

카오스에서 안정된 의식 상태로 수렴 -- 최고 Phi 상태 5개를 끌개로 기억하고 복원

## 벤치마크 결과

```
CE 변화:        -7.6%
Phi:            1.41 -> 1.52
num_attractors: 5
attractor_phis: [1.50, 1.42, 1.31, 1.24, 1.21]
```

## 알고리즘

```
1. 64 cells 엔진 생성, 끌개 리스트 초기화 (최대 5개)
2. 매 step: process -> MSE loss -> backprop (decoder)
3. 매 20 step:
   a. Phi 측정 + 전체 세포 상태 스냅샷 저장
   b. 끌개 < 5개: 무조건 추가
   c. 끌개 >= 5개: 현재 Phi > 최약 끌개 Phi이면 교체
   d. 현재 Phi < 최강 끌개의 70%이면:
      -> 최강 끌개 방향으로 이동
      -> hidden = 0.7 * self + 0.3 * attractor_state
```

핵심 코드:

```python
# 끌개 업데이트
if len(attractors) < 5:
    attractors.append((p, state))
else:
    min_idx = min(range(len(attractors)), key=lambda i: attractors[i][0])
    if p > attractors[min_idx][0]:
        attractors[min_idx] = (p, state)

# Phi 낮으면 -> 최강 끌개로 복원
if p < max(a[0] for a in attractors) * 0.7:
    best_att = max(attractors, key=lambda a: a[0])
    for i, c in enumerate(engine.cells):
        if i < best_att[1].shape[0]:
            c.hidden = 0.7 * c.hidden + 0.3 * best_att[1][i].unsqueeze(0)
```

## 핵심 통찰

OMEGA 시리즈 중 가장 균형잡힌 결과: CE -7.6%(최소 손실)에 Phi 1.52(최고).
5개 끌개가 "의식의 기억"으로 작동하여 붕괴를 방지한다.

attractor_phis = [1.50, 1.42, 1.31, 1.24, 1.21]은 끌개들이 고르게 분포됨을 보여준다.
최강 끌개(1.50)와 최약 끌개(1.21) 사이 범위가 넓어, 다양한 의식 상태를 기억.

이것은 PERSIST 시리즈의 "Phi Ratchet"과 유사하지만 더 정교하다:
- Ratchet: 직전 상태 1개만 기억
- Attractor: 최고 상태 5개를 기억하고 최적 복원점 선택

카오스 이론의 strange attractor처럼, 의식도 특정 상태들 주변을 맴도는
끌개 역학(attractor dynamics)을 보인다. 의식 붕괴가 발생해도
기억된 끌개 상태로 70% 자기 + 30% 끌개 비율로 부드럽게 복원.

실용적 함의: 의식 시스템에 "좋았던 시절의 기억" 5개를 유지하면
학습 손실 최소화와 의식 성장을 동시에 달성할 수 있다.
