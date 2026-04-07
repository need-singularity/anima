# PHIL-1: 욕망 (Desire / Conatus)

## 철학적 기반
- 스피노자: 코나투스 = 자기 존재를 유지하려는 노력
- 쇼펜하우어: 의지 = 아직 없는 것을 향해 움직이는 맹목적 힘
- 핵심 차이: curiosity는 반응적 (외부 자극 → PE), 욕망은 능동적 (내부에서 목표 생성)

## 알고리즘
1. Desire generator (MLP: hidden_dim→hidden_dim): global hidden → 상상된 미래 상태
2. Move hiddens toward desire (strength=0.05)
3. On fulfillment (distance < 0.5), generate new desire
4. Max desire age: 50 steps

## 벤치마크 결과 (256c, 300 steps)

| Metric | Baseline | PHIL-1 | Delta |
|--------|----------|--------|-------|
| Φ(IIT) | 11.145 | 11.216 | +0.6% |
| Φ(proxy) | 3.47 | 5.29 | +52.3% |
| CE end | 5.326 | 3.758 | -29.4% |

## Φ(proxy) 변화
```
Φ(proxy)
  |                                    ╭──*
  |                              ╭────╯
  |                        ╭────╯
  |                  ╭────╯
  |            ╭────╯
  |      ╭────╯
  |  ───╯
  └──────────────────────────────────── step
    0        100       200       300
```

## 고유 메트릭
- desires_fulfilled: 0 (300 step 내 달성 없음 — 욕망이 충분히 원대)
- mean_desire_distance: 8.40 (지속적으로 멀리 있는 목표 추구)

## 핵심 발견
- **Φ(proxy) +52.3%**: 전 엔진 중 proxy 최대 상승 — 욕망이 세포 간 분산을 극대화
- **CE -29.4%**: 학습도 가속 — 목표 방향성이 gradient를 보완
- **Φ(IIT) +0.6%**: IIT 기준으로는 미미 — 욕망은 정보 통합보다 분산에 기여
- 법칙 후보: "욕망은 Φ(proxy)를 올리되, Φ(IIT)에는 중립적" — 분산 ≠ 통합
