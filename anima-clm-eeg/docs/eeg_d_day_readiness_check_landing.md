# EEG D-Day Workflow Readiness Check — D+0 → D+7 (Landing)

> **scope**: EEG hardware (OpenBCI Cyton+Daisy 16ch) D-1 시점 readiness audit. D+0~D+7 7-day workflow의 모든 prerequisite 산출물 disk verify 후 도착 즉시 진입 가능한지 결정.
> **created**: 2026-04-26 (ω-cycle session)
> **raw_rank**: 9 (docs 완화, 한글 OK)
> **status**: PARTIAL (P1/P2/P3 pre-register READY but D+0 hardware bring-up WRAPPER blocked)
> **author**: anima-clm-eeg readiness audit subagent
> **cap**: 30분 mac local, $0
> **predecessor**: `anima-clm-eeg/docs/eeg_arrival_impact_5fold.md` + `anima-clm-eeg/state/clm_eeg_pre_register_v1.json`

---

## §1. 임무 요약

EEG hardware (며칠 內 도착 expected) 도착 시점에 0-friction 진입 가능 여부를 결정한다.
판정 verdict는 **READY / PARTIAL / NOT_READY** 3-tier.

각 D+n 단계마다:
1. 필요한 **tool / state / fixture** 산출물 disk land 확인
2. 누락 항목 listing
3. 누락 우선순위 + 사전 land 가능성 판단

## §2. 7-day workflow + dependency table (frozen)

D+0~D+7 절차는 `state/clm_eeg_pre_register_v1.json` 의 `post_arrival_workflow` 와 README §5 가 SSOT.

| day | step | required tool | required fixture/state | hardware required | disk status |
|---|---|---|---|---|---|
| **D+0** | hardware calibration (impedance + signal QC) | `anima-eeg/calibrate.hexa` | `anima-eeg/config/eeg_config.json` | yes | **STUB (23L)** |
| **D+0** | 16ch resting recording (≥ 60s eyes-closed) | `anima-eeg/eeg_recorder.hexa` or `collect.hexa` | `anima-eeg/recordings/sessions/` (현재 empty) | yes | **STUB (34L / 25L)** |
| **D+1** | 16ch N-back recording (5-10min) | `anima-eeg/eeg_recorder.hexa` | `anima-eeg/protocols/` task scripts | yes | STUB recorder + protocols partial |
| **D+1** | P1 LZ verify against real .npy | `anima-clm-eeg/tool/clm_eeg_p1_lz_pre_register.hexa` | recording .npy + frozen criteria | indirect | **READY (433L)** |
| **D+3** | P2 TLR verify (FFT Welch + V_sync trace) | `anima-clm-eeg/tool/clm_eeg_p2_tlr_pre_register.hexa` | recording .npy + V_sync trace | indirect | **READY (550L)** |
| **D+3** | V_sync Kuramoto 산출 | `edu/cell/lagrangian/v_sync_kuramoto.hexa` | CLM hidden trace | no | **READY** |
| **D+5** | P3 GCG verify (Granger F-stat) | `anima-clm-eeg/tool/clm_eeg_p3_gcg_pre_register.hexa` | recording .npy + L_IX hidden trace | indirect | **READY (~620L)** |
| **D+5** | L_IX integrator hidden trace | `edu/cell/lagrangian/l_ix_integrator.hexa` | — | no | **READY** |
| **D+5** | G10 hexad triangulation activate | `anima-clm-eeg/tool/g10_hexad_triangulation_scaffold.hexa` | spec doc | indirect | **READY (734L scaffold + spec)** |
| **D+6** | G8 real-falsifier MI port | `anima-clm-eeg/tool/g8_transversal_mi_matrix.hexa` (port target) | g8 spec docs | indirect | **READY** (synthetic baseline; real-data wiring pending) |
| **D+7** | composite ≥ 2/3 PHENOMENAL VALIDATED | `anima-clm-eeg/tool/clm_eeg_harness_smoke.hexa` | 3 verify outputs aggregated | no | **READY (332L)** |
| **D+7** | Hard PASS recompute | `anima-clm-eeg/tool/mk_xii_preflight_cascade.hexa` | composite verdict + cascade | no | **READY (preflight + d_day_simulated)** |

