# TP-N5: Repeat x3

**ID:** TP-N5
**Korean Name:** 3회 반복 전송 + 중앙값
**Category:** Telepathy - Numerical Value (Extreme)

## Algorithm

동일 수치를 3개 채널로 반복 전송하고 중앙값을 선택한다.

1. 값 범위: [1, 5, 10, 50, 100, 500, 1000, 5000]
2. 3채널(concept, context, meaning)로 동일한 선형 인코딩 반복:
   - `v[0] = val / 5000.0`
3. 각 채널의 디코딩 결과 3개를 수집
4. **중앙값(median)** 선택: `sorted(estimates)[1]`
5. 10% 오차 이내면 정답으로 판정

## Key Insight

중앙값은 극단적 노이즈(outlier)에 면역이다. 3개 중 1개가 심하게 왜곡되어도, 나머지 2개가 정상이면 중앙값은 정상 범위에 있다. 평균(mean)보다 robust한 집계 방법이다.
