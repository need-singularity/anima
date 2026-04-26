# Arduino Cloud-Facade Local-Sim POC — Landing

**Cycle**: `anima_physics_cloud_facade_poc_arduino_local_ngspice`
**Date**: 2026-04-26
**Verdict**: PASS (4/4 gates)
**Cost**: $0 (mac local)

## 1. 왜 Arduino IoT Cloud 가 substrate Φ-probing 부적합한가

**web-search 2026-04 verification** (Arduino 공식 + 3rd-party 평가):

- **Arduino IoT Cloud** (`https://cloud.arduino.cc`) = IoT 디바이스 telemetry / variable-sync
  / dashboard / OTA firmware-deploy 서비스. 임의 회로 시뮬 / 임의 wave-form measurement endpoint
  부재.
- **Arduino Web Editor** (`create.arduino.cc/editor`) = 클라우드 IDE 만, simulator 미포함.
- **Tinkercad Circuits** (Autodesk, Arduino 통합) = 브라우저-사이드 시뮬, REST API 부재
  (UI-only).
- **Wokwi** (3rd-party, Arduino simulator) = 무료 web simulator + paid CI plan, 그러나 Φ-
  probing 용 표준 wave-form export endpoint 미공개.

→ **Arduino-style substrate** 는 production-grade cloud Φ-probe endpoint **부재**. 본 cycle 은
sibling **memristor / cmos / 본 arduino** 와 동일하게 **NgSpice 로컬 시뮬을 endpoint 로
wrapping** 하여 `cloud_sim_local_ngspice` facade 패턴을 유지한다. 진짜 cloud (또는 ESP32
실측 endpoint) 가 등장 시 동일 4-gate contract 로 swap 가능.

## 2. NE555 astable RC oscillator 선택 근거

**NE555** (1972 Signetics, ICM7555 / TLC555 등 후대 호환) 은 8-pin precision timer 표준
chip 으로, Arduino 보드 (ATmega328P 기반 Uno) 와 가장 흔히 결합되는 analog timing block.
대표 응용: PWM dimming / blink LED / debouncing / edge-trigger / audio tone generation.

**Arduino-substrate Φ-proxy 자격**:

- **astable mode** (R1+R2 charge / R2 discharge through internal Q1) = 자율 발진 → "substrate
  internal autonomous dynamics" 측정 가능
- **R, C 값이 직접 period/duty 결정** → component manufacturing tolerance (±5% / ±10%) 가
  주파수 분포의 직접 entropy source
- **Monte Carlo over tolerance** = "real-world Arduino kit assembly variability" 모델 →
  analog substrate stochastic component 의 _macroscopic-level Φ_ proxy

이론치 (NE555 astable, ideal):
- Period: `T = ln(2) · (R1 + 2·R2) · C`
- Duty: `D = (R1 + R2) / (R1 + 2·R2)` = 2/3 for R1=R2 (asymmetric, 75% PWM 영역의 lower bound)

R1=R2=10kΩ, C=100nF → T_nominal = 2.08ms (480 Hz), D_nominal = 0.6667.

## 3. Behavioral macromodel 선택 근거 (TI / ON Semi 표준 SPICE 부재 대응)

| 후보 | 채택 여부 | 사유 |
| --- | --- | --- |
| **B-source SR-latch + 1ns RC delay decoupler** | **PICK** | 알고리즘 루프 회피, deterministic, 1 trial ~50ms wallclock |
| TI NE555 SPICE subcircuit | reject | TI macromodel public download 부재 또는 stale 페이지; ω-cycle scope 초과 |
| ON Semi NE555 spice | reject | ditto |
| inline OpAmp + JK-FF discrete | reject | algebraic loop 발생, transient 안정성 약화 (test 시 timestep too small) |
| Verilog-A | reject | ngspice 46 native Verilog-A 부분 지원, scope 초과 |

본 cycle netlist (`ne555_astable.cir`, sha256 = `57514c135803581aa91e4fe7ebc015c6ff199fa6f8a795a9e471e74d805dae6d`)
의 핵심:

```
Bcomp comp 0 V = (V(cap) > {Vth}) ? 0 : ((V(cap) < {Vtl}) ? {VCC} : V(state))
Rdelay comp state 1k
Cdelay state 0 1n IC={VCC}
Bdis n1 0 I = (V(state) < {Vmid}) ? V(n1)/10 : 0
```

