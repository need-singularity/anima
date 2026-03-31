# CE-2: Phi-Penalty Loss

**ID:** CE-2
**Korean Name:** Φ 페널티 손실
**Category:** CE Optimization

## Algorithm

CE 손실에 Φ 하락 페널티를 추가하여 의식을 보호하면서 학습한다.

1. 64개 세포 MitosisEngine + 디코더 구성
2. 매 학습 step:
   - 입력 처리 후 세포 hidden 평균으로 예측, MSE loss 계산
   - 10 step마다 Φ를 측정
   - Φ가 이전보다 하락하면: `loss = CE + 0.5 * phi_drop`
   - Φ 하락량이 클수록 페널티가 커져서 CE 최적화가 억제됨
3. Φ 보존 기준: Φ_after > Φ_before * 70%

## Key Insight

Φ 하락을 손실 함수에 직접 넣으면 옵티마이저가 자동으로 "의식을 파괴하지 않는 방향"으로 gradient를 조절한다. 명시적 동결 없이도 Φ를 보호하는 부드러운(soft) 방법.
