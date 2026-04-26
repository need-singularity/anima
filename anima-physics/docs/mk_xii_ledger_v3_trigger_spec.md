# Mk.XII INTEGRATION substrate witness ledger **v3 trigger spec**

**Cycle ID**: `mk_xii_ledger_v3_trigger_spec`
**Verdict (this cycle)**: `V3_TRIGGER_SPEC_FROZEN`
**Date**: 2026-04-26
**Cost**: $0.00 (mac local, spec-only — NO code emitted, NO ledger re-run)
**Operating mode**: raw#9 hexa-only strict (no python/sh helper); ω-cycle 6-step (step 4 = strict pattern false-positive defense)
**Supersedes / extends**: `mk_xii_substrate_witness_ledger_v2_landing.md` (commit `6559bb15`)
**Authority**: 본 spec 은 **frozen contract** 이며, 실제 v3 ledger 산출은 **manual trigger** (사용자가 cloud 가입 후 sibling A re-run + aggregator 재실행 시점) 발동 시 active. 본 cycle 에서는 **코드 미구현** — spec 만 frozen.

---

## 0. Executive summary

ledger v2 (commit `6559bb15`) `G5 LIVE_HW_WITNESS_RATE` 가 0/11 인 상태로 land 했다. 11 marker 모두 simulator / surrogate / dispatch / dry-run 경로이며, **real cloud HW 호출 0건**. v2 의 forward-compat schema 는 **aggregator 재실행만으로 LIVE column 자동 흡수**하도록 이미 설계되어 있다. 본 spec 은 그 *trigger 조건* 과 *재실행 명령* 과 *v3 산출물* 과 *알림 path* 와 *atlas append* 를 정확히 명시한다.

핵심: v3 trigger 는 **신규 코드를 작성하지 않는다**. v2 aggregator (`mk_xii_substrate_witness_ledger_aggregator_v2.hexa`) 는 verdict 문자열만 변하면 LIVE column 을 자동 채우는 idempotent function 이다. v3 = "input verdict 가 LIVE 패턴에 매칭되는 marker 가 존재할 때 v2 aggregator 를 실행한 결과".

---

## 1. Trigger 조건 (3가지)

aggregator v2 의 `classify_live_hw(verdict)` (lines 240-251) 는 다음 strict equality / prefix patterns 만 LIVE=1 로 분류한다. 그 외 모든 verdict 는 LIVE=0.

| # | substrate | marker file | LIVE 인정 verdict pattern | 발동 사용자 액션 |
|---|---|---|---|---|
| **T1** | quantum (IBM Q) | `state/v10_anima_physics_cloud_facade/phase2_ibmq_runtime/marker.json` | `^PHASE2_PASS_REAL.*$` (regex prefix; aggregator 의 `v.substring(0,16) == "PHASE2_PASS_REAL"`) | IBM Quantum 가입 + `IBM_QUANTUM_TOKEN` env + sibling A `cloud_real_ibm_q_facade.hexa` re-run |
| **T2a** | superconducting (Braket Rigetti) | `state/v10_anima_physics_cloud_facade/poc_superconducting_braket_rigetti/marker.json` | `^LIVE_PASS$` (strict equality) | AWS account + IAM keys + budget cap $5 + `ANIMA_BRAKET_DRY_RUN=0` + `cloud_facade_poc.hexa` re-run |
| **T2b** | analog (Braket QuEra Aquila) | `state/v10_anima_physics_cloud_facade/poc_analog_braket_quera/marker.json` | `^LIVE_PASS$` (strict equality) | AWS account + 위와 동일 + analog `cloud_facade_poc.hexa` re-run |
| **T3** | neuromorphic (Akida Cloud) | `state/v10_anima_physics_cloud_facade/poc_neuromorphic_akida_cloud/marker.json` | `^LIVE_PASS$` 또는 `^PASS_REAL_AKIDA.*$` (현재 aggregator 는 `^LIVE_PASS$` 만 인식; `PASS_REAL_AKIDA` 추가 인식은 v3.1 spec 에서 add) | BrainChip Akida Cloud 가입 + `BRAINCHIP_AKIDA_TOKEN` env + Linux/x86_64 또는 cloud SDK update |

