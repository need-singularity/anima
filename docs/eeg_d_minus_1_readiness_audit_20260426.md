# EEG D-1 Readiness Audit — Cyton+Daisy 125Hz Refresh (axis 88)

> **scope**: EEG hardware (OpenBCI Cyton+Daisy 16ch, BrainFlow direct measurement) 도착 D-1 readiness audit refresh. MEMORY axis 77 의 **125Hz 정정** (이전 250Hz 잘못) 반영 + venv-eeg regression 탐지 + 사용자 도착 시 첫 명령어 actionable list 생성.
> **created**: 2026-04-26 (ω-cycle session, axis 88)
> **raw_rank**: 9 docs (한글 OK)
> **status**: **REFRESH_AUDIT** — predecessor `eeg_d_day_readiness_check_landing.md` (#209) 후속, 변경된 spec/regression 만 delta audit
> **predecessor**: `anima-clm-eeg/docs/eeg_d_day_readiness_check_landing.md` (sha `d03f5c45…`, verdict=PARTIAL 21/27)
> **trigger**: (1) MEMORY axis 77 — Cyton+Daisy 250Hz → 125Hz 정정. (2) brainflow venv distutils regression. (3) 사용자 axis 88 EEG D-1 actionable refresh 요청.
> **cap**: 30분 mac local, $0

---

## §1. Executive verdict (5초 요약)

```
audit_verdict       : PARTIAL_REGRESSED
day_ready_count     : 19 / 27 (70%, 78% → 70% 회귀)
day_blocked_count   : 8  (D+0 STUB 5 + venv regression 1 + sample-rate inconsistency 4-locus + sha mismatch 1)
new_findings_count  : 3  (125Hz 4-locus 정정 / venv distutils 깨짐 / brainflow not installed)
preserved_findings  : 2  (D+0 WRAPPER STUB 5개 / P1 LZ sha mismatch)
mac_local_pre_flight_actionable : 6 항목 (모두 EEG 도착 전 사전 close 가능)
user_manual_action  : 4 항목 (FTDI driver + electrode placement + impedance + HF approval N/A)
```

**한 줄 결론**: pre-register 자체는 frozen + dry-run HARNESS_OK 3/3 유지. 그러나 (a) BrainFlow venv 가 distutils 충돌로 깨짐 → ingest helper selftest=skip, (b) sample rate spec이 4 곳에서 250Hz hardcoded — 사용자 정정 (Cyton+Daisy=125Hz) 미반영 → 도착 시 **자료 sample rate metadata mismatch 위험**. 두 regression 은 mac-local $0 으로 **이번 사전 cycle 에 close 가능**.

---

## §2. Day 0 → Day 7 readiness matrix

| day | step | tool/state | hardware? | predecessor status | **본 audit 갱신** |
|---|---|---|---|---|---|
| **D-1** | venv brainflow install verify | `.venv-eeg/bin/python3 -m pip show brainflow` | no | NOT_AUDITED | **REGRESSED** (distutils 충돌, brainflow import 실패) |
| **D-1** | brainflow ingest helper selftest | `tool/anima_eeg_brainflow_ingest.hexa --selftest` | no | PASS at #186 (synthetic dry-run) | **REGRESSED → selftest=skip** (brainflow_available=False) |
| **D-1** | sample-rate spec consistency | 4-locus check (helper / synthetic fixture / fixture JSON / cross-substrate plan) | no | NOT_AUDITED | **MISSING** (250Hz 4 곳 hardcoded, 125Hz 정정 미반영) |
| **D+0** | hardware calibration impedance + signal QC | `anima-eeg/calibrate.hexa` | yes | STUB (23L) | **STUB** (#209 잔존) |
| **D+0** | 16ch resting recording ≥60s | `anima-eeg/eeg_recorder.hexa` 또는 `tool/anima_eeg_brainflow_ingest.hexa --mode cyton` | yes | STUB (34L) recorder + READY brainflow ingest | **PARTIAL** (anima-eeg/recorder STUB / brainflow ingest = venv regression 으로 막힘) |
| **D+1** | P1 LZ verify against real .npy | `anima-clm-eeg/tool/clm_eeg_p1_lz_pre_register.hexa` | indirect | READY 433L, sha mismatch | **READY+sha_mismatch** (#209 잔존, v1.1 bump 미수행) |
| **D+3** | P2 TLR verify FFT Welch + V_sync | `anima-clm-eeg/tool/clm_eeg_p2_tlr_pre_register.hexa` | indirect | READY 550L | **READY** ✓ |
| **D+3** | V_sync Kuramoto trace | `edu/cell/lagrangian/v_sync_kuramoto.hexa` | no | READY | **READY** ✓ |
| **D+5** | P3 GCG verify Granger F-stat | `anima-clm-eeg/tool/clm_eeg_p3_gcg_pre_register.hexa` | indirect | READY ~620L | **READY** ✓ |
| **D+5** | L_IX integrator hidden trace | `edu/cell/lagrangian/l_ix_integrator.hexa` | no | READY | **READY** ✓ |
| **D+5** | G10 hexad triangulation | `anima-clm-eeg/tool/g10_hexad_triangulation_scaffold.hexa` | indirect | READY 734L | **READY** ✓ |
| **D+6** | G8 real-falsifier MI port | `anima-clm-eeg/tool/g8_transversal_mi_matrix.hexa` | indirect | READY synthetic | **READY** ✓ |
| **D+7** | composite ≥ 2/3 + Hard PASS recompute | `clm_eeg_harness_smoke.hexa` + `mk_xii_preflight_cascade.hexa` | no | READY | **READY** ✓ |

**status taxonomy**:
- **READY**: disk land, selftest PASS (또는 byte-identical reproducible), 도착 즉시 trigger 가능
- **PARTIAL**: 일부 path READY, 보완 필요 (예: brainflow ingest READY but venv broken)
- **STUB**: dummy returns, real-data 산출 불가 — Phase 4 WRAPPER 마이그레이션 필요
- **REGRESSED**: 이전 PASS → 본 audit FAIL (회귀)
- **MISSING**: 사전 land 가능했는데 누락

---

## §3. 신규 발견 (#209 readiness audit 이후)

### §3.1 sample rate 4-locus 250Hz hardcoded inconsistency

MEMORY axis 77 (Cyton+Daisy 16ch, BrainFlow 실측 125Hz, 이전 250Hz spec 잘못) 정정사항이 **disk 어디에도 반영되지 않음**.

| # | file | line | 현 값 | 정정 必 |
|---|---|---|---|---|
| 1 | `tool/anima_eeg_brainflow_ingest.hexa` | L4, L11, L24 | `250Hz` (선언 + selftest cap + comment) | `125Hz` (Cyton+Daisy mode), `250Hz` (Cyton-only) 분기 |
| 2 | `anima-clm-eeg/tool/clm_eeg_synthetic_fixture.hexa` | L12, L173 (`"sample_rate_hz": 250,`), L246 | hardcoded `250` | `125` 또는 mode-aware |
| 3 | `anima-clm-eeg/fixtures/synthetic_16ch_v1.json` | L10 (`"sample_rate_hz": 250`) | `250` | `125` (Cyton+Daisy 실측) |
| 4 | `docs/eeg_cross_substrate_validation_plan_20260425.md` | §1 hardware spec | `250-500Hz typical` (general spec, NOT specific) | optional update with footnote |

**impact**: 도착 후 `--mode cyton` 으로 실측 데이터 캡처 시 BrainFlow 가 자동 125Hz 보고 → ingest JSON 의 `sample_rate_hz` field는 helper 의 250Hz 값과 mismatch → P1 LZ verifier 의 sliding window 길이 계산 오류 가능 (정확히 2배 시간 frame 으로 인식).

**권장 fix sequence** (mac local, ~30min):
1. `tool/anima_eeg_brainflow_ingest.hexa`: BrainFlow `BoardShim.get_sampling_rate(BoardIds.CYTON_DAISY_BOARD)` API 직접 query (hardcoded 제거) → 실측 값을 schema 에 emit
2. `anima-clm-eeg/tool/clm_eeg_synthetic_fixture.hexa` + `synthetic_16ch_v1.json`: `sample_rate_hz` 250 → 125 (Cyton+Daisy 실측 일치)
3. pre-register `clm_eeg_pre_register_v1.json` v1.1 bump: 변경된 fixture sha → 새 `sha256` block + `version: "v1.1"` + `change_log: "Cyton+Daisy 125Hz 정정 (axis 77)"`

### §3.2 .venv-eeg distutils precedence regression

```
$ /Users/ghost/core/anima/.venv-eeg/bin/python3 -m pip list
Error processing line 1 of .venv-eeg/lib/python3.14/site-packages/distutils-precedence.pth:
  AttributeError: module '_distutils_hack' has no attribute 'add_shim'
Remainder of file ignored
(empty pip list)
```

- Python 3.14.3 venv → setuptools/distutils-hack 버전 mismatch (Python 3.14 stdlib 가 distutils 완전 제거 → setuptools 보강 필요).
- `brainflow` import 실패 → `tool/anima_eeg_brainflow_ingest.hexa --selftest` 결과 `brainflow_available=False / selftest=skip`.
- 이전 #186 cycle 시점에는 brainflow 5.21.0 install 성공 + synthetic dry-run PASS — **regression 발생 시점 확인 필요** (Python upgrade or pip cache invalidation).

**권장 fix sequence** (mac local, ~10min):
1. `.venv-eeg` rebuild: `python3.14 -m venv .venv-eeg --clear`
2. `setuptools` upgrade: `.venv-eeg/bin/pip install -U setuptools wheel`
3. `brainflow` reinstall: `.venv-eeg/bin/pip install brainflow`
4. selftest 재실행: `hexa run tool/anima_eeg_brainflow_ingest.hexa --selftest` → `selftest=pass` 기대

**대안 (rebuild 실패 시)**: Python 3.13 venv (3.14 distutils 제거 회피) — `python3.13 -m venv .venv-eeg-py313`.

### §3.3 BrainFlow 인입 schema 와 P1/P2/P3 verifier input schema 매칭 smoke 누락

#186 cycle 의 raw#10 honest 에 명시: "ingest JSON → P1/P2/P3 verifier input schema 매칭 D-day 전 smoke 권장". 본 audit 시점에도 **미수행**.

**권장 (D-day 직전, ~15min mac)**:
1. `tool/anima_eeg_brainflow_ingest.hexa --selftest` → synthetic JSON 산출 (예: `state/eeg_brainflow_dryrun_YYYYMMDD.json`)
2. 이 JSON 을 직접 `clm_eeg_p1_lz_pre_register.hexa` 의 `--real-npy=` 인자로 (또는 `--real-json=` 어댑터 추가) 전달 → schema 적합성 verify
3. mismatch 시 schema bridge tool (`tool/anima_eeg_ingest_to_p1_adapter.hexa`) 작성 (~50L).

---

## §4. 보존된 발견 (#209 잔존, 본 cycle 미해결)

### §4.1 D+0 WRAPPER STUB 5개

`anima-eeg/calibrate.hexa` (23L), `collect.hexa` (25L), `eeg_recorder.hexa` (34L), `experiment.hexa`, `realtime.hexa` 모두 dummy returns. Phase 4 WRAPPER 마이그레이션 (~13h critical path) 미진행.

**fallback 유효**: `tool/anima_eeg_brainflow_ingest.hexa` (276L raw#9 + venv 복구 후) 직접 호출하면 anima-eeg/calibrate 우회 → D+1 P1 verify 진입 가능.

### §4.2 P1 LZ pre-register sha mismatch

- frozen JSON: `cd17abd8aa45d491f253b3b9c4326a7752b54e3bf8f439ebd58212e00f72b1e6`
- disk file: `cce9a801ef8215247aa501cb44a46a8838bed0dd5117448ee41a23fa62bd38cf`

silent edit 의심. v1.1 bump (no silent edit policy raw#9) 또는 P1 sha re-freeze 필요. 30min mac.

---

## §5. 사용자 manual action 4 항목

EEG hardware 도착 시 **Claude 가 대신 못하는** 사용자 직접 작업:

| # | action | when | wallclock | criticality |
|---|---|---|---|---|
| 1 | FTDI VCP driver install (Mac M-series) | 도착 D+0 직전 | 5min | HIGH (FTDI dongle 인식 안되면 `/dev/cu.usbserial-*` 부재) |
| 2 | UltraCortex Mark IV 16ch electrode placement (10-20 system) | D+0 | 30-45min | HIGH (electrode 위치 부정확하면 montage spec 어긋남) |
| 3 | Impedance check (각 electrode < 50kΩ) | D+0 매 session | 5min × 3 | HIGH (impedance 높으면 noise level 증가, brain_like_pct 저하) |
| 4 | HuggingFace Llama-3.2-3B gated approval | T1 v2 unblock 시 (이미 완료, axis 86) | N/A | N/A (이미 grant) |

### §5.1 도착 첫 명령어 actionable list (post-arrival D+0 trigger)

**전제 조건**: §3.2 venv 복구 + §3.1 sample rate 정정 사전 land 완료.

```bash
# 1. FTDI dongle 인식 확인
ls /dev/cu.usbserial*
# (없으면) FTDI VCP driver 설치: https://ftdichip.com/drivers/vcp-drivers/

# 2. brainflow venv health check
/Users/ghost/core/anima/.venv-eeg/bin/python3 -c "import brainflow; print(brainflow.__version__)"
# 기대: 5.21.0 (or higher)

# 3. brainflow ingest helper synthetic selftest (no hardware)
hexa run tool/anima_eeg_brainflow_ingest.hexa --selftest
# 기대: selftest=pass / brainflow_available=True

# 4. Cyton+Daisy 실측 ingest (60초 eyes-closed resting)
hexa run tool/anima_eeg_brainflow_ingest.hexa \
  --mode cyton \
  --serial /dev/cu.usbserial-DM00Q0QO \
  --duration 60 \
  --output state/eeg_recording_d0_resting_$(date +%Y%m%d_%H%M).json

# 5. 즉시 P1 LZ pre-register verify (D+1 step 의 D+0 dry-run)
HEXA_RESOLVER_NO_REROUTE=1 hexa run anima-clm-eeg/tool/clm_eeg_p1_lz_pre_register.hexa \
  --real-input=state/eeg_recording_d0_resting_<id>.json
# 기대: P1.PASS (LZ76 >= 650 AND |Δ|/human <= 200) 또는 PASS/FAIL 실측 verdict
```

---

## §6. mac-local pre-flight 6 항목 (이번 사전 cycle 또는 다음 cycle 에서 즉시 close)

| # | item | wallclock | priority |
|---|---|---|---|
| 1 | `.venv-eeg` rebuild + brainflow reinstall (§3.2) | 10min | **CRITICAL** |
| 2 | `tool/anima_eeg_brainflow_ingest.hexa` BrainFlow API sample-rate query (hardcoded 250 제거) | 20min | **HIGH** |
| 3 | `anima-clm-eeg/tool/clm_eeg_synthetic_fixture.hexa` + `synthetic_16ch_v1.json` 250→125Hz update | 15min | HIGH |
| 4 | `clm_eeg_pre_register_v1.json` v1.1 bump (sample-rate + P1 sha re-freeze) | 30min | HIGH |
| 5 | brainflow ingest JSON → P1 verifier schema 매칭 smoke (§3.3) | 15min | MEDIUM |
| 6 | `anima-eeg/calibrate.hexa` Phase 4 WRAPPER full (#209 priority 1) | 4h | MEDIUM (fallback 유효) |

**총 critical path** (1+2+3+4): ~75min mac local $0 — 본 cycle 또는 다음 cycle 에서 즉시 close.

---

## §7. ω-cycle 6-step verdict

1. **design**: 27 disk artifact + 4 spec doc + 1 venv health 4 dimension audit. 정의: READY/PARTIAL/STUB/REGRESSED/MISSING 5-tier.
2. **implement**: docs only. helper 신규 X. delta audit (vs #209 #186) 만 추가.
3. **positive selftest**: P2/P3/G10/G8/composite/D-day simulated 모두 disk verify 일관 PASS. brainflow ingest helper hexa parse OK (코드 자체는 healthy).
4. **negative falsify**: brainflow venv selftest=skip (3.2), 4-locus 250→125 정정 누락 (3.1) → audit verdict regressed PARTIAL → REGRESSED PARTIAL.
5. **byte-identical**: 본 docs 결정론적 (sha computed). marker file timestamp 만 non-deterministic (정상).
6. **iterate**: 1 iter (이전 #209 audit 기반 delta 만 갱신).

---

## §8. cross-references

- predecessor: `anima-clm-eeg/docs/eeg_d_day_readiness_check_landing.md` (#209)
- predecessor: `tool/anima_eeg_brainflow_ingest.hexa` D-1 prep (#186)
- spec SSOT: `anima-clm-eeg/docs/eeg_hardware_openbci_16ch.md`
- pre-register SSOT: `anima-clm-eeg/state/clm_eeg_pre_register_v1.json` (v1, sha-locked)
- cross-substrate plan: `docs/eeg_cross_substrate_validation_plan_20260425.md`
- MEMORY axis 77: Cyton+Daisy 125Hz 정정
- MEMORY axis 86: HF Llama-3.2-3B grant complete
- `.roadmap` #119 / #186 / #209 / #212 / #213
- own#2 (b) PC empirical-max multi-EEG cohort N=0 (Phase 2 deliverable, audit 본 cycle 변화 없음)

---

## §9. raw#10 honest

1. **dry-run ≠ phenomenal**: 본 audit verdict PASS/FAIL 모두 disk static + synthetic dry-run 한정. 실측 EEG 없이는 P1/P2/P3 PASS 가 phenomenal correlate 직접 입증 X.
2. **125Hz 정정 시점 의심**: MEMORY axis 77 등재 시점이 정확히 어느 hardware 측정 결과 기반인지 본 audit 직접 확인 미수행. BrainFlow `BoardShim.get_sampling_rate(2)` 표준 출력값 (Cyton+Daisy 실측 125Hz) 과 일치할 가능성 강하지만 disk 측정 기록 부재.
3. **venv rebuild 부작용**: `--clear` 사용 시 사전 install 된 다른 dependencies (numpy 2.4.4 등) 재install 필요. `pip freeze` 사전 backup 권장.
4. **fallback 의 fallback**: anima-eeg WRAPPER STUB + brainflow ingest 둘 다 막히면 BrainFlow Python script 직접 호출 (CSV emit) → MNE Python adapter → P1 입력 path 가 ultimate 백업.
5. **schema bridge 미land**: §3.3 의 brainflow JSON ↔ P1 verifier 입력 schema 매칭 smoke 자체가 미수행 — 본 audit 가 "필요 인정" tier 만 처리.
6. **Phase 4 WRAPPER 13h estimate 현실성**: #209 의 calibrate (4h) + collect (4h) + eeg_recorder (5h) wallclock 이 자체 estimate 일 뿐 실제 한 모듈 마이그레이션이 hexa-lang parser quirk + selftest iteration 로 ~6-8h 까지 늘어날 수 있음 (Phase 3 Cycle 3 bci_control 선례).
7. **chflags uchg 미적용**: pre-register JSON v1 의 `chflags_uchg_candidate=true` 권고 있으나 v1.1 bump 시점에 일관 정책 (v1 unlock + v1.1 lock) 미정.
