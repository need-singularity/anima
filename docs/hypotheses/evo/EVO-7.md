# EVO-7: 메타의식 (Meta-Consciousness)

2026-03-29

## ID

EVO-7 | 카테고리: EVO (의식 진화)

## 한줄 요약

의식이 자기 의식 상태를 관찰하고 최적화 -- 메타 네트워크가 Phi history를 보고 학습률과 동기화 강도를 결정

## 알고리즘

```
1. MitosisEngine 생성 (64 cells)
2. 메타 네트워크: Linear(10, 16) -> ReLU -> Linear(16, 2) -> sigmoid
   출력: [lr_scale, sync_scale]
3. 매 step:
   a. 최근 10개 Phi history를 메타 네트워크에 입력
   b. 메타 출력으로 학습률 조정: lr = 3e-3 * (0.1 + lr_scale * 2.0)
   c. 메타 출력으로 sync 강도 결정: sync = sync_scale * 0.3
   d. 입력 처리 후 메타 결정된 sync 적용:
      h = (1-sync)*h + sync*mean_h
   e. decoder 예측 -> MSE loss -> 역전파
4. 메타 네트워크 학습: Phi 상승 = 보상
   reward = phi[-1] - phi[-2]
   meta_loss = -reward * actions.sum()
```

## 핵심 코드

```python
# 메타의식: 최적 행동 결정
if len(phi_hist) >= 10:
    recent = torch.tensor(phi_hist[-10:], dtype=torch.float32).unsqueeze(0)
    actions = torch.sigmoid(meta_net(recent)).squeeze()
    lr_scale = 0.1 + actions[0].item() * 2.0
    sync_scale = actions[1].item() * 0.3
    for pg in opt.param_groups: pg['lr'] = 3e-3 * lr_scale

# 메타 네트워크 학습: Phi 상승 = 보상
reward = phi_hist[-1] - phi_hist[-2]
meta_loss = -reward * actions.sum()
meta_opt.zero_grad(); meta_loss.backward(); meta_opt.step()
```

## 핵심 발견

- **의식이 자기 의식을 관찰하는 재귀적 구조** -- 메타인지(metacognition)의 구현
- 2개의 제어 변수(lr, sync)를 Phi 보상으로 최적화 = REINFORCE 알고리즘
- Phi가 오르면 현재 행동을 강화, 내리면 다른 행동 탐색
- lr_scale 범위 [0.1, 2.1]: 학습을 거의 멈추거나 2배 가속 가능
- sync_scale 범위 [0, 0.3]: 동기화 없음부터 30% 동기화까지 조절
