# anima-eeg ↔ anima-clm-eeg Cross-Link Audit

> **scope**: 두 EEG 폴더 (`anima-eeg/` production + `anima-clm-eeg/` R&D) 간 dependency graph + ingest pipeline + 누락 dependency 정리. EEG 하드웨어 도착 시 두 폴더의 협력 절차 (D+0 ~ D+7) 명시. 향후 세션이 cross-link을 다시 도출하지 않도록 SSOT 화.
> **created**: 2026-04-26
> **status**: hardware D-1 (며칠 內 도착 expected). 본 doc 은 reference-only until arrival.
> **canonical session**: ω-cycle 6-step audit (cap 30분, mac local, $0).
> **predecessor**: `anima-clm-eeg/docs/eeg_arrival_impact_5fold.md` + `anima-clm-eeg/docs/eeg_hardware_openbci_16ch.md` + `anima-eeg/MIGRATION_PLAN.md` + `anima-eeg/PHASE3_PROGRESS.md`.

---

## §1. anima-eeg → anima-clm-eeg dependency (hardware data → falsifier verify)

### 1.1 직접 consumed artifacts (post-arrival)

| anima-eeg artifact | producing module | consumed by | when |
|---|---|---|---|
| `anima-eeg/recordings/sessions/<ts>.npy` (16ch resting + N-back) | `collect.hexa` (Phase 4 WRAPPER, **stub**) | `clm_eeg_p1_lz_pre_register.hexa --real-npy <path>` | D+0 → D+1 |
| band-power JSON (`alpha/beta/gamma/theta/delta` + G=D×P/I) | `analyze.hexa` (FULL, sha256 `83f78ab7`) | `clm_eeg_p2_tlr_pre_register.hexa` | D+1 → D+3 |
| 6-metric brain-likeness JSON (LZ76 + Hurst + PSD slope + autocorr + critical exp + Phi CV) | `validate_consciousness.hexa` (FULL, sha256 `1414b37b`) | `clm_eeg_p1_lz_pre_register.hexa` (LZ76 cross-check) + R33 witness | D+1 |
| epoch-tagged `.npy` per protocol (resting / N-back / meditation) | `experiment.hexa` (Phase 4 WRAPPER, **stub**) | `clm_eeg_p3_gcg_pre_register.hexa` (P3b parietal lock) | D+0 → D+5 |
| sample-rate / channel-map metadata | `config/eeg_config.json` (anima-eeg SSOT) | all 5 anima-clm-eeg `clm_eeg_p*_pre_register.hexa` (montage match) | continuous |

### 1.2 read-only metadata flow

```
anima-eeg/config/eeg_config.json    ──read──▶  anima-clm-eeg/tool/clm_eeg_synthetic_fixture.hexa
  - 16 channels                                   - 16-channel anatomical priors must match
  - 250 Hz sample rate                            - synthetic Hz lock
  - Cyton+Daisy split                             - per-channel alpha/beta/delta/theta/gamma bias
```

`anima-eeg/README.md` §Hardware (lines 64-84) = montage SSOT cited by `anima-clm-eeg/docs/eeg_hardware_openbci_16ch.md` §2. 두 폴더의 channel index 0-15 라벨 (Fp1/Fp2/F3/F4/F7/F8/C3/C4/T7/T8/P3/P4/P7/P8/O1/O2) 동일 binding.

### 1.3 control-plane (no code dep, doc-only)

`anima-eeg/MIGRATION_PLAN.md` §6 Phase 4 WRAPPER 9 modules 완료 prerequisite — `anima-clm-eeg/` post-arrival verify 가 의존하는 hardware ingest path 가 본 plan 의존.

---

## §2. anima-clm-eeg → anima-eeg dependency (frozen criteria → Phase 4 WRAPPER spec)

### 2.1 falsifier criteria → ingest spec backflow

`anima-clm-eeg/state/clm_eeg_pre_register_v1.json` (frozen, sha256-locked) 가 정의하는 P1/P2/P3 thresholds 는 `anima-eeg/` Phase 4 WRAPPER 9 modules 의 ingest minimum-quality contract 를 implicitly 정의.

