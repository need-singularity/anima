# TP-N1: Log Scale Transmission

**ID:** TP-N1
**Korean Name:** 로그 스케일 전송
**Category:** Telepathy - Numerical Value

## Algorithm

수치를 로그 스케일로 변환하여 전송함으로써 넓은 범위의 값을 균일하게 표현한다.

1. 값 범위: [1, 5, 10, 50, 100, 500, 1000, 5000]
2. 인코딩: `v[0] = log(val + 1) / log(5001)` (0~1로 정규화)
3. concept 채널로 전송 (noise=0.02)
4. 디코딩: `pred = exp(r[0] * log(5001)) - 1`
5. 50회 반복, correlation 측정

## Key Insight

선형 정규화(val/5000)는 작은 값(1, 5, 10)을 0에 가깝게 압축하여 노이즈에 취약하게 만든다. 로그 스케일은 모든 크기의 값을 균일하게 분포시킨다. 1->5와 1000->5000의 차이가 비슷한 크기로 표현되어, Weber-Fechner 법칙(인간의 감각도 로그 스케일)과 일치한다.
