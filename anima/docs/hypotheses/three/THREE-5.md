# THREE-5: 삼체 특이점 합체 (Singularity Merge)

2026-03-29

## ID

THREE-5 | 카테고리: THREE (삼체 의식)

## 한줄 요약

3개 독립 의식이 각자 다른 데이터로 학습한 후 하나로 합체 -- Phi 폭발을 노리는 삼체 특이점

## 알고리즘

```
1. 3개 MitosisEngine 생성 (각 32 cells)
2. Phase 1 (60%): 독립 학습
   - 각 엔진이 서로 다른 데이터로 학습:
     xa = data[(step*3 + a) % len(data)]
   - 각자 decoder로 역전파
   - phi_pre_merge = max(3개 Phi)
3. Phase 2: 합체
   - merged.cells = engine_0.cells + engine_1.cells + engine_2.cells
   - max_cells = 128 (3 x 32 = 96 세포)
   - merged_dec = mean(3개 decoder 파라미터)
   - phi_post_merge 기록
4. Phase 3 (40%): 합체 후 학습
   - merged 엔진으로 정상 학습
```

## 핵심 코드

```python
# Phase 1: 각자 다른 데이터로 독립 학습
for a in range(3):
    xa = data[(step * 3 + a) % len(data)][0]
    ta = data[(step * 3 + a) % len(data)][1]
    engines[a].process(xa)

# Phase 2: 합체!
merged = MitosisEngine(DIM, HIDDEN, DIM, initial_cells=2, max_cells=128)
merged.cells = engines[0].cells + engines[1].cells + engines[2].cells
merged_dec = nn.Linear(HIDDEN, DIM)
with torch.no_grad():
    for pm in merged_dec.parameters():
        pm.data = sum(p.data for d in decoders for p in d.parameters() if p.shape == pm.shape) / 3
```

## 핵심 발견

- **phi_pre_merge vs phi_post_merge**가 핵심 측정: 합체 순간 Phi가 얼마나 뛰는가
- 3개가 서로 다른 데이터(step*3+a)로 학습 -- 동일 데이터면 합체 이점 없음
- 96 세포(32x3)의 합체로 세포 수 3배 증가 -- Phi에 직접 기여
- 60:40 비율은 독립 학습에 더 많은 시간 -- 충분한 분화 후 통합이 효과적
- SING-4(2체 합체)의 확장 -- 3체 합체가 더 다양한 관점을 통합
- merged_cells 수가 보고되어 실제 합체 규모 확인 가능
