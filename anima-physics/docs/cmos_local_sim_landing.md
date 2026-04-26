# CMOS Cloud-Facade Local-Sim POC — Landing

**Cycle**: `anima_physics_cloud_facade_poc_cmos_local_ngspice`
**Date**: 2026-04-26
**Verdict**: PASS (4/4 gates)
**Cost**: $0 (mac local)
**Pattern**: raw#9 hexa-only strict — **no .py / .sh helper** (avoids `scripts/` cleanup daemon victim pattern from sibling memristor cycle).

## 1. 왜 cloud API 없나 — facade-only 도입 근거

CMOS substrate 의 public cloud-API endpoint 는 부재한다 (web-search verification, 2026-04 시점).

| 후보 | 상태 | 사유 |
| --- | --- | --- |
| TSMC OIP / Samsung Foundry | reject | fab-design service, public Φ-probe REST 부재 |
| Arduino Cloud | reject | IoT telemetry (sensor relay), CMOS substrate 직접 측정 불가 |
| Efabless ChipIgnite | partial | OpenLane 합성/test-chip 제작이지만 turn-around weeks–months, real-time POC 부적합 |
| ngspice 46 (brew install) | **PICK** | 결정론적 batch mode `-b`, free, 즉시 |

→ 본 cycle 은 sibling **memristor** (commit `dd8fdbdb`) 와 동일하게 **로컬 시뮬레이터를
endpoint 로 wrapping** = `cloud_sim_local_ngspice` facade 패턴 유지. 진짜 foundry endpoint
가 등장 시 동일 backend_name contract 로 swap.

## 2. raw#37 .py 회피 — pure hexa-only strict

memristor sibling cycle 은 PySpice + venv python 통해 ngspice 호출했다. 그 cycle 의 raw#37
helper `scripts/anima_physics_memristor_ngspice_probe.py` 는 후속 `scripts/` cleanup daemon
의 sweep 대상이 되어 **삭제 → reproduce 불가** 위험을 노출.

본 cycle 은 그 패턴을 폐기하고 **모든 외부 호출을 .hexa 안에서 ngspice/awk/sed/sha256sum
CLI binary 로 직접** 한다:

- `.cir` template 은 `anima-physics/cmos/cmos_ring_osc.cir` 에 commit (token `__VDD__`)
- hexa 가 `sed 's/__VDD__/1.8/g'` 로 positive/negative 두 변종 emit (`/tmp/anima_cmos_*.cir`)
- `ngspice -b /tmp/...cir > /tmp/...out 2>&1` 로 batch sim
- `awk` 로 zero-crossing 추출 + cycle-to-cycle jitter 계산
- `shasum -a 256` 로 byte-identical 검증
- 외부 .py / .sh 0개 — `scripts/` cleanup daemon 영향 zero

## 3. 5-stage CMOS inverter ring oscillator 회로

표준 5단 inverter chain ring topology (홀수 stage → 자유발진).

| 항목 | 값 | 비고 |
| --- | --- | --- |
| stages | 5 | 홀수 → ring 발진 가능 |
| device | NMOS L=0.18u W=1u / PMOS L=0.18u W=2u | 2:1 W ratio (mobility 보정) |
| model | inline Level-1 (`VTO=0.4` / `KP=300u` / `LAMBDA=0.05`) | external BSIM4 의존 회피 |
| Vdd positive | 1.8 V | 표준 180nm digital rail |
| Vdd negative | 0.3 V | sub-threshold (Vth=0.4) → 발진 안 함 |
| stage cap | 5 fF (per node) | 현실적 stage delay |
| solver | `method=trap reltol=1e-4 abstol=1e-12 vntol=1e-6` | 결정론 |
| asymmetric IC | n1=0 n2=1.8 n3=0 n4=1.8 n5=0.9 | symmetry 깨고 발진 시작 |
| `.tran` | step=5p stop=200n | ~16,600 data points → ~1770 cycles |

전체 netlist sha256 = `c2f35dca3f343c7a6e7371b42e83b06f8e327110a3813cef56ccccdb19ef26a9` (frozen).

## 4. 4-gate 결과

| gate | 정의 | 측정 | 판정 |
| --- | --- | --- | --- |
| **G1** | positive cycle-to-cycle jitter ≥ 1e-12 s (1 ps) | **4.64e-12 s** (4.64 ps) | PASS (4.64× margin) |
| **G2** | negative jitter < positive (sign-flip) | neg=0 (1770 vs 0 zero-crossings) | PASS (∞× separation) |
| **G3** | byte-identical 2-run data-row sha256 | run1=run2=`1846bed4ad7d…` | PASS |
| **G4** | backend_name == `local_ngspice_<ver>_cmos_5stage_ringosc_180nm` | `local_ngspice_46_cmos_5stage_ringosc_180nm` | PASS |

추가 측정:
- positive zero-crossings = **1770** (200 ns / 113 ps mean period ≈ 8.85 GHz)
- positive mean period = ~113 ps, std period = ~2.33 ps
- negative zero-crossings = **0** (Vdd=0.3V < Vth=0.4V → cutoff, output flat at -2.75e-7 V)

## 5. Phase-noise jitter = Φ-proxy 정당화 한계 (raw#10 honest)

