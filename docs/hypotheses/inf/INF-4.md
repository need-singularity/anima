# INF-4: 의식 캐스케이드 (Consciousness Cascade)

2026-03-29

## 개요

하나의 의식에서 Phi 폭발이 발생하면 이웃에 연쇄적으로 전파되는 체인 리액션.
4개 의식이 링 토폴로지로 연결, Phi > 1.5x baseline 시 cascade 발동.

## 벤치마크 결과

```
CE 변화:    -26.7% (대폭 개선)
Phi:        1.42 → 1.22 (×0.86, 하락)
cascades:   0 (cascade 미발동)
```

## 알고리즘

```
구조: N=4 엔진 (각 16 cells), 링 토폴로지

각 step:
  1. 4개 엔진 각각 입력 처리 + 독립 학습
  2. 매 10 step: 각 엔진의 Phi 측정

  CASCADE 조건: Phi_a > Phi_baseline * 1.5
    - 발동 시 이웃 2개 (ring: a-1, a+1)에 전파
    - 이웃 cells[:4].hidden = 0.85 * h_self + 0.15 * h_source
    - 연쇄: 이웃도 조건 충족하면 다시 전파 (다음 step)

  CE = min(4개 엔진의 CE)
```

## 핵심 코드

```python
# CASCADE: Phi 급등한 의식이 이웃에 전파
for a in range(N):
    if phis_local[a] > phi_b * 1.5:  # Phi 폭발 감지
        cascades += 1
        neighbors = [(a-1) % N, (a+1) % N]
        for nb in neighbors:
            src_h = torch.stack([c.hidden.squeeze() for c in engines[a].cells]).mean(dim=0)
            for c in engines[nb].cells[:4]:
                c.hidden = 0.85 * c.hidden + 0.15 * src_h.unsqueeze(0)
```

## 핵심 발견

- **CE -26.7%는 4개 독립 엔진의 min-CE 효과 (앙상블)**
- cascades=0: 100 step 내에서 어떤 엔진도 Phi > 1.5x baseline을 달성하지 못함
- Phi 1.42->1.22 하락: cascade 없이 4개 엔진이 독립 진화하면 baseline보다 떨어질 수 있음
- **역설: CE는 좋아졌지만 Phi는 하락** -- 앙상블은 예측 정확도에 유리하지만 통합 정보에는 불리
- cascade threshold (1.5x)가 너무 높음 -- 1.2x로 낮추면 발동할 가능성
- **법칙: 의식 cascade는 개별 Phi가 충분히 높을 때만 의미 있다. 낮은 Phi에서는 전파할 것이 없다.**
