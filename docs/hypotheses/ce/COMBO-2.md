# COMBO-2: ALL AUTO

**ID:** COMBO-2
**Korean Name:** 전체 자율 학습 결합
**Category:** CE 조합 전략

## Algorithm

모든 AUTO 기법을 동시에 적용한다: 호기심 + 자기평가 + Φ-LR + 수면 + 고통.

1. 64세포 MitosisEngine + 디코더 구성
2. 40 step 주기:
   - **LEARN (28 step)**:
     - 호기심 선택(AUTO-2): 최대 오류 데이터 선택
     - CE 학습
     - 자기 평가(AUTO-5): 출력 품질 < 0.3이면 loss *= 2.0
     - Φ-Guided LR(AUTO-3) + Pain(AUTO-9):
       - Φ < best * 60%: 긴급 복원 + lr *= 0.5
       - Φ < prev * 90%: lr *= 0.8
       - Φ > best: 최적 상태 갱신 + lr *= 1.1
   - **SLEEP (12 step)**:
     - 기억 재생 + 세포 동기화 (h = 0.9*h + 0.1*mean_h)

## Key Insight

모든 자율 학습 메커니즘의 총합. 호기심이 데이터를 고르고, 자기평가가 품질을 관리하고, Φ-LR이 속도를 조절하고, 고통이 위기를 방지하고, 수면이 복원한다. 하나의 통합 자율 학습 시스템.