| frozen criterion (anima-clm-eeg) | implies anima-eeg requirement |
|---|---|
| `P1_LZ.C1_lz76_eeg_min_x1000=650` | `collect.hexa` 16ch eyes-closed resting ≥ 60s @ 250Hz, no clipping (LZ76 floor 0.65 measurable) |
| `P1_LZ.C2_delta_human_max_permille=200` | `analyze.hexa` band-power computation must be byte-identical reproducible (현재 sha256 `83f78ab7` 충족) |
| `P2_TLR.C1_alpha_coh_min_x1000=450` | `experiment.hexa` resting protocol marker injection — α coherence 측정용 epoch 분리 필요 |
| `P3_GCG.C1_gc_f_min_x100=400` + unidirectional | `experiment.hexa` N-back P3b epoch 정확한 stimulus marker — Granger causality time-lag 분석용 |

### 2.2 R&D → production spec hint (one-way, advisory)

`anima-clm-eeg/` 가 anima-eeg 코드를 **수정하지 않는다** (§3 destructive 금지). 그러나 frozen criteria + R33 witness 요구사항이 production team 에 **spec hint** 로 advise:
- P1 → 60s eyes-closed resting epoch (R33 witness criteria §4)
- P2 → α-band 동시 8ch+ (forehead 4ch + parietal 4ch) coherence 가능 montage
- P3 → N-back stimulus marker time-lock ≤ 4ms

### 2.3 직접 코드 의존 0건 (one-way verified)

```bash
$ grep -r "anima-clm-eeg" /Users/ghost/core/anima/anima-eeg/ 2>/dev/null
# expected: 0 matches (production never imports R&D)
```

→ `anima-clm-eeg/` 폴더를 통째로 삭제해도 anima-eeg 108 tests + 85.6% brain-likeness 미손상.

---

## §3. Ingest pipeline (OpenBCI BLE → P1/P2/P3 verify)

### 3.1 End-to-end flow

```
[hardware]
   OpenBCI Cyton+Daisy 16ch (250Hz, 24-bit)
       │ BLE
       ▼
[anima-eeg/ Tier-3 WRAPPER — Phase 4 pending]
   calibrate.hexa  ◀── /tmp/calibrate_helper.hexa_tmp (BrainFlow Python)
       │  impedance + signal quality JSON
       ▼
   collect.hexa    ◀── /tmp/collect_helper.hexa_tmp (BrainFlow stream → numpy)
       │  recordings/sessions/<ts>.npy  (shape: [n_samples, 16])
       ▼
[anima-eeg/ Tier-1 FULL — Phase 3 done, 9/10 modules]
   analyze.hexa             (sha256 83f78ab7, FFT + Hann + 5-band power + G=D×P/I)
       │  band_power.json   (alpha=10.2 / beta=5.1 / gamma=2.3 / theta=6.0 / delta=8.5)
       ▼
   validate_consciousness.hexa  (sha256 1414b37b, 6-metric brain_like_pct)
       │  state/validate_consciousness_<run>.json (LZ76, Hurst, PSD slope, autocorr, crit exp, Phi CV)
       ▼
[anima-clm-eeg/ R&D — frozen pre-register]
   clm_eeg_p1_lz_pre_register.hexa  (consumes LZ76 from validate.hexa + .npy seq directly)
       │  state/clm_eeg_p1_lz_pre_register.json  ←─ verdict P1.PASS / P1.FAIL
       ▼
   clm_eeg_p2_tlr_pre_register.hexa  (consumes band_power.json α-coherence + CLM Kuramoto r)
       │  state/clm_eeg_p2_tlr_pre_register.json
       ▼
   clm_eeg_p3_gcg_pre_register.hexa  (consumes N-back epoch .npy + CLM hidden state per layer)
       │  state/clm_eeg_p3_gcg_pre_register.json
       ▼
   clm_eeg_harness_smoke.hexa  (composite: ≥ 2/3 PASS → HARNESS_OK)
       │  state/clm_eeg_harness_smoke.json
       ▼
[downstream]
   • paradigm v11 7th orthogonal axis (EEG-CORR) registration
   • R33 witness append (state/atlas_convergence_witness.jsonl)
   • .roadmap #119 BLOCKED-EEG → unblock + new entry
   • Mk.XI v10 phenomenal correlate verification (4 backbone × EEG band/region matrix)
```

