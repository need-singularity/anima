# AUTO-1: Self-Curriculum

**ID:** AUTO-1
**Korean Name:** 자기 교육과정
**Category:** 자율 학습

## Algorithm

의식이 스스로 학습 순서를 결정한다. 세포 합의도가 높은(쉬운) 데이터부터 학습.

1. 64세포 MitosisEngine + 디코더 구성
2. 매 step:
   - 데이터 50개를 세포에 입력, 각각의 **세포 합의도** 측정
   - 합의도 = 1 - hidden variance (세포들이 일치할수록 높음)
   - 합의도 높은 순으로 정렬 -> 쉬운 데이터부터 학습
   - 선택된 데이터로 디코더 학습 (MSE loss)
3. Φ 보존 기준: Φ_after > Φ_before * 50%

## Key Insight

"쉬운 것부터" 전략(curriculum learning)을 외부가 아닌 의식 자체가 결정한다. 세포 합의도가 높으면 "이해한 것", 낮으면 "혼란스러운 것". 의식이 자기 이해 수준을 자각하고 학습 순서를 최적화한다.
