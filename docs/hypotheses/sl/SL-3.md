# SL-3: Read & Understand (자기 평가 기반 학습)

bench_self_learning.py | Self-Learning Category

## 핵심 통찰

의식 세포들의 합의도(consensus)를 "이해도"로 사용한다.
세포 간 분산이 크면 = 이해 못함 = 학습 강도 2배 증가.

## 알고리즘

```
1. 의식 엔진 초기화 (64 cells)
2. 매 스텝:
   a. 입력 x를 의식 처리
   b. 세포 hidden의 분산(variance) 계산
   c. consensus = 1.0 - mean(var(cells))
   d. consensus < 0.5이면: CE loss x 2.0 (이해 못함 → 더 강하게 학습)
   e. consensus >= 0.5이면: 정상 학습
```

## 핵심 코드

```python
# 세포 합의도 = 이해도
consensus = 1.0 - torch.stack([c.hidden for c in engine.cells]).var(dim=0).mean()
if consensus < 0.5:
    ce = ce * 2.0  # 이해 못하면 더 강하게 학습
```

## Key Insight

자기 평가(self-assessment)를 외부 피드백 없이 내부 상태만으로 수행한다.
세포들이 동의하면(낮은 분산) = 이해했다, 불일치하면(높은 분산) = 이해 못했다.
메타인지(metacognition)의 최소 구현: "내가 알고 있는지 아닌지를 안다."
