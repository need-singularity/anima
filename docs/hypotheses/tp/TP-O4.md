# TP-O4: Contrastive Learning

**ID:** TP-O4
**Korean Name:** 대조 학습 분리
**Category:** Telepathy - Object Type (Extreme)

## Algorithm

비슷한 물체 쌍을 대조 학습으로 벡터 공간에서 밀어내어 분리한다.

1. 8개 물체 클래스 벡터 생성
2. **대조 분리** (50 iterations):
   - 모든 쌍의 cosine similarity 측정
   - similarity > 0.5인 쌍: 서로 반대 방향으로 밀어냄
   - `objs[n1] += (v1 - v2) * 0.1`
   - `objs[n2] += (v2 - v1) * 0.1`
3. 분리된 벡터로 전송 테스트 (높은 noise=0.05)
4. concept 채널, cosine similarity 분류

## Key Insight

원본 벡터의 유사도가 높으면 노이즈에 취약하다. 대조 학습으로 모든 클래스를 벡터 공간에서 최대한 분리하면, 더 높은 노이즈(0.05)에서도 정확한 분류가 가능하다. 전송 전에 "코드북을 최적화"하는 전략.
