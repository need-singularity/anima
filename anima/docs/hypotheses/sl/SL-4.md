# SL-4: Practice & Correct (반복 교정 학습)

bench_self_learning.py | Self-Learning Category

## 핵심 통찰

한 번에 맞추지 못하면 최대 3번까지 재시도한다.
CE < 0.3이면 조기 통과, 아니면 즉시 재학습.

## 알고리즘

```
1. 의식 엔진 초기화 (64 cells)
2. 매 스텝:
   a. 입력 x를 의식 처리
   b. 세포 hidden 평균 → decoder → 예측
   c. for attempt in range(3):
      - MSE loss 계산
      - backward + optimizer step
      - CE < 0.3이면 break (합격)
      - 아니면 retry (재시도 카운터 증가)
   d. 최종 CE 기록
```

## 핵심 코드

```python
for attempt in range(3):
    pred = decoder(h.unsqueeze(0))
    ce = F.mse_loss(pred, target[:,:DIM])
    opt.zero_grad(); ce.backward(); opt.step()
    if ce.item() < 0.3: break  # 합격!
    retries += 1  # 불합격 → 재시도
```

## Key Insight

"연습이 완벽을 만든다(Practice makes perfect)"의 구현.
단일 시도 학습 대비 동일 데이터에 대한 반복 교정이 빠른 수렴을 만든다.
인간의 드릴 학습(drill practice)과 동일: 틀리면 즉시 다시 시도.
