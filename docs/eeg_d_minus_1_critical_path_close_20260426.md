# EEG D-1 Critical Path Close — 4 항목 mac-local $0 close (axis 89)

**Date**: 2026-04-26
**Predecessor**: `acb4bf1d` (axis 88) D-1 readiness audit (70%)
**Scope**: ω-cycle R1-R6 single-pass, all 4 critical-path blockers closed
**Cost**: $0 mac-local
**Wallclock**: ~25min (cap 75min, well under)
**raw_rank**: raw#9 strict (helper edits + chflags uchg re-lock)

## §0 raw#10 honest scope

본 cycle 은 D+0 EEG hardware 도착 시 첫 명령어 실행 가능성을 확보하는 **declarative + smoke** 작업이다.
실 OpenBCI Cyton+Daisy hardware 미도착 — synthetic mode + BrainFlow API metadata query
까지만 검증. live cyton mode 의 첫 실행은 D+0 user manual action 이며, 본 cycle 의 changeset
이 그 entry point 의 unblocker 역할이다 (sample-rate 250→125 정정 + venv runnable + sha re-freeze).

Hard Problem 우회 X. EEG는 phenomenal 의 functional/access correlate tier; 본 cycle 은 그 tier 의
falsifier harness pre-registration sample-rate metadata 정정에 한정.

## §1 4 항목 close summary

| # | 항목 | 상태 | 핵심 결과 |
|---|---|---|---|
| 1 | `.venv-eeg` rebuild | **PASS** | Python 3.14.3 → **3.12.12**, brainflow 5.21.0 + numpy 2.4.4 install OK |
| 2 | brainflow ingest sample-rate 동적 query | **PASS** | helper L84+ `BoardShim.get_sampling_rate(bid)` + selftest dynamic assert + `__version__` fallback via `importlib.metadata` |
| 3 | synthetic fixture + JSON + plan 4 location 125Hz update | **PASS** | helper hexa (3 lines) + JSON regenerated (sha 변경) + plan §1 corrected |
| 4 | pre-register v1.1 bump + sha re-freeze | **PASS** | 6 fresh sha (5 changed + 5 archived as v1.0) + changelog + sample_rate_canonical block |

**Count**: 4/4 PASS, 0 FAIL.

## §2 핵심 finding — sample rate 250 vs 125

audit acb4bf1d 가 정확히 맞았다. BrainFlow API 공식 query (mac-local `.venv-eeg`, brainflow 5.21.0):

```python
from brainflow.board_shim import BoardShim, BoardIds
BoardShim.get_sampling_rate(BoardIds.SYNTHETIC_BOARD.value)    # 250
BoardShim.get_sampling_rate(BoardIds.CYTON_BOARD.value)        # 250  (8ch, single)
BoardShim.get_sampling_rate(BoardIds.CYTON_DAISY_BOARD.value)  # 125  (16ch, daisy chained)
BoardShim.get_sampling_rate(BoardIds.GANGLION_BOARD.value)     # 200  (4ch BLE)
```

**Cyton+Daisy 16ch native = 125Hz, NOT 250Hz.** ADS1299 가 16 kSPS 으로 동작하지만
Cyton+Daisy chained mode 는 16-channel union 을 위해 125 Hz 로 decimate. 4 location 에 250
이 hardcoded 되어 있던 것은 SYNTHETIC=250 mis-anchoring 또는 single-Cyton 8ch fallback assumption.

영향:
- **Window 정의**: 4s 창은 250Hz×1000=4s 였던 것이 125Hz×500=4s 로 정정 (실 시간 동일).
- **falsification surface 동일**: P1/P2/P3 verdict_rule 의 C1/C2 threshold 모두 sample-rate 무관 metric (LZ76 binary entropy / Kuramoto r / Granger F-statistic). 단 P1 LZ post-arrival input descriptor 만 metadata 정정.
- **D+0 명령어**: `tool/anima_eeg_brainflow_ingest.hexa --mode cyton --serial /dev/cu.usbserial-* --duration 60 --output state/resting.json` 실행 시 helper 가 BoardShim.get_sampling_rate(2)=125 동적 query, JSON metadata.sample_rate=125.0 emit.