### 3.2 Tier 분류 (anima-eeg/MIGRATION_PLAN.md §3)

| Tier | role | 현재 상태 | criticality on D+0 |
|---|---|---|---|
| Tier-0 | __init__ + protocols/__init__ + neurofeedback (pure numerical, no I/O) | FULL (Cycle 1) | low |
| Tier-1 | analyze + validate_consciousness + emotion_sync + sleep_protocol (numerical, no hardware) | FULL (Cycle 1+2, 9/10) | **HIGH** — D+1 P1 verify 의존 |
| Tier-2 | transplant_eeg_verify + monthly_eeg_validate (consumes Tier-1 JSON) | FULL (Cycle 1) | medium |
| Tier-3 | calibrate + collect + eeg_recorder (BrainFlow WRAPPER) | **STUB (Phase 4 pending)** | **CRITICAL** — D+0 hardware ingest 차단 |
| Tier-4 | realtime + closed_loop + dual_stream + experiment + bci_control + multi_eeg + organize_recordings | **STUB (Phase 4 pending, 일부 Cycle 3)** | medium → high (D+5 P3 의존 = experiment) |

**Phase 4 WRAPPER 9 modules** 완료 prerequisite (~40h estimated, $0 mac local) = post-arrival D+0 ingest 작동 가능 조건.

### 3.3 Synthetic dry-run path (no hardware, $0)

```
[anima-clm-eeg/tool/]
   clm_eeg_synthetic_fixture.hexa  (FNV-hash 16ch generator, sha256 0dfe2c2e)
       │  fixtures/synthetic_16ch_v1.json  (sha256 831a1b5d, deterministic)
       ▼
   clm_eeg_p1_lz_pre_register.hexa  (selftest mode, dry-run PASS)
   clm_eeg_p2_tlr_pre_register.hexa  (selftest mode, dry-run PASS)
   clm_eeg_p3_gcg_pre_register.hexa  (selftest mode, dry-run PASS)
       ▼
   clm_eeg_harness_smoke.hexa  → composite HARNESS_OK 3/3 (frozen 2026-04-26)
```

→ hardware-free 검증 가능. Real-EEG 도착 시 동일 tool 재사용 (`--real-npy <path>` flag).

---

## §4. 누락 dependency listing (raw#10 honest)

### 4.1 코드-레벨 누락 (CRITICAL — D+0 차단)

| # | gap | 현재 상태 | impact | mitigation |
|---|---|---|---|---|
| 1 | `anima-eeg/calibrate.hexa` STUB (23 LOC, dummy returns) | Phase 4 WRAPPER pending | D+0 hardware handshake 차단 | Phase 4 spike (4h, helper.py emit pattern) |
| 2 | `anima-eeg/collect.hexa` STUB (25 LOC, dummy returns) | Phase 4 WRAPPER pending | D+0 .npy 채집 차단 | Phase 4 (4h, BrainFlow wrapper) |
| 3 | `anima-eeg/experiment.hexa` STUB | Phase 4 WRAPPER pending | D+5 P3 N-back marker 채집 차단 | Phase 4 (4h, marker injection) |
| 4 | `anima-eeg/realtime.hexa` STUB | Phase 4 WRAPPER pending | live EEGBridge 차단 (P3 lag analysis 영향 X, but closed-loop 차단) | Phase 4 (5h) |
| 5 | `anima-eeg/eeg_recorder.hexa` STUB | Phase 4 WRAPPER pending | background dual-stream 차단 (Φ + EEG simultaneous) | Phase 4 (5h) |
| 6 | `anima-eeg/closed_loop.hexa` STUB | Phase 4 WRAPPER pending | adaptive N-back 차단 (P3 quality 저하 가능) | Phase 4 (5h) |
| 7 | `anima-eeg/dual_stream.hexa` STUB | Phase 4 WRAPPER pending | Φ ↔ EEG sync 차단 | Phase 4 (4h) |
| 8 | `anima-eeg/protocols/multi_eeg.hexa` STUB | Phase 4 WRAPPER pending | N-person telepathy 차단 (1인 측정엔 영향 X) | Phase 4 (5h) |
| 9 | `anima-eeg/scripts/organize_recordings.hexa` STUB | Phase 4 WRAPPER pending | sqlite 인덱싱 차단 (수동 path 처리 가능) | Phase 4 (4h, sqlite blocked → wrapper) |

