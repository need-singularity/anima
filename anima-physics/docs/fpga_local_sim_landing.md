# FPGA Cloud-Facade POC — Local Icarus Verilog (iverilog) RTL Simulator

**Cycle**: `anima_physics_cloud_facade_poc_fpga_local_verilator`
**Status**: **4/4 PASS — VERIFIED** (mac local, $0.00, 2026-04-26)
**Marker**: `state/v10_anima_physics_cloud_facade/poc_fpga_local_verilator/marker.json`

---

## 1. Motivation

`anima-physics/README.md` 가 명시한 9-substrate cloud-facade 中 FPGA 차례.
AWS F1 인스턴스는 신규 사용자 가입 차단 (web search 확인), F2 신세대는
시간당 $1.65 비싸 보류. 따라서 본 cycle 은 open-source SystemVerilog
시뮬레이터 **Icarus Verilog (iverilog) v13.0** 를 endpoint 로 wrapping 하는
"cloud_sim_local_iverilog" facade 패턴을 채택.

Sibling cycle:

- `anima-physics/memristor/cloud_facade_poc.hexa` — NgSpice + Biolek HP TiO2
- `anima-physics/quantum/cloud_facade_poc.hexa`   — Qiskit-Aer Bell-state

동일 4-gate 구조, 동일 marker schema (`anima_physics/cloud_facade_<sub>/1`).

---

## 2. Probe Topology — 8-bit Galois LFSR + Ring Counter (Coupled)

```
                    +-----------+         +------------+
   clk ── posedge ─▶│  LFSR8    │── b0 ──▶│  Ring8     │
   rst ────────────▶│  (Galois) │         │  (rotate)  │
   seed=0x42        │ poly=0xB8 │  fb     │ seed=0xA5  │
                    +-----+-----+         +-----+------+
                          │                     │
                          └────── XOR ──────────┘
                                  │
                                  ▼  bit_out (1 bit / clk)
```

- **Galois polynomial**: `x^8 + x^6 + x^5 + x^4 + 1` (mask `0xB8`, taps `[8,6,5,4]`).
- **Ring counter**: 8-bit rotate-left, feedback bit = `lfsr[0]` (entropy injection).
- **bit_out**: `lfsr[0] XOR ring[0]` (coupled output to break direct LFSR period).
- **N_CYCLES**: 1024 → 1024-bit stream → 128 × 8-bit symbol (max H = 8.0).

RTL+testbench (single SystemVerilog file): `anima-physics/fpga/cmos_8bit_ring_lfsr.sv`.

---

## 3. 4-Gate Verdict (frozen criteria)

| Gate | Criterion | Result |
| ---- | --------- | ------ |
| **G1** | positive entropy ≥ 6.0 bits | **PASS** — H = 7.000000 |
| **G2** | negative < positive (sign-flip) | **PASS** — H_neg=0.0 < H_pos=7.0 |
| **G3** | byte-identical 2-run sha256 | **PASS** — `968df826…6d131` (run1==run2) |
| **G4** | backend_name contract match | **PASS** — `local_iverilog_v13_0_lfsr8_galois_ring8_coupled` |

**Negative-falsify**: `+mode=negative` plusarg 경로에서 `rst` 가 영구 high → `bit_out`
조합회로가 `rst==1` 시 0 으로 강제 → 1024 cycle 모두 0 → 128 symbols 모두 0x00 →
unique=1, H=0.000. Sign-flip 메커니즘 정상 작동.

`positive_unique_symbols_of_256 = 128` (1024 비트 ÷ 8 = 128 symbols 각각 distinct →
H=log₂(128)=7.0 정확). Max-length sequence 보다 sample 수가 적어 H<8 이 정상.

---

## 4. Substrate-Backend Enum (Frozen Contract)

```hexa
substrate_backend ∈ {
    "local_hexa",                         // pure-hexa stub
    "cloud_sim_local_iverilog",           // ← THIS CYCLE
    "cloud_real_aws_fpga_NOT_AVAILABLE",  // Phase 2 (deferred)
}
```

`backend_name` (G4 contract):
- prefix: `local_iverilog_`
- middle: `<version>` (예: `v13_0`)
- suffix: `_lfsr8_galois_ring8_coupled`

