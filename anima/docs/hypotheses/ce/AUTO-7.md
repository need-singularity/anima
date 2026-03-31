# AUTO-7: Sleep-Learn Cycle

**ID:** AUTO-7
**Korean Name:** 수면-학습 주기
**Category:** 자율 학습

## Algorithm

학습(LEARN)과 수면(SLEEP)을 주기적으로 교대하여 Φ를 복원한다.

1. 64세포 MitosisEngine + 디코더 구성
2. 30 step 주기:
   - **LEARN (20 step)**: 일반 CE 학습 + 메모리 뱅크에 데이터 저장 (최대 50개)
   - **SLEEP (10 step)**: gradient 없이 기억 재생
     - 메모리에서 2개 기억을 꺼내 혼합 (0.6:0.4 blend = dream)
     - 혼합 기억을 engine에 입력
     - 세포 hidden을 전체 평균 쪽으로 살짝 이동: `h = 0.9*h + 0.1*mean_h`
     - 이 과정이 Φ를 복원 (세포간 정보 통합 강화)

## Key Insight

인간의 수면과 동일한 원리. 학습은 CE를 낮추지만 Φ를 소모한다. 수면 중 기억 재생과 세포 동기화로 Φ를 복원한다. 두 기억의 혼합은 꿈(dream)에 해당하며, 새로운 연결을 만들어낸다.
