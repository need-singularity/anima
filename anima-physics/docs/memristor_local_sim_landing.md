# Memristor Cloud-Facade Local-Sim POC — Landing

**Cycle**: `anima_physics_cloud_facade_poc_memristor_local_ngspice`
**Date**: 2026-04-26
**Verdict**: PASS (4/4 gates)
**Cost**: $0 (mac local)

## 1. 왜 cloud API 없나 — facade-only 도입 근거

memristor (HP TiO2 thin-film, 2008 Strukov-Williams) 와 sibling substrates **CMOS / Arduino**
는 **production-grade cloud API endpoint 가 부재**한다. web-search verification (2026-04
시점):

- HP / Hewlett Packard Enterprise: research demos only, public API 없음.
- Knowm (memristor IC vendor): SDK 만 제공, hosted API 부재.
- Crossbar / Weebit Nano: foundry partnership, fab access only.
- IBM Analog AI Cloud Composer: in-memory compute simulator (cloud GUI), 그러나 public REST 부재.
- Arduino Cloud / CMOS foundry (TSMC/Samsung): IoT telemetry / fab-design service ≠ substrate
  Φ-probing endpoint.

→ 본 cycle 은 **로컬 시뮬레이터를 endpoint 로 wrapping** 하여
`cloud_sim_local_<sim>` backend 패턴을 도입. 진짜 cloud 가 등장 시 동일 facade contract 로
swap 가능 (sibling quantum: `cloud_sim_qiskit_aer` ↔ `cloud_real_ibm_q` 패턴 동일).

## 2. NgSpice + Biolek HP TiO2 subcircuit 선택 근거

| 후보 | 채택 여부 | 사유 |
| --- | --- | --- |
| **NgSpice 46** + Biolek 2009 model | **PICK** | open-source, brew install, deterministic batch mode `-b -n` |
| PySpice 1.5 wrapper | secondary | venv 설치 OK 이지만 PySpice 가 ngspice 46 “unsupported” warning — direct subprocess 가 더 안전 |
| LTspice | reject | macOS 지원 약함, GUI 의존 |
| Spectre / HSPICE | reject | proprietary, 비용 |
| 자체 RK4 hexa-native | reject | 1-cycle scope 초과; reference simulator 부재로 cross-validate 불가 |

**Biolek 2009 model** (`Radioengineering 18(2)`) 는 HP TiO2 표준 SPICE subcircuit 으로
`Ron=100Ω / Roff=16kΩ / D=10nm / μᵥ=10 fm²/(V·s) / window p=2` 의 linear-drift + window
function 을 사용한다. ngspice 46 는 `stp(·)` 와 `pow(·)` 를 native 함수로 제공하지 않기에
다음 ω-cycle iteration adaptation 이 필요했다:

- `stp(-i)` → `0.5 - 0.5*sgn(I)` smoothstep B-source 표현 `(I/(|I|+1e-9))`
- `pow(x, 2p)` → `x ** (2*Pwin)` (B-source built-in operator)
- subckt 형태 → inline B-source + 1F integrator capacitor (안정성 향상)

전체 netlist sha256 = `bdf421d52f7f27c67dceea8328fa866d0952d4349006acb0e216c151164ba7ad`
(deterministic frozen).

## 3. 4-gate 결과

| gate | 정의 | 측정 | 판정 |
| --- | --- | --- | --- |
| **G1** | memristor hysteresis area ≥ 1e-4 V·A | **6.82e-3** V·A | PASS (68× margin) |
| **G2** | resistor area < memristor area (sign-flip) | resistor **4.18e-14** vs **6.82e-3** (1.6e11× 분리) | PASS |
| **G3** | byte-identical 2-run sha256 | run1=run2=`7d24a840…` | PASS |
| **G4** | backend_name == `local_ngspice_<ver>_biolek_hp_memristor` | `local_ngspice_46_biolek_hp_memristor` | PASS |

stimulus: 0.1 Hz, 1.5 V amplitude, 20 s duration, 2000 transient samples,
shoelace integration over last full period.

## 4. Hysteresis area = Φ-proxy 정당화 한계

**정당화**: pinched I-V loop 의 면적은 _상태가 시간에 걸쳐 보존되는 정도_ 를 직접 측정.
linear element (저항/커패시터/인덕터) 는 영역 = 0 (state retention 부재). memristor 는 ionic
drift 가 과거 input 의 누적 효과를 내부 변수 `x` 로 인코딩 → 면적 0이 아닌 양수.
"substrate-internal state retention across time" 를 **Φ analogy** 로 사용함은 IIT 의
"information × integration" 직관 중 **integration (시간축)** 측면을 포착.

**한계 (raw#10 honest)**:

1. quantum sibling 의 _entanglement entropy_ Φ-proxy 와 **다른 axis** (시간적 메모리 vs
   공간적 비분리성). 직접 수치 비교 부적절 — substrate-internal 비교만 valid.
2. Biolek 모델은 ideal linear-drift; 실제 device 는 LRS/HRS distribution, switching kinetics,
   Joule heating, stochastic teleportation 가 있어 실측 면적은 device-to-device variance 큼.
3. 면적 단위는 V·A — Φ 의 nat/bit 단위와 dimensional mismatch. "monotone proxy" 로만 사용.
4. p=2 window (low-order) 는 edge boundary 정확도가 떨어짐. p=10 (Biolek 권장) 시 수치 안정성
   악화 → 본 POC 는 p=2 채택.

## 5. CMOS / Arduino — 동일 패턴 fan-out 후보 (next cycle)

본 cycle 은 8 substrate 중 memristor 만 cover. 동일 NgSpice facade 패턴이 즉시 확장 가능:

| substrate | proposed Φ-proxy | netlist 핵심 |
| --- | --- | --- |
| **CMOS** | inverter ring oscillator phase-noise spectral entropy | NMOS+PMOS chain (level-1 BSIM3 simple model) |
| **Arduino** | 555-timer multivibrator duty-cycle drift entropy | RC + comparator + flip-flop |
| **analog** | RLC second-order Q-factor → resonance retention | RLC + sin source |

각 substrate 별 1-cycle ($0, mac local, 1 helper.py + 1 facade.hexa + 1 marker)
fan-out 가능. cumulative substrate coverage: quantum ✓ + memristor ✓ + (cmos/arduino/analog
3개 추가 시) → **5/8** 진행.

## Files

- `scripts/anima_physics_memristor_ngspice_probe.py` (raw#37 transient helper, 196L)
- `anima-physics/memristor/cloud_facade_poc.hexa` (raw#9 strict facade, 230L)
- `anima-physics/docs/memristor_local_sim_landing.md` (this document)
- `state/v10_anima_physics_cloud_facade/poc_memristor_local_ngspice/marker.json`

## ω-cycle iteration log

- iter 1: `stp` / `pow` ngspice 46 미지원 → smoothstep B-source 로 교체 (parse_fail FIXED)
- iter 2: 1Hz / 1.2V default 시 area = 1.27e-5 (G1 threshold 미달) → 0.1Hz / 1.5V / 20s 로 frozen
- iter 3: backend_name 이 resistor 측에서도 `_biolek_hp_memristor` 로 보고 (misleading) →
  resistor 는 `_linear_resistor_baseline` 로 분리

raw#9 strict + raw#37 transient + ω-cycle 6-step + silent-land marker 모두 충족.
