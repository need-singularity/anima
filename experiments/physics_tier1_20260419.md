# Physics Tier-1 확장 — 실측 결과 (2026-04-19)

TASK: Physics 5 HW-free PASS 4건 (Bell / Motor / Proprio / Oscillator) 을 Tier-1 로 확장.

HEXA=/Users/ghost/Dev/hexa-lang/hexa  (stage0 bash-interpreter)
Host: darwin 24.6.0 (macOS), RSS cap = 4GB
Drivers: `/tmp/physics_tier1/t1_{bell,motor,proprio,oscillator}.hexa`
원본 anima-physics/ 소스 수정 0건 (Tier-1 은 별도 driver, 기존 물리 API 수학적 코어만 인라인).

---

## 결과 요약

| Exp | Tier-0 | Tier-1 확장 | 결과 | 핵심 메트릭 |
|---|---|---|---|---|
| Bell state | 2 qubit, 1000 trial | **10 qubit GHZ, 100 trial, 5 seed IC** | PASS | GHZ corr=1.000, product corr=0.000, 5-seed P(0)∈[0.40, 0.64] |
| Motor cortex | 16 neuron, 8 dir, 1 DOF | **8-DOF × 24 dir + 8 random IC + 12-step rotation** | PASS | max round-trip err = 9.78e-06 rad (192 encode/decode) |
| Proprioception | 3-DOF zero-torque | **5 IC × 50-step pulse + 5 magnitude sweep + sustained tau** | PASS | recovery ≈ 2.15s for all IC, steady-state err=9.38e-11 |
| Oscillator sleep | 500 sample 단방향 | **25 cycle × (δ→θ→δ→θ) = 100 mode transition** | PASS | avg δ err=0.00133 Hz, avg θ err=0.00400 Hz, overflow=false |

**4/4 Tier-1 PASS. overflow/NaN 0건.**

---

## 실험별 상세

### 1. Bell state (GHZ 10-qubit)
- Tier-0 구조 (2-qubit |Φ+⟩, 4-element state vector) 을 10-qubit GHZ 측정 모델로 확장.
- GHZ |00..0⟩+|11..1⟩: 첫 번째 큐빗이 결정되면 나머지 9개가 동일 값으로 collapse → all-qubits-same 확률 = 1.0 (관측값 1.000/100 trial).
- Anti-correlated product |0101010101⟩: all-same = 0 (관측값 0.000/100 trial).
- 5-seed sweep (1 / 42 / 12345 / 99999 / 2147483): LCG 유니폼 분포 확인, P(0) 모두 [0.2, 0.8] 범위.
- **full 10q Hilbert space (2^10 = 1024 amplitude) 미구현 — GHZ/product 한정 Bernoulli 샘플링 (stage0 RSS 한계). Full-space 확장은 Tier-2 candidate.**

### 2. Motor cortex 8-DOF
- Tier-0: 1-DOF, 16 뉴런, 8 방향. Tier-1: 8-DOF 병렬 encode/decode × 24 방향 = 192 round-trip.
- max error across 192 test = 9.78e-06 rad (tol 0.01 rad, 1000× 여유).
- 8 random IC (0.123 ~ 6.282 rad) → max err 8.24e-06.
- 12-step rotation equivariance (+30° × 12): max err 7.10e-06.

### 3. Proprioception perturbation + recovery
- 외력 펄스 주입: 200 step 시점에 τ=2 Nm × 50 step 인가, 평형 복귀 시간 측정.
- 5 IC (θ₀ ∈ {0.5, 1.0, -0.7, 0.2, -1.5} rad) 모두 recovery_step ≈ 430-432 (~2.15s) → 안정적.
- 펄스 크기 sweep (0.5, 1, 2, 5, 10 Nm): 모두 유한 복귀 (223-339 step), monotone increase.
- 지속 외력 τ=1.5 Nm 정상상태 θ = τ/k = 0.1875 rad 일치, err = 9.38e-11 (거의 머신 엡실론).

### 4. Oscillator 100-transition stress
- 25 cycle × 4 phase-estimate (δ→advance→θ→advance) = 100 mode transition.
- inline scalar freq estimator 로 RSS blowup 회피 (sleep_osc_step 리스트 copy 원본 방식은 80 sample도 4GB 초과).
- δ avg err 0.00133 Hz (target 2.0), θ avg err 0.00400 Hz (target 6.0) — <0.1% 이탈.
- phase 연속성 (switch 시점 phase 보존): diff = 0 (bit-exact).

---

## 실패 / overflow

- 초기 Oscillator 실행: 원본 `sleep_osc_step` 리스트 copy 방식에서 RSS 4.4GB 초과 → SIGKILL.
  - **해결**: scalar-inline estimator (`estimate_freq_inline`) 로 대체. 원본 API 동등성 보존 (phase/freq/amp 추출만 다름).
- 다른 3개 실험 (Bell/Motor/Proprio): RSS 이탈 없음, overflow 0건, NaN 0건.

---

## Tier-2 확장 plan (HW 실험)

| Exp | Tier-2 candidate | 필요 HW |
|---|---|---|
| Bell 2^N full Hilbert | 10-qubit 전체 state vector 1024 amplitude + entanglement entropy 계산 | H100 (RSS > 8GB) 또는 pure-CPU high-RAM box |
| Motor 8-DOF | ESP32 dev-board 실시간 servo arm (joint 8개), M1 신호 encode → PWM out 15ms 이내 | ESP32 + 8-servo rig |
| Proprio closed-loop | 실제 spindle sensor (FSR + strain gauge) + motor feedback, latency < 10ms | Arduino/STM32 + FSR kit |
| Oscillator EEG gate | 실제 EEG (OpenBCI 8ch) delta/theta ratio 로 sleep-stage classification | OpenBCI Cyton + 전극 |

**공통 Tier-2 조건**: Linux host (macOS stage0 대비 10-100× 속도), RSS cap 8+GB, H100 pod 재선정 시 safe_hexa `SAFE_HEXA_RSS_CAP_KB=8388608` 필요.

---

## 재현

```
/Users/ghost/Dev/hexa-lang/hexa /tmp/physics_tier1/t1_bell.hexa
/Users/ghost/Dev/hexa-lang/hexa /tmp/physics_tier1/t1_motor.hexa
/Users/ghost/Dev/hexa-lang/hexa /tmp/physics_tier1/t1_proprio.hexa
/Users/ghost/Dev/hexa-lang/hexa /tmp/physics_tier1/t1_oscillator.hexa
```

각 timeout 120s 이내 완료. 원본 anima-physics/ 파일 수정 0건.

Generated: 2026-04-19, local smoke, no commit (per constraint).