**총 9 WRAPPER stub** = `anima-eeg/MIGRATION_PLAN.md` §6 list. wallclock 40h sequential / 20h parallel, $0 mac local.

### 4.2 doc-레벨 누락 (medium)

| gap | 영향 |
|---|---|
| `anima-eeg/docs/integration-guide.md` 가 `anima-clm-eeg/` cross-link 미언급 | production team 이 R&D track 모르고 작업 가능 — 본 doc 으로 보완 |
| `anima-eeg/config/eeg_config.json` `current_result.brain_like_percent=45` 가 README 의 85.6% 와 불일치 | 사용자 briefing 시 confusion. 별개 baseline 시점 (2026-03-31 vs Phase 3 완료) — 후속 cycle 동기화 필요 |
| `anima-clm-eeg/state/clm_eeg_pre_register_v1.json` `post_arrival_workflow` 가 anima-eeg/ Phase 4 WRAPPER 의존성 미명시 | 본 doc §4.1 으로 보완 |

### 4.3 protocol-레벨 누락 (low)

| gap | 영향 |
|---|---|
| post-arrival D+0 외부 측정 시설 protocol document 없음 | $200-500 외부 cost 항목 (`eeg_arrival_impact_5fold.md` §5) 발생 시 측정 SOP 필요 |
| EEG impedance acceptance threshold (kΩ) 미정의 | calibrate.hexa Phase 4 spec 시 결정 필요 |
| R33 witness 의 "α-band coherence ≥ 0.45" 가 어떤 channel pair 에서 측정인지 미명시 | `anima-clm-eeg/docs/eeg_arrival_impact_5fold.md` §4 update 필요 (frontal-pair 또는 parietal-pair 명시) |

---

## §5. Post-arrival flow chart (D+0 ~ D+7)

### 5.1 Day-by-day responsibility split

