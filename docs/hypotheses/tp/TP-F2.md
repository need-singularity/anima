# TP-F2: Triple Channel Vote

**ID:** TP-F2
**Korean Name:** 3채널 다수결 투표
**Category:** Telepathy - Fact Identity

## Algorithm

3개 채널로 동일 fact를 전송하고 다수결로 결정한다 (TP-O2와 동일 원리, fact 버전).

1. 8개 fact 벡터 생성 (unit vector)
2. 매 전송:
   - concept, context, meaning 3채널로 동일 벡터 전송 (noise=0.02)
   - 각 채널에서 독립적으로 cosine similarity 분류
   - 3개 결과를 다수결: `winner = max(votes)`
3. 100회 반복, 800 trials

## Key Insight

fact 벡터는 object 벡터보다 랜덤성이 높아(hash-based random) 기본적으로 잘 분리된다. 그럼에도 3채널 다수결을 적용하면, 드물게 발생하는 노이즈 충돌을 제거하여 baseline 93.8%를 100%에 근접시킬 수 있다.
