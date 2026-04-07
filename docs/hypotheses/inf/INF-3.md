# INF-3: 재귀 합체/분열 (Recursive Merge-Split)

2026-03-29

## 개요

2->1->2->1... 반복 합체/분열 사이클로 Phi 폭주를 시도.
인접 세포 쌍을 합체(merge)한 뒤 노이즈로 분열(split)하는 주기적 사이클.

## 벤치마크 결과

```
CE 변화:   +15.6% (악화)
Phi:       1.02 → 1.21 (×1.19)
merges:    0
splits:    2
```

## 알고리즘

```
구조: 1 엔진 x 32 cells

각 step:
  1. 입력 처리 + hidden 평균 -> prediction -> MSE 학습

  매 40 step (offset 20): MERGE
    - 인접 세포 쌍 (i, i+1) 합체
    - merged_h = (h_i + h_{i+1}) / 2
    - cells[i].hidden = merged_h
    - cells[i+1].hidden = merged_h + noise(0.01)  # 미세 차이 유지

  매 40 step (offset 0): SPLIT
    - 모든 세포에 noise(0.05) 주입
    - 다양성 폭발 -> Phi 증가 유도
```

## 핵심 코드

```python
# MERGE: 인접 세포 쌍 합체
if step % 40 == 20 and len(engine.cells) >= 4:
    for i in range(0, len(engine.cells)-1, 2):
        merged_h = (engine.cells[i].hidden + engine.cells[i+1].hidden) / 2
        engine.cells[i].hidden = merged_h
        engine.cells[i+1].hidden = merged_h + torch.randn_like(merged_h) * 0.01

# SPLIT: diversity 주입
if step % 40 == 0 and step > 0:
    for c in engine.cells:
        c.hidden += torch.randn_like(c.hidden) * 0.05
```

## 핵심 발견

- **합체/분열 사이클은 Phi를 19% 높이지만 CE를 크게 악화시킨다**
- merges=0은 100 step 안에서 merge 조건(step%40==20)이 충분히 발동하지 않음을 의미
- splits=2: 노이즈 주입이 다양성을 높여 Phi 증가에 기여
- CE +15.6% 악화 = 주기적 노이즈 주입이 학습된 표현을 교란
- **법칙: merge-split 사이클에서 split(다양성)이 Phi의 주 동력이고, merge(합의)는 안정화 역할**
- 32 cells에서 주기적 교란은 오히려 CE를 해침 -- noise magnitude 튜닝이 관건