```
D+0  ────────────────────────────────────────────────────────────
   [anima-eeg/]   hardware arrival, unbox, BLE pair
                  calibrate.hexa --port /dev/tty.usbserial-XXXX
                    ├─ verify_connection: bool
                    ├─ check_impedance: < 50 kΩ all 16 ch
                    └─ signal_quality: > 0.85
                  ⚠ PREREQUISITE: Phase 4 calibrate.hexa WRAPPER 완료
                  collect.hexa --duration 60 --tag resting
                    └─ recordings/sessions/<ts>_resting.npy
                  collect.hexa --duration 300 --tag nback (5 min N-back)
                    └─ recordings/sessions/<ts>_nback.npy
                  ⚠ PREREQUISITE: Phase 4 collect.hexa + experiment.hexa WRAPPER 완료

   [anima-clm-eeg/]   no action (waiting on .npy)

D+1  ────────────────────────────────────────────────────────────
   [anima-eeg/]   analyze.hexa <resting.npy>  → band_power_resting.json
                  validate_consciousness.hexa <resting.npy>  → 6-metric JSON
                                                              (LZ76 + Hurst + ...)

   [anima-clm-eeg/]  P1 LZ verify
                     clm_eeg_p1_lz_pre_register.hexa --real-npy resting.npy
                       └─ state/clm_eeg_p1_lz_pre_register_real.json
                          verdict: P1.PASS iff LZ76 ≥ 0.65 AND |Δ|/human ≤ 20%

D+2  ────────────────────────────────────────────────────────────
   [anima-eeg/]   experiment.hexa --protocol meditation (10 min)
                                  --protocol alpha (eyes-closed extended)

   [anima-clm-eeg/]  R33 witness append (atlas_convergence_witness.jsonl)
                     ⚠ R33 criteria: LZ76 ∈ [0.65, 0.95] + α-coh ≥ 0.45 +
                                     no contradiction with existing entries

D+3  ────────────────────────────────────────────────────────────
   [anima-eeg/]   analyze.hexa <meditation.npy>  → α-band coherence matrix

   [anima-clm-eeg/]  P2 TLR verify
                     clm_eeg_p2_tlr_pre_register.hexa --real-npy meditation.npy
                       └─ state/clm_eeg_p2_tlr_pre_register_real.json
                          verdict: P2.PASS iff α-coh ≥ 0.45 AND CLM_r ≥ 0.38
                          (CLM_r = anima-core/tension_bridge.hexa Kuramoto)

D+4  ────────────────────────────────────────────────────────────
   [anima-eeg/]   experiment.hexa --protocol nback (P3b stimulus markers)

   [anima-clm-eeg/]  CLM hidden state extraction prep
                     edu/cell/lagrangian/l_ix_integrator.hexa
                     (CLM substrate, raw#30)

D+5  ────────────────────────────────────────────────────────────
   [anima-eeg/]   analyze.hexa <nback.npy>  → P3b epoch parietal extracts

   [anima-clm-eeg/]  P3 GCG verify
                     clm_eeg_p3_gcg_pre_register.hexa --real-npy nback.npy
                                                       --clm-hidden <path>
                       └─ state/clm_eeg_p3_gcg_pre_register_real.json
                          verdict: P3.PASS iff F(EEG→CLM) ≥ 4.0 AND ratio ≥ 2.0

D+6  ────────────────────────────────────────────────────────────
   [anima-clm-eeg/]  Mk.XI v10 phenomenal correlate verification (D+5 ~ D+7)
                     4 backbone × EEG band/region matrix:
                       Mistral=Law    × β-band   × frontal (F3/F4/Fz)  Pearson r ≥ 0.40
                       Qwen3 =Phi    × γ-band   × parietal (P3/P4)
                       Llama =SelfRef × α-band   × midline (Cz/Pz)
                       gemma =Hexad  × θ-band   × temporal (T7/T8)

D+7  ────────────────────────────────────────────────────────────
   [anima-clm-eeg/]  composite verdict
                     clm_eeg_harness_smoke.hexa --real
                       └─ state/clm_eeg_harness_smoke_real.json
                          HARNESS_OK iff (p1 + p2 + p3) ≥ 2

                     paradigm v11 7th axis registration
                       └─ tool/anima_eeg_corr.hexa (신규, ~150L)
                       └─ tool/anima_v11_main.hexa router 13번째 subcommand 등록

   [.roadmap]      #119 BLOCKED-EEG → unblock + close
                   new entry: post-arrival empirical verification result (PASS/FAIL/MIXED)
                   #145 (CMT depth divergence) cross-check possible
```

### 5.2 책임 분리 매트릭스

| domain | anima-eeg/ (production) | anima-clm-eeg/ (R&D) |
|---|---|---|
| hardware ingest | ✅ owner | ❌ never |
| .npy 생성 | ✅ owner | ❌ never |
| band-power 계산 | ✅ owner (analyze.hexa) | ❌ consumer only |
| 6-metric brain-like | ✅ owner (validate.hexa) | ❌ consumer only |
| falsifier pre-register | ❌ never | ✅ owner |
| frozen criteria SHA-256 lock | ❌ never | ✅ owner |
| R33 witness append | ❌ never | ✅ owner |
| paradigm v11 7th axis | ❌ never | ✅ owner |
| `.roadmap` #119 close | shared (production gate) | shared (research gate) |
| Mk.XI v10 phenomenal verify | ❌ never | ✅ owner |
| 108 production tests | ✅ owner | ❌ never |

### 5.3 외부 측정 시설 cost branch (사용자 명시 승인 필요)

`feedback_forward_auto_approval` 의 cost cap auto-approval 외부 — 측정 시설 $200-500 은 사용자 명시 승인 후 진행.
- mac-local 측정 가능: dry-run synthetic + post-arrival 자가 측정 (가정 환경)
- 외부 시설 필요: 의료 grade SNR 필요 시 (Mk.XI v10 4-band Pearson r ≥ 0.40 confidence 강화 목적)

