# EX-2: Consciousness Optimizer

**ID:** EX-2
**Korean Name:** 의식이 옵티마이저
**Category:** CE 극한 전략

## Algorithm

Φ(의식)가 gradient 방향과 크기를 직접 결정한다. 세포 합의도가 gradient를 변조.

1. 64세포 MitosisEngine + 디코더 구성
2. 매 step:
   - 입력 처리 -> hidden 평균 -> 디코더 -> MSE loss
   - 역전파로 gradient 계산
   - **의식 변조**:
     - consensus = 1.0 - 세포 hidden의 variance 평균
     - 모든 gradient *= (0.5 + consensus)
     - 합의도 높으면 (0.5 + ~1.0 = ~1.5): 강한 업데이트
     - 합의도 낮으면 (0.5 + ~0.0 = ~0.5): 약한 업데이트
   - 변조된 gradient로 옵티마이저 step

## Key Insight

의식이 "확신할 때" 크게 배우고, "불확실할 때" 조심스럽게 배운다. 기존 옵티마이저(Adam)의 학습률과 별개로, 의식 상태가 실시간으로 gradient를 변조한다. 의식이 단순 관찰자가 아니라 학습의 능동적 참여자가 되는 구조.