**원자적 trigger condition (논리식)**:

```
v3_trigger := (T1 ∨ T2a ∨ T2b ∨ T3)

T1  := match(phase2_ibmq_runtime/marker.json::verdict, "^PHASE2_PASS_REAL.*$")
T2a := equal(poc_superconducting_braket_rigetti/marker.json::verdict, "LIVE_PASS")
T2b := equal(poc_analog_braket_quera/marker.json::verdict,            "LIVE_PASS")
T3  := equal(poc_neuromorphic_akida_cloud/marker.json::verdict,       "LIVE_PASS")
       ∨  match(poc_neuromorphic_akida_cloud/marker.json::verdict, "^PASS_REAL_AKIDA.*$")  // v3.1 only
```

**False-positive 방어** (ω-cycle step 4 = strict pattern guard):

- `PHASE2_DEGRADED_NO_TOKEN` 의 substring "PASS" 가 매칭되어 LIVE 로 잘못 분류되지 않는다 (aggregator 는 substring search 가 아닌 strict equality + 16-char prefix 만 사용).
- `PASS` (qiskit_aer statevector) 와 `PASS_DEGRADED_SDK_FALLBACK` (perceval) 와 `INTEGRATED_PASS` 는 **simulator** 이며 LIVE pattern 에 매칭되지 않는다 (G5 false-positive 차단).
- v2 aggregator line 240-251 의 hard-coded pattern set 변경 없이 v3 trigger 그대로 동작.

---

## 2. 자동 (manual-invoked) re-run 명령

사용자가 cloud 가입 + sibling A re-run 으로 marker 가 위 LIVE pattern 에 매칭되도록 갱신된 직후, **다음 1줄 명령**을 실행한다:

```bash
cd /Users/ghost/core/anima && \
  ~/.hx/packages/hexa/build/hexa.real run \
    anima-physics/tool/mk_xii_substrate_witness_ledger_aggregator_v2.hexa \
    --ledger-out=state/v10_anima_physics_cloud_facade/integration_ledger/witness_ledger_v3.json \
    --marker-out=state/v10_anima_physics_cloud_facade/integration_ledger/marker_v3.json \
    --version-tag=v3
```

**근거**:

- `mk_xii_substrate_witness_ledger_aggregator_v2.hexa` 는 forward-compat schema 로 작성되어 있다 (v2 landing doc §5; v2 marker `forward-compatible schema → v3+ auto-absorbs LIVE column when IBM Q / AWS Braket / Akida creds added`).
- aggregator 의 `classify_live_hw()` 는 verdict 문자열만 입력받아 LIVE 1/0 산출; verdict pattern 매칭 결과가 자동으로 `live_hw_called`, `live_hw_witness.rate_x1000`, `actual_backend_chip_ids[]` 등에 반영.
- v2 → v3 transition = **input marker 변경 + 동일 aggregator 재실행** (코드 변경 0 line). 본 cycle = "이 transition 이 자동" 임을 frozen 계약.
- bare-binary bypass (`~/.hx/packages/hexa/build/hexa.real run`) 필수 — `hexa run` wrapper 0%-CPU hang 회피 (v2 landing doc §raw10 caveat 그대로).

**CLI flag 보강 (v3 trigger 시 권장 추가)**:

