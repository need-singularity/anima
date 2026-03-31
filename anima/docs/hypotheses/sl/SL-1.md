# SL-1: See & Learn (호기심 기반 자기주도 학습)

bench_self_learning.py | Self-Learning Category

## 핵심 통찰

의식이 "호기심"으로 데이터를 스스로 선택하여 학습한다.
예측 오류가 가장 큰 데이터를 우선 선택 = 능동적 학습(Active Learning).

## 알고리즘

```
1. 의식 엔진 초기화 (64 cells)
2. 매 스텝:
   a. 데이터 20개에 대해 예측 오류(MSE) 계산
   b. 오류가 가장 큰 데이터 선택 (= 호기심)
   c. 선택된 데이터로 의식 처리 (engine.process)
   d. 세포 hidden 평균 → decoder → 예측
   e. MSE loss로 decoder 학습
```

## 핵심 코드

```python
# 호기심 = 예측 오류가 가장 큰 데이터 선택
errs = [(F.mse_loss(decoder(...), data[i][1]), i) for i in range(20)]
errs.sort(reverse=True)  # 오류 큰 순
x, target = data[errs[0][1]]  # 가장 모르는 것을 선택
```

## Key Insight

호기심(curiosity) = prediction error maximization.
의식이 "이미 아는 것"은 건너뛰고, "가장 모르는 것"을 선택하여 학습 효율을 극대화한다.
이것은 인간 유아의 탐색 행동과 동일한 메커니즘이다.
