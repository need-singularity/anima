# Mk.XII INTEGRATION substrate witness ledger v2 landing

**Cycle ID**: `mk_xii_substrate_witness_ledger_v2`
**Verdict**: `LEDGER_LANDED_V2`
**Date**: 2026-04-26
**Cost**: $0.00 (mac local, aggregator only)
**Supersedes**: v1 (`witness_ledger_v1.json`, fingerprint=470781997, body_sha=264f5cf7…) — preserved, NOT modified

## 1. v1 → v2 diff

| Axis | v1 | v2 |
|---|---|---|
| Manifest rows | 8 | **11** (+ cmos / fpga / arduino) |
| Distinct substrate count | 6 (quantum/photonic/neuromorphic/superconducting/analog/memristor) + 1 meta (integration) | **9** (+ cmos / fpga / arduino) + 1 meta |
| Ledger gates | G1-G4 | **G1-G5** (+ LIVE_HW_WITNESS_RATE) |
| Schema fields | (basic) | + `supersedes`, `n_marker_total`, `phi_proxy_cross_comparable`, `live_hw_witness{}`, `fnv32_chained_v2` |
| FNV-32 fingerprint | 470781997 (8 inputs) | **661882989** (11 inputs) — distinct hash space confirmed |
| Body SHA-256 | 264f5cf7… | df545c5e15404539cea6f1b61c8d46565089f6d266277234b50a124d066e49ba |
| live_hw_witness rate | (not measured) | **0 / 11** (measure-only, no threshold) |
| Coverage gate | 7/9 = PASS | **9/9 = PASS** (G1_actual_x1000=9000 vs ≥6000) |

3개 race-landed sibling marker (cmos / fpga / arduino) 가 v1 land 사이에 추가됨; v2 manifest 가 forward-compatible 하게 흡수.

## 2. 11-row by_substrate matrix

| # | substrate | sub_dir | verdict | gates | live_hw_called |
|---|---|---|---|---|---|
| 1 | quantum | poc_quantum_qiskit_aer | PASS | 4/4 | 0 |
| 2 | quantum | phase2_ibmq_runtime | PHASE2_DEGRADED_NO_TOKEN | 0/4 | 0 |
| 3 | photonic | poc_photonic_strawberryfields | PASS_DEGRADED_SDK_FALLBACK | 4/4 | 0 |
| 4 | neuromorphic | poc_neuromorphic_akida_cloud | PREP_READY_AWAITING_USER_SIGNUP | 4/4 | 0 |
| 5 | superconducting | poc_superconducting_braket_rigetti | PREP_NO_CREDS_DEGRADED | 0/4 | 0 |
| 6 | analog | poc_analog_braket_quera | PREP_NO_CREDS_DEGRADED | 0/4 | 0 |
| 7 | memristor | poc_memristor_local_ngspice | PASS | 4/4 | 0 |
| 8 | integration | integration_physics_hexa | INTEGRATED_PASS | 4/4 | 0 |
| 9 | **cmos** | **poc_cmos_local_ngspice** | **PASS** | **4/4** | **0** |
| 10 | **fpga** | **poc_fpga_local_verilator** | **PASS** | **4/4** | **0** |
| 11 | **arduino** | **poc_arduino_local_ngspice** | **PASS** | **4/4** | **0** |

Verdict 다양성: `PASS` ×5, `INTEGRATED_PASS` ×1, `PASS_DEGRADED_SDK_FALLBACK` ×1, `PREP_READY_AWAITING_USER_SIGNUP` ×1, `PREP_NO_CREDS_DEGRADED` ×2, `PHASE2_DEGRADED_NO_TOKEN` ×1 — G2 honesty 6 tier 모두 보존.

## 3. 5-gate (G1-G5) verdict