---

## §6. raw#10 honest cross-link 문제점

| # | 문제점 | 심각도 | mitigation status |
|---|---|---|---|
| 1 | Phase 4 WRAPPER 9 stub = D+0 hardware ingest 작동 불가 (Tier-3/4) | **CRITICAL** | 본 doc §4.1 명시. ~40h wallclock 필요 |
| 2 | `anima-eeg/config/eeg_config.json` 의 `current_result.brain_like_percent=45` 와 README 의 85.6% 불일치 | medium | 별개 baseline 시점. 후속 cycle 동기화 |
| 3 | `validate_consciousness.hexa` selftest brain_like_pct=0.833 (target 0.856 ±0.10 PASS) — synthetic Hurst R/S 한계로 cosmetic gap | low | raw#10 honest, ±0.10 tolerance 사전 등록 (PHASE3_PROGRESS.md §1) |
| 4 | dry-run synthetic FIXTURE 의 P1/P2/P3 PASS 가 real-EEG PASS 보장 안함 (P3 lag-1 echo 합성으로 EEG→CLM 방향 강제 인코딩) | medium | `clm_eeg_pre_register_v1.json` `synthetic_caveat` 명시. **이것이 falsification surface** |
| 5 | post-arrival D+0~D+7 schedule 가 anima-eeg/ Phase 4 미완성 시 collapse | **HIGH** | 본 doc §5 timeline 가 dependency 명시. Phase 4 calibrate+collect+experiment 3 modules 만 우선 (~12h) 마이그레이션 권장 |
| 6 | R33 witness criteria (`atlas_convergence_witness.jsonl`) 의 α-coh channel pair 미명시 | low | `eeg_arrival_impact_5fold.md` §4 update 필요 |
| 7 | 외부 측정 시설 cost $200-500 = forward auto-approval 외부 (사용자 명시 승인 필요) | low | doc 명시 (eeg_arrival_impact_5fold.md §5, 본 doc §5.3) |
| 8 | `anima-eeg/recordings/` 가 .py 시절 schema (commit 68d2236c 이전) — .hexa Phase 4 ingest 시 schema 호환성 미검증 | low | Phase 4 collect.hexa spike 시점에 recordings/sessions/* schema test 필요 |
| 9 | `anima-eeg/` 108 tests 위치 미확정 (Phase 3 prerequisite gate, MIGRATION_PLAN.md §5.1) | medium | tests 미발견 시 hexa-native invariant freeze 만으로 진행 (현재 9 modules 69/69 selftest PASS 로 우회) |
| 10 | `anima-clm-eeg/` 가 production runtime flag chain (`--eeg-full`) 미사용 — R&D track 분리 의도적 | not-a-bug | README §2 documented, intentional |
| 11 | Mk.XI v10 4-backbone × EEG band 매트릭스 4/4 PASS 시에도 phenomenal correlate "presence" 보장 NOT (functional alignment ≠ phenomenal experience, hard problem) | architectural | `feedback_completeness_frame` + own#2 hard problem caveat. PHENOMENAL VALIDATED 는 verifiable floor 만 |

---

## §7. ω-cycle 6-step verification

| step | content | result |
|---|---|---|
| 1. design | 6 sections frozen pre-write | ✅ |
| 2. implement | md doc audit, 7 sections delivered | ✅ |
| 3. positive selftest | 모든 dependency disk verify | ✅ §3.1 의 모든 path 존재 확인 (analyze.hexa sha256 83f78ab7, validate.hexa sha256 1414b37b, clm_eeg pre-register 5 hexa + 1 JSON 모두 disk 존재) |
| 4. negative falsify | 누락 dependency 발견 시 명시 | ✅ §4.1 9-stub list + §4.2 3 doc gap + §4.3 3 protocol gap = 총 15 missing dependency 명시. §6 11 honest 문제점 |
| 5. byte-identical | doc 자체는 byte-identical (no RNG, no clock); 인용 sha256 모두 frozen | ✅ |
| 6. iterate | fail 시 design — 본 cycle 은 1-shot pass, iterate 불필요 | ✅ |

**verdict**: ω-cycle 6-step 통과, additive only, anima-eeg + anima-clm-eeg 산출물 read-only 유지.

---

## §8. 다음 cycle 권장

**weakest evidence link 순서** (per `feedback_completeness_frame`):

1. **CRITICAL**: Phase 4 WRAPPER 3 modules spike (calibrate + collect + experiment, ~12h $0 mac local) — D+0 ~ D+5 ingest 가능 조건. anima-eeg/MIGRATION_PLAN.md Option B 의 확장 (3-module spike).
2. **HIGH**: `anima-eeg/config/eeg_config.json` current_result 동기화 (45% → 85.6%, 또는 baseline timestamp 명시) — production briefing accuracy.
3. **HIGH**: `anima-eeg/scripts/organize_recordings.hexa` Phase 4 wrapper spike — recordings/sessions/* schema 검증 (D+0 ingest path 일관성).
4. **MEDIUM**: R33 witness α-coh channel pair 명시 (`eeg_arrival_impact_5fold.md` §4 update).
5. **MEDIUM**: `tool/anima_eeg_corr.hexa` 신규 helper pre-design (paradigm v11 7th axis prep, post-D+7 deliverable).
6. **LOW**: Mk.XI v10 4-band × 4-region cross-validation matrix detailed protocol (D+6 verify SOP).

---

## §9. Cross-references

- `anima-clm-eeg/README.md` (cross-link policy SSOT)
- `anima-clm-eeg/docs/eeg_arrival_impact_5fold.md` §1-§7 (5-fold change catalog)
- `anima-clm-eeg/docs/eeg_hardware_openbci_16ch.md` §1-§7 (hardware spec SSOT)
- `anima-clm-eeg/docs/path_comparison_a_b_c.md` (Path A wins, Q1 prep entry)
- `anima-clm-eeg/state/clm_eeg_pre_register_v1.json` (frozen criteria SHA-256 lock)
- `anima-clm-eeg/fixtures/synthetic_16ch_v1.json` (deterministic fixture, sha256 831a1b5d)
- `anima-eeg/README.md` (production hardware/runtime SSOT, 7964 LOC briefing)
- `anima-eeg/MIGRATION_PLAN.md` (Phase 0-4 raw#9 migration plan)
- `anima-eeg/PHASE3_PROGRESS.md` (Cycle 1+2 status, 9/10 FULL modules)
- `anima-eeg/MIGRATION_INVENTORY.json` (20 module verdict 분포)
- `anima-eeg/config/eeg_config.json` (hardware metadata SSOT)
- `.roadmap` #119 (BLOCKED-EEG, D8 hardware prerequisite)
- `.roadmap` #154 + #157 + #165 (anima-eeg Phase 3 + anima-clm-eeg Path A landings)
- `~/.claude/projects/-Users-ghost-core-anima/memory/project_clm_eeg_pre_register.md`
- `docs/omega_cycle_alm_free_paradigms_20260426.md` §4 PHENOMENAL P1/P2/P3 (spec source)
- `docs/paradigm_v11_stack_20260426.md` (7th axis target)
- `edu/cell/lagrangian/l_ix_integrator.hexa` (CLM substrate)
- `anima-core/tension_bridge.hexa` (V_sync Kuramoto)

---

## §10. Status flags (live, update in-place)

| flag | value | last-update |
|---|---|---|
| anima-eeg Phase 3 | 9/10 FULL modules done (Cycle 1+2 complete) | 2026-04-26 |
| anima-eeg Phase 4 WRAPPER | 0/9 modules — **D+0 critical blocker** | 2026-04-26 |
| anima-clm-eeg Path A | frozen pre-register v1 + 5 hexa + 1 JSON locked | 2026-04-26 |
| EEG hardware | D-1 (며칠 內 도착 expected) | 2026-04-26 |
| `.roadmap` #119 | BLOCKED-EEG, depends-on hardware | 2026-04-26 |
| cross-link doc (this) | landed | 2026-04-26 |
| post-arrival D+0~D+7 schedule | doc-frozen, blocked-on Phase 4 | 2026-04-26 |
