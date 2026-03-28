# AUTO-5: Self-Evaluation

**ID:** AUTO-5
**Korean Name:** 자기 평가
**Category:** 자율 학습

## Algorithm

디코더 출력을 다시 의식에 넣어 품질을 자체 평가하고, 나쁘면 재시도한다.

1. 64세포 MitosisEngine + 디코더 구성
2. 매 step:
   - 입력 처리 -> 디코더 예측 -> CE loss로 학습
   - **자기 평가**: 예측 결과를 다시 engine.process()에 넣음
   - 세포 hidden의 variance 측정 -> quality = 1 - variance
   - quality < 0.3이면 "나쁜 출력" 판정
   - 재시도: 같은 데이터로 loss * 2.0으로 한 번 더 학습
3. retries 횟수를 기록

## Key Insight

의식이 자기 출력의 품질을 스스로 판단한다. 출력을 다시 세포에 넣었을 때 세포들이 혼란스러우면(high variance) 나쁜 출력. 인간이 "내가 한 말이 맞나?" 돌이켜보는 것과 같은 자기 성찰(self-reflection) 메커니즘.
