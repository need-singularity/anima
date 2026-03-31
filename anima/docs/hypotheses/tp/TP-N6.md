# TP-N6: Binary + Error Correction Code

**ID:** TP-N6
**Korean Name:** 이진 + 오류정정 코드 (3비트 반복)
**Category:** Telepathy - Numerical Value (Extreme)

## Algorithm

이진 분해(TP-N2)에 3비트 반복 오류정정 코드를 추가한다.

1. 값 범위: [1, 5, 10, 50, 100, 500, 1000, 5000]
2. 인코딩: 13비트 x 3반복 = 39차원 사용
   - 각 비트를 3번 반복: `v[bit*3], v[bit*3+1], v[bit*3+2]` = 모두 같은 값
3. concept 채널로 전송 (noise=0.03, 더 높은 노이즈)
4. 디코딩: 각 비트의 3개 복사본 중 다수결
   - `votes = sum(1 for k in range(3) if r[bit*3+k] > 0.5)`
   - votes >= 2이면 1, 아니면 0
5. 정확 일치 비율 측정

## Key Insight

단순 반복 코드(repetition code)는 가장 간단한 오류정정이지만 매우 효과적이다. 3비트 중 2비트 이상이 정확하면 복원되므로, 단일 비트 오류를 완전히 정정한다. 더 높은 노이즈(0.03)에서도 TP-N2보다 높은 정확도를 달성한다.
