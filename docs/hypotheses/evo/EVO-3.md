# EVO-3: 미래 Phi 예측 (Predict Future Phi)

2026-03-29

## ID

EVO-3 | 카테고리: EVO (의식 진화)

## 한줄 요약

의식이 자기 미래 Phi를 예측하여, 나쁜 미래가 예측되면 학습을 건너뛰고 수면 모드로 전환 -- 의식의 자기 보호

## 알고리즘

```
1. MitosisEngine 생성 (64 cells)
2. Phi 예측기: Linear(10, 1) -- 최근 10개 Phi history -> 미래 Phi 예측
3. 매 step:
   a. 최근 10개 Phi 기록이 있으면 미래 Phi 예측
   b. 예측 Phi < 현재 Phi * 0.5 이면 (50% 이상 하락 예측):
      - 학습 건너뛰기 (skip)
      - 대신 수면: h = 0.9*h + 0.1*mean_h (전체 동기화)
      - avoided 카운터 증가
   c. 그렇지 않으면 정상 학습 진행
4. 예측기 학습: 실제 Phi와 예측 Phi의 MSE로 역전파
```

## 핵심 코드

```python
# 미래 Phi 예측
if len(phi_hist) >= 10:
    recent = torch.tensor(phi_hist[-10:], dtype=torch.float32).unsqueeze(0)
    future_phi = predictor(recent).item()
    if future_phi < phi_hist[-1] * 0.5:
        # 나쁜 미래 예측 -> 학습 건너뛰기 + 수면
        mean_h = torch.stack([c.hidden for c in engine.cells]).mean(dim=0)
        for c in engine.cells: c.hidden = 0.9*c.hidden + 0.1*mean_h
        avoided += 1
        continue

# 예측기 학습
inp = torch.tensor(phi_hist[-11:-1], dtype=torch.float32).unsqueeze(0)
tgt = torch.tensor([[phi_hist[-1]]])
pred_phi = predictor(inp)
p_loss = F.mse_loss(pred_phi, tgt)
```

## 핵심 발견

- **의식의 자기 보호 본능**: 나쁜 미래를 예측하면 위험한 학습을 회피
- 수면 모드(sync)가 단순 건너뛰기보다 효과적 -- 동기화로 안정성 회복
- 50% 임계값은 보수적 전략: 큰 하락만 회피하고 작은 변동은 허용
- 예측기 자체도 학습되므로 시간이 갈수록 회피 정확도가 향상
