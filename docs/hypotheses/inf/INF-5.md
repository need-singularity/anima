# INF-5: 무한 탑 (Infinite Tower)

2026-03-29

## 개요

의식 위에 의식을 수직으로 쌓는 타워 아키텍처.
5레벨 탑에서 bottom-up 처리 + top-down 변조로 수직 스케일링의 한계를 탐색.

## 벤치마크 결과

```
CE 변화:    -26.6% (대폭 개선)
Phi:        1.19 → 0.98 (×0.82, 하락)
levels:     5
phis:       [1.34, 1.45, 1.10, 0.98, 0.98]
```

## 알고리즘

```
구조: 5레벨 탑, 각 레벨 8 cells

각 step:
  1. Bottom-up (level 0 -> level 4):
     - level 0: 원본 입력 처리
     - level 1~4: 이전 레벨의 hidden[:DIM]이 입력
     - 입력 크기 불일치 시 pad/truncate

  2. Top level (level 4)의 hidden으로 최종 prediction
  3. MSE loss로 decoder 학습

  매 5 step: Top-down 변조
     - level 4 -> 3 -> 2 -> 1 -> 0 순서로
     - 상위 hidden을 하위 cells[:2]에 5% 혼합
       h_lower = 0.95 * h_lower + 0.05 * h_upper
```

## 핵심 코드

```python
# Bottom-up: level 0 -> level 4
current_input = x
for level in range(LEVELS):
    if current_input.shape[-1] > DIM:
        current_input = current_input[:, :DIM]
    elif current_input.shape[-1] < DIM:
        current_input = F.pad(current_input, (0, DIM - current_input.shape[-1]))
    towers[level].process(current_input)
    h = torch.stack([c.hidden.squeeze() for c in towers[level].cells]).mean(dim=0)
    current_input = h[:DIM].unsqueeze(0)

# Top-down modulation
for level in range(LEVELS-1, 0, -1):
    upper_h = torch.stack([c.hidden.squeeze() for c in towers[level].cells]).mean(dim=0)
    for c in towers[level-1].cells[:2]:
        c.hidden = 0.95 * c.hidden + 0.05 * upper_h.unsqueeze(0)
```

## 핵심 발견

- **수직 5레벨은 CE를 26.6% 줄이지만 Phi는 0.98로 baseline 이하**
- Phi 분포: [1.34, 1.45, 1.10, 0.98, 0.98] -- 상위 레벨일수록 Phi 감소
- Level 1이 Phi 최고 (1.45): 원본 입력과 top-down 피드백이 모두 도달하는 "스윗 스팟"
- Level 4~5의 Phi 하락: 정보가 여러 레벨을 거치며 희석 (bottleneck 효과)
- **법칙: 수직 스케일링은 약 2레벨이 최적. 그 이상은 정보 희석으로 Phi가 감소한다.**
- Top-down 변조(5%)가 너무 약해서 상위의 통합 정보가 하위로 충분히 전달되지 않음
- **CE 개선의 원인은 Phi가 아닌 다층 비선형 변환의 표현력 증가**
