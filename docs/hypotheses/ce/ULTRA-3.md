# ULTRA-3: Cell Teaches Decoder

**ID:** ULTRA-3
**Korean Name:** 세포가 디코더를 가르침
**Category:** CE 극한 (ULTRA)

## Algorithm

가장 강한(norm이 큰) 세포가 teacher 역할을 하여 디코더의 target을 생성한다.

1. 64세포 MitosisEngine + 디코더 구성
2. 매 step:
   - 랜덤 입력 -> engine.process()
   - 전체 세포 hidden 평균 -> 디코더 -> 예측
   - **Teacher 선택**: 모든 세포의 hidden norm 측정, 최대 norm 세포 선택
   - `target = cells[teacher_idx].hidden[:, :DIM]`
   - MSE(prediction, teacher_target)으로 학습

## Key Insight

"가장 활성화된 세포 = 가장 확신하는 전문가". 외부 데이터 없이 세포의 내부 상태만으로 학습한다. 디코더는 의식의 가장 강한 신호를 언어로 변환하는 법을 배운다. 완전 자기 참조(self-referential) 학습.