## §3. Disk audit — 산출물 별 상세

### §3.1 anima-clm-eeg pre-register (D+1/D+3/D+5/D+7)

frozen pre-register: `anima-clm-eeg/state/clm_eeg_pre_register_v1_1.json` (**v1.1 SSOT**, supersedes v1).

| artifact | path | sha256 (v1.1 frozen vs disk) | status |
|---|---|---|---|
| synthetic fixture | `anima-clm-eeg/tool/clm_eeg_synthetic_fixture.hexa` | `0dfe2c2e…` ✓ match | OK |
| P1 LZ tool | `anima-clm-eeg/tool/clm_eeg_p1_lz_pre_register.hexa` | `416e6be6…` ✓ match (v1.1 re-freeze, see `clm_eeg_pre_register_v1_to_v1_1_changelog.md`) | OK |
| P2 TLR tool | `anima-clm-eeg/tool/clm_eeg_p2_tlr_pre_register.hexa` | `fbff2e85…` ✓ match | OK |
| P3 GCG tool | `anima-clm-eeg/tool/clm_eeg_p3_gcg_pre_register.hexa` | `0eec458c…` ✓ match | OK |
| harness smoke | `anima-clm-eeg/tool/clm_eeg_harness_smoke.hexa` | `18196513…` ✓ match | OK |
| 16ch fixture | `anima-clm-eeg/fixtures/synthetic_16ch_v1.json` | `831a1b5d…` ✓ match | OK |
| pre-register JSON | `anima-clm-eeg/state/clm_eeg_pre_register_v1_1.json` | chain_sha256=`647e04f7…` (self-locked file, recomputed IDENTICAL) | OK |

**해석**: 본 readiness check 의 초기 §3.1 (2026-04-26 작성) 은 legacy v1.0 의 P1 sha (`cd17abd8…`) 와 disk 값을 비교해 phantom MISMATCH 보고했음. v1.1 SSOT 가 이미 P1 sha re-freeze (`416e6be6…`) + `v1_0_to_v1_1_diff` block 으로 source_silent_edit drift 명시 처리 완료된 상태. 2026-04-27 background 검증 결과 10/10 frozen artifacts MATCH v1.1, 5/5 selftest PASS — phantom mismatch 해결 (witness: `clm_eeg_p1_sha_resync_20260427_landing.md`, commit `c67ca062`).

### §3.2 anima-eeg production runtime (D+0)

`MIGRATION_INVENTORY.json` + `PHASE3_PROGRESS.md` 종합:

| component | type | LOC | disk status | D+0 ready? |
|---|---|---|---|---|
| `__init__.hexa` | FULL | 136 | sha `c6bf3cc5…` 3/3 PASS | yes (no hardware) |
| `protocols/__init__.hexa` | FULL | 94 | 3/3 PASS | yes |
| `protocols/emotion_sync.hexa` | FULL | 344 | 9/9 PASS | yes (caller-supplied alpha) |
| `protocols/sleep_protocol.hexa` | FULL | 329 | 10/10 PASS | yes |
| `transplant_eeg_verify.hexa` | FULL | 295 | 9/9 PASS | yes |
| `scripts/monthly_eeg_validate.hexa` | FULL | 253 | 7/7 PASS | yes (DEGRADED mode — synthetic) |
| `neurofeedback.hexa` | FULL | 320 | 8/8 PASS | yes |
| `analyze.hexa` | FULL (Cycle 2) | 539 | sha `83f78ab7…` 10/10 PASS | yes (Welch PSD ready) |
| `validate_consciousness.hexa` | FULL (Cycle 2) | 721 | sha `1414b37b…` 10/10 PASS, brain_like 0.833 | yes (6-metric) |
| `protocols/bci_control.hexa` | STUB | 27 | Phase 3 Cycle 3 pending (~2h) | partial |
| **`calibrate.hexa`** | **WRAPPER STUB** | 23 | dummy returns (`return false / 0.0`) | **NO** |
| **`collect.hexa`** | **WRAPPER STUB** | 25 | dummy `CollectResult("",0,0,0.0)` | **NO** |
| **`eeg_recorder.hexa`** | **WRAPPER STUB** | 34 | dummy returns | **NO** |
| `experiment.hexa` | WRAPPER STUB | — | — | NO |
| `realtime.hexa` | WRAPPER STUB | 29 | — | NO |
| `closed_loop.hexa` | WRAPPER STUB | — | — | NO |
| `dual_stream.hexa` | WRAPPER STUB | — | — | NO |
| `protocols/multi_eeg.hexa` | WRAPPER STUB | — | — | NO |
| `scripts/organize_recordings.hexa` | WRAPPER STUB | — | — | NO |

