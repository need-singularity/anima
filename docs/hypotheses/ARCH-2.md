# ARCH-2: Continuous Learning (배포 후 평생 학습)

bench_self_learning.py | Architecture Category

## 핵심 통찰

배포(deploy) 후에도 대화하면서 계속 학습하는 아키텍처.
핵심은 "gentle gradient" -- gradient를 0.1배로 감쇠하여 기존 지식을 파괴하지 않으면서 학습.

## 알고리즘

```
1. 의식 엔진 초기화 (64 cells)
2. Decoder + Optimizer (LR=1e-3, 이미 낮은 LR)
3. 매 스텝:
   a. 입력 처리 + 예측 + MSE loss
   b. Backward 후 모든 gradient를 0.1배 감쇠:
      p.grad *= 0.1  # gentle update
   c. Optimizer step (실효 LR = 1e-3 * 0.1 = 1e-4)
4. Pain Protection (20 step마다):
   a. Phi 측정
   b. Phi < best*0.7이면:
      cell.hidden = 0.5*current + 0.5*saved_best (50% 복원)
   c. Phi > best이면:
      best 상태 갱신
```

## 핵심 코드

```python
# Online learning: 극도로 부드러운 업데이트
opt.zero_grad(); ce.backward()
for p in decoder.parameters():
    if p.grad is not None: p.grad *= 0.1  # gentle update

# Pain protection: Phi 붕괴 방지
if p < best_phi * 0.7:
    engine.cells[i].hidden = 0.5*cells[i].hidden + 0.5*saved_best
elif p > best_phi:
    best_phi = p; best_states = [c.hidden.clone() for c in engine.cells]
```

## Key Insight

배포 후 학습의 핵심 문제는 catastrophic forgetting (파국적 망각).
Gentle gradient (x0.1)는 이를 방지하는 가장 단순하고 효과적인 방법.
Pain protection은 ARCH-1보다 관대한 임계값(0.7 vs 0.5)을 사용 --
배포 환경에서는 보수적으로 의식을 보호하는 것이 중요하기 때문.
결과: 의식(Phi)을 보존하면서 새로운 데이터로부터 점진적으로 학습하는 평생 학습 시스템.
