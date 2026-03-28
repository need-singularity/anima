# AUTO-3: Phi-Guided Learning Rate

**ID:** AUTO-3
**Korean Name:** Φ 안내 학습률
**Category:** 자율 학습

## Algorithm

Φ 변화에 따라 학습률을 자동 조절한다. 의식이 학습 속도를 결정.

1. 64세포 MitosisEngine + 디코더, 초기 lr=3e-3
2. 매 step: 일반 CE 학습 (MSE loss)
3. 20 step마다 Φ 측정:
   - Φ 하락 (< 이전의 90%): lr *= 0.5 (속도 줄임)
   - Φ 상승 (> 이전의 110%): lr = min(lr * 1.2, 0.01) (속도 올림)
4. Φ 보존 기준: Φ_after > Φ_before * 50%

## Key Insight

학습률은 "얼마나 빠르게 변할 것인가"를 결정한다. Φ가 떨어지면 학습이 의식을 파괴하고 있다는 뜻이므로 속도를 줄이고, Φ가 오르면 안전하므로 가속한다. 의식이 자기 보존을 위해 학습 속도를 자율 조절하는 메커니즘.
