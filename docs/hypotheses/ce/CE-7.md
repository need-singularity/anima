# CE-7: Dialogue Fine-Tune

**ID:** CE-7
**Korean Name:** 대화 미세조정
**Category:** CE Optimization

## Algorithm

질문-답변(Q/A) 쌍으로 대화 특화 학습을 수행한다.

1. 64개 세포 MitosisEngine 구성 + warm-up
2. 대화 데이터 생성: Q(질문)에서 A(답변) = Q * 0.5 + noise * 0.3 (질문과 관련된 답변)
3. 높은 학습률(5e-3) 사용 (일반 CE의 3e-3보다 높음)
4. 매 step:
   - 질문 입력 -> 세포 처리 -> hidden 평균 -> 디코더 -> 답변 예측
   - MSE loss로 학습
5. Φ 보존 기준: Φ_after > Φ_before * 50%

## Key Insight

대화는 일반 텍스트보다 구조적(Q->A 매핑). 높은 학습률로 빠르게 수렴 가능하며, Q/A 관계가 명확하므로 디코더가 "의식의 의도를 언어로 변환"하는 능력을 효율적으로 학습한다.