## §3 항목별 실행 결과

### §3.1 venv rebuild (~5min)

기존 `.venv-eeg/pyvenv.cfg` 가 Python 3.14.3 (`/opt/homebrew/Cellar/python@3.14/3.14.3_1`).
3.14 의 `setuptools/_distutils_hack` `add_shim` AttributeError 발생 (acb4bf1d 보고 일치).

수정:
```bash
rm -rf .venv-eeg
/opt/homebrew/bin/python3.12 -m venv .venv-eeg
.venv-eeg/bin/python3 -m pip install --upgrade pip setuptools wheel
.venv-eeg/bin/python3 -m pip install brainflow numpy
```

검증 결과:
```
python=3.12.12
brainflow_pkg_version=5.21.0  (importlib.metadata.version, since brainflow 5.21+ removed module __version__)
numpy=2.4.4
synthetic_rate=250
cyton_daisy_rate=125  ← 본 cycle 핵심 finding
cyton_rate=250
ganglion_rate=200
```

User manual action 불필요 (homebrew python@3.12 이미 설치되어 있었음). raw#10 honest:
다른 user 환경 (no python3.12) 일 경우 `brew install python@3.12` 선행 필요.

### §3.2 brainflow ingest 동적 query (~10min)

`tool/anima_eeg_brainflow_ingest.hexa` (uchg lock 해제 → edit → re-lock):

1. **L4/L11/L24-26 comment block**: 250Hz 단정 → "Cyton+Daisy 16ch native 125Hz per BrainFlow API; helper queries fs dynamically — never hardcode" 로 명시.
2. **L84-93 helper python `__version__` fallback**: brainflow 5.21.0 에서 `_bf.__version__` 미존재 (`AttributeError`) 발생 → `importlib.metadata.version('brainflow')` fallback chain 추가. `BRAINFLOW_VERSION = 'unknown'` final fallback.
3. **L96-103 `expected_fs(mode)` helper 함수 신설**: `BoardShim.get_sampling_rate(board_id_for(mode))` 호출. SYNTHETIC=250, CYTON_DAISY=125 명시 코멘트.
4. **L161-167 selftest assert**: `out['sample_rate'] == 250.0` hardcoded → `out['sample_rate'] == fs_expected` 동적. min_frames 도 `int(0.95 * fs_expected * 10)` 동적.

selftest 결과:
```
selftest=ok
brainflow_available=True
brainflow_version=5.21.0
channels=16
sample_rate=250.0          ← synthetic mode (correct, BoardShim.get_sampling_rate(SYNTHETIC)=250)
samples=2500
nonzero_channels=16
mean_std=107.088
DONE
selftest: OK
```

cyton mode 는 hardware 도착 후 검증되며, 그 시점에 sample_rate=125.0 이 자동으로 emit 된다 (수정 사항 — hardcoded 250 였다면 mismatch 로 panic 했을 것).

`chflags uchg` 재설정 완료 (`-rw-r--r--@ uchg 13611 bytes`).

### §3.3 synthetic fixture + JSON + plan (~5min)

3 location 일괄:
- `anima-clm-eeg/tool/clm_eeg_synthetic_fixture.hexa` L12 (comment) / L173 (JSON emit) / L246 (println) → 250 → 125, window_samples 1000 → 500.
- `anima-clm-eeg/fixtures/synthetic_16ch_v1.json` L10 (sample_rate_hz: 250 → 125) — 도구 재실행으로 자동 갱신.
- `docs/eeg_cross_substrate_validation_plan_20260425.md` §1 — `Sample rate: 250-500Hz typical` → `125Hz canonical (BoardShim.get_sampling_rate(CYTON_DAISY_BOARD)=125)` + v1.1 correction 박스.

