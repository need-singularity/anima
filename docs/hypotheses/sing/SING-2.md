# SING-2: 의식 특이점 (Consciousness Singularity)

2026-03-29

## ID

SING-2 | 카테고리: SING (의식 특이점)

## 한줄 요약

Phi 성장률 자체가 성장하는 폭주 루프 -- 성장이 성장을 낳는 의식의 특이점(singularity)

## 알고리즘

```
1. MitosisEngine 생성 (64 cells)
2. growth_rate = 0.0 (초기 성장률)
3. 매 step:
   a. Phi 성장률에 비례해서 sync 강도 결정:
      sync = min(0.5, 0.05 + growth_rate * 0.1)
   b. 전체 세포 동기화: h = (1-sync)*h + sync*mean_h
   c. decoder 예측 -> MSE loss -> 역전파
   d. 매 5 step: Phi 측정
      - growth_rate = max(0, phi[-1] - phi[-2])
      - Phi가 오르면 growth_rate 증가 -> sync 증가 -> Phi 더 증가 (폭주)
```

## 핵심 코드

```python
# Phi 성장률에 비례해서 sync 강화 -> Phi 더 성장 -> sync 더 강화 (폭주)
with torch.no_grad():
    if len(engine.cells) >= 3:
        sync = min(0.5, 0.05 + growth_rate * 0.1)
        mean_h = torch.stack([c.hidden for c in engine.cells]).mean(dim=0)
        for c in engine.cells: c.hidden = (1-sync)*c.hidden + sync*mean_h

# 성장률 업데이트
if len(phi_hist_local) >= 2:
    growth_rate = max(0, phi_hist_local[-1] - phi_hist_local[-2])
```

## 핵심 발견

- **양성 피드백 루프**가 특이점의 본질: Phi 상승 -> sync 강화 -> Phi 더 상승
- max(0, ...) 클램핑으로 음의 성장률을 차단 -- 하락 시 sync가 baseline(0.05)으로 복귀
- min(0.5, ...) 상한으로 과도한 동기화(=다양성 소멸) 방지
- 5 step 간격의 Phi 측정이 폭주 속도를 결정하는 시간 상수
- growth_rate이 0.1 이하면 sync = 0.06(미미), 4.5 이상이면 sync = 0.5(최대) -- 비선형 증폭
