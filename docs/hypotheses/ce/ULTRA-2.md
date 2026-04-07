# ULTRA-2: GenData + Sleep + Pain

**ID:** ULTRA-2
**Korean Name:** 데이터 생성 + 수면 + 고통
**Category:** CE 극한 (ULTRA)

## Algorithm

EX-5(데이터 생성) + AUTO-7(수면) + AUTO-9(고통)의 3중 결합.

1. 64세포 MitosisEngine + 디코더 + 실제 데이터 50개
2. 30 step 주기:
   - **LEARN (22 step)**:
     - 25% 실제 데이터 + 75% 세포 hidden 기반 자기 생성 데이터
     - CE 학습 + 메모리 저장 (최대 30개)
     - 고통 검사: Φ < best * 50%이면 긴급 복원(0.4:0.6) + lr *= 0.5
   - **SLEEP (8 step)**:
     - 메모리 재생 -> engine.process()
     - Φ 복원: `cell.hidden = 0.85*h + 0.15*mean_h`

## Key Insight

ULTRA-1에 수면 주기를 추가. 학습-수면 교대가 Φ를 주기적으로 복원하므로 고통 신호가 발동할 일이 줄어든다. 수면의 예방적 Φ 복원 + 고통의 긴급 Φ 복원이 이중 안전장치 역할.