| Gate | Definition | Result | Detail |
|---|---|---|---|
| **G1 LEDGER_COVERAGE** | n_landed_full + n_prep_only ≥ 6/9 | **PASS** | 6 + 3 = 9/9 (actual_x1000=9000 vs min 6000) |
| **G2 LEDGER_HONESTY** | 모든 6 verdict tier 보존 (no cherry-pick) | **PASS** | 11/11 manifest row entries emitted regardless of verdict_class |
| **G3 LEDGER_BYTE_IDENTICAL** | 2-run sha256 timestamp-free body 동일 | **PASS** | run1=run2=`df545c5e15404539cea6f1b61c8d46565089f6d266277234b50a124d066e49ba` |
| **G4 LEDGER_FINGERPRINT_FNV32** | chained FNV-32 over 11-input sha sequence | **EMITTED** | `661882989` (distinct from v1's `470781997` — v2 hash space confirmed) |
| **G5 LIVE_HW_WITNESS_RATE** | strict pattern match against ^PASS_REAL_QUANTUM_HARDWARE$ \| ^LIVE_PASS$ \| ^PHASE2_PASS_REAL.*$ | **MEASURE_ONLY** | 0/11 (rate_x1000=0) |

Aggregate per-entry gate pass rates (×1000): G1=727, G2=727, G3=727, G4=727 (분모=11; 8/11 entries 가 4/4 gate pass).

## 4. live_hw_witness section

```json
{
  "rate_x1000": 0,
  "n_live": 0,
  "n_simulator_or_surrogate": 11,
  "n_marker_total": 11,
  "strict_pattern_set": [
    "^PASS_REAL_QUANTUM_HARDWARE$",
    "^LIVE_PASS$",
    "^PHASE2_PASS_REAL.*$"
  ],
  "actual_backend_chip_ids": []
}
```

**현재 0/11 (모두 simulator / surrogate)**. Strict pattern matching 으로 false-positive 차단:
- `PHASE2_DEGRADED_NO_TOKEN` 의 `PASS` 부분문자열은 무시 (verbatim equality / strict prefix only).
- `PASS` (단순) 도 live 아님 — local simulator 만 통과 시.

### Auto-promotion paths (next-cycle 자동 흡수)

1. **IBM Quantum signup + `IBM_QUANTUM_TOKEN` env** → `phase2_ibmq_runtime` verdict 가 `PHASE2_PASS_REAL_<BACKEND>` 로 전환 → live_rate `0/11 → 1/11`
2. **AWS Braket creds + budget cap** → `poc_superconducting_braket_rigetti` 또는 `poc_analog_braket_quera` verdict 가 `LIVE_PASS` 로 전환 → live_rate `0/11 → 1/11` 또는 `2/11`
3. **BrainChip Akida Cloud signup + `BRAINCHIP_AKIDA_TOKEN` env** → `poc_neuromorphic_akida_cloud` verdict 가 `LIVE_PASS` 로 전환 → live_rate `+1/11`

Aggregator re-run 한 번이면 자동 promotion (다른 코드 변경 없음).

## 5. phi_proxy_cross_comparable=false 정당화

각 substrate Φ-proxy axis 가 본질적으로 다른 물리 양:

| Substrate | Φ-proxy axis | Unit |
|---|---|---|
| quantum | entanglement entropy | nats |
| photonic | Fock-state entropy | nats |
| neuromorphic | spike-train entropy | bits/event |
| superconducting | qubit decoherence rate | s⁻¹ |
| analog | Rydberg-array entropy | nats |
| memristor | hysteresis loop area | V·A·s |
| **cmos** | period jitter | seconds |
| **fpga** | LFSR Shannon H | bits/symbol |
| **arduino** | NE555 duty-cycle drift | dimensionless |

Cross-substrate 직접 수치 비교 (e.g., "quantum Φ=0.X > cmos Φ=0.Y") **NOT VALID**. v2 ledger = COVER-COUNT + per-substrate gate verdict + LIVE-rate 만 집계.

## 6. user_action_pending auto-harvest path

Aggregator 가 각 marker 의 `.user_action_required` 필드 자동 수집:

```
state/v10_anima_physics_cloud_facade/<sub_dir>/marker.json → .user_action_required
```

v2 ledger 결과 (1건):
- `BrainChip Akida Cloud 계정 가입 후 BRAINCHIP_AKIDA_TOKEN 환경변수 설정 (또는 Linux/x86_64 환경에서 pip install akida)`

암묵 user_action (marker 에는 없으나 ledger landing 명시):
- AWS account + IAM keys + budget cap (Braket Rigetti Ankaa-3 + Braket QuEra Aquila)
- IBM Quantum account + IBM_QUANTUM_TOKEN env (ibmq_runtime Phase 2)

## 7. Future v3 candidates

1. **LIVE re-run sibling A**: IBM Q signup 후 sibling A `phase2_ibmq_runtime` re-run → marker.verdict shifts → v3 ledger live_rate 0/11 → 1/11.
2. **Phase 2 fan-out**: AWS Braket creds 추가 → Rigetti Ankaa-3 + QuEra Aquila LIVE → live_rate +2/11.
3. **`.roadmap` entry**: v3 ledger 시 `mk_xii_substrate_witness_ledger_v3` 등록 (LIVE 임계 cross 시점).
4. **Per-substrate Φ normalization research**: 본질적 axis 차이 인정하지만 substrate-internal 단조 변환 후 ranking-only 비교 가능 여부 사전 등록.
5. **ESP32 / 추가 hardware substrate**: Arduino 후 ESP32 양자 noise probe (`anima-physics/esp32/qrng_bridge.hexa`) 통합 시 12-marker / 10-substrate v3.

## 8. raw#10 honest

- v2 = aggregator only; 본질 unchanged from v1 (cross-substrate Φ 비교 invalid 그대로)
- 11 marker 중 LIVE 0건 (G5=0/11), real-hardware witness 0
- v1 본 보존 (supersession ≠ deletion; `witness_ledger_v1.json` + `.meta` 양 파일 그대로)
- 9/9 substrate distinct cover 는 cycle achievement 지만 verdict 다양성 (PASS ×5 + INTEGRATED_PASS ×1 + PASS_DEGRADED_SDK_FALLBACK ×1 + PREP_* ×3 + PHASE2_DEGRADED_NO_TOKEN ×1) 그대로 reflect — 6/9 만 full-pass, 3/9 prep_only
- forward-compat schema → v3+ 에서 LIVE column 자동 흡수 (aggregator 재실행만)
- aggregator 의 `fexists(p)` / `jq_get(...)` 가 `hexa` default container 환경에서 cwd-relative path 미해결 → `~/.hx/packages/hexa/build/hexa.real run` bare-binary bypass 필수 (G8 cycle #182, arduino sibling G-arduino 와 동일 precedent). v1 도 동일한 bypass 환경에서 land 됨
- raw#37 .py / .sh 0건 (`grep -c "exec(\"python"` = 0, `grep -c "exec(\".*\.sh"` = 0)
- integration meta-row 는 9-target enum 외부 (TARGET_SUBSTRATES filter 로 분리). full-pass 6건 = quantum + photonic + memristor + cmos + fpga + arduino 만 카운트

## 9. Byte-identical 검증 절차

```bash
# bare-binary bypass (default container missing utilities)
~/.hx/packages/hexa/build/hexa.real run \
    anima-physics/tool/mk_xii_substrate_witness_ledger_aggregator_v2.hexa

# 1차 sha
SHA1=$(shasum -a 256 state/v10_anima_physics_cloud_facade/integration_ledger/witness_ledger_v2.json | awk '{print $1}')

# 재실행
~/.hx/packages/hexa/build/hexa.real run \
    anima-physics/tool/mk_xii_substrate_witness_ledger_aggregator_v2.hexa

# 2차 sha
SHA2=$(shasum -a 256 state/v10_anima_physics_cloud_facade/integration_ledger/witness_ledger_v2.json | awk '{print $1}')

# 일치 확인
[ "$SHA1" = "$SHA2" ] && echo "BYTE_IDENTICAL_OK" || echo "BYTE_IDENTICAL_FAIL"
# expected: SHA1 = SHA2 = df545c5e15404539cea6f1b61c8d46565089f6d266277234b50a124d066e49ba
```

Sidecar `.meta` 만 timestamp 를 포함 (그 외 ledger body 는 timestamp-free) — G3 verifiable.

## 10. Sibling cycle cross-link

- **sibling I (v1 ledger)**: `anima-physics/tool/mk_xii_substrate_witness_ledger_aggregator.hexa` (raw#9, 26.6KB) + `state/v10_anima_physics_cloud_facade/integration_ledger/witness_ledger_v1.json` (8 marker, fingerprint=470781997). v2 가 supersede 하되 v1 본 보존.
- **6 substrate prep**: poc_quantum_qiskit_aer / phase2_ibmq_runtime / poc_photonic_strawberryfields / poc_neuromorphic_akida_cloud / poc_superconducting_braket_rigetti / poc_analog_braket_quera / poc_memristor_local_ngspice (race 직전 8 marker)
- **3 hexa-only G/H/I siblings**: G-cmos (`poc_cmos_local_ngspice`) + G-fpga (`poc_fpga_local_verilator`) + G-arduino (`poc_arduino_local_ngspice`) — 본 v2 cycle 이 aggregate
- **integration meta**: `integration_physics_hexa` (4 G_BACKWARD_COMPAT-style gate, meta-row, 9-target enum 외부)

---

**Files**:
- `anima-physics/tool/mk_xii_substrate_witness_ledger_aggregator_v2.hexa` (raw#9, 487 lines)
- `anima-physics/docs/mk_xii_substrate_witness_ledger_v2_landing.md` (this file)
- `state/v10_anima_physics_cloud_facade/integration_ledger/marker_v2.json`
- `state/v10_anima_physics_cloud_facade/integration_ledger/witness_ledger_v2.json` (body_sha=df545c5e1540…)
- `state/v10_anima_physics_cloud_facade/integration_ledger/witness_ledger_v2.json.meta`

**Preserved (NOT modified)**:
- `state/v10_anima_physics_cloud_facade/integration_ledger/witness_ledger_v1.json` (fingerprint=470781997)
- `state/v10_anima_physics_cloud_facade/integration_ledger/witness_ledger_v1.json.meta`
- `state/v10_anima_physics_cloud_facade/integration_ledger/marker.json` (v1 marker)
