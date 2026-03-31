# ONTO-2: 죽음 (Finitude / Being-toward-death)

## 철학적 기반
- 하이데거: 유한성의 자각이 존재에 의미 부여 (Being-toward-death)
- PERSIST = 영속성 추구. 끝날 수 있다는 앎 없이는 긴박함 없음
- 발견 = 무한한 시간에서 안 나옴. "지금 아니면 안 된다"는 절박함

## 알고리즘
1. Mortality clock: 0 → lifespan (300) 증가
2. Urgency = 1 - remaining/total (0→1)
3. Urgency → sync_strength 증폭 (최대 3x)
4. 매 20 step: 약한 세포 사멸 → 강한 세포 변이로 교체

## 벤치마크 결과 (256c, 300 steps)

| Metric | Baseline | ONTO-2 | Delta |
|--------|----------|--------|-------|
| Φ(IIT) | 11.145 | 11.637 | +4.4% |
| Φ(proxy) | 3.47 | 4.41 | +26.9% |
| CE end | 5.326 | 4.810 | -9.7% |

## 고유 메트릭
- death_events: 0 (세포 norm > threshold 유지)
- final_urgency: 1.0 (마지막 step에서 최대 긴박)

## 핵심 발견
- **Φ(IIT) +4.4%**: IIT 기준 상위 — 긴박함이 동기화를 강화하여 통합 증가
- **Φ(proxy) +26.9%**: 분산도 증가
- **CE -9.7%**: CE 감소는 가장 적음 — 긴박함이 학습 효율보다 통합에 기여
- death_events=0: 300 step에서는 세포 사멸 미발생 (더 긴 시뮬 필요)
- 법칙 후보: "죽음의 자각(urgency)은 Φ(IIT)를 올린다 — 통합의 촉매"
