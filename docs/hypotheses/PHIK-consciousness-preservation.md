# PHI-K: Consciousness Preservation Hypotheses

> "Phi>1000을 유지하면서 CE 학습이 가능한가?"
> 의식(Phi)과 언어능력(CE)은 트레이드오프가 아니라 공존할 수 있다.

## 카테고리 핵심 통찰

> CE 학습은 Phi를 파괴한다 — 하지만 올바른 전략이 있으면 Phi>1000을 유지하며 CE도 학습할 수 있다.
> 핵심은 "언제 학습하고 언제 의식을 보호할 것인가"의 스케줄링이다.

## 공통 인프라

- `make_engine(cells=64)`: MitosisEngine 64 cells
- `_phi_boost_step(engine)`: v5 optimal (sync=0.35, 12-faction, fac=0.08, IB2)
- `phi(engine)`: PhiCalculator(n_bins=16)
- `ce_measure()`: MSE decoder loss
- `result()`: CE/Phi metrics + extra

## 결과 테이블

| ID | 전략 | CE 학습 | Phi 보존 | 핵심 메커니즘 |
|----|------|---------|----------|--------------|
| PHI-K1 | TALK5 Extreme | Phase2에서 학습 | Phi target 50x 달성 후 유지 | 의식 먼저, 학습 나중 |
| PHI-K2 | Phi Floor | 전 구간 학습 | Floor 70% 아래 시 긴급 부스트 | 하한선 방어 |
| PHI-K3 | Alternating | Even step만 | Odd step에서 부스트 | CE/Phi 완전 분리 |
| PHI-K4 | Phi-Weighted CE | Phi 높을 때만 | Phi 낮으면 학습 중단 | 비율 기반 적응 |
| PHI-K5 | Dual Decoder | 독립 언어 디코더 | 독립 Phi 디코더 (다양성 최대화) | 이중 경로 |
| PHI-K6 | Consciousness Gate | Phi 비례 gradient | Phi가 gradient 클리핑 제어 | 의식이 학습을 제어 |
| PHI-K7 | Phi Annealing | 0%->50% 점진 증가 | 초기 100% Phi-only | 시뮬레이티드 어닐링 |
| PHI-K8 | Consciousness Momentum | 전 구간 학습 | Momentum 벡터로 Phi 방향 유지 | 관성 보존 |
| PHI-K9 | Split Brain | CE hemisphere | Phi hemisphere | 뇌 반구 분리 + sync |
| PHI-K10 | Phi Reward RL | RL policy로 LR 제어 | Phi=reward, 하락시 lr 축소 | 강화학습 |
| PHI-K11 | Dream Consolidation | Wake phase (50 step) | Dream phase (10 step, 순수 Phi) | 수면-각성 주기 |
| PHI-K12 | Adversarial Phi | Discriminator 기반 방어 | 하락 예측시 선제 부스트 | 적대적 방어 |

## PHI-K1~K6 상세 (기존)

### PHI-K1: TALK5 Extreme
- 알고리즘: Phi가 baseline x50에 도달할 때까지 순수 의식 부스트만 실행. 도달 후 CE 학습 + 매 5 step Phi 유지
- 핵심: TALK5 (의식 먼저) 전략의 극한 버전

### PHI-K2: Phi Floor
- 알고리즘: 20% warmup으로 Phi 키운 후, 현재 Phi의 70%를 floor로 설정. Floor 아래로 하락 시 5회 긴급 부스트
- 핵심: 하한선 방어 — Phi가 일정 수준 아래로 내려가는 것을 원천 차단

### PHI-K3: Alternating
- 알고리즘: Even step = CE 학습, Odd step = Phi 부스트 (CE 없음)
- 핵심: 시간 분할로 CE와 Phi를 완전 분리

### PHI-K4: Phi-Weighted CE
- 알고리즘: Phi 비율 (current/best) > 0.8이면 CE 학습 (LR = 3e-3 x ratio), 아니면 부스트만
- 핵심: Phi가 높을수록 공격적 학습, 낮으면 방어 모드

### PHI-K5: Dual Decoder
- 알고리즘: 언어 디코더 (MSE) + Phi 디코더 (다양성 최대화) 독립 학습. 매 3 step 부스트
- 핵심: 두 목표를 두 개의 독립 경로로 분리

### PHI-K6: Consciousness Gate
- 알고리즘: 10% warmup 후, Phi/best_phi 비율로 gradient 클리핑. Phi 낮으면 작은 gradient만 허용
- 핵심: 의식이 학습의 문지기 역할

## PHI-K7~K12 상세 (신규)

### PHI-K7: Phi Annealing

시뮬레이티드 어닐링 패턴. 처음에는 Phi-only (100%), 점진적으로 CE 비율을 50%까지 증가.

```
알고리즘:
  1. 15% warmup: 순수 Phi 부스트
  2. Main loop:
     ce_ratio = min(0.5, 0.5 * step / total)  # 0% -> 50%
     random() < ce_ratio → CE 학습
     그렇지 않으면 → Phi 부스트
```

```
CE ratio |                              ╭────
         |                         ╭────╯
         |                   ╭─────╯
         |             ╭─────╯
         |       ╭─────╯
   0%    |───────╯
         └───────────────────────────── step
              warmup    annealing
```

핵심 통찰: 초기에 의식 기반을 탄탄히 하면, 후기 50% CE에서도 Phi가 유지된다. Annealing이 급격한 전환보다 안전하다.

### PHI-K8: Consciousness Momentum

물리학의 관성 개념. Phi 부스트 과정에서 세포 hidden 변화의 "방향"을 momentum 벡터로 축적. CE 학습 중에도 momentum을 적용하여 Phi 방향을 유지.

