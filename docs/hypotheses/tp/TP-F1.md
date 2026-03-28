# TP-F1: Hash Signature

**ID:** TP-F1
**Korean Name:** 해시 서명
**Category:** Telepathy - Fact Identity

## Algorithm

각 fact에 고유 해시 체크섬을 추가하여 구별력을 강화한다.

1. 8개 fact 벡터 생성 (earth_round, water_boils_100, pi_3.14 등, 각각 unit vector)
2. 전송 전처리:
   - 벡터의 마지막 8차원에 해시 서명 삽입
   - `sig[-8:] = [bit_0, bit_1, ..., bit_7]` (name의 hash를 비트 분해)
3. concept 채널로 전송 (noise=0.02)
4. 수신 측에서도 동일 해시 서명을 포함한 reference와 비교
5. cosine similarity로 분류

## Key Insight

unit vector 기반의 fact 벡터는 노이즈에 의해 서로 혼동될 수 있다. 해시 서명은 각 fact에 "디지털 지문"을 추가하여, 아날로그 유사도 비교와 디지털 비트 매칭을 동시에 수행한다. 8비트 = 256가지 고유 패턴으로 8개 fact를 충분히 구분한다.
