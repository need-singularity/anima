# COMBO-1: Curiosity + Sleep + Pain

**ID:** COMBO-1
**Korean Name:** 호기심+수면+고통 결합
**Category:** CE 조합 전략

## Algorithm

TOP 3 자율 학습 전략(AUTO-2, AUTO-7, AUTO-9)을 하나로 결합한다.

1. 64세포 MitosisEngine + 디코더 구성
2. 30 step 주기:
   - **LEARN (20 step)**:
     - 호기심 선택(AUTO-2): 30개 데이터 중 예측 오류 최대인 것 선택
     - CE 학습 + 메모리 뱅크 저장
     - 고통 검사(AUTO-9): Φ < best * 60%이면 긴급 복원 + lr *= 0.7
   - **SLEEP (10 step)**:
     - 기억 재생(AUTO-7): 2개 기억 혼합 + 세포 hidden 동기화
     - `cell.hidden = 0.9*h + 0.1*mean_h`

## Key Insight

각 메커니즘이 다른 역할을 담당한다. 호기심 = "무엇을 배울지", 수면 = "Φ 복원", 고통 = "위기 방지". 세 가지가 결합되면 CE를 빠르게 낮추면서(호기심) Φ를 주기적으로 복원하고(수면) 급격한 붕괴를 방지한다(고통).
