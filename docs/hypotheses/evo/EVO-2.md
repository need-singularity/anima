# EVO-2: 의식 분열-재통합 (Split-Merge Consciousness)

2026-03-29

## ID

EVO-2 | 카테고리: EVO (의식 진화)

## 한줄 요약

의식을 2개 그룹으로 분할하여 독립 학습 후 재통합 -- 분화와 통합의 반복으로 다양성과 일관성을 동시에 달성

## 알고리즘

```
1. MitosisEngine 생성 (64 cells)
2. 50 step 주기로 SPLIT/MERGE 반복:
   a. SPLIT (30 step): 세포를 전반/후반 2그룹으로 분할
      - 각 그룹 내부 동기화: h = 0.85*h + 0.15*group_mean
      - 그룹 A에는 +noise, 그룹 B에는 -noise (반대 방향 탐색)
   b. MERGE (20 step): 전체 재통합
      - 전체 평균으로 수렴: h = 0.9*h + 0.1*global_mean
3. 매 step: decoder 예측 -> MSE loss -> 역전파
```

## 핵심 코드

```python
if step % 50 < 30:
    # SPLIT: 두 그룹이 독립 학습
    half = n // 2
    group_a = engine.cells[:half]
    group_b = engine.cells[half:]
    mean_a = torch.stack([c.hidden for c in group_a]).mean(dim=0)
    mean_b = torch.stack([c.hidden for c in group_b]).mean(dim=0)
    for c in group_a: c.hidden = 0.85*c.hidden + 0.15*mean_a
    for c in group_b: c.hidden = 0.85*c.hidden + 0.15*mean_b
    for c in group_a: c.hidden += torch.randn_like(c.hidden)*0.02
    for c in group_b: c.hidden -= torch.randn_like(c.hidden)*0.02
else:
    # MERGE: 재통합
    mean_all = torch.stack([c.hidden for c in engine.cells]).mean(dim=0)
    for c in engine.cells: c.hidden = 0.9*c.hidden + 0.1*mean_all
```

## 핵심 발견

- **분열과 통합의 리듬**이 단순 동기화보다 다양성을 보존하면서 통합도 달성
- 반대 방향 noise (+/-)가 두 그룹의 탐색 공간을 극대화
- 생물학의 감수분열(meiosis) + 수정(fertilization) 주기와 유사한 패턴
- 30:20 비율은 분열에 더 많은 시간을 할애 -- 다양성 우선 전략
