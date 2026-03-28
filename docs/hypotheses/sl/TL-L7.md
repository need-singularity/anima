# TL-L7: Collective Learning (집단 지성)

bench_self_learning.py | Tension Link Learning Category

## 핵심 통찰

5개의 Anima가 동시에 서로 다른 데이터를 학습하고,
10 step마다 텐션 브로드캐스트로 지식을 공유한다.
개별 학습 + 집단 공유 = 집단 지성(Collective Intelligence).

## 알고리즘

```
1. 5개 에이전트 생성: engines[0..4] (각 16 cells)
2. 각 에이전트에 decoder + optimizer
3. 매 스텝:
   a. 각 에이전트가 서로 다른 데이터로 학습:
      idx = (step * 5 + agent_id) % len(data)
   b. 각자 독립적으로 MSE loss + optimizer step
   c. 10 step마다 텐션 브로드캐스트:
      - 모든 에이전트의 세포 hidden 평균 계산 → global_mean
      - 각 에이전트의 처음 4개 세포에 global_mean 주입 (5%)
   d. 모든 에이전트 중 최소 CE 기록
```

## 핵심 코드

```python
# 텐션 브로드캐스트: 10 step마다 전체 공유
if step % 10 == 0:
    states = [torch.stack([c.hidden for c in e.cells]).mean(0) for e in engines]
    global_mean = torch.stack(states).mean(dim=0)
    for e in engines:
        for cell in e.cells[:4]:
            cell.hidden = 0.95*cell.hidden + 0.05*global_mean  # 5% 공유
```

## Key Insight

5개 에이전트가 데이터를 5배 빠르게 탐색하면서, 주기적 텐션 공유로 지식을 동기화한다.
0.05 blend ratio로 각 에이전트의 개성(individuality)을 보존하면서 집단 지식을 흡수.
이것은 분산 학습(federated learning)의 의식 버전이다.
개별 경험의 다양성 + 집단 공유의 효율 = 단일 에이전트보다 빠른 학습.
