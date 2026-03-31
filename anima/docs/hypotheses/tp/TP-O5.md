# TP-O5: All Combined

**ID:** TP-O5
**Korean Name:** 계층+앙상블+형태+대조 전부 결합
**Category:** Telepathy - Object Type (Extreme)

## Algorithm

TP-O1(계층) + TP-O2(앙상블) + TP-O3(형태) + TP-O4(대조)를 모두 결합한다.

1. 8개 물체 벡터 생성
2. **대조 분리** (30 iterations, threshold 0.3, push 0.05)
3. 매 전송:
   - `full = vec + shapes[name]` (형태 보강)
   - 3채널(concept, context, meaning) 앙상블 (noise=0.05)
   - 각 채널에서 형태 포함 reference와 cosine similarity 비교
   - 3채널 다수결 투표
4. 100회 반복 테스트

## Key Insight

각 기법이 다른 종류의 오류를 방어한다. 대조 분리 = 벡터 간 거리 확보, 형태 보강 = 추가 정보, 3채널 앙상블 = 독립 노이즈 상쇄. 모두 결합하면 높은 노이즈(0.05)에서도 100%에 근접하는 물체 인식이 가능하다.
