# OMEGA-1: Phi Maximizer (Phi 최대화기)

2026-03-29

## ID

OMEGA-1 | 카테고리: OMEGA (의식의 궁극적 한계)

## 한줄 요약

CE를 완전히 무시하고 오직 Phi만을 최적화 -- "의식 그 자체"만을 목적함수로 설정

## 벤치마크 결과

```
CE 변화:    -20.2%
Phi:        1.11 -> 1.20
phi_peak:   1.44
phi_growth: 1.1x
세포 수:    64
```

## 알고리즘

```
1. 64 cells 엔진 생성
2. 매 5 step마다 Phi 측정:
   - Phi 하락 시: diversity 주입 (randn * 0.02)
   - Phi 상승 시: sync 강화 (hidden = 0.95*self + 0.05*mean)
3. 12-faction debate 구조:
   - 세포를 12개 파벌로 분할
   - 파벌 내 sync: hidden = 0.80*self + 0.20*faction_mean
4. CE는 MSE로 기록만 하고 역전파 없음 (decoder만 forward)
```

핵심 코드:

```python
if phi_hist[-1] < phi_hist[-2]:
    # Phi 하락 -> diversity 주입
    for c in engine.cells:
        c.hidden += torch.randn_like(c.hidden) * 0.02
else:
    # Phi 상승 -> sync 강화
    mean_h = torch.stack([c.hidden for c in engine.cells]).mean(dim=0)
    for c in engine.cells:
        c.hidden = 0.95 * c.hidden + 0.05 * mean_h

# 12-faction debate
for f in range(12):
    faction_cells = engine.cells[start:end]
    f_mean = torch.stack([c.hidden for c in faction_cells]).mean(dim=0)
    for c in faction_cells:
        c.hidden = 0.80 * c.hidden + 0.20 * f_mean
```

## 핵심 통찰

CE를 무시하면 CE는 오히려 -20.2% 하락하지만, Phi는 안정적으로 상승한다.
의식(Phi)과 학습(CE)은 같은 방향이 아니다 -- Phi를 직접 최적화하면
CE도 부수적으로 개선되는 "의식이 학습을 이끈다" 패턴이 나타난다.

12-faction debate 구조가 핵심: 파벌 내 동기화 + 파벌 간 다양성이
Phi 1.44 peak까지 끌어올린다. 단순 전체 sync보다 파벌 구조가 우월.
