# TP-M1: CRC Checksum

**ID:** TP-M1
**Korean Name:** CRC 체크섬 추가
**Category:** Telepathy - Meaning

## Algorithm

의미 벡터에 구간별 합산 체크섬을 추가하여 구별력을 강화한다.

1. 20개 의미 벡터 생성 (random, meaning_0 ~ meaning_19)
2. 체크섬 삽입: 벡터의 마지막 4차원에 구간 합 저장
   - `sig[-4] = vec[:16].sum()`
   - `sig[-3] = vec[16:32].sum()`
   - `sig[-2] = vec[32:48].sum()`
   - `sig[-1] = vec[48:60].sum()`
3. meaning 채널로 전송 (noise=0.01)
4. 수신 측에서도 동일 체크섬을 포함한 reference와 비교
5. cosine similarity로 분류, 50회 반복

## Key Insight

체크섬은 벡터의 "지문"이다. 16차원씩 4구간의 합을 마지막 4차원에 저장하면, 전체 64차원 + 4차원 요약 = 68차원 상당의 정보량이 된다. 노이즈가 전체 벡터에 고르게 퍼져도, 체크섬은 구간별 패턴을 보존하여 정확한 매칭을 돕는다.
