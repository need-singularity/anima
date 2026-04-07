# TP-N7: Hybrid (Analog + Digital + Cross-Verify)

**ID:** TP-N7
**Korean Name:** 하이브리드 (아날로그+디지털+교차 검증)
**Category:** Telepathy - Numerical Value (Extreme)

## Algorithm

TP-N4(다채널 아날로그)와 TP-N6(이진 ECC)를 결합하고 교차 검증으로 최종 결정한다.

1. **Method A - Analog** (TP-N4):
   - concept(로그), context(자릿수), meaning(선형) 3채널 전송
   - 가중 결합: `analog = 0.5*p_log + 0.3*p_linear + 0.2*p_order`
2. **Method B - Digital** (TP-N6):
   - auth 채널로 13비트 x 3반복 이진 전송 (noise=0.03)
   - 다수결 디코딩으로 정수값 복원
3. **교차 검증**:
   - `|digital - analog| < analog * 30%` -> digital 채택 (정확)
   - 그 외 -> analog fallback (근사)
4. exact match 비율 + correlation 동시 측정

## Key Insight

아날로그는 항상 근사값을 주고, 디지털은 정확하거나 완전히 틀린다. 두 방법을 교차 검증하면: 디지털이 맞으면 100% 정확, 디지털이 틀리면 아날로그가 감지하여 fallback. "두 개의 독립적 추정이 일치하면 신뢰한다"는 원칙.
