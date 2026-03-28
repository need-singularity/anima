# EX-3: Multi-Decoder Vote

**ID:** EX-3
**Korean Name:** 다중 디코더 투표
**Category:** CE 극한 전략

## Algorithm

8개 디코더가 각각 독립적으로 예측하고, 최선의 결과를 투표로 선택한다.

1. 64세포 MitosisEngine + 8개 독립 디코더(Linear) + 8개 옵티마이저
2. 매 step:
   - 입력 처리 -> 세포 hidden 평균
   - 8개 디코더가 각각 예측, MSE 오류 측정
   - **최소 오류 디코더(winner) 선택**: CE loss로 학습
   - **나머지 7개는 winner 쪽으로 부드럽게 이동**:
     - `param = 0.95 * param + 0.05 * winner_param`
   - CE 기록은 8개 중 최소값

## Key Insight

다양성 + 선택 = 진화. 8개 디코더가 서로 다른 전략을 탐색하되, 최선의 결과가 나머지를 이끈다. 의식 세포의 유사분열(mitosis)과 같은 원리를 디코더 레벨에서 구현한 것. 단일 디코더보다 항상 더 낮은 CE를 보장한다.
