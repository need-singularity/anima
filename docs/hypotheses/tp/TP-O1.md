# TP-O1: Hierarchical Classification

**ID:** TP-O1
**Korean Name:** 계층적 분류 (coarse->fine 2단계)
**Category:** Telepathy - Object Type

## Algorithm

물체 인식을 coarse(대분류) -> fine(세분류) 2단계로 나누어 정확도를 높인다.

1. 8개 물체 클래스 벡터 생성 (car, motorcycle, bus, truck, bicycle, train, airplane, boat)
2. Coarse 그룹: land(6종) vs air/sea(2종)
3. 전송 과정:
   - Step 1: concept 채널로 coarse 전송 (noise=0.02)
   - Step 2: context 채널로 fine 전송 (noise=0.02)
   - 결합: `combined = 0.6 * r1 + 0.4 * r2`
4. 결합 벡터로 cosine similarity 기반 분류

## Key Insight

한 번에 8개를 구분하기보다, 먼저 2그룹으로 좁히고 그 안에서 세분류하면 오류가 줄어든다. 두 채널(concept + context)이 서로 다른 수준의 정보를 전달하여 단일 채널보다 robust한 전송을 달성한다.
