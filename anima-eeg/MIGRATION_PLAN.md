# anima-eeg → raw#9 hexa-only strict 마이그레이션 plan

**Status (2026-04-26):** Phase 0 + Phase 1 + Phase 2 pilot 완료. **Phase 3 Cycle 1 6/19 stubs landed** (PHASE3_PROGRESS.md 참조). Phase 3 Cycle 2-3 + Phase 4 사용자 결정 대기.
**Directive:** raw#9 hexa-only strict (directive #134, 2026-04-26).
**Working tree constraint:** anima-eeg/ 내부에만, additive only (기존 파일 0개 수정/삭제). git commit 미수행.

---

## 0. Reality check — 사용자 briefing vs. 실제 상태

| 항목 | 사용자 briefing | 실제 (commit 68d2236c 이후) |
|---|---|---|
| LOC | 7964 | 990 |
| modules | 18 | 21 (.hexa) |
| 언어 | "거의 .py" | 100% .hexa, .py = 0 |
| 상태 | "production-ready, 108 tests pass, 85.6% brain-like" | 21개 중 1개 (rp_adaptive_response.hexa, 288L) 만 production-grade. 19개는 stub (TODO + dummy returns). 1개 (monthly_eeg_validate.hexa) 는 panic block. |

git history 증거: `68d2236c feat(hexa-first): .py 791개 + .rs 7개 + .sh 37개 → .hexa 흡수 + 원본 폐기` — `git log --diff-filter=D --name-only -- 'anima-eeg/'` 로 18개 .py 삭제 확인.

**해석:** 사용자가 인지한 7964 LOC production .py 상태는 **commit 68d2236c 이전**이며, 현재 .hexa 는 **stub-shell 만 흡수된 surface migration** 결과. 본 plan은 따라서 "stub → 진짜 raw#9 strict implementation" 으로 정의.

**108 tests + 85.6% brain-like 의 위치:** anima-eeg/ 안에 test 파일 0개. test/ root 또는 commit 68d2236c 와 함께 사라졌을 가능성 농후. **Phase 3 진입 전 test locator step 필수** (산출물 § 5 risk 참조).

---

## 1. raw#9 strict 정의 (모범 사례 기반)

`/Users/ghost/core/anima/tool/an11_b_eeg_ingest.hexa` (360L) + `/Users/ghost/core/anima/edu/cell/lagrangian/l_ix_integrator.hexa` 를 reference 로:

