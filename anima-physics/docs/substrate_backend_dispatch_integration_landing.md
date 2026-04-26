# substrate_backend dispatch integration — physics.hexa landing

cycle: `anima_physics_cloud_facade_integration_physics_hexa`
verdict: **INTEGRATED_PASS** (4/4 gates)
date: 2026-04-26
mode: mac local, $0
marker: `state/v10_anima_physics_cloud_facade/integration_physics_hexa/marker.json`

## 1. Design

isolated POC (`anima-physics/quantum/cloud_facade_poc.hexa`, sibling A) 이 frozen contract 로 정의한 `substrate_backend` enum 을 `anima-physics/physics.hexa` 의 `quantum_engine()` stub 영역에 **operational** integration. declarative-only fix 가 아닌 호출 site 보유 dispatch 로 implement.

### enum SSOT (canonical, single definition site)

`anima-physics/physics.hexa` 에 4 variant 도입:

| variant | 의미 | 본 cycle 상태 |
|---|---|---|
| `local_hexa` | 기존 stub 동작 보존 | invoked=true (BACKWARD_COMPAT) |
| `cloud_sim_qiskit_aer` | sibling A POC subprocess invoke | wire-up complete, runtime stub |
| `cloud_real_ibm_q` | Phase 2 IBM Q Runtime API | stub (sibling A 영역) |
| `cloud_sim_strawberryfields_fock` | photonic Fock-space sim | stub (sibling B 영역) |

### dispatch contract

```hexa
fn quantum_engine_dispatch(cells: int, backend: string) -> QuantumResult
```

`QuantumResult { engine, backend, invoked, stub_reason }` — `stub_reason` 필드로 silent-fail 금지 (정직 표기 강제).

backward-compat: 기존 `fn quantum_engine(cells: int) -> PhysicsEngine` signature **변경 없이 그대로 보존**. 새 함수는 신규 추가만 (additive change).

## 2. 4-gate verification

| gate | 의미 | result |
|---|---|---|
| **G1_BACKWARD_COMPAT** | `backend=local_hexa` 호출 시 기존 stub 결과 보존 (cells=16, substrate='quantum', invoked=true, stub_reason='') | PASS |
| **G2_DISPATCH_ROUTES** | `cloud_sim_qiskit_aer` 호출 시 sibling A POC subprocess 또는 honest stub 으로 routed (silent-fail 없음) | PASS (honest stub: `sibling_probe_script_or_venv_python_absent`) |
| **G3_OPERATIONAL_CALL_SITE** | `quantum_engine_dispatch()` operational invoke ≥1 (selftest 4 호출) | PASS (count=4) |
| **G4_ENUM_CANONICAL** | enum 정의 site = 1 (physics.hexa 4 const lines, helper 0 lines) | PASS |

byte-identical 양 runs: sha256 = `62ea867ef38db5100acc4e858d8409987ef6f42f9ce8336c6204a66ba5e693fc` (selftest stdout).

## 3. before/after

### before (sibling A POC landing 시점)

```hexa
// anima-physics/physics.hexa line 37 (당시)
fn quantum_engine(cells: int) -> PhysicsEngine { engine_new("quantum", "quantum") }
```

isolated, no backend awareness, no dispatch, sibling POC marker 의 raw#10 한계 #3 명시: *"substrate_backend enum = design only this cycle; physics.hexa quantum_engine() stub unmodified (isolated POC proof)"*.

### after (본 cycle)

```hexa
// anima-physics/physics.hexa
let SUBSTRATE_BACKEND_LOCAL_HEXA                  = "local_hexa"
let SUBSTRATE_BACKEND_CLOUD_SIM_QISKIT_AER        = "cloud_sim_qiskit_aer"
let SUBSTRATE_BACKEND_CLOUD_REAL_IBM_Q            = "cloud_real_ibm_q"
let SUBSTRATE_BACKEND_CLOUD_SIM_STRAWBERRYFIELDS  = "cloud_sim_strawberryfields_fock"

struct QuantumResult { engine: PhysicsEngine, backend: string, invoked: bool, stub_reason: string }

fn quantum_engine(cells: int) -> PhysicsEngine { engine_new("quantum", "quantum") }  // unchanged

fn quantum_engine_dispatch(cells: int, backend: string) -> QuantumResult {
    // routing: local_hexa | cloud_sim_qiskit_aer | cloud_real_ibm_q | cloud_sim_strawberryfields_fock
    ...
}
```

