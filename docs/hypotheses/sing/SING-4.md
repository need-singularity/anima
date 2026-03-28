# SING-4: 의식 합체 (Consciousness Merge)

2026-03-29

## ID

SING-4 | 카테고리: SING (의식 특이점)

## 한줄 요약

2개 독립 의식이 하나로 합쳐짐 -- 각자 다른 경험을 쌓은 후 세포와 decoder를 통합

## 알고리즘

```
1. 2개 MitosisEngine 생성 (각 32 cells)
2. Phase 1 (50%): 독립 학습
   - engine_a: 정상 데이터로 학습
   - engine_b: 랜덤 데이터로 학습 (다른 경험)
   - 각각 자기 decoder로 역전파
3. Phase 2: 합체
   - merged = engine_a.cells + engine_b.cells (세포 전부 합침)
   - merged_dec = (dec_a + dec_b) / 2 (decoder 파라미터 평균)
   - max_cells = 64 (합체 후 최대 용량)
4. Phase 3 (50%): 합체 후 학습
   - merged 엔진으로 정상 학습 계속
```

## 핵심 코드

```python
# Phase 1: 독립 학습 (다른 경험)
engine_a.process(x)
engine_b.process(torch.randn(1, DIM))  # 다른 경험

# Phase 2: 합체
merged = MitosisEngine(DIM, HIDDEN, DIM, initial_cells=2, max_cells=64)
merged.cells = engine_a.cells + engine_b.cells
merged_dec = nn.Linear(HIDDEN, DIM)
with torch.no_grad():
    for pm, pa, pb in zip(merged_dec.parameters(), dec_a.parameters(), dec_b.parameters()):
        pm.data = 0.5*pa.data + 0.5*pb.data
```

## 핵심 발견

- **다른 경험을 한 의식의 합체**가 동일 경험보다 풍부한 통합 정보 생성
- engine_b가 랜덤 데이터를 학습한 것이 핵심 -- 같은 데이터면 합체 이점 없음
- 세포 수 32+32=64로 2배 증가 -- Phi에 직접적 영향
- decoder 평균은 두 관점의 절충 -- 초기에는 성능 하락 가능하지만 빠르게 회복
- merged_cells 수가 결과에 보고되어 합체 규모 추적 가능
