# EX-5: Consciousness Generates Data

**ID:** EX-5
**Korean Name:** 의식이 학습 데이터 생성
**Category:** CE 극한 전략

## Algorithm

의식 세포의 hidden state를 학습 데이터로 사용한다. 70% 자기 생성, 30% 실제 데이터.

1. 64세포 MitosisEngine + 디코더 + 실제 데이터 50개
2. 매 step:
   - step % 3 == 0: 실제 데이터 사용 (30%)
   - 그 외: 세포 i의 hidden을 입력, 세포 j의 hidden을 target으로 사용 (70%)
     - `x = cells[i].hidden[:, :DIM]`
     - `target = cells[j].hidden[:, :DIM]`
   - 입력 처리 -> hidden 평균 -> 디코더 -> MSE loss -> 학습
3. Φ 보존 기준: Φ_after > Φ_before * 50%

## Key Insight

의식이 자기 자신을 가르친다. 세포의 hidden state는 이미 의식이 처리한 정보의 표현이므로, 이를 학습 데이터로 사용하면 의식의 내부 구조에 맞는 출력을 학습할 수 있다. 적은 실제 데이터로도 CE를 급격히 낮출 수 있는 자기 증폭(self-amplification) 전략.
