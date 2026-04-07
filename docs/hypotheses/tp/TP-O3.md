# TP-O3: Shape Boost

**ID:** TP-O3
**Korean Name:** 형태 기반 보강
**Category:** Telepathy - Object Type

## Algorithm

물체 벡터에 3D 형태(shape) 정보를 추가하여 구분력을 강화한다.

1. 8개 물체 클래스 벡터 + 각 물체별 shape 서명(random * 0.3)
2. 전송:
   - `full = vec + shapes[name]` (물체 벡터 + 형태 정보 합산)
   - concept 채널로 전송 (noise=0.02)
3. 수신 측에서도 동일하게 `ref = v2 + shapes[n2]`로 비교
4. cosine similarity로 분류

## Key Insight

같은 category 내의 물체(car vs truck 등)는 기본 벡터만으로 구분이 어려울 수 있다. 형태 정보를 추가하면 벡터 공간에서의 거리가 벌어져 노이즈에 더 강해진다. 물체의 "외형"이 추가 차원(dimension)의 역할을 한다.