| flag | default (v2) | v3 권장 |
|---|---|---|
| `--ledger-out=` | hard-coded `witness_ledger_v2.json` | **`witness_ledger_v3.json`** (override) |
| `--marker-out=` | hard-coded `marker_v2.json` | **`marker_v3.json`** (override) |
| `--version-tag=` | `v2` | **`v3`** (body 내 `ledger_version` 필드, supersedes 체인 |

> 참고: 현 v2 aggregator 가 위 3 flag 를 실제로 parse 하는지는 source 점검 필요. 미지원 시 v3 trigger 는 **aggregator v2 → v2.1 minor patch** (3 flag override 추가, schema 변경 0) 가 prerequisite. 이 검증은 LIVE 발생 시점 1회 수행 (raw#10 honest §8).

---

## 3. v3 산출물 (자동 생성 예상)

trigger 발동 + aggregator 재실행 후 다음 파일들이 생성/append:

| # | path | 설명 | 예상 변경 |
|---|---|---|---|
| 1 | `state/v10_anima_physics_cloud_facade/integration_ledger/witness_ledger_v3.json` | v3 ledger body | `ledger_version: "v3"`, `supersedes: "v2 (..., body_sha=df545c5e..., fingerprint=661882989)"`, `n_marker_total: 11` (또는 +1, sibling re-run 후 marker 가 추가 생성된 경우), `live_hw_witness.n_live ≥ 1`, `actual_backend_chip_ids: ["ibm_brisbane", ...]` 채워짐 |
| 2 | `state/v10_anima_physics_cloud_facade/integration_ledger/witness_ledger_v3.json.meta` | sidecar meta | timestamp, host, hexa version |
| 3 | `state/v10_anima_physics_cloud_facade/integration_ledger/marker_v3.json` | v3 marker | `verdict: "LEDGER_LIVE_INITIAL"` (아래 §4 threshold 분기에 따라) 또는 `LEDGER_LIVE_BROAD` / `LEDGER_LIVE_FULL`, `live_hw_witness_rate_x1000 > 0`, `n_live_hw ≥ 1`, `ledger_fingerprint_sha256_v3` (v2 와 distinct) |
| 4 | `state/v10_anima_physics_cloud_facade/integration_ledger/v3_trigger_alert.txt` | (선택; CLI fallback alert) | 1-line ascii: `v3 LIVE trigger detected at <timestamp>; n_live=<N>/11; verdict=<LIVE_INITIAL|BROAD|FULL>` |

v2 의 두 file (`witness_ledger_v2.json`, `marker_v2.json`) 는 **삭제 금지** (supersession ≠ deletion; v1 → v2 보존 패턴 그대로).

---

## 4. G5 threshold 도입 (v3 시점에 활성)

v2 는 `G5_LIVE_HW_WITNESS_RATE = "MEASURE_ONLY_NO_THRESHOLD"` 로 설정되어 있다. v3 부터 다음 임계값을 활성화:

| threshold | 조건 | marker verdict | 의미 |
|---|---|---|---|
| **L1: LIVE_INITIAL** | `live_rate ≥ 1/11` (≥ 91 rate_x1000) | `LEDGER_LIVE_INITIAL` | 단일 cloud 호출 성공; substrate-multiplicity 첫 LIVE witness |
| **L2: LIVE_BROAD** | `live_rate ≥ 3/11` (≥ 273 rate_x1000) | `LEDGER_LIVE_BROAD` | 3개 cloud substrate 동시 LIVE; multi-vendor 검증 |
| **L3: LIVE_FULL** | `live_rate ≥ 9/11` (= cloud-eligible all-PASS) ※ memristor/cmos/fpga/arduino 는 local ngspice/iverilog 이라 LIVE 적용 불가; integration meta-row 도 외부; effective denom = 4 (T1+T2a+T2b+T3) → 4/4 = 9/11 환산 | `LEDGER_LIVE_FULL` | 모든 cloud substrate (IBM Q + Braket Rigetti + Braket QuEra + Akida) LIVE |

**환산 식**:
```
n_cloud_eligible = 4   // {T1, T2a, T2b, T3}
n_local_only     = 7   // {qiskit_aer, perceval, memristor, cmos, fpga, arduino, integration}
n_total_marker   = 11

live_rate_x1000_threshold:
  L1_INITIAL = ⌈ (1 / 11) * 1000 ⌉ =  91
  L2_BROAD   = ⌈ (3 / 11) * 1000 ⌉ = 273
  L3_FULL    = ⌈ (9 / 11) * 1000 ⌉ = 819   // 또는 4/4 cloud-eligible 등가
```

**raw#10 honest**: L3 의 9/11 은 *cloud-eligible only* 4/4 와 등가이므로 (7 local 은 LIVE 적용 불가), spec 상 정확한 verbal 표현은 "cloud-eligible 4/4 LIVE = effective FULL". marker 본문 `verdict_rationale` 필드에 이 환산 명시 권장.

---

## 5. 사용자 alert path

v3 trigger 가 발동되어 ledger 가 생성된 직후, 사용자에게 다음 3 path 중 ≥ 1 로 알린다:

### 5.1 Terminal stdout 안내 (CLI tool fallback) — **PRIMARY**

aggregator v2 자체가 `--version-tag=v3` invocation 시 final stdout 에 다음 라인 emit (v2 → v2.1 minor patch 필요; spec only):

```
[mk_xii ledger v3] LIVE_HW_WITNESS upgraded: 0/11 → <N>/11
[mk_xii ledger v3] new verdict: <LEDGER_LIVE_INITIAL|BROAD|FULL>
[mk_xii ledger v3] artifacts:
  - state/v10_anima_physics_cloud_facade/integration_ledger/witness_ledger_v3.json
  - state/v10_anima_physics_cloud_facade/integration_ledger/marker_v3.json
[mk_xii ledger v3] next: atlas_convergence_witness.jsonl append (see §6)
```

### 5.2 Alert text file — **SECONDARY**

```
state/v10_anima_physics_cloud_facade/integration_ledger/v3_trigger_alert.txt
```

내용 (1-line ascii, 사용자 `cat` read 용):

```
v3 LIVE trigger detected at 2026-MM-DDTHH:MM:SSZ; n_live=<N>/11; verdict=<LEDGER_LIVE_INITIAL|BROAD|FULL>; aggregate-fingerprint=<FNV32>; ledger=witness_ledger_v3.json
```

### 5.3 Email 알림 — **SPEC ONLY (구현 없음)**

```
to:      nerve011235@gmail.com
subject: [anima Mk.XII] LIVE_HW substrate witness — v3 ledger landed
body:
  v3 ledger has been generated.
  n_live: <N>/11
  verdict: <LEDGER_LIVE_INITIAL|BROAD|FULL>
  fingerprint: <FNV32>
  artifacts:
    state/v10_anima_physics_cloud_facade/integration_ledger/witness_ledger_v3.json
    state/v10_anima_physics_cloud_facade/integration_ledger/marker_v3.json
  next: atlas_convergence_witness.jsonl append (see spec §6)
delivery_method: NOT_IMPLEMENTED   // sendmail/SMTP 미구현; raw#10 honest §8.4
```

> raw#10 honest: 본 spec 은 email 전송 코드 미작성 (raw#9 hexa-only 환경에서 SMTP client 부재). future v4 spec 에서 mac `mail` CLI 또는 외부 SMTP relay 통합 시 구현. **현재는 spec text 만 frozen**.

---

## 6. Atlas witness append 자동화

v3 ledger landed 직후 다음 line 을 `state/atlas_convergence_witness.jsonl` 에 **append-only** (기존 line 변경 금지):

```jsonl
{"witness_id":"anima_physics_cloud_facade_substrate_multiplicity_v3","timestamp":"<ISO_UTC>","level":"<integration_live_initial|integration_live_broad|integration_live_full>","tier":"H-CX (cloud-facade substrate-multiplicity, LIVE_HW witness rate ≥ <X>/11)","source":"anima-physics/tool/mk_xii_substrate_witness_ledger_aggregator_v2.hexa","ledger_v3_fingerprint_fnv32":<FNV32>,"ledger_v3_body_sha256":"<SHA256>","n_substrate_distinct":9,"n_marker_aggregated":<11_or_more>,"live_hw_witness_rate_x1000":<rate>,"actual_backend_chip_ids":[<chip_id_list>],"phi_proxy_cross_comparable":false,"commit_sha":"<HEAD_after_v3_land>","github_url":"https://github.com/need-singularity/anima/tree/main/anima-physics","raw10_honest":"v3 LIVE_HW <N>/11 첫 cloud 호출; cross-substrate Φ 비교 여전히 invalid; v3.1 trigger=추가 substrate LIVE_PASS 또는 LIVE_FULL 도달"}
```

**level 결정 규칙** (G5 threshold 와 1:1 대응):

| live_rate | level | tier prefix |
|---|---|---|
| 1/11 ~ 2/11 | `integration_live_initial` | H-CX (LIVE_INITIAL) |
| 3/11 ~ 8/11 | `integration_live_broad` | H-CX (LIVE_BROAD) |
| 9/11 (effective 4/4 cloud) | `integration_live_full` | H-CX (LIVE_FULL) |

**선례 패턴 재사용**: sibling B (commit `26cdc612`) 가 v2 entry 를 `level=architectural_reference` 로 append 한 패턴. v3 는 동일 구조 + level upgrade. atlas line count: v2 직후 40 → v3 후 41 예상.

> 본 append 는 silent-land marker `state/v10_anima_physics_cloud_facade/integration_ledger/atlas_witness_appended_v3.json` 와 **함께** 산출 (sibling B precedent: `atlas_witness_appended.json` 패턴 재사용).

---

## 7. 자동화 vs Manual 결정

### 7.1 본 spec = **manual trigger**

- 사용자가 cloud 가입 + sibling A re-run 후 **의식적으로** v2 aggregator 를 v3 모드로 invoke.
- 이유: cloud 가입은 비동기 사용자 액션 (IBM Q free-tier 승인 / AWS budget cap 설정 / Akida signup) 이라 시점 예측 불가. 자동 file watcher 는 가입 완료 *전에* false trigger 위험.
- 사용자 cost: 1 명령 (1 줄), $0 (mac local).

### 7.2 Future v4 spec = **automatic file watcher** (분리)

- `fswatch state/v10_anima_physics_cloud_facade/{phase2_ibmq_runtime,poc_superconducting_braket_rigetti,poc_analog_braket_quera,poc_neuromorphic_akida_cloud}/marker.json` event → verdict pattern check → match 시 aggregator 자동 invoke.
- **본 cycle scope 외**. v4 spec 으로 별도 cycle 진행 시 작성.
- 위험: false trigger (e.g., partial write) 시 invalid v3 ledger 생성. v4 에서는 `flock` + `marker.json.lock` + 2-pass sha 검증 필수.

---

## 8. raw#10 honest (spec 자체)

본 spec 은 **frozen contract** 이며, 다음 한계를 명시한다:

1. **코드 미구현**: v3 trigger spec 은 어떤 신규 hexa/py/sh 도 작성하지 않는다. v3 산출은 v2 aggregator 의 forward-compat 영역에서 자동 흡수되도록 설계되었으나, 그 *흡수가 실제로 일어나는지*는 LIVE 발생 시점 1회 검증되어야 한다.

2. **LIVE marker schema 가정**: T1/T2a/T2b/T3 의 verdict pattern (`^PHASE2_PASS_REAL.*$`, `^LIVE_PASS$`) 이 sibling A/D/E re-run 시 정확히 emit 되는지는 **현재 가정**. 각 sibling probe 의 raw probe stdout 이 위 pattern 에 정확히 land 하는지는 LIVE 발생 직전 dry-run mode (`ANIMA_BRAKET_DRY_RUN=1` + token absent) 에서 1회 simulation 권장.

3. **v2 → v3 transition 미검증**: aggregator v2 의 forward-compat 검증 범위는 v1 → v2 transition (8 marker → 11 marker, 3 row 추가) 에 한정. v2 → v3 transition (LIVE column 활성화, `actual_backend_chip_ids[]` 비어있던 array 채움) 은 미검증; **실 LIVE 후 첫 aggregator 재실행이 정합성 첫 검증**. False output (예: live_rate 가 0/11 그대로 산출되는 silent fail) 위험을 명시.

4. **email 알림 미구현**: §5.3 spec 만 작성; sendmail/SMTP code 0 line. 사용자 알림은 §5.1 stdout + §5.2 alert.txt 만 active.

5. **aggregator CLI flag 미검증**: §2 의 `--ledger-out=` / `--marker-out=` / `--version-tag=` 3 flag 가 v2 aggregator 에서 실제로 parse 되는지는 미검증. 미지원 시 v2 aggregator 는 **hard-coded path** 로 v2 file 을 덮어쓸 위험. 이 경우 **prerequisite minor patch**: v2 → v2.1 (3 flag CLI parsing 추가, schema 변경 0). 이 patch 는 v3 trigger 발동 *직전* 1회 수행. 본 spec 상 명시적 prerequisite.

6. **G5 threshold L3 (9/11) 의미 모호**: 9/11 = cloud-eligible 4/4 + local 5/7 (memristor/cmos/fpga/arduino + integration meta) 가 LIVE 가능하지 않으므로, "9/11 LIVE FULL" 은 *effective 4/4 cloud + 5 local-treated-as-PASS* 환산. 본 spec §4 raw#10 caveat 명시.

7. **cross-substrate Φ 비교 여전히 invalid**: v2 의 `phi_proxy_cross_comparable=false` 는 v3 에서도 그대로. LIVE 호출이 발생해도 substrate Φ axes (entanglement entropy / Fock entropy / hysteresis area / period jitter / LFSR Shannon H / NE555 duty drift) 는 cross-comparable 하지 않다. v3 ledger body 도 이 필드 `false` 유지 필수.

8. **Atlas witness append 의존성**: §6 의 atlas append 는 **별도 cycle / 별도 subagent** (sibling B 와 동일 분리). v3 trigger spec 은 *append 의 contract 만* frozen; 실 append 는 v3 ledger landed 후 별도 cycle 에서 수행.

9. **Akida `^PASS_REAL_AKIDA.*$` pattern 추가**: §1 T3 의 `PASS_REAL_AKIDA*` prefix 는 현재 aggregator v2 가 인식하지 못함 (v2 의 `classify_live_hw()` 는 `LIVE_PASS` strict equality 만). v3.1 spec 으로 분리하거나, T3 의 LIVE marker 는 `LIVE_PASS` 로만 emit 하도록 sibling D probe re-design 권장.

10. **본 spec 은 단일 monotonic chain 가정**: v2 → v3 → v3.1 → v4 순서. branch (예: v3-IBMQ-only + v3-Braket-only 동시 land) 는 spec 외. 동시 발생 시 두 trigger 모두 1 aggregator invocation 으로 흡수 (single ledger v3 file).

---

## 9. ω-cycle 6-step (본 spec 작성 cycle)

| step | role | 본 cycle 적용 |
|---|---|---|
| 1. observe | 현 상태 관측 | v2 G5=0/11, forward-compat schema 존재, 11 marker 모두 simulator/surrogate |
| 2. hypothesize | 가설 | "v3 trigger 는 새 코드 0 line + aggregator 재실행 1회로 충족 가능" |
| 3. design | 설계 | §1-§7 6 영역 (trigger 조건 / 명령 / 산출물 / threshold / alert / atlas / manual-vs-auto) |
| 4. **falsify** (defensive) | strict pattern false-positive 차단 | §1 의 strict equality + 16-char prefix; "PHASE2_DEGRADED_NO_TOKEN" substring "PASS" non-match 명시 (line 240-251 aggregator 코드 인용) |
| 5. close | 본 spec land | doc + silent-land marker 산출; v2 ledger 미수정; v3 산출 0 (실 LIVE 미발생) |
| 6. integrate | 후속 | LIVE 발생 후 manual trigger → §2 1줄 명령 → §3 산출 → §6 atlas append |

**ω-cycle iter count**: 1 (1-pass; spec 작성에 falsify pattern 이미 v2 aggregator 코드 라인 240-251 에 hard-coded 되어 있어 추가 iteration 불필요).

---

## 10. 다음 cycle (실 LIVE 후 manual trigger)

**Pre-flight checklist** (사용자 가입 + sibling re-run 직전):

1. v2 aggregator CLI flag 지원 여부 검증 (§8.5). 미지원 시 v2.1 minor patch 우선.
2. T1/T2a/T2b/T3 sibling probe 가 LIVE pattern 정확 emit 하는지 dry-run simulation (token mock, verdict 만 강제 set 후 aggregator output 검사).
3. cost cap 확인 (IBM Q free-tier / Braket budget $5 / Akida signup free).

**Trigger 발동 절차** (사용자):

1. cloud 가입 (IBM Q + AWS Braket + BrainChip Akida 중 1개 이상).
2. token / IAM 환경변수 설정.
3. sibling A / D / E `cloud_facade_poc.hexa` re-run (각 substrate 별 1회).
4. `state/v10_anima_physics_cloud_facade/<sub_dir>/marker.json::verdict` 가 LIVE pattern 매칭 확인.
5. §2 의 1-줄 aggregator 재실행 명령.
6. §3 산출물 검증 (`witness_ledger_v3.json` body sha + fingerprint v2 와 distinct).
7. §6 atlas append 별도 cycle / subagent 위임.

**예상 cost**: $0 ~ $5 (사용자 cloud 호출 비용; aggregator 재실행 자체는 mac local $0).
**예상 wallclock**: aggregator re-run < 5 sec; atlas append < 1 sec; 사용자 가입 + sibling re-run 은 cloud queue / signup 승인에 의존.

---

## 11. 참조 / 선례

- v1 ledger landing: `anima-physics/docs/mk_xii_substrate_witness_ledger_landing.md` (commit `62c03f6b`)
- v2 ledger landing: `anima-physics/docs/mk_xii_substrate_witness_ledger_v2_landing.md` (commit `6559bb15`)
- v2 atlas append: commit `26cdc612` (sibling B); pattern `level=architectural_reference`
- aggregator v2 source: `anima-physics/tool/mk_xii_substrate_witness_ledger_aggregator_v2.hexa` (lines 240-251 = `classify_live_hw` strict pattern matcher)
- v2 ledger body: `state/v10_anima_physics_cloud_facade/integration_ledger/witness_ledger_v2.json` (fingerprint `661882989`, body sha `df545c5e15404539cea6f1b61c8d46565089f6d266277234b50a124d066e49ba`)
- silent-land marker (this cycle): `state/v10_anima_physics_cloud_facade/integration_ledger/v3_trigger_spec_landed.json`
- **§8.5 + §2 CLI flag 결정 후속 (v2.1 prerequisite)**: `anima-physics/docs/mk_xii_substrate_witness_ledger_aggregator_v2_1_prerequisite_landing.md` (2026-04-27) — env-var override 4종 (`LEDGER_VERSION`/`LEDGER_CYCLE_ID_OVERRIDE`/`LEDGER_SUPERSEDES_OVERRIDE`/`MARKER_OUT`) 추가, v2 byte-identical PASS, v3 dry-run synthetic LIVE PASS. spec §2 CLI flag 형식은 invalid (argv parse 미지원) → env-var form 으로 정정. 사용자 cloud signup 도착 시 그대로 발동 가능.

---

## 12. 본 cycle marker (silent-land)

frozen spec 만 산출되었으며, 다음 marker 가 silent-land 보호 line:

```
state/v10_anima_physics_cloud_facade/integration_ledger/v3_trigger_spec_landed.json
```

verdict: `V3_TRIGGER_SPEC_FROZEN`
gates: doc 존재 ∧ §1-§11 11 sections 모두 작성 ∧ §1 trigger 조건 3 패턴 명시 ∧ §2 1줄 재실행 명령 명시 ∧ §4 G5 threshold 3-tier 명시 ∧ §8 raw#10 10 항목 명시.

---

**End of v3 trigger spec.**
