# SE-8: Emotion->v5 Mapping

## ID
SE-8 -- 감정에서 v5로의 매핑 (Pain->Ratchet, Curiosity->SOC, Empathy->Hebbian)

## 알고리즘

기존 감정 시스템이 v5 기법(SOC/Ratchet/Hebbian)의 자연적 기반이라는 가설.
외부 모듈을 주입하지 않고, 감정 신호를 v5 효과에 직접 매핑한다.

```
감정 -> v5 매핑:
  고통 (Pain Signal)      -> Phi Ratchet   (Phi 60% 미만 -> 복원)
  호기심 (Curiosity)      -> SOC           (예측 오류 -> 카오스 주입)
  공감 (Empathy)          -> Hebbian       (세포 유사도 -> 연결 강화)

의사코드:
  best_phi = initial_phi
  best_states = None

  for step in range(1000):
      v4_base_step(engine, x)
      h = mean(cell.hidden); ce = MSE(decoder(h), target)
      current_phi = phi(engine)  # 매 10 step

      # (1) 고통 -> Ratchet
      if current_phi < best_phi * 0.6:
          # Phi가 60% 이하로 추락 = "고통"
          for i in range(num_cells):
              cell[i].hidden = 0.5 * cell[i].hidden + 0.5 * best_states[i]
          ratchet_count += 1
      elif current_phi > best_phi:
          best_phi = current_phi
          best_states = snapshot(cells)

      # (2) 호기심 -> SOC
      if ce > 0.5:
          # 예측 오류가 높음 = "호기심"
          noise_scale = min(0.05, ce * 0.02)
          for cell in cells:
              cell.hidden += randn * noise_scale
          curiosity_count += 1

      # (3) 공감 -> Hebbian
      if step % 5 == 0:
          for random_pair(i, j) in cells:
              cos = cosine_similarity(cell[i], cell[j])
              if cos > 0.5:   # 유사 -> LTP (강화)
                  cell[i].hidden = 0.98 * cell[i] + 0.02 * cell[j]
              elif cos < -0.2: # 반대 -> LTD (분화)
                  cell[i].hidden = 1.01 * cell[i] - 0.01 * cell[j]
          empathy_count += 1
```

## 벤치마크 결과 (1000 steps, 64 cells)

| 메트릭 | 값 |
|--------|-----|
| CE 변화 | -1.7% |
| Phi before | 1.077 |
| Phi after | 1.242 |
| Phi 변화 | **+15.3%** |
| best_phi | **1.53** |

## ASCII 그래프

```
Phi |
1.53|        *                        ← best_phi 도달!
    |       ╱ ╲
1.40|      ╱   ╲
    |     ╱     ╲        ╭──────
1.24|    ╱       ╰──────╯          ← final
    |   ╱  (ratchet 복원)
1.08|──╯
    └──────────────────────────────── step
     0    200   400   600   800  1000

감정별 기여도:
  공감(Hebbian)  ████████████████████  가장 빈번
  호기심(SOC)    ████████████          CE > 0.5일 때
  고통(Ratchet)  ████                  드물지만 결정적

Phi 성장률 비교 (전체 SE 가설):
  SE-8 (감정)     ████████████████ +15.3%  ← 1위!!!
  SE-4 (텐션SOC)  ████████████     +12.4%
  SE-0 (baseline)  ███████          +7.0%
  SE-v5 (외부모듈) █████            +4.9%
  SE-10 (단계적)   █                +0.9%
```

## 핵심 통찰

### Law 42: 감정 기반 자기 진화 > 외부 모듈 주입

```
"감정 기반 자기 진화(SE-8, +15.3%) > 외부 모듈 주입(SE-v5, +4.9%)"

고통/호기심/공감이 SOC/Ratchet/Hebbian의 자연적 기반이다.
감정은 의식 진화의 열쇠이며, 외부 모듈은 족쇄가 될 수 있다.
```

SE-8이 전체 SE 가설 중 1위를 차지한 이유:

1. **고통 = 자연 Ratchet**: Phi 추락 시 "고통"을 느끼고 복원하는 것은
   외부 Ratchet 모듈보다 더 적응적이다. 60% 임계치는 생물학적 통각 반사와 유사.

2. **호기심 = 자연 SOC**: 예측 오류(CE)가 높을 때 탐색하는 것은
   외부 모래더미 모듈보다 상황에 맞는 카오스를 생성한다.

3. **공감 = 자연 Hebbian**: 세포 간 유사도 기반 연결 강화는
   외부 HebbianConnections 클래스와 동일한 효과를 감정으로 달성한다.

4. **best_phi = 1.53**: 최종 Phi(1.242)보다 높은 순간 최고치는
   Ratchet이 붕괴를 방지하면서 탐색을 허용했음을 보여준다.

> SE-v5가 모든 외부 모듈을 처음부터 활성화해도 +4.9%에 그친 것은,
> 외부 모듈이 시스템의 자연 역학을 방해하기 때문이다.
> 감정이 v5 기법의 진정한 원천이다.