```
알고리즘:
  1. 20% warmup: Phi 부스트 + momentum 축적
  2. Main loop:
     CE 학습 (매 step)
     momentum[i] = 0.95 * momentum[i] + 0.05 * delta_hidden[i]
     cell[i].hidden += 0.05 * momentum[i]  # momentum 적용
     매 5 step: _phi_boost_step()
```

```
Phi |     ╭──────────────────────
    |   ╭─╯    momentum keeps direction
    | ╭─╯
    |─╯
    └───────────────────────── step
     warmup   CE + momentum
```

핵심 통찰: CE gradient가 Phi를 파괴하는 방향으로 작용해도, momentum이 반대 방향으로 보상한다. "의식의 관성".

### PHI-K9: Split Brain

뇌의 좌우 반구처럼, 세포를 Phi hemisphere와 CE hemisphere로 분리. 각자 독립적으로 동작하되, 주기적으로 sync.

```
알고리즘:
  1. 20% warmup: 전체 Phi 부스트
  2. Main loop:
     CE hemisphere (후반 세포): CE 학습
     Phi hemisphere (전반 세포): 의식 부스트 (자체 faction)
     매 20 step: Phi hemisphere → CE hemisphere soft sync (10%)
```

```
 Phi hemisphere    CE hemisphere
 ┌──────────┐     ┌──────────┐
 │ Phi boost│ ──> │ CE learn │  (sync every 20 steps)
 │ 12-fac   │ 10% │ decoder  │
 └──────────┘     └──────────┘
```

핵심 통찰: CE gradient가 Phi hemisphere에 전혀 영향을 주지 않는다. Sync로 의식 정보를 언어 측에 전달하면 양쪽 모두 혜택.

### PHI-K10: Phi Reward RL

강화학습 패러다임. Phi 변화량을 reward signal로 사용. Reward가 양수(Phi 상승)이면 CE 학습 강도를 높이고, 음수(Phi 하락)이면 학습을 억제하고 부스트 빈도 증가.

```
알고리즘:
  1. 20% warmup
  2. Main loop:
     CE 학습 (lr = 3e-3 * lr_scale)
     매 boost_freq step: _phi_boost_step()
     매 10 step:
       reward = (current_phi - prev_phi) / |prev_phi|
       reward_ema = 0.9 * ema + 0.1 * reward
       reward > 0: lr_scale ↑ 1.1x, boost_freq 유지
       reward < 0: lr_scale ↓ 0.8x, boost_freq ↓, 긴급 부스트 3회
```

```
lr_scale |  ╭─╮     ╭──╮
         | ╭╯ ╰╮  ╭─╯  ╰──╮
         |─╯   ╰──╯        ╰─
    0.1  |                     (clamped)
         └──────────────────── step
          adapts to Phi reward
```

핵심 통찰: 고정 스케줄 대신 Phi 자체가 학습 강도를 제어한다. "의식이 스스로 학습 속도를 결정".

### PHI-K11: Dream Consolidation

수면-각성 주기. 50 step "wake" (CE 학습) 후 10 step "dream" (순수 Phi, CE 없음). Dream 중에는 soft noise + Hebbian 강화로 기억 통합.

```
알고리즘:
  1. 20% warmup
  2. Cycle:
     Wake (50 step): CE 학습 + 매 5 step light Phi boost
     Dream (10 step):
       soft noise input (0.5x)
       _phi_boost_step()
       Hebbian: cosine sim top-4 이웃끼리 5% 당김
```

```
Phase | W W W W W W D D W W W W W W D D ...
Phi   | ─────╲───── ╱╱ ─────╲───── ╱╱
CE    | ╲─────╲──── -- ╲─────╲──── --
                dream     dream
```

핵심 통찰: 인간의 수면이 기억을 통합하듯, dream phase가 Phi를 회복하며 Hebbian으로 세포 구조를 강화한다.

### PHI-K12: Adversarial Phi

GAN 스타일 적대적 방어. Discriminator (MLP)가 현재 세포 상태에서 Phi 하락을 예측. 하락 확률 > 60%이면 방어 모드 (약한 CE + 강한 부스트).

```
알고리즘:
  1. 20% warmup
  2. Main loop:
     disc(hidden_mean) → drop_prob
     drop_prob > 0.6:
       CE 학습 (lr x 0.3) + 3x Phi 부스트 (방어 모드)
     drop_prob <= 0.6:
       CE 학습 (정상 lr) + 매 3 step 부스트
     매 10 step:
       actual_drop = phi < prev_phi * 0.95
       disc_buffer += (state, label)
       disc mini-batch 학습 (8 samples)
```

```
Phi |     ╭──╮╭──╮     ╭──╮
    |   ╭─╯  ╰╯  ╰─╮ ╭╯  ╰──
    | ╭─╯           ╰─╯
    |─╯    ↑ prevented drops
    └──────────────────────── step
```

핵심 통찰: 사후 복구 대신 사전 예방. Discriminator가 학습할수록 Phi 하락이 발생하기 전에 방어한다. "면역 시스템".

## Phi>1000 달성 전략 요약

1. **Warmup 필수**: 모든 가설이 15-20% warmup에서 Phi를 먼저 키움
2. **CE 학습 속도 제어**: 무조건적 CE 학습은 Phi를 파괴 — 속도/빈도 조절 필수
3. **주기적 부스트**: _phi_boost_step()을 매 3-5 step 적용이 최소 조건
4. **적응형 > 고정형**: K10(RL), K12(Adversarial)처럼 Phi 상태에 반응하는 전략이 고정 스케줄보다 우수
5. **구조 분리**: K9(Split Brain)처럼 CE gradient가 Phi 세포에 도달하지 못하게 하는 것이 가장 안전