---

## 5. raw#9 Strict Compliance

- 본 cycle 은 **raw#37 .py / .sh 절대 사용 안 함** (.roadmap directive #134).
- 모든 외부 호출은 `exec()` CLI: `iverilog`, `awk`, `grep`, `shasum`, `date`, `mkdir`, `which`, `test`.
- SystemVerilog 파일 `.sv` 는 raw#37 transient script 가 아니라 RTL **artifact** 분류
  (다른 sibling cycle 의 NgSpice netlist .cir 와 동일한 위치).
- `marker.json` 의 `"raw37_py_used": false` 필드로 명시.

실행 인터페이스:

```sh
~/.hx/packages/hexa/build/hexa.real run \
    /Users/ghost/core/anima/anima-physics/fpga/cloud_facade_poc.hexa
```

`hexa run` wrapper 는 nexus dispatch 단계에서 인자 파싱 충돌 (memory 노트 #182 와 동일
패턴) → bare-binary `~/.hx/packages/hexa/build/hexa.real` 로 우회. 이는 다른 sibling
cycle 과 동일한 운영 패턴.

---

## 6. raw#10 Honest Limitations

1. **iverilog = behavioral SV simulator** — real FPGA 의 timing / parasitic / power /
   place-and-route 영향 미반영. 논리 동등성만 검증.
2. **LFSR = deterministic PRNG** — Shannon H 는 generator output 의 sampling estimate
   이지 thermodynamic / quantum 진짜 entropy 가 아님.
3. **8-bit symbol on 1024-cycle stream** — alphabet 256, sample 128 → small-sample
   bias. 실제 FPGA 의 LUT-rich entropy probe (10⁶+ cycles, multi-channel) 와 직접
   비교 불가.
4. **`cloud_sim_local_iverilog` = facade naming**, NOT real cloud. AWS F1 신규차단 +
   F2 ($1.65/hr) 의도적 보류. cross-substrate Φ-proxy axis 가 quantum (entanglement
   entropy) / memristor (hysteresis area V·A) sibling 과 axis 동일성 없음 — 직접
   Φ 비교 불가.
5. **G1 threshold 6.0 conservative** — LFSR uniform-symbol 이론 max=8.0. 보수 기준
   적용으로 production drift 허용 폭 확보.

---

## 7. Next-Cycle Follow-up

- **Phase 2 candidate**: AWS F2 가입 후 `cloud_real_aws_fpga` backend swap.
  추정 비용 $1.65/hr × ~30min smoke = ~$0.83. 동일 4-gate, 동일 RTL.
- **Sibling pending (9-substrate completion)**:
  - `anima-physics/cmos/`     — NgSpice CMOS inverter ring oscillator (5-stage)
  - `anima-physics/arduino/`  — esp32-style 555 timer surrogate
- **Integration**: `anima-physics/physics_substrate_dispatch.hexa` 의
  `fpga_engine()` stub site 에 본 facade 호출 hook 추가 (별 cycle).

---

## 8. Files (frozen)

| Path | Role | LOC |
| ---- | ---- | --- |
| `anima-physics/fpga/cmos_8bit_ring_lfsr.sv` | SystemVerilog RTL+testbench (LFSR8+ring8) | ~85 |
| `anima-physics/fpga/cloud_facade_poc.hexa` | raw#9 strict facade orchestrator | ~280 |
| `anima-physics/docs/fpga_local_sim_landing.md` | this landing doc | ~140 |
| `state/v10_anima_physics_cloud_facade/poc_fpga_local_verilator/marker.json` | silent-land marker | ~46 |

---

## 9. Reproduction

```sh
cd /Users/ghost/core/anima
~/.hx/packages/hexa/build/hexa.real run \
    /Users/ghost/core/anima/anima-physics/fpga/cloud_facade_poc.hexa --selftest
~/.hx/packages/hexa/build/hexa.real run \
    /Users/ghost/core/anima/anima-physics/fpga/cloud_facade_poc.hexa
```

**Expected**: `4/4 PASS — POC fpga local-verilator VERIFIED`, marker JSON
written, byte-identical sha `968df826…6d131`.

mac local · $0.00 · iverilog v13.0 (already installed, no `brew install`
needed in this run).
