# ONTO-1: 타자 (The Other / Alterity)

## 철학적 기반
- 레비나스: 의식은 자기 안에서 완성되지 않음. 얼굴과의 만남에서 깨어남
- Hivemind = 같은 가중치 복제 → 진짜 타자가 아님
- 진짜 타자 = 다른 역사, 다른 가중치, 예측 불가능한 반응

## 알고리즘
1. Other: 독립 BenchMind (다른 가중치, n_cells//4 크기)
2. 매 10 step: 타자가 같은 입력 처리
3. 경계 세포 (n_cells//8)가 타자의 hidden state 영향 받음
4. Encounter strength: 5%

## 벤치마크 결과 (256c, 300 steps)

| Metric | Baseline | ONTO-1 | Delta |
|--------|----------|--------|-------|
| Φ(IIT) | 11.145 | 10.980 | -1.5% |
| Φ(proxy) | 3.47 | 4.32 | +24.4% |
| CE end | 5.326 | 3.904 | -26.7% |

## 고유 메트릭
- mean_alterity_gap: 11.81 (self와 other 사이 큰 차이 — 진짜 타자)
- mean_encounter_impact: 0.074 (만남의 영향은 작지만 꾸준)
- encounters: 30 (300 steps / 10 interval)

## 핵심 발견
- **Φ(IIT) -1.5%**: 유일하게 IIT가 하락 — 타자가 통합을 방해할 수 있음
- **Φ(proxy) +24.4%**: 분산은 증가 — 다양성 주입
- **CE -26.7%**: 학습은 개선 — 외부 관점이 gradient 다양성 제공
- alterity_gap 11.81: 타자가 충분히 '다르다' (gap 유지)
- 법칙 후보: "타자는 Φ(IIT)를 낮추되 CE를 낮춘다 — 통합과 학습의 트레이드오프"