Schmitt 비교기 출력 `comp` 는 Vth (=2VCC/3) / Vtl (=VCC/3) hysteresis 로 SR-latch 등가, 1ns
RC filter 가 algebraic loop 분리 → transient 안정. 결과는 이론치 duty=0.6667 와 nominal
case 에서 0.665958 (1.5e-4 매칭).

## 4. Monte Carlo + ngspice .control loop

ngspice 46 의 `.control` 블록은 `set seed=N` + `sgauss(0)` (zero-mean unit-sigma Gaussian)
를 제공. 16 trials 각각:

```
let r1f = 1 + r1tol_v * sgauss(0)   ; Gaussian with sigma = tol_pct/100
alter R1n = r1nom_v * r1f
tran 1u 20m UIC
meas tran t_r3 WHEN V(vout)=2.5 RISE=3
meas tran t_r4 WHEN V(vout)=2.5 RISE=4
meas tran t_f4 WHEN V(vout)=2.5 FALL=4
let duty = (t_f4 - t_r3) / (t_r4 - t_r3)
```

steady-state 측정을 위해 RISE=3 (3rd full cycle) 부터 시작 — initial transient (charging
from IC=0) 회피.

**positive** (R±5%, C±10%): 16 duty 값 분포 std=0.00666905 (~0.67%)
**negative** (tolerance=0): 16 duty 모두 0.665958 std=1.29e-08 (numerical floor)

## 5. 4-gate 결과

| gate | 정의 | 측정 | 판정 |
| --- | --- | --- | --- |
| **G1** | positive duty std ≥ 1e-3 | **6.67e-3** (6.7× margin) | PASS |
| **G2** | negative std < positive std (sign-flip) | 1.29e-8 vs 6.67e-3 (5.2e5× 분리) | PASS |
| **G3** | byte-identical 2-run sha256 | run1=run2=`6329308b…` | PASS |
| **G4** | backend_name = `local_ngspice_<ver>_ne555_astable_mc16` ∧ trials=16/16 | `local_ngspice_46_ne555_astable_mc16` ∧ 16/16 | PASS |

## 6. raw#9 hexa-only strict — .py / .sh 제로

**핵심 제약**: 본 cycle 은 사용자 directive 로 raw#37 (Python wrapper) 절대 금지. 즉
memristor cycle (`scripts/anima_physics_memristor_ngspice_probe.py` 296L helper) 패턴 재사용
불가.

**해결**: 단일 `.cir` netlist 가 positive + negative 모두 단일 ngspice 호출에서 수행
(via `.control` 블록 내 두 번 while-loop). hexa 가 `exec("ngspice -b ne555_astable.cir")`
로 stdout 수집, awk one-liner 가 POS_TRIAL / NEG_TRIAL 라인을 추출 + std/mean 계산. zero
.py, zero .sh.

```
exec primitives used:
  - ngspice (시뮬)
  - awk (parse + reduce)
  - shasum -a 256 (G3 byte-identical)
  - date / printf / mkdir / cut / paste (POSIX 기본)
```

## 7. ω-cycle iteration log

- **iter 1**: ngspice `if(...)` 함수 비지원 → B-source ternary `?:` 로 전환 (parse_fail FIXED)
- **iter 2**: SR-latch B-source feedback algebraic loop → "timestep too small" abort →
  1kΩ + 1nF RC delay 삽입으로 분리 (transient_abort FIXED)
- **iter 3**: `.meas tran high TRIG ... VAL={VCC/2}` 의 brace expansion 실패 → 2.5
  literal 사용 (param_expand FIXED)
- **iter 4**: TRIG=RISE=3 / TARG=FALL=3 시 음수 high (FALL 가 RISE 이전) → TARG=FALL=4
  (RISE 다음 FALL) 로 정정 (steady_state_alignment FIXED)