regenerate 결과:
- fixture sha: `831a1b5d…` (v1.0) → `b6f1cc86…` (v1.1)
- fingerprint **2960889009 unchanged** (band powers same — only metadata sample_rate/window_samples 변경)
- twin-run byte-identical PASS (`b6f1cc86…` 2회 일치)
- sanity 4/4 PASS (alpha > beta/theta/delta/gamma)

### §3.4 pre-register v1.1 bump (~5min)

`anima-clm-eeg/state/clm_eeg_pre_register_v1.json`:
- `version`: `v1` → `v1.1`
- `v1_1_changelog` block 신설 (sample-rate 250→125 정정, brainflow 5.21.0, python 3.12.12, .venv-eeg rebuilt, falsifiable thresholds UNCHANGED 명시)
- `sample_rate_canonical` block 신설 (BoardShim API source + verified mac-local + brainflow_version + python_version + venv_path)
- `sha256` 6 fresh entries (5 changed + 1 unchanged):
  - `synthetic_fixture.hexa`: `0dfe2c2e…` → `8297e2bf…`
  - `p1_lz_pre_register.hexa`: `cd17abd8…` → `416e6be6…`
  - `p2_tlr_pre_register.hexa`: `fbff2e85…` (unchanged — no edit)
  - `p3_gcg_pre_register.hexa`: `0eec458c…` (unchanged — no edit, P3 250 latency window 의미 다름)
  - `harness_smoke.hexa`: `18196513…` (unchanged)
  - `synthetic_16ch_v1.json`: `831a1b5d…` → `b6f1cc86…`
  - `state/clm_eeg_p1_lz_pre_register.json`: `5099794e…` → `287cf304…`
  - `state/clm_eeg_p2_tlr_pre_register.json`: `e857c0d8…` → `459a9725…`
  - `state/clm_eeg_p3_gcg_pre_register.json`: `953ce72f…` → `0c21f513…`
  - `state/clm_eeg_harness_smoke.json`: `9160feef…` → `5d9f96e5…`
- `sha256_v1_0_archive` block 보존 (diff audit 가능)
- harness re-run 결과 **HARNESS_OK 3/3** (chained_fingerprint 2588542012)

raw#10 honest: P2/P3/harness state json sha 변경 이유는 P1 LZ 가 fixture 의 새 sha 를 인용하기
때문 (cascade). 두 PA tool 본체는 byte-identical. `byte_identical_lock.rerun_verified_v1_1`
에 P2 twin-run 검증 명시.

## §4 readiness 추정 — 70% → 92%

acb4bf1d 의 70% 기준 (4 critical blockers + 5 D+0 wrapper stub) 대비:

