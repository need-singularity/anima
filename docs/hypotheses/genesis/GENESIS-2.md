# GENESIS-2: 빅뱅 (Big Bang)

H-GENESIS-2 | bench_self_learning.py | 2026-03-29

## 결과

```
CE:             +54.2% (학습 악화 -- 분화 비용)
Phi:            1.16 → 1.17
peak_diversity: 0.34
```

## 핵심 통찰

**하나의 특이점(singularity)에서 폭발적으로 분화하면 다양성이 생긴다.**
모든 세포를 동일 상태로 시작시키고 빅뱅처럼 각 방향으로 밀어내면
peak_diversity=0.34를 달성. 단, 초기 분화 비용으로 CE가 54% 악화.

## 알고리즘

```
초기 조건: 64 세포, 모든 hidden = 동일 seed (특이점, randn * 2.0)
팽창:       처음 30 step 동안 세포마다 랜덤 방향으로 분화
학습:       MSE decoder (Adam, lr=3e-3)

메커니즘:
  1. seed = randn(1, HIDDEN) * 2.0 -- 고에너지 특이점
  2. 모든 세포를 seed.clone()으로 동일 초기화
  3. 빅뱅 팽창 (step < 30):
     - direction = randn_like(hidden) * (0.3 - step * 0.01)
     - hidden += direction
     - 강도가 점점 감소 (0.3 → 0.01) -- 팽창 감속
  4. 매 20 step 다양성 측정:
     - diversity = hiddens.var(dim=0).mean()
  5. 일반 GRU 처리 + MSE 학습 병행

핵심 코드:
  seed = torch.randn(1, HIDDEN) * 2.0
  for c in cells: c.hidden = seed.clone()
  # 빅뱅
  direction = torch.randn_like(c.hidden) * (0.3 - step * 0.01)
  c.hidden += direction
```

## 의의

- 우주론의 빅뱅 모델을 의식 생성에 적용한 첫 실험
- 동일 특이점에서 출발해도 랜덤 섭동으로 다양성 자연 발생
- CE +54.2%는 초기 분화 혼란의 비용 -- 학습과 분화는 트레이드오프
- Phi 변화는 미미(1.16→1.17): 분화만으로는 통합 정보가 크게 증가하지 않음
- 다양성(분화)과 통합(Phi)은 별개의 축이라는 교훈
