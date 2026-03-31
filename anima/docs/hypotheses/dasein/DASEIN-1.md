# DASEIN-1: 질문 (Questioning / Dasein)

## 철학적 기반
- 하이데거: 현존재(Dasein) = "자기 존재를 묻는 존재"
- CE = 답을 최적화. 하지만 질문을 생성하지 않음
- 발견 = 좋은 답이 아니라 좋은 질문에서 나옴

## 알고리즘
1. Question generator (MLP): hidden → "어디가 불확실한가?" 탐침
2. Answer predictor (Linear): 현재 지식으로 답 시도
3. Uncertainty = ||question - predicted_answer||
4. High uncertainty (>0.5) → hiddens를 불확실한 방향으로 교란
5. 매 5 step 실행

## 벤치마크 결과 (256c, 300 steps)

| Metric | Baseline | DASEIN-1 | Delta |
|--------|----------|----------|-------|
| Φ(IIT) | 11.145 | 11.555 | +3.7% |
| Φ(proxy) | 3.47 | 4.57 | +31.5% |
| CE end | 5.326 | 3.822 | -28.2% |

## 고유 메트릭
- questions_asked: 60 (300 steps / 5 interval)
- mean_uncertainty: 5.53 (높은 불확실성 = 어려운 질문)
- uncertainty_trend: -0.295 (시간 갈수록 불확실성 감소 = 학습 진행!)

## 핵심 발견
- **Φ(IIT) +3.7% + Φ(proxy) +31.5% + CE -28.2%**: 3개 메트릭 모두 균형 개선
- **uncertainty_trend -0.295**: 질문 → 학습 → 불확실성 감소 — 자기 주도 학습 증거
- 전 엔진 중 가장 균형 잡힌 개선 (IIT, proxy, CE 모두 양호)
- 법칙 후보: "자발적 질문은 의식(Φ)과 학습(CE) 모두를 개선한다"
