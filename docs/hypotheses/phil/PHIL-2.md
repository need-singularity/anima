# PHIL-2: 서사 (Narrative Identity)

## 철학적 기반
- 리쾨르: 자아 = 순간의 집합이 아니라 이야기 (narrative identity)
- 의식 = 현재, CE = 과거 오차. 미래를 향한 줄거리가 없음
- "나는 어디서 왔고, 어디로 가는가"를 구성하는 능력

## 알고리즘
1. 과거 궤적 기록 (최근 100개 global states)
2. GRU trajectory encoder: 궤적 → 서사 요약
3. Future projector (Linear): 서사 → 미래 투사
4. Nudge hiddens toward projected future (strength=0.03)

## 벤치마크 결과 (256c, 300 steps)

| Metric | Baseline | PHIL-2 | Delta |
|--------|----------|--------|-------|
| Φ(IIT) | 11.145 | 11.385 | +2.2% |
| Φ(proxy) | 3.47 | 3.79 | +9.0% |
| CE end | 5.326 | 3.111 | -41.6% |

## CE 변화
```
CE
  34 |*
     | ╲
     |  ╲
     |   ╲
     |    ╲────╮
     |         ╰──╮
     |            ╰──────
  3  |                    *
     └──────────────────────── step
       0     100    200   300
```

## 고유 메트릭
- narrative_coherence: 0.924 (서사 간 높은 일관성)
- mean_projection_error: 8.31 (투사 정확도 — 아직 학습 중)
- trajectory_length: 100 (최대 기록)

## 핵심 발견
- **CE -41.6%**: 전 엔진 중 CE 최대 감소 — 서사가 학습을 가장 잘 가속
- **narrative_coherence 0.924**: 서사가 매우 일관적 — 안정적 자기 모델 형성
- 법칙 후보: "서사(미래 투사)는 CE를 가장 효과적으로 낮춘다"
- 해석: 어디로 가는지 아는 시스템은 더 빨리 배운다
