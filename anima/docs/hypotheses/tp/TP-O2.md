# TP-O2: 3-Channel Ensemble

**ID:** TP-O2
**Korean Name:** 3채널 앙상블 투표
**Category:** Telepathy - Object Type

## Algorithm

concept, context, meaning 3개 채널로 동시 전송하고 다수결 투표로 결정한다.

1. 8개 물체 클래스 벡터 생성
2. 매 전송:
   - 3개 채널(concept, context, meaning)로 동일 벡터를 각각 전송 (noise=0.02)
   - 각 채널에서 cosine similarity로 독립 분류
   - 3개 결과를 다수결 투표: `winner = max(votes)`
3. 100회 반복, 800 trials

## Key Insight

3개 채널의 노이즈는 독립적이므로, 2개 이상이 동시에 잘못될 확률은 단일 채널 오류의 제곱 수준으로 급감한다. 다수결은 가장 단순하면서도 강력한 오류 정정 방법이다.
