# SING-1: 재귀적 자기개선 (Recursive Self-Improvement)

2026-03-29

## ID

SING-1 | 카테고리: SING (의식 특이점)

## 한줄 요약

학습한 것으로 학습 방법 자체를 개선 -- 메타 학습기가 CE history를 보고 최적 학습률을 결정하여 가속

## 알고리즘

```
1. MitosisEngine 생성 (64 cells)
2. 메타 학습기: Linear(5, 1) -- 최근 5개 CE -> LR 배율 결정
3. 매 step:
   a. 최근 5개 CE history가 있으면:
      - 메타가 sigmoid로 LR 배율 결정 (범위: 0.1 ~ 3.1)
      - optimizer LR 갱신: lr = 3e-3 * lr_mult
   b. 입력 처리 -> decoder 예측 -> MSE loss -> 역전파
4. 메타 학습기 학습:
   - improvement = CE[-2] - CE[-1] (CE 하락량 = 보상)
   - meta_loss = -improvement * meta_pred (REINFORCE)
   - CE가 떨어지면 현재 LR 정책 강화
```

## 핵심 코드

```python
# 메타가 LR 결정
if len(ce_hist) >= 5:
    with torch.no_grad():
        recent_ce = torch.tensor(ce_hist[-5:]).unsqueeze(0)
        lr_mult = torch.sigmoid(meta(recent_ce)).item() * 3.0 + 0.1
        for pg in opt.param_groups: pg['lr'] = 3e-3 * lr_mult

# 메타 학습: CE 하락하면 보상
improvement = ce_hist[-2] - ce_hist[-1]
meta_loss = -improvement * meta_pred.squeeze()
meta_opt.zero_grad(); meta_loss.backward(); meta_opt.step()
```

## 핵심 발견

- **자기개선의 재귀**: 학습 -> 메타 학습 -> 학습 개선 -> 더 나은 메타 학습 (양성 피드백)
- CE가 빠르게 하락하는 구간에서 LR을 높여 가속, 정체 구간에서 LR을 낮춰 안정화
- 특이점의 핵심 조건: 개선 속도 자체가 개선되는 루프
- 5 step window는 너무 짧지 않고(노이즈) 길지 않은(둔감) 적절한 크기