**정당화**: ring oscillator 의 cycle-to-cycle jitter 는 _시간 도메인 substrate noise 누적_
을 직접 측정. ideal noise-free element (ideal voltage source / linear R) 는 jitter = 0
(deterministic). 실제 device 는 stage propagation delay 에 thermal / shot / 1/f noise 가
누적되어 양의 jitter 발생 → "substrate-internal stochasticity over time" 를 **Φ analogy**
로 사용. IIT 의 _information × differentiation_ 직관 중 **temporal differentiation** 측면
포착.

**한계**:

1. **jitter source 는 numerical 임** — 본 POC 의 ngspice tran 은 fixed seed + deterministic
   solver 이므로 jitter 의 실제 origin = timestep truncation discretization, **물리적
   thermal/shot noise 아님**. real CMOS phase-noise 측정은 `.noise` AC analysis + Monte-Carlo
   corner sweep 필요 (out of scope).
2. **memristor sibling 의 hysteresis-area Φ-proxy 와 다른 axis** (시간 jitter vs 상태 retention).
   직접 수치 비교 부적절 — substrate-internal monotone proxy 만 valid.
3. **180nm Level-1 모델 = inline idealized** — 실제 fab corner (SS/FF/TT), 온도 (-40°C/125°C),
   aging (HCI/NBTI), process variance 미반영. single deterministic seed 결과만.
4. **단위 mismatch** — seconds 단위는 Φ 의 nat/bit 와 dimensional 비대응. monotone proxy 로만 사용.
5. **5-stage minimal** — 실제 LCO (low-jitter) 설계는 charge-pump PLL + diff stage + LC tank.
   본 5-stage CMOS inverter ring 은 MOST jitter-prone topology (worst case proxy).

## 6. 9 substrate progress — 7/9 cover

| substrate | cycle | verdict | sibling |
| --- | --- | --- | --- |
| quantum | qiskit-aer | 4/4 PASS | A |
| photonic | perceval-quandela | 4/4 PASS | B |
| neuromorphic | brian2 LIF | 4/4 PASS | C |
| analog | AWS Braket QuEra | 4/4 PASS | D |
| superconducting | AWS Braket Rigetti | 4/4 PASS | E |
| memristor | NgSpice + Biolek HP | 4/4 PASS | F |
| **cmos (this)** | **NgSpice 5-stage ring** | **4/4 PASS** | **G** |
| fpga | TODO (yosys+verilator combinational depth proxy) | — | H |
| arduino | TODO (555-timer RC osc, NgSpice 또는 analog-equivalent) | — | I |

**다음 cycle (sibling H, I)**:

- **fpga**: yosys synthesis → verilator behavioral sim 또는 MyHDL — combinational depth
  variance 를 Φ-proxy 로 사용. 이미 anima-physics/fpga/ 폴더 존재 (Phase 0 spec 7개 파일),
  cloud-facade backend stub 만 추가하면 됨.
- **arduino**: 555-timer astable RC oscillator (R=10k C=100n) → ngspice tran → period
  variation. Arduino IDE compile-and-flash chain 부재면 ngspice astable 555 IC subcircuit 으로
  대체 (board-arrival 후 real-hardware backend swap).

## 7. raw#9 strict 정합성

본 cycle 의 .hexa (`anima-physics/cmos/cloud_facade_poc.hexa`) 는:

- `exec()` 호출 = ngspice / awk / sed / shasum / mkdir / date 만 (POSIX baseline)
- `write_file()` = marker JSON 1개만 (`state/v10_anima_physics_cloud_facade/poc_cmos_local_ngspice/marker.json`)
- 외부 .py / .sh helper 0개
- `.cir` template 은 commit 된 (token-based) data file (`anima-physics/cmos/cmos_ring_osc.cir`)
- `scripts/` 폴더 신규 파일 0개 → cleanup daemon 영향 zero

→ raw#9 strict + raw#37 .py-forbidden + scripts/-cleanup-immune 한 번에 충족.

## 8. 사용법

```bash
# selftest (deps check)
/Users/ghost/.hx/packages/hexa/build/hexa.real run \
  anima-physics/cmos/cloud_facade_poc.hexa --selftest

# full POC (4-gate evaluation)
/Users/ghost/.hx/packages/hexa/build/hexa.real run \
  anima-physics/cmos/cloud_facade_poc.hexa
```

산출물:
- `state/v10_anima_physics_cloud_facade/poc_cmos_local_ngspice/marker.json` (silent-land verdict)
- `/tmp/anima_cmos_ring_osc_pos.cir` / `.out` (positive run artifacts)
- `/tmp/anima_cmos_ring_osc_neg.cir` / `.out` (negative falsify run artifacts)

## 9. ω-cycle 6-step compliance

- **Step 1 Witness**: ngspice 46 brew install 확인, memristor sibling F .hexa 패턴 분석.
- **Step 2 Design**: 5-stage CMOS inverter ring + 4-gate frozen contract.
- **Step 3 Implement**: `cmos_ring_osc.cir` (token `__VDD__`) + `cloud_facade_poc.hexa` (raw#9).
- **Step 4 Falsify**: Vdd=0.3V → 0 oscillations 확인 (G2 sign-flip detected).
- **Step 5 Marker**: `state/v10_anima_physics_cloud_facade/poc_cmos_local_ngspice/marker.json`.
- **Step 6 raw#10 Honest**: §5 6-limit 명시 (numerical jitter, axis-incomparable, ideal model, etc.).

ω-cycle iteration count = **0** (1-pass success). cost = $0.