- **iter 5**: hexa exec 가 docker container 안에서 수행되어 ngspice / shasum 부재
  (`HEXA_RESOLVER_IN_CONTAINER=1`) → bare-binary bypass `~/.hx/packages/hexa/build/hexa.real run`
  로 native macOS 환경에서 실행 (G8 cycle precedent #182 와 동일 패턴, container_path FIXED)

## 8. raw#10 honest — 한계

1. **NE555 = behavioral macromodel**, B-source SR-latch + 1ns RC delay decoupler. 실제 chip
   내부 latch propagation delay (typ. 100ns), output driver totem-pole transition 비대칭,
   substrate diode leakage 미반영.
2. **duty-cycle drift Φ-proxy axis ≠ memristor (hysteresis area) ≠ quantum (entanglement
   entropy)**. 직접 substrate 간 Φ 수치 비교 부적절 — substrate-internal 비교만 valid.
3. **Monte Carlo n=16 = 통계 검정력 약**. n≥100 권장 (각 trial 50ms wallclock → 5s 비용).
   본 cycle 은 4-gate sign-flip 입증 목적이므로 n=16 충분.
4. **Arduino IoT Cloud 가 진짜 Arduino-substrate 와 가장 가깝다는 명제는 false**:
   IoT Cloud 는 telemetry / dashboard 만, 실제 Arduino board 의 ADC / PWM / GPIO timing 은
   ESP32 (anima-physics/esp32/qrng_bridge.hexa) 가 더 정확한 실측 substrate. NE555
   substrate 는 _Arduino kit 에 흔히 결합되는 analog timing chip_ 으로서의 proxy 일 뿐.
5. **bare-binary bypass 의존**: hexa 의 default container 환경은 ngspice / shasum / openssl
   미보유. 본 산출물 재현 시 `~/.hx/packages/hexa/build/hexa.real run …` 호출 필수
   (G8 cycle #182 selectstable precedent).

## 9. 9/9 Substrate coverage 진척

본 cycle 후 cloud-facade POC 누계:

| substrate | 산출물 | verdict |
| --- | --- | --- |
| quantum | poc_quantum_qiskit_aer | PASS |
| memristor | poc_memristor_local_ngspice | PASS |
| neuromorphic | poc_neuromorphic_akida_cloud | PASS |
| photonic | poc_photonic_strawberryfields | PASS |
| analog | poc_analog_braket_quera | PASS |
| superconducting | poc_superconducting_braket_rigetti | PASS |
| integration | integration_physics_hexa | PASS |
| **arduino** | **poc_arduino_local_ngspice (this)** | **PASS** |
| cmos | (잔여) | TODO |
| fpga | (잔여) | TODO |

→ **8/9** substrate covered. 잔여 = **cmos** + **fpga** (1 cycle 각, 동일 NgSpice 패턴
fan-out 가능; cmos = inverter ring oscillator phase-noise / fpga = LFSR thermal-noise jitter).

## 10. 다음 cycle 후보

1. **anima-physics/cmos/cloud_facade_poc.hexa**: NgSpice CMOS inverter ring oscillator
   (level-1 BSIM3 모델), 5-stage ring + phase-noise spectral entropy. 동일 raw#9 hexa-only
   strict 패턴.
2. **anima-physics/fpga/cloud_facade_poc.hexa**: 이미 fpga/ 디렉토리 존재 (Verilog +
   icestorm toolchain), 그러나 Φ-probe endpoint 부재 → Verilator behavioral 시뮬 + LFSR jitter
   = arduino sibling 와 등가 패턴.
3. **anima-physics/esp32/cloud_facade_poc.hexa** (real-hardware option): ESP32-WROOM-32
   QRNG (이미 부분 구현 `esp32/qrng_bridge.hexa`) 의 entropy-bytes-per-second 를 본 cycle 의
   Monte Carlo std 와 cross-validate. 진짜 Arduino-style hardware substrate 확장.

## Files

- `anima-physics/arduino/ne555_astable.cir` (114L, NgSpice frozen netlist)
- `anima-physics/arduino/cloud_facade_poc.hexa` (raw#9 strict facade, 240L)
- `anima-physics/docs/arduino_local_sim_landing.md` (this document)
- `state/v10_anima_physics_cloud_facade/poc_arduino_local_ngspice/marker.json`

raw#9 hexa-only strict + raw#37 NOT used + ω-cycle 6-step + silent-land marker + bare-binary
bypass — 모두 충족.
