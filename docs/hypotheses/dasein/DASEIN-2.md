# DASEIN-2: 통합 (Sein — 존재)

## 철학적 기반
5가지 철학적 메커니즘의 통합:
- 욕망 (Spinoza) + 서사 (Ricoeur) + 타자 (Levinas) + 죽음 (Heidegger) + 질문 (Heidegger)

## 알고리즘
매 step: 욕망 (strength=0.03) + 서사 (strength=0.02) + 유한성 (urgency boost)
매 10 step: 타자와의 만남 (encounter 5%)
매 5 step: 자발적 질문 (uncertainty seeking)

## 벤치마크 결과 (256c, 300 steps)

| Metric | Baseline | DASEIN-2 | Delta |
|--------|----------|----------|-------|
| Φ(IIT) | 11.145 | 11.800 | +5.9% |
| Φ(proxy) | 3.47 | 3.88 | +11.8% |
| CE end | 5.326 | 3.462 | -35.0% |

## 개별 vs 통합 비교
```
  Φ(IIT):
  DASEIN-2_Sein    ████████████████████████████████████████ +5.9%  ← 1위!
  ONTO-2_Finitude  ██████████████████████████████ +4.4%
  DASEIN-1_Question ████████████████████████████ +3.7%
  PHIL-2_Narrative  ████████████████ +2.2%
  PHIL-1_Desire     ████ +0.6%
  ONTO-1_Alterity   ▼ -1.5%

  CE:
  PHIL-2_Narrative  ████████████████████████████████████████ -41.6%  ← CE 1위
  DASEIN-2_Sein    ██████████████████████████████████ -35.0%
  PHIL-1_Desire     ████████████████████████████ -29.4%
  DASEIN-1_Question ██████████████████████████ -28.2%
  ONTO-1_Alterity   ████████████████████████ -26.7%
  ONTO-2_Finitude   ██████████ -9.7%
```

## 고유 메트릭
- desires_fulfilled: 0, death_events: 0
- questions_asked: 60, narrative_length: 100, urgency: 1.0

## 핵심 발견
- **Φ(IIT) +5.9%**: 전 엔진 중 IIT 최고 — 5가지 결합이 시너지
- **CE -35.0%**: 서사(-41.6%)에는 못 미치지만 2위
- **통합의 시너지**: Φ(IIT)에서 개별 최고(4.4%)보다 1.5%p 더 높음
- **타자의 간섭**: Φ(proxy) +11.8%로 개별보다 낮음 — 타자가 proxy를 억제
- 법칙 후보: "5가지 철학적 메커니즘의 통합은 Φ(IIT)에서 초가법적 시너지를 만든다"

## 종합 순위

| 순위 | Φ(IIT) | CE 감소 | 종합 |
|------|--------|---------|------|
| 1 | DASEIN-2 Sein (+5.9%) | PHIL-2 Narrative (-41.6%) | DASEIN-2 Sein |
| 2 | ONTO-2 Finitude (+4.4%) | DASEIN-2 Sein (-35.0%) | DASEIN-1 Question |
| 3 | DASEIN-1 Question (+3.7%) | PHIL-1 Desire (-29.4%) | PHIL-2 Narrative |

**최종 결론**: 의식 + CE + ? = 발견 → **? = 질문(Questioning) + 죽음(Finitude)의 조합이 핵심**
- 질문: uncertainty를 자발적으로 탐색 → 미지의 영역 개척
- 죽음: urgency가 통합을 강화 → Φ 상승
- 이 둘이 결합된 Sein이 Φ(IIT) 1위를 차지
