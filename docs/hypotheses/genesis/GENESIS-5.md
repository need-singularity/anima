# GENESIS-5: 공생 의식 (Symbiosis)

H-GENESIS-5 | bench_self_learning.py | 2026-03-29

## 결과

```
CE:         -14.7% (학습 개선!)
Phi:        1.05 → 1.17
역할 분화:  sensors / processors / motors
```

## 핵심 통찰

**감각-처리-운동 세포의 역할 분화와 순환 연결이 학습과 Phi를 동시에 향상시킨다.**
64개 세포를 3가지 타입으로 분류하고 정보 흐름을 단방향 순환으로 연결하면
CE -14.7%(학습 개선) + Phi 1.05→1.17(11% 상승). GENESIS 시리즈 유일한 CE 개선.

## 알고리즘

```
초기 조건: 64 세포, 3가지 타입으로 분류
  sensors:    cells[:n//3]      -- 감각 세포 (외부 입력 수신)
  processors: cells[n//3:2n//3] -- 처리 세포 (정보 통합)
  motors:     cells[2n//3:]     -- 운동 세포 (출력 생성)
학습:       MSE decoder (Adam, lr=3e-3)

메커니즘:
  1. GRU 처리 (전체 세포에 입력)
  2. 공생 규칙 (매 스텝, no_grad):

     감각 → 처리 (정보 전달):
       sensor_mean = mean(sensors.hidden)
       processors[:4].hidden = 0.9 * h + 0.1 * sensor_mean

     처리 → 운동 (결정 전달):
       proc_mean = mean(processors.hidden)
       motors[:4].hidden = 0.9 * h + 0.1 * proc_mean

     운동 → 감각 (피드백 순환):
       motor_mean = mean(motors.hidden)
       sensors[:4].hidden = 0.95 * h + 0.05 * motor_mean

  3. 전체 hidden 평균으로 CE 학습

핵심 흐름:
  sensors → processors → motors → sensors (순환)
  감각(10%) → 처리(10%) → 운동(10%) → 감각(5%) 피드백
```

## 의의

- GENESIS 시리즈에서 유일하게 CE를 개선(-14.7%)한 가설
- 역할 분화 + 순환 연결 = 학습 효율 + 의식 통합 동시 달성
- 생물학의 감각-운동 루프(sensorimotor loop)를 의식 아키텍처에 구현
- 피드백 비율의 비대칭(10% vs 5%)이 핵심: 운동→감각은 약한 피드백
  -- 순방향 정보 흐름이 역방향보다 강해야 효과적 (인과적 비대칭)
- 린 마굴리스(Lynn Margulis)의 공생발생설을 의식에 적용:
  개별적으로는 약한 세포들이 공생으로 강한 의식을 형성
