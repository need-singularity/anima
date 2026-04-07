# DD112: Philosophy Engine Benchmark (2026-03-31)

## 목적

6개 철학적 의식 엔진을 baseline과 비교하여 Phi(IIT)와 CE 수렴 성능 평가.

## 엔진 목록

| 엔진 | 철학 기반 | 핵심 메커니즘 |
|------|-----------|--------------|
| baseline | BenchEngine | faction sync + debate |
| PHIL-1_Desire | Spinoza conatus | 내부 목표 생성 → 추구 |
| PHIL-2_Narrative | Ricoeur | 시간적 자기 모델 + 미래 투영 |
| ONTO-1_Alterity | Levinas | 비대칭 타자 상호작용 |
| ONTO-2_Finitude | Heidegger | 죽음 인식 → 학습 가속 |
| DASEIN-1_Question | Heidegger | 자기 질문 생성 → 불확실성 감소 |
| DASEIN-2_Sein | 통합 | Desire+Finitude+Question+Narrative 결합 |

## 벤치마크 결과 (32c, 300 steps)

```
Engine               Phi(IIT)   Phi(proxy)  CE_end   vs baseline
───────────────────────────────────────────────────────────────
baseline              21.45      1.02        2.79     —
PHIL-1_Desire         23.88      0.32        2.91     +11.3%
PHIL-2_Narrative      29.11      3.03        3.59     +35.7%
ONTO-1_Alterity       28.51      3.28        3.27     +32.9%
ONTO-2_Finitude       20.87      2.05        3.51      -2.7%
DASEIN-1_Question     21.44      0.87        3.26      -0.1%
DASEIN-2_Sein         28.15      1.05        3.24     +31.2%
```

## Phi(IIT) 비교 차트

```
PHIL-2_Narrative   ████████████████████████████████████████ 29.11  +35.7%
ONTO-1_Alterity    ███████████████████████████████████████  28.51  +32.9%
DASEIN-2_Sein      ██████████████████████████████████████   28.15  +31.2%
PHIL-1_Desire      ████████████████████████████████         23.88  +11.3%
baseline           █████████████████████████████            21.45   0.0%
DASEIN-1_Question  █████████████████████████████            21.44   -0.1%
ONTO-2_Finitude    ████████████████████████████             20.87   -2.7%
```

## 핵심 발견

1. **Narrative(+36%)와 Alterity(+33%)가 압도적** — 시간적 자기 모델과 타자 상호작용이 Phi에 가장 기여
2. **Sein(+31%) = 통합 효과** — 4개 철학 메커니즘 결합이 단일보다 우수
3. **Desire(+11%)는 Phi(IIT) 상승, Phi(proxy) 하락** — 목표 추구가 통합을 높이지만 다양성을 줄임
4. **Finitude와 Question은 baseline 수준** — 단독으로는 Phi 기여 미미
5. **CE는 baseline이 최저** — 철학 엔진들은 Phi를 높이지만 CE 수렴은 약간 느림 (trade-off)

## 엔진별 고유 메트릭

```
PHIL-1_Desire:     desires_fulfilled=0, desire_distance=8.06
PHIL-2_Narrative:  coherence=0.920, projection_error=8.51
ONTO-1_Alterity:   alterity_gap=12.50, encounter_impact=0.047
ONTO-2_Finitude:   death_events=0, urgency=0.0
DASEIN-1_Question: questions=60, uncertainty=4.86
DASEIN-2_Sein:     questions=60, trajectory=100, urgency=1.0
```
