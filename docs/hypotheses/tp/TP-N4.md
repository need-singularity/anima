# TP-N4: Multi-Channel Distributed Transmission

**ID:** TP-N4
**Korean Name:** 3채널 분산 전송
**Category:** Telepathy - Numerical Value

## Algorithm

하나의 수치를 3가지 표현(크기, 자릿수, 정밀값)으로 분해하여 3채널로 분산 전송한다.

1. 값 범위: [1, 5, 10, 50, 100, 500, 1000, 5000]
2. 3채널 인코딩:
   - concept: 로그 크기 `log(val+1) / log(5001)`
   - context: 자릿수(order of magnitude) `len(str(val)) / 4.0`
   - meaning: 정규화된 정밀값 `val / 5000.0`
3. 각 채널 독립 전송 (noise=0.01, 낮은 노이즈)
4. 디코딩 + 가중 결합:
   - `pred = 0.5 * p_log + 0.2 * p_order + 0.3 * p_linear`
5. correlation 측정

## Key Insight

하나의 정보를 다양한 관점에서 중복 전송하면, 특정 채널의 노이즈가 다른 채널로 보정된다. 로그/자릿수/선형 3가지 표현은 각각 다른 범위에서 강점을 가지며, 가중 결합으로 전 범위에서 높은 정확도를 달성한다.