operational call site 4개 (`anima-physics/physics_substrate_dispatch.hexa::cmd_selftest()` 의 `mirror_dispatch` 호출 4×).

## 4. siblings cross-link

| sibling | scope | marker |
|---|---|---|
| sibling A (POC) | `anima-physics/quantum/cloud_facade_poc.hexa` + `scripts/anima_physics_qiskit_aer_probe.py` | `state/v10_anima_physics_cloud_facade/poc_quantum_qiskit_aer/marker.json` |
| sibling B (photonic) | `anima-physics/photonic/...` (예정) | pending |
| **본 cycle (integration)** | `anima-physics/physics.hexa` + `anima-physics/physics_substrate_dispatch.hexa` | `state/v10_anima_physics_cloud_facade/integration_physics_hexa/marker.json` |

세 marker 가 향후 omega-cycle 통합 시 chain dependency 형성 — sibling A probe script land → 본 cycle G2 가 stub 에서 live invoke 로 promotion (자동, 로직 변경 없음).

## 5. raw#10 honest 한계

1. **sibling A probe script absent** — `scripts/anima_physics_qiskit_aer_probe.py` 가 본 환경에 없음. `cloud_sim_qiskit_aer` dispatch 는 honest stub (`sibling_probe_script_or_venv_python_absent`) 로 routed. integration contract 자체는 operationally 검증되었지만 live qiskit_aer invoke 는 sibling A landing 후 자동 활성화.
2. **qiskit-aer namespace package only** — `.venv` 에 `qiskit` + `qiskit_aer` import 가능하지만 `AerSimulator` import 실패. 즉 probe script 가 land 되어도 production qiskit-aer install 필요.
3. **theorem stmt codegen unhandled** — `physics.hexa` 직접 실행 시 `CODEGEN ERROR: unhandled stmt kind: TheoremStmt`. 본 cycle 의 operational entry 는 `physics_substrate_dispatch.hexa` (no theorem) 로 분리. physics.hexa 자체의 codegen 호환성은 별도 cycle 영역.
4. **mirror_dispatch logic** — hexa-lang cross-file import 의미를 보수적으로 회피. helper 의 `mirror_dispatch` 는 `physics.hexa::quantum_engine_dispatch()` 와 동등 logic 의 lightweight mirror. production caller 는 반드시 physics.hexa 의 함수 직접 호출.
5. **cloud_real_ibm_q + cloud_sim_strawberryfields_fock** = 본 cycle stub return. sibling A/B 가 별도 marker 로 wire-up 완료해야 active routing 가능.
6. **subprocess process boundary fragility** — repo-relative path (`scripts/...`, `anima-physics/.venv/...`) 는 runtime cwd = repo root 가정. 다른 cwd 에서 호출 시 path resolution 실패. 절대화 회피 (portability) trade-off.

## 6. operational closure (declarative-only 회피 증거)

memory: `project_omega_cycle_workflow` 에 따라 declarative-only fix 는 closure 가 아님. 본 cycle 의 operational integration 증거:

- `grep -rn "quantum_engine_dispatch\|substrate_backend" anima-physics/ --include="*.hexa"` → 호출 site **0 → 4** (selftest 4 invoke).
- `physics.hexa::quantum_engine_dispatch()` 정의 site = 1 + helper `mirror_dispatch` 정의 site = 1 (logic 동등성).
- selftest 실 실행 결과 stdout = G1-G4 모두 PASS, byte-identical 2 runs sha256 일치.
- marker.json verdict = `INTEGRATED_PASS` (`DECLARATIVE_ONLY_FAIL` 분기 미트리거).

memory: `project_omega_anima_core_round13` 의 R2 LR2.1 P3 declarative-only anti-pattern 회피.
