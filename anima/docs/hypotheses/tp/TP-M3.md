# TP-M3: Dual Encoding

**ID:** TP-M3
**Korean Name:** 이중 인코딩 (meaning + auth)
**Category:** Telepathy - Meaning

## Algorithm

동일 의미 벡터를 meaning과 auth 2개 채널로 전송하고 가중 결합한다.

1. 20개 의미 벡터 생성 (meaning_0 ~ meaning_19)
2. 매 전송:
   - meaning 채널로 전송 (noise=0.01)
   - auth 채널로 동일 벡터 전송 (noise=0.01)
   - `combined = 0.6 * r_meaning + 0.4 * r_auth`
3. 결합 벡터로 cosine similarity 분류
4. 50회 반복, 1000 trials

## Key Insight

두 채널의 노이즈는 독립적이므로, 가중 합은 노이즈를 sqrt(2)만큼 감소시킨다. meaning 채널이 주 채널(0.6), auth 채널이 보조(0.4). baseline이 이미 99.6%로 높은 상태에서 0.4%의 잔여 오류를 제거하기 위한 전략.