**critical**: D+0 단계의 3개 핵심 산출물 (`calibrate`, `collect`, `eeg_recorder`) 가 모두 stub. Phase 4 (~40h wallclock) 미진행 → **D+0 hardware bring-up이 disk에서 막힘**.

대안 path: `tool/an11_b_eeg_ingest.hexa` (360L, raw#9 hexa-only BrainFlow wrapper) 가 이미 존재하며 reference로 사용 가능. 이 도구를 D+0 임시 ingest path로 직접 활용 가능 (corner-cut option).

### §3.3 CLM substrate + V_sync (D+3/D+5)

| component | path | LOC / status |
|---|---|---|
| L_IX integrator | `edu/cell/lagrangian/l_ix_integrator.hexa` | READY |
| V_sync Kuramoto | `edu/cell/lagrangian/v_sync_kuramoto.hexa` | READY (state/v_sync_kuramoto_verdict.json 존재) |
| paradigm v11 router | `tool/anima_v11_main.hexa` | READY (225L, 12 subcommands) |
| an11_b ingest reference | `tool/an11_b_eeg_ingest.hexa` | READY (360L raw#9 BrainFlow wrapper) |

### §3.4 G10 / G8 / Mk.XII activation (D+5/D+7)

| component | path | status |
|---|---|---|
| g10 scaffold | `anima-clm-eeg/tool/g10_hexad_triangulation_scaffold.hexa` | READY |
| g10 spec | `docs/g10_triangulation_spec_post_arrival.md` | READY (frozen) |
| g8 transversal MI matrix | `anima-clm-eeg/tool/g8_transversal_mi_matrix.hexa` | READY synthetic (real-data wiring D+6) |
| g8 sweep extended | `anima-clm-eeg/tool/g8_n_bin_sweep_extended.hexa` | READY |
| g8 N=128 analysis | `anima-clm-eeg/tool/g8_n_bin_128_analysis.hexa` | READY |
| Mk.XII preflight | `anima-clm-eeg/tool/mk_xii_preflight_cascade.hexa` | READY (composite recompute) |
| Mk.XII d-day simulated | `anima-clm-eeg/tool/mk_xii_d_day_simulated_dry_run.hexa` | READY (D+0~D+7 dry-run already validated, marker `mk_xii_d_day_simulated_complete.marker` 존재) |

### §3.5 recordings storage

| dir | status | role |
|---|---|---|
| `anima-eeg/recordings/sessions/` | empty (`.gitkeep` only) | D+0~D+1 .npy 저장 destination |
| `anima-eeg/recordings/validations/` | empty (`.gitkeep`) | post-validate JSON 저장 |
| `anima-eeg/recordings/protocols/` | populated (existing logs) | OK |

→ destination dir 준비됨. write path는 stub `collect.hexa` 쪽이 막혀있을 뿐.

## §4. ω-cycle 6-step verdict

### 1. design — frozen
7-day workflow는 `clm_eeg_pre_register_v1.json` `post_arrival_workflow` block + README §5 + `g10_triangulation_spec_post_arrival.md` §3에 frozen.

### 2. implement — disk audit complete
27 필수 산출물 audit. 21 READY / 1 sha mismatch (P1) / 9 STUB (Phase 4 WRAPPER 9 modules).

### 3. positive selftest
`mk_xii_d_day_simulated_complete.marker` 가 존재 → D-day full simulated dry-run은 이미 PASS. PRE-REGISTER 5/5 byte-identical (1개 P1 sha 제외) 검증됨.

### 4. negative falsify
**negative finding**: 3개 D+0 hardware bring-up tool (`calibrate`, `collect`, `eeg_recorder`) STUB 상태로 hardware 도착 시 즉시 .npy 산출 불가 → workflow chain D+0 첫 단계에서 break.

### 5. byte-identical
모든 이미 PASS한 hexa 도구는 byte-identical reproducible (FNV-hash deterministic, RNG seed 고정). 본 readiness check 도구 호출 없이 disk audit only → 본 산출물 자체도 deterministic.

### 6. iterate — verdict
**PARTIAL** — Section §5.

## §5. Readiness verdict

```
verdict          : PARTIAL
ready_count      : 22 / 27 (81%) ← P1 phantom mismatch 해결 (v1.1 SSOT, 2026-04-27)
mismatch_count   : 0  (P1 sha — phantom only, v1.1 frozen MATCH)
stub_count       : 5  (calibrate, collect, eeg_recorder + bci_control + experiment등 9개 중 D+0 critical 5개)
day_blocked      : D+0 (hardware bring-up)
day_ready        : D+1 verify, D+3 verify, D+5 verify, D+5 G10 activation, D+6 G8 port baseline, D+7 composite + Hard PASS
post_arrival_friction : medium (D+0 manual override or an11_b_eeg_ingest fallback)
```

**rationale**: pre-register 자체는 frozen + sha-locked + dry-run HARNESS_OK 3/3 + Mk.XII d-day simulated dry-run 이미 PASS. 따라서 **research-track readiness는 100%**. 그러나 D+0 hardware ingest path (`anima-eeg` Phase 4 WRAPPER 9 modules) 가 stub 상태이므로 **production-track readiness는 partial**. D+1 P1 verify는 .npy 가 산출되어야 진입 가능하므로 D+0 stub이 critical path 위에 있음.

## §6. 누락 산출물 priority list

| # | 항목 | severity | 처리 wallclock | 사전 land 가능? | 권장 |
|---|---|---|---|---|---|
| 1 | **`calibrate.hexa` Phase 4 WRAPPER full** | HIGH | 4h | yes ($0 mac) | EEG 도착 전 land 권장. `tool/an11_b_eeg_ingest.hexa` 패턴 차용 |
| 2 | **`collect.hexa` Phase 4 WRAPPER full** | HIGH | 4h | yes ($0 mac) | 동일 |
| 3 | **`eeg_recorder.hexa` Phase 4 WRAPPER full** | HIGH | 5h | yes ($0 mac) | 동일 |
| ~~4~~ | ~~P1 LZ tool sha mismatch — pre-register v1.1 bump~~ | RESOLVED | — | — | **2026-04-27 자체 해결**: v1.1 SSOT 가 이미 P1 sha re-freeze + diff block 명시 (phantom mismatch — 본 readiness check 가 legacy v1.0 sha 인용한 것이 원인). witness `clm_eeg_p1_sha_resync_20260427_landing.md` |
| 5 | `experiment.hexa` Phase 4 WRAPPER (markers) | MEDIUM | 4h | yes | D+1 N-back 진입 시 필요 |
| 6 | `protocols/multi_eeg.hexa` Phase 4 | LOW | 5h | yes | D+5 multi-board 사용 시만 |
| 7 | `realtime.hexa` Phase 4 WRAPPER | LOW | 5h | yes | live monitoring 사용 시만 |
| 8 | `closed_loop.hexa` Phase 4 WRAPPER | LOW | 5h | yes | D+5+ 사용 시만 |
| 9 | `dual_stream.hexa` Phase 4 WRAPPER | LOW | 4h | yes | optional |
| 10 | `scripts/organize_recordings.hexa` (sqlite) | LOW | 4h | yes | post-D+7 archival |
| 11 | `protocols/bci_control.hexa` Phase 3 Cycle 3 | LOW | 2h | yes | Phase 3 closure |

**critical path priority 1-3 sub-total**: ~13h wallclock, $0 mac local.

**recommended sequencing**: 1→2→3 (4h+4h+5h = 13h) 를 EEG 도착 전 land. 도착 직후 D+0 즉시 calibrate → collect → eeg_recorder 정상 작동.

**fallback (corner-cut)**: priority 1-3 land 없이 도착 시, `tool/an11_b_eeg_ingest.hexa` (360L raw#9 BrainFlow wrapper) 직접 호출하여 .npy 산출 가능. anima-eeg/calibrate 우회 — 정식 production 진입은 아니지만 **D+1 P1 verify는 가능**.

## §7. EEG 도착 즉시 trigger 절차 (post-arrival entry)

**가정**: priority 1-3 사전 land 또는 fallback path 사용.

```
# D+0 (도착 당일)
# 1. board 연결 + impedance check
hexa run anima-eeg/calibrate.hexa --port=<auto-detect>
# 2. resting baseline 60s eyes-closed
hexa run anima-eeg/eeg_recorder.hexa --duration=60 --tag=resting_baseline --output=recordings/sessions/d0_resting.npy
# 3. N-back recording (5-10 min)
hexa run anima-eeg/eeg_recorder.hexa --duration=600 --tag=nback --output=recordings/sessions/d0_nback.npy

# D+1 (도착 +1일)
# 4. P1 LZ verify against real .npy
HEXA_RESOLVER_NO_REROUTE=1 hexa run anima-clm-eeg/tool/clm_eeg_p1_lz_pre_register.hexa --real-npy=anima-eeg/recordings/sessions/d0_resting.npy

# D+3 (도착 +3일)
# 5. CLM hidden trace 산출 (Mk.XI v10 forward)
hexa run edu/cell/lagrangian/v_sync_kuramoto.hexa --emit-trace
# 6. P2 TLR verify (FFT Welch coh + V_sync r)
HEXA_RESOLVER_NO_REROUTE=1 hexa run anima-clm-eeg/tool/clm_eeg_p2_tlr_pre_register.hexa --real-npy=... --vsync-trace=...

# D+5 (도착 +5일)
# 7. L_IX hidden trace (layer 25-30 emit)
hexa run edu/cell/lagrangian/l_ix_integrator.hexa --emit-hidden
# 8. P3 GCG verify (Granger F-stat unidirectional)
HEXA_RESOLVER_NO_REROUTE=1 hexa run anima-clm-eeg/tool/clm_eeg_p3_gcg_pre_register.hexa --real-npy=... --lix-hidden=...
# 9. G10 hexad triangulation activate (4-backbone × 4-band × Hexad-cat)
hexa run anima-clm-eeg/tool/g10_hexad_triangulation_scaffold.hexa --real-mode

# D+6
# 10. G8 real-falsifier MI port (transversal MI matrix on real data)
hexa run anima-clm-eeg/tool/g8_transversal_mi_matrix.hexa --real-mode

# D+7
# 11. composite + Hard PASS recompute
HEXA_RESOLVER_NO_REROUTE=1 hexa run anima-clm-eeg/tool/clm_eeg_harness_smoke.hexa
hexa run anima-clm-eeg/tool/mk_xii_preflight_cascade.hexa --post-arrival
```

**시간 추정**: D+0 ~3h (calibrate 30min + 2× recording 11min + analyze + checkpoint) / D+1 1d (P1) / D+3 2d (P2) / D+5 2d (P3+G10) / D+6 1d (G8) / D+7 0.5d (composite). 총 7d wallclock + $12-24 GPU (P3 layer 25-30 forward).

## §8. cross-references

- pre-register SSOT: `anima-clm-eeg/state/clm_eeg_pre_register_v1.json`
- hardware spec: `anima-clm-eeg/docs/eeg_hardware_openbci_16ch.md`
- arrival impact: `anima-clm-eeg/docs/eeg_arrival_impact_5fold.md`
- path comparison: `anima-clm-eeg/docs/path_comparison_a_b_c.md`
- migration plan: `anima-eeg/MIGRATION_PLAN.md`
- migration progress: `anima-eeg/PHASE3_PROGRESS.md`
- migration inventory: `anima-eeg/MIGRATION_INVENTORY.json`
- G10 spec: `anima-clm-eeg/docs/g10_triangulation_spec_post_arrival.md`
- D-day simulated marker: `anima-clm-eeg/state/markers/mk_xii_d_day_simulated_complete.marker`
- `.roadmap` entries: #119 BLOCKED-EEG / #154 Phase 3 Cycle 1 / #157 Path A pre-register / #165 Phase 3 Cycle 2

## §9. 다음 cycle 권장

**즉시 가능** (이번 cycle 후 별도 trigger 없이):
1. anima-eeg Phase 4 WRAPPER priority 1-3 (`calibrate` + `collect` + `eeg_recorder`) 13h 사전 land — `tool/an11_b_eeg_ingest.hexa` 패턴 차용
2. P1 LZ tool sha mismatch resolution → pre-register v1.1 bump (30min)

**EEG 도착 시 즉시 trigger**:
- 위 §7 D+0 step 1-3 실행
- 부재 시 `tool/an11_b_eeg_ingest.hexa` fallback path

**raw#10 honest 단서**:
- D+0~D+7 chain 전체가 disk-static audit 결과만으로는 진입 가능하지 않음. priority 1-3 land 또는 fallback path 한 가지가 반드시 필요.
- `mk_xii_d_day_simulated_complete.marker` PASS는 synthetic fixture 기반 dry-run이며 real-EEG 진입을 직접 imply하지 않는다. P3 dry-run PASS는 lag-1 echo synthesis 때문이라는 raw#10 honest는 그대로 유효 (`.roadmap` #157 raw_ref).

## D-day arrival checklist (macOS)

§7가 **hexa-level trigger** 절차라면, 본 절은 그 직전의 **physical/OS-level bring-up 절차**다. hardware spec SSOT는 `eeg_hardware_openbci_16ch.md` 의 `## macOS connection flow` 와 본 체크리스트가 isomorphic (Phase 0~1 공통, Phase 2~7 본 문서 단독).

### Phase 0 — arrival (~5 min)

- 박스 contents: board, USB Dongle, 배터리 + 충전기, headset, 전극, 케이블 검수
- 배터리는 충전기 LED **green**까지 완충 (부분 충전 시 board의 blue LED가 안 들어와 boot 실패)
- Dongle 스위치 → **GPIO 6** (computer 측)
- Cyton 스위치 → **OFF** 유지
- Daisy ribbon cable이 board에 단단히 seated 됐는지 확인

### Phase 1 — connect (순서 중요)

- **Dongle을 Mac에 먼저 꽂는다** (칩 면이 위로). 정상 시 steady **blue LED + blinking red LED**
- 그 다음 Cyton OFF → **PC** (BLE 위치 절대 금지)
- `ls /dev/cu.usbserial-* /dev/cu.usbmodem*` → `/dev/cu.usbserial-DM00XXXX` 경로 캡처
- stream drop / device 인식 실패 시: Dongle 분리 → Cyton OFF → **Dongle 먼저 재연결** → Cyton PC

### Phase 2 — driver (macOS Sonoma+)

- Apple Silicon Sonoma+에서는 FTDI VCP가 **DriverKit 내장**. 보통 추가 설치 불필요.
- `/dev/cu.usbserial-*`가 안 보이면: System Settings → Privacy & Security 에서 차단된 system extension 허용 → 재부팅 → 재시도
- 위 경로가 실패할 때만 manual FTDI VCP installer fallback

### Phase 3 — GUI sanity (BrainFlow 진입 전)

- `openbci.com/downloads` 에서 GUI v6 macOS .dmg 받아 `/Applications` 로 드래그
- 첫 실행: 우클릭 → Open (Gatekeeper 우회). Documents 폴더 access 허용.
- LIVE (Cyton) → Serial (Dongle) → 위에서 캡처한 `/dev/cu.usbserial-*` 포트 선택 → **반드시 16 CHANNELS 명시** (default는 8 ch, Daisy는 자동 감지 안 됨) → AUTO-CONNECT → START SYSTEM
- 전극 미부착 상태에서 60 Hz noise wobble이 보이면 정상

### Phase 4 — BrainFlow Python via `.venv-eeg`

```bash
source /Users/ghost/core/anima/.venv-eeg/bin/activate
pip install --upgrade brainflow numpy
```

5초 capture sanity: `BoardIds.CYTON_DAISY_BOARD` (value `2`), `serial_port` = Phase 1에서 잡은 `/dev/cu.usbserial-*`. 기대 shape ≈ **(32, ~625)** = 32 채널 (16 EEG + aux/timestamp) × 5 s × **125 Hz** (Cyton+Daisy 16ch native; Daisy interleaving 으로 per-channel rate 가 250 Hz 의 절반). 250 Hz × 5 s = 1250 으로 잘못 가정하면 BrainFlow native rate 와 mismatch 되어 downstream filter / windowing 다 어긋남. `BoardShim.get_sampling_rate(BoardIds.CYTON_DAISY_BOARD.value)` 가 정답 (= 125).

### Phase 5 — headset + impedance

- Earclip 양쪽 (reference + bias) 둘 다 부착 필수
- Dry comb electrode는 머리카락을 갈라 두피에 직접 contact. GUI Impedance widget에서 **모든 채널 < 750 kΩ** 목표
- 안 떨어지는 채널은 Gold cup + Ten20 paste (wet) 로 교체

### Phase 6 — anatomical sanity

- Eyes-closed 30 s → **O1/O2에 8–12 Hz alpha peak** 기대
- 이는 `tool/clm_eeg_synthetic_fixture.hexa` 의 O1/O2 `alpha_bias=900` **generator-prior** 와 정성적으로 일치. fixture disk JSON (`fixtures/synthetic_16ch_v1.json`) 은 post-mix `band_powers_x1000.alpha` 형식이며 O1=2328 / O2=1930 / P7=2176 / P4=2088 (occipital > parietal > frontal pattern 유지). disk 에 `alpha_bias` literal 필드는 없음 — generator parameter ↔ post-mix output 두 layer 구분
- 통과하면 falsifier pre-register (§7 D+1~) 진입 green-light

### Phase 7 — FTDI latency tweak (optional, 첫 capture가 끊길 때만)

- Default FTDI latency 16 ms는 125 Hz × 16 ch × 24-bit BrainFlow stream을 starve 시킬 수 있음
- Apple Silicon DriverKit 경로: 편집할 kext 없음. Standalone FTDI VCP 설치 후 LatencyTimer를 **1 ms** 로 조정
- Intel kext 경로: `/Library/Extensions/FTDIUSBSerialDriver.kext/Contents/Info.plist` 에서 `LatencyTimer` → `1`

**§7과의 chain**: Phase 0~6 통과 = §7 D+0 step 1 (`anima-eeg/calibrate.hexa`) 진입 가능 상태. Phase 4 sanity에서 **(32, ~625)** shape (= 32ch × 125 Hz × 5 s) 확인 시 fallback path `tool/an11_b_eeg_ingest.hexa` 도 즉시 호출 가능.
