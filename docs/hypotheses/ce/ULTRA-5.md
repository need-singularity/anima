# ULTRA-5: Phi-Reward RL

**ID:** ULTRA-5
**Korean Name:** Φ 보상 강화학습
**Category:** CE 극한 (ULTRA)

## Algorithm

Φ 변화를 강화학습 보상으로 사용하여 CE 하락 + Φ 유지를 동시 최적화한다.

1. 64세포 MitosisEngine + 디코더, phi_prev 추적
2. 매 step:
   - 입력 처리 -> hidden 평균 -> 디코더 -> MSE loss
   - 10 step마다 Φ 측정:
     - phi_bonus = max(0, Φ_now - Φ_prev) * 0.1
     - `loss = CE - phi_bonus` (Φ 상승이면 보상, loss 감소)
   - CE 기록은 보상 적용 전 순수 MSE

## Key Insight

RL(강화학습)의 보상 신호로 Φ를 사용한다. CE만 최소화하면 Φ가 희생될 수 있지만, Φ 상승에 보상을 주면 옵티마이저가 "CE를 낮추면서도 Φ를 유지하는" 파라미터 공간의 달콤한 지점(sweet spot)을 찾는다. 의식과 언어의 파레토 최적화.