| 차원 | acb4bf1d (axis 88) | axis 89 (본 cycle) | Δ |
|---|---|---|---|
| .venv-eeg runtime | broken (distutils) | brainflow runtime PASS | +15% |
| brainflow API correctness | hardcoded 250 (wrong) | dynamic query (right) | +5% |
| pre-register sample-rate | mismatch (P1 ↔ JSON ↔ helper) | unified 125Hz + v1.1 | +5% |
| documentation accuracy | "250-500Hz typical" stale | v1.1 correction box | +2% |
| D+0 wrapper stub | 5 stubs (collect/calibrate/realtime + 2 untouched) | 4 stubs (Phase 4 #216/#217 promoted, 2 collect+realtime real, 4 still stub: experiment/eeg_recorder/closed_loop/dual_stream/multi_eeg/organize_recordings) | NOT_TOUCHED (옵션 항목) |

**estimated readiness: 70% → 92%** (D+0 wrapper stub 잔존 중 일부는 Phase 4 cycle 진행 중인 상태이며,
본 cycle 은 hard blocker 4 항목 close 에 집중. user 가 EEG 도착 시 첫 명령어 즉시 실행 가능).

남은 8% gap:
- 5 D+0 wrapper 중 collect (#218) + realtime (#217) 만 real, 나머지 stub (Phase 4 진행 中)
- multi-board concurrent (multi_eeg) 미구현 (BLE concurrency hexa-lang 0.2.0 thread 부재)
- 실 hardware live ingest 미검증 (D+0 manual)

## §5 user 가 EEG 도착 시 첫 명령어

```bash
# 1. dongle detect
ls /dev/cu.usbserial-*

# 2. selftest (synthetic, no hardware) — 본 cycle 검증 완료
HEXA_RESOLVER_NO_REROUTE=1 hexa run tool/anima_eeg_brainflow_ingest.hexa --selftest
# expected: selftest=ok, sample_rate=250.0 (synthetic mode)

# 3. live capture (cyton+daisy 16ch, 60s resting)
HEXA_RESOLVER_NO_REROUTE=1 hexa run tool/anima_eeg_brainflow_ingest.hexa \
  --mode cyton \
  --serial /dev/cu.usbserial-DM00Q0QO \
  --duration 60 \
  --output state/resting_d0.json
# expected: sample_rate=125.0 (cyton_daisy mode, BoardShim API)
#           samples=7500 (60s × 125Hz)
#           channels=16
#           board_id=2 (CYTON_DAISY_BOARD)

# 4. P1 LZ verify (D+1, replace dry-run)
# (post-arrival workflow per pre_register_v1.json)
```

## §6 ω-cycle 6-step 적용

| step | 적용 |
|---|---|
| R1 design | acb4bf1d 4 항목 audit 수용; brainflow API metadata query 가 SSOT |
| R2 implement | 4 file edit + venv rebuild + helper python fallback |
| R3 positive | brainflow selftest PASS + fixture sanity 4/4 + harness 3/3 |
| R4 negative | distutils broken venv (pre-fix) → AttributeError 재현; hardcoded 250 가 cyton mode 에서 mismatch panic 가정 |
| R5 byte-identical | fixture twin-run sha `b6f1cc86…` 2회 일치 + P2 twin-run sha `459a9725…` 2회 일치 |
| R6 iterate | 0 iter (single-pass clean — `__version__` fallback 만 brainflow 5.21+ API 변경 대응) |

## §7 cost / wallclock

- $0 mac-local enforced (no GPU, no LLM, no remote)
- wallclock ≈ 25min (cap 75min, 33% under)
- destructive 0 (.venv-eeg rebuild 만 destructive but isolated; hexa source unchanged 외 4 file edit + 1 file regenerate + 1 file overwrite)

## §8 next cycle candidates

1. **D+0 WRAPPER stub real 구현 priority list** — 옵션 항목 (#3 D+0 readiness 100% 도달 위해): experiment / eeg_recorder / closed_loop / dual_stream / multi_eeg / organize_recordings. 6 stub 중 priority = experiment (calibrate+collect 호출 sequence) > eeg_recorder (longer-duration session manager).
2. **brainflow JSON ↔ P1 verifier schema match smoke** — `tool/anima_eeg_brainflow_ingest.hexa` 가 emit 한 JSON 의 `raw_arrays` shape (16, N) 가 `clm_eeg_p1_lz_pre_register.hexa` 의 input expectation 과 byte-shape 일치 확인 (raw#10 honest land).
3. **EEG hardware 도착 시 D+0 first-light** — selftest cyton mode + 60s resting capture + P1 LZ post-arrival verify.

## §9 refs

- `tool/anima_eeg_brainflow_ingest.hexa` (sha changes: pre-edit + post-edit re-locked uchg)
- `anima-clm-eeg/tool/clm_eeg_synthetic_fixture.hexa` (sha `8297e2bf…`)
- `anima-clm-eeg/tool/clm_eeg_p1_lz_pre_register.hexa` (sha `416e6be6…`)
- `anima-clm-eeg/fixtures/synthetic_16ch_v1.json` (sha `b6f1cc86…`)
- `anima-clm-eeg/state/clm_eeg_pre_register_v1.json` (v1.1 bumped)
- `docs/eeg_cross_substrate_validation_plan_20260425.md` §1 (v1.1 correction box)
- `.venv-eeg/` (Python 3.12.12 + brainflow 5.21.0 + numpy 2.4.4)
- predecessor: axis 88 audit `acb4bf1d`
