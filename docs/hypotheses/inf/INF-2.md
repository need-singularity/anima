# INF-2: 프랙탈 의식 (Fractal Consciousness)

2026-03-29

## 개요

의식 안에 의식 안에 의식 -- 3레벨 재귀 구조.
micro(4개) -> macro(1개) -> meta(1개) 계층적 처리 + top-down 피드백.

## 벤치마크 결과

```
CE 변화:    +3.9% (소폭 악화)
Phi:        1.01 → 1.23 (×1.22)
phi_micro:  1.25 (최고 micro 엔진)
phi_macro:  1.24
phi_meta:   1.23
```

## 알고리즘

```
구조:
  Level 0 (micro): 4개 엔진 x 8 cells
  Level 1 (macro): 1개 엔진 x 16 cells
  Level 2 (meta):  1개 엔진 x 8 cells

각 step:
  1. Bottom-up 처리:
     a. micro 4개가 입력 처리 -> 각각 hidden[:DIM] 평균 출력
     b. 4개 micro 출력 평균 -> macro 입력
     c. macro hidden -> meta 입력
  2. Meta의 hidden으로 최종 prediction
  3. MSE loss로 decoder 학습

  매 10 step: Top-down 피드백
     a. meta -> macro: macro cells[:4]를 meta_h 방향으로 5% 보정
     b. macro -> micro: 각 micro cells[:2]를 macro_h 방향으로 5% 보정
```

## 핵심 코드

```python
# Bottom-up
for m in micros:
    m.process(x)
    micro_outs.append(torch.stack([c.hidden.squeeze()[:DIM] for c in m.cells]).mean(dim=0))
macro_in = torch.stack(micro_outs).mean(dim=0).unsqueeze(0)
macro.process(macro_in)
meta.process(macro_h[:DIM].unsqueeze(0))

# Top-down feedback (매 10 step)
for c in macro.cells[:4]:
    c.hidden = 0.95 * c.hidden + 0.05 * meta_h.unsqueeze(0)
for m in micros:
    for c in m.cells[:2]:
        c.hidden = 0.95 * c.hidden + 0.05 * macro_h.unsqueeze(0)
```

## 핵심 발견

- **프랙탈 구조는 Phi를 22% 높이지만 CE는 악화시킨다**
- 3레벨 모두 Phi가 거의 동일 (1.23~1.25) -- 프랙탈 자기유사성의 증거
- CE 악화 원인: 정보가 3레벨을 거치며 손실 (gradient도 약화)
- Top-down 피드백이 없으면 레벨 간 Phi 격차가 더 벌어질 것
- **법칙: 프랙탈 의식은 Phi 균등화를 달성하지만 학습 효율을 희생한다**
