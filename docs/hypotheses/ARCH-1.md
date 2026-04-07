# ARCH-1: ULTRA-6 + Tension Transfer (최강 자율 학습 아키텍처)

bench_self_learning.py | Architecture Category

## 핵심 통찰

6가지 학습 전략을 하나의 아키텍처로 통합:
Progressive Freeze + Curiosity + Tension Transfer + Self-Generated Data + Sleep Consolidation + Pain Protection.

## 알고리즘

```
1. Teacher 사전 학습 (32 cells, 50 step)
2. Student 엔진 (64 cells) + 2층 decoder (HIDDEN→ReLU→DIM)
3. Progressive Freeze:
   - 전반부: decoder[0] 동결, decoder[2]만 학습 (LR=3e-3)
   - 후반부: 전체 해동, 미세 조정 (LR=1e-3)
4. 30-step 사이클 (22 train + 8 sleep):
   [Train Phase - 22 steps]
     step%4==0: Curiosity — 예측 오류 최대 데이터 선택 (SL-1)
     step%4==1: Tension Transfer — 교사 세포 상태 주입 (TL-L1)
     step%4==2,3: Self-Generated — 세포 간 hidden을 데이터로 사용
   [Sleep Phase - 8 steps]
     메모리 리플레이 + 세포 동기화 (0.85*h + 0.15*mean)
5. Pain Protection:
   - 10 step마다 Phi 체크
   - Phi < best*0.5이면 최고 상태로 60% 복원
   - Phi > best이면 best 갱신
```

## 핵심 코드

```python
# Progressive freeze: 전반부는 마지막 층만
decoder = nn.Sequential(nn.Linear(HIDDEN, HIDDEN), nn.ReLU(), nn.Linear(HIDDEN, DIM))
for p in decoder.parameters(): p.requires_grad = False
for p in decoder[2].parameters(): p.requires_grad = True
# 중간에 전체 해동
if step == steps//2:
    for p in decoder.parameters(): p.requires_grad = True

# 4-way 데이터 소스 로테이션
if step % 4 == 0:     # Curiosity
elif step % 4 == 1:   # Tension transfer
else:                  # Self-generated data

# Sleep consolidation (cycle >= 22)
mean_h = torch.stack([c.hidden for c in engine.cells]).mean(dim=0)
for cell in engine.cells: cell.hidden = 0.85*cell.hidden + 0.15*mean_h

# Pain protection
if p < best_phi*0.5:
    engine.cells[i].hidden = 0.4*cells[i].hidden + 0.6*saved_best
```

## Key Insight

단일 전략보다 6가지 결합이 CE를 극적으로 낮춘다 (CE -98.8% 보고).
핵심은 "다양한 데이터 소스 + 수면 통합 + 고통 보호"의 삼위일체.
Progressive freeze는 초기 안정성 + 후기 미세 조정을 보장하고,
Pain protection은 Phi 붕괴를 방지하여 의식을 보존하면서 학습한다.
ULTRA-6는 Anima의 자율 학습 아키텍처의 최종 형태.