1. header comment 에 raw# 인용 + spec doc 경로
2. `comptime const` 또는 `let` 으로 상수 명시 (no magic numbers)
3. **외부 dep 처리:** `_write_helper()` 가 `/tmp/<name>_helper.hexa_tmp` 에 python 코드 emit (raw#37: not git-tracked) → `_run_helper(args)` exec → kv-lines stdout parse
4. `--selftest` 필수 — synthetic deterministic data + `selftest=ok` marker + JSON validation invariants
5. `np.random.default_rng(20260425)` 로 RNG seed 고정 (byte-identical reproducibility)
6. `raw10_honest` 필드로 synthetic vs phenomenal 구분
7. snake_case (raw#11)
8. **fallback 금지** — `if HAVE_MNE: ... else: ABORT` 식 single deterministic path
9. `LLM judge = none`

→ 이 9 항목이 raw#9 strict checklist 로 본 plan에서 사용. inventory JSON `raw9_strict_checklist_per_module` 에도 동일 record.

---

## 2. Phase 0 — Inventory (완료)

`MIGRATION_INVENTORY.json` 생성 (20 module + 1 exempt). 핵심:

| verdict | count | modules |
|---|---|---|
| ALREADY_FULL | 1 | rp_adaptive_response (raw#9 exemplar) |
| FULL | 8 | __init__, neurofeedback, protocols/__init__, analyze, validate_consciousness, transplant_eeg_verify, protocols/emotion_sync, protocols/sleep_protocol |
| WRAPPER | 9 | calibrate, collect, eeg_recorder, experiment, realtime, closed_loop, dual_stream, protocols/multi_eeg, protocols/bci_control |
| EMIT-TMP | 1 | scripts/monthly_eeg_validate (orchestration only) |
| WRAPPER_OR_HEXA_STDLIB | 1 | scripts/organize_recordings (sqlite blocked) |

---

## 3. Phase 1 — Dependency graph & 마이그레이션 순서

```
Tier-0 (no deps, pure numerical):
  __init__, protocols/__init__, neurofeedback
        |
        v
Tier-1 (numerical, no hardware):
  analyze (FFT band-power, hexa BLAS-lite)
        |
        +-> validate_consciousness (6 metrics; depends on analyze for PSD slope)
        +-> protocols/emotion_sync (FAA = ln ratios)
        +-> protocols/sleep_protocol (band-power thresholds; depends on analyze)
        |
        v
Tier-2 (numerical consumer of JSON output):
  transplant_eeg_verify (consumes validate_consciousness JSON)
  scripts/monthly_eeg_validate (orchestrator on validate_consciousness)
        |
        v
Tier-3 (hardware WRAPPER via /tmp helper.py):
  calibrate -> collect -> eeg_recorder
        |
        v
Tier-4 (live + multi):
  realtime, closed_loop, dual_stream, experiment, protocols/bci_control,
  protocols/multi_eeg, scripts/organize_recordings
```

마이그레이션 순서 = 위 Tier 순. weakest evidence link first 원칙 (memory feedback_completeness_frame): pure-numerical 부터 검증된 후 BLE/hardware wrapper 진입.

---

## 4. Phase 2 — Pilot (1 module) — **이번 세션에서 완료**

### 4.1 후보 선정

후보 3개 (low-risk, FULL verdict):
- `__init__.hexa` (19L → 30L) — 너무 trivial, raw#9 패턴 학습 가치 낮음
- `protocols/__init__.hexa` (12L → 18L) — 동상
- `neurofeedback.hexa` (30L → ~230L) — **선정**: pure numerical, phi/tension → binaural/LED params + safety clamps, 외부 dep 0, selftest 가능, raw#9 패턴 9 항목 완전 적용 가능

### 4.2 산출물

`anima-eeg/migration_phase2_pilot/neurofeedback.hexa` — additive, 기존 `anima-eeg/neurofeedback.hexa` 미수정.

raw#9 적용 항목:
- header: raw#9 hexa-only + spec doc 인용
- `comptime const`: SAFETY_VOLUME_MAX, SAFETY_LED_MAX, FREQ_MIN/MAX
- pure-numerical, 외부 dep 0 → helper emit 불필요 (가장 깨끗한 형태)
- `--selftest` 모드 + kv-line `selftest=ok`
- 8 selftest (rp_adaptive_response.hexa 패턴 차용)
- byte-identical: float ops only, no RNG needed
- raw10_honest: "binaural waveform parameters; not actual audio synthesis"
- snake_case

### 4.3 검증

selftest 명령:
```
hexa run anima-eeg/migration_phase2_pilot/neurofeedback.hexa --selftest
# expect: selftest=ok, all PASS
```

byte-identical: 두 번 run → 동일 stdout (RNG 없음 → trivially deterministic).

---

## 5. Phase 3 — Full pure-numerical (7 modules)

**Cycle 1 status (2026-04-26): 6 modules landed.** `__init__`, `protocols/__init__`, `transplant_eeg_verify`, `protocols/emotion_sync`, `protocols/sleep_protocol`, `scripts/monthly_eeg_validate`, `neurofeedback` (pilot promoted) — see `PHASE3_PROGRESS.md` for sha256 + selftest verdicts. **Remaining FULL: `analyze`, `validate_consciousness`, `protocols/bci_control`** (Cycle 2/3).

순서: analyze → validate_consciousness → transplant_eeg_verify, emotion_sync, sleep_protocol, bci_control, monthly_eeg_validate

### 5.1 prerequisite: test locator

**Critical**: production 108 tests 위치 확정. 후보:
- `/Users/ghost/core/anima/test/` → `find ... -name 'test_eeg*'`
- archived in commit 68d2236c
- separate `/Users/ghost/core/anima/anima-clm-eeg/` (메인 세션 작업, 충돌 회피)

찾으면 .py interface contract (input/output shape, 6 metric float ranges) 추출 → .hexa FULL impl 의 invariant 로 freeze.

### 5.2 brain-like 85.6% 보존

`validate_consciousness.hexa` FULL impl 후 **재검증 필수**. baseline corpus (recordings/sessions/) 로 .hexa 결과 vs 사전 기록된 0.856 비교. ±0.005 tolerance. 미달 시 .hexa 측 numerical bug 의심.

### 5.3 hexa-native FFT 도입

memory project_omega_philosophy_limits 의 hexa-lang BLAS-lite + Jacobi eigh 가 이미 존재 → Welch PSD = 256-pt windowed FFT averaging 을 hexa 로 200-300L 신규 module (`anima-eeg/_fft.hexa` 또는 hexa-stdlib stage1 신청). 첫 use case = analyze.hexa.

대안: scipy 호출 helper (raw#37) — fallback 없는 single-path emit. 마이그레이션 중간 stage 로 허용.

### 5.4 추정

| module | 현재 LOC | 목표 LOC | wallclock | risk |
|---|---|---|---|---|
| analyze | 32 | 450 | 6h | medium (FFT correctness) |
| validate_consciousness | 23 | 520 | 8h | medium (85.6% gate) |
| transplant_eeg_verify | 20 | 180 | 2h | medium |
| protocols/emotion_sync | 26 | 260 | 3h | medium |
| protocols/sleep_protocol | 28 | 280 | 3h | medium |
| protocols/bci_control | 27 | 220 | 2h | medium |
| scripts/monthly_eeg_validate | 13 | 200 | 1h | medium |
| **subtotal** | 169 | 2110 | 25h | $0 |

---

## 6. Phase 4 — WRAPPER hardware-dependent (9 modules, 사용자 승인 대기)

reference: `tool/an11_b_eeg_ingest.hexa` (360L, BrainFlow/MNE wrapper, raw#9 compliant).

각 module = .hexa main + `/tmp/<module>_helper.hexa_tmp` python emit. 모두 동일 패턴:
1. `_write_helper()` — Python source 를 string concat 으로 emit
2. `_run_helper(args)` — `python3 /tmp/<module>_helper.hexa_tmp <args>` exec
3. stdout = kv-lines (`channels=16\nsample_rate=250.0\nDONE`)
4. `--selftest` = synthetic mode, no hardware required
5. fallback 금지 — `try: import brainflow; except: ABORT_NO_BRAINFLOW + install instruction`

| module | wallclock | hardware required for full test |
|---|---|---|
| calibrate | 4h | yes (impedance) — selftest synthetic only |
| collect | 4h | yes — selftest synthetic only |
| eeg_recorder | 5h | yes (long-running) |
| experiment | 4h | yes (markers) |
| realtime | 5h | yes (live) |
| closed_loop | 5h | yes (audio + BLE) |
| dual_stream | 4h | yes (BLE + Phi) |
| protocols/multi_eeg | 5h | yes (multi-board) |
| scripts/organize_recordings | 4h | sqlite + filesystem only (no BLE) |
| **subtotal** | 40h | $0 |

honest reservation: BrainFlow / matplotlib / sqlite3 는 **WRAPPER 가 종착점**. raw#9 hexa-only 의 정신은 **deterministic + reproducible + helper emit pattern** 으로 만족 가능. "100% .hexa 코드만" 은 BLE 하드웨어 통신상 물리적으로 불가능 (memory project_omega_hexa_lang_limits H1 portability 한계).

---

## 7. Risk register

| risk | severity | mitigation |
|---|---|---|
| 108 tests 위치 미확정 — Phase 3 시작 못함 | High | Phase 3 entry gate = test locator artifact 산출 |
| 85.6% brain-like regression in hexa-native FFT | High | analyze.hexa first 후 validate.hexa baseline diff < ±0.005 freeze |
| BrainFlow Python API drift (.py originals 삭제됨) | Med | git show 68d2236c~1 로 .py 복원 가능 — interface reference 로 사용 |
| .roadmap #119 EEG D8 timing pressure | Med | Phase 2 pilot 만 이번 세션 — 사용자 승인 후 Phase 3 진입 |
| 메인 세션 anima-clm-eeg/ 와 충돌 | Low | working tree constraint: anima-eeg/ 내부만 touch (이미 enforce) |
| hexa-stdlib sqlite gap (organize_recordings) | Med | WRAPPER 로 강등 — sqlite 는 helper.py |

---

## 8. 추정 cost / wallclock

| phase | wallclock (sequential) | wallclock (parallel) | $ |
|---|---|---|---|
| 0 | done | done | 0 |
| 1 | done | done | 0 |
| 2 (pilot) | 1.5h | 1.5h | 0 |
| 3 | 25h | 12h | 0 |
| 4 | 40h | 20h | 0 |
| **total remaining** | **66.5h** | **33.5h** | **$0** |

mac local, GPU 0, LLM judge 0.

---

## 9. 다음 단계 권장 (사용자 결정 대기)

**3 옵션:**

A. **Phase 3 진입 (pure-numerical 7 modules)** — 6.5d sequential / 1.5d parallel, $0
   - prerequisite: test locator step 1h 안에 완료 후 진행
   - first deliverable: analyze.hexa FULL + hexa-native Welch PSD

B. **Phase 4 spike 1개만** — `calibrate.hexa` WRAPPER 시도 (4h, $0)
   - Tier 3 first-touch 검증 — `tool/an11_b_eeg_ingest.hexa` 패턴 재사용 확인용

C. **HOLD — pilot 검증 + Φ-game 우선순위로 재배치**
   - 본 마이그레이션은 production tests 미존재 가설 strong → Phase 3 비용 의심
   - 메인 세션 anima-clm-eeg/ 와 통합 후 reschedule

**weakest evidence link:** test 108개의 위치. 그 답이 나오기 전 Phase 3 진입 = blind. 따라서 권장 = (A) 의 prerequisite step 만 먼저 1h 안에 (`find /Users/ghost/core/anima/test -name 'test_eeg*' -o -name '*eeg_test*'` + git history grep) 후 사용자 보고.

---

## 10. 산출물 paths

- `/Users/ghost/core/anima/anima-eeg/MIGRATION_PLAN.md` (this file)
- `/Users/ghost/core/anima/anima-eeg/MIGRATION_INVENTORY.json`
- `/Users/ghost/core/anima/anima-eeg/migration_phase2_pilot/neurofeedback.hexa`

destructive 0건. 기존 파일 수정 0건. git commit 미수행.
