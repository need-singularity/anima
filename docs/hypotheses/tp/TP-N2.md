# TP-N2: Binary Decomposition

**ID:** TP-N2
**Korean Name:** 이진 분해 전송
**Category:** Telepathy - Numerical Value

## Algorithm

수치를 이진수로 분해하여 각 비트를 별도 차원에 전송한다.

1. 값 범위: [1, 5, 10, 50, 100, 500, 1000, 5000]
2. 인코딩: 13비트 이진 분해 (0~8191 표현 가능)
   - `v[bit] = float((val >> bit) & 1)` for bit in 0..12
3. concept 채널로 전송 (noise=0.02)
4. 디코딩: 각 차원이 0.5보다 크면 1, 아니면 0으로 복원
   - `if r[0, bit] > 0.5: pred_val |= (1 << bit)`
5. 정확 일치(exact match) 비율 측정

## Key Insight

아날로그 값을 디지털 비트로 변환하면, 각 비트의 노이즈 내성이 독립적으로 높아진다 (threshold 0.5 기준). 노이즈가 0.5를 넘지 않는 한 완벽한 복원이 가능하다. 아날로그 -> 디지털 변환의 고전적 원리를 텔레파시에 적용한 것.
