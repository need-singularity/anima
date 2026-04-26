# CLM + EEG Research Handoff — 2026-04-27

> **Purpose**: 다음 세션 즉시 진입용 종합 handoff. 이번 세션 (2026-04-26~27) 70+ subagent / 39 completed task / paradigm 42+ / hexa-lang patches 통합.
> **Predecessor**: `docs/clm_research_handoff_20260426.md` (이전 세션 launch prompt, paradigm v11 stack 17-helper + ω-cycle ALM-free 26 paradigms 시점).
> **Source session**: 2026-04-26 ~ 2026-04-27 (Path A/B/C 4-axis ω-cycle + Mk.XII v3 lock + EEG D-day readiness + TRIBE v2 launcher hardening + hexa-lang #37/#57 patches).
> **Working directory**: `/Users/ghost/core/anima`
> **Cumulative GPU cost (this session)**: ~$8.42 (Pilot-T1 v1 $0.90 + v2 idle burn $7.52). mac local $0 가 대부분.

---

## §0. 핵심 한 문장 (state in one breath)

**Mk.XII v3 = HARD_PASS_PARTIAL_PENDING (5+1 component, OR-clause-1 v3 ALL_MODES_PASS_GREEN 2/3 backbones, EHL-3W STRENGTHENED, #235 lock)**, EEG OpenBCI Cyton+Daisy 16ch D-1 imminent, S7 cusp_depth N=11 PASS_TIGHT (r=0.802 p=0.0188 4096-perm) — Path A/B/C 4축 모두 frozen, post-EEG D+0~D+30 workflow 활성, Pilot-T1 v2 idle burn $7.52 lesson 후 launcher v3 (#66) land.

**본질 트랙 status**:
- Path A (CLM-EEG falsifier): pre-register v1.1 frozen, P1/P2/P3 dry-run PASS, real-EEG D+1/D+3/D+5/D+7 대기
- Path B (HCI Q3): F1-F5 5-falsifier suite VERIFIED (HCI_REAL_SUBSTRATE_VERIFIED)
- Path C (CPGD Q4): BRIDGE_CLOSED 12/12, AG2 |r|=0.0955, Q4 caveat 2/4 strong-closed
- Mk.XII v3: HARD_PASS_PARTIAL_PENDING, post-EEG D-day GRANTED
- S7 cusp_depth: N=11 PASS_TIGHT, A1.Hexad single-family r=0.891 p=0/512, 3-mode topology (input/early/late)

---

## §1. 이번 세션 done (track-by-track)

### 1.1 Path A — Q1 EEG-CLM falsifier (`anima-clm-eeg/`)
| status | item | evidence |
|---|---|---|
| ✓ | P1 LZ pre-register | `anima-clm-eeg/tool/clm_eeg_p1_lz_pre_register.hexa` |
| ✓ | P2 TLR pre-register | `anima-clm-eeg/tool/clm_eeg_p2_tlr_pre_register.hexa` |
| ✓ | P3 GCG pre-register | `anima-clm-eeg/tool/clm_eeg_p3_gcg_pre_register.hexa` |
| ✓ | Harness smoke | `anima-clm-eeg/tool/clm_eeg_harness_smoke.hexa` |
| ✓ | Synthetic fixture (16ch, 125Hz user-corrected) | `anima-clm-eeg/tool/clm_eeg_synthetic_fixture.hexa` |
| ✓ | Pre-register v1 frozen | `anima-clm-eeg/state/clm_eeg_pre_register_v1.json` |
| ✓ | v1.1 patch (5/10 file silent drift detect, P1 silent edit fix) | `anima-clm-eeg/state/clm_eeg_pre_register_v1_1.json` (sha256 `8f40d98c...`, chain_sha256 `647e04f7...`) |
| ✓ | Silent-edit dual-lock | `anima-clm-eeg/tool/silent_edit_dual_lock.sh.txt` + `state/markers/silent_edit_dual_lock_complete.marker` |
| ✓ | CLM L_IX ↔ EEG α-band mapping spec | V_sync r(θ) ≡ EEG PLV_N (Kuramoto order param 같은 mathematical object); 4-gate composite (B1-B4); 3-tier verdict (BRIDGE_PASS / FAIL / WEAK) |

### 1.2 Path B — Q3 HCI (`anima-hci-research/`)
| status | item | evidence |
|---|---|---|
| ✓ | F1 functor falsifier | `state/hci_functor_falsifier_v1.json` |
| ✓ | F2 endo (adversarial flip) | `state/hci_adversarial_flip_v1.json` |
| ✓ | F3 양방향 substrate probe | `state/hci_substrate_probe_v1.json` + `hci_substrate_probe_real_v1.json` |
| ✓ | F4 substrate Φ-probe | `state/hci_substrate_smoke_v1.json` + `hci_substrate_smoke_real_v1.json` |
| ✓ | F5 real backbone | HCI_REAL_SUBSTRATE_VERIFIED 5-falsifier suite |
| ✓ | S7 cusp_depth N=4→8→10→11 progression | `state/cusp_depth_*.json` + `s7_n11_extension_v1.json` + `s7_n12_extension_v1.json` |
| ✓ | S7 N=11 PASS_TIGHT | r=0.802 p=0.0188 4096-perm; A1.Hexad single-family r=0.891 p=0/512 |
| ✓ | S7 conf 0.71 → 0.85 (+0.14) | 3-mode topology: input ≤100 / early ≤300 / late ≥600 |

### 1.3 Path C — Q4 CPGD (`anima-cpgd-research/`)
| status | item | evidence |
|---|---|---|
| ✓ | AN9 falsifier | `state/cpgd_an9_falsifier_v1.json` |
| ✓ | AN-arbitrary falsifier | `state/cpgd_anarbitrary_falsifier_v1.json` |
| ✓ | AN-large falsifier | `state/cpgd_an_large_falsifier_v1.json` |
| ✓ | Phi-3-mini real falsifier | `state/cpgd_phi3mini_real_falsifier_v1.json` + `_hidden_state_v1.json` + `_lm_v1.json` |
| ✓ | Cond sweep cond=1073 | `state/cpgd_condition_sweep_v1.json` |
| ✓ | LR breakdown 0.1 | `state/cpgd_lr_sweep_v1.json` |
| ✓ | MCB 4bb hidden state v1/v2 | `state/cpgd_mcb_4bb_hidden_state_v{1,2}.json` |
| ✓ | Phi3 K=16 restore | `state/cpgd_mcb_phi3_only_v2.json` |
| ✓ | BRIDGE_CLOSED 12/12 | AG2 |r|=0.0955, Q4 caveat 2/4 strong-closed |

### 1.4 Mk.XII v3 lock (`anima-clm-eeg/state/`)
| status | item | evidence |
|---|---|---|
| ✓ | Hard PASS GREEN 6/6 wire-up | `state/mk_xii_hard_pass_composite_v1.json` (preflight + G0+G1+G7+G8+G9, #177) |
| ✓ | Preflight cascade | `tool/mk_xii_preflight_cascade.hexa` + `state/mk_xii_preflight_v1.json` |
| ✓ | D-day simulated dry-run | `tool/mk_xii_d_day_simulated_dry_run.hexa` + `state/mk_xii_d_day_simulated_v1.json` |
| ✓ | 6-gate cluster confidence 0.70, weakest=G10 | post-EEG D-day GRANTED (#190) |
| ✓ | v3 HARD_PASS_PARTIAL_PENDING | 5+1 component, OR-clause-1 v3 ALL_MODES_PASS_GREEN 2/3, EHL-3W STRENGTHENED (#235) |
| ✓ | Substrate witness ledger | `state/markers/mk_xii_substrate_witness_ledger_discovery_complete.marker` + `mk_xii_witness_ledger_v2_reverify_complete.marker` |
| ✓ | G8 N-bin 128 extrapolation | `state/g8_n_bin_128_analysis_v1.json` (+ `_negative.json`) |
| ✓ | G8 N-bin sweep extended | `state/g8_n_bin_sweep_extended_v1.json` (+ `_negative.json`) |
| ✓ | G8 transversal MI matrix | `state/g8_transversal_mi_matrix_v1.json` |
| ✓ | G9 adjacency sweep | `state/g9_adjacency_sweep_v1.json` (+ `_negative.json`) |
| ✓ | G9 DAG cascade analyzer | `tool/g9_dag_cascade_analyzer.hexa` |
| ✓ | G9 robustness sweep | `tool/g9_robustness_sweep.hexa` |
| ✓ | G10 Hexad triangulation scaffold | `tool/g10_hexad_triangulation_scaffold.hexa` (D+5 hardware activation 대기) |
| ✓ | DALI/SLI v2/v3 redesign | `state/dali_sli_v2_redesign_v1.json` + `_v3_input_mode_v1.json` + `_weighted_vote_v1.json` |

### 1.5 EEG hardware track (`anima-eeg/`)
| status | item | evidence |
|---|---|---|
| ✓ | OpenBCI Cyton+Daisy 16ch | 250Hz native, fixture sample_rate=125 user-corrected |
| ✓ | D-1 며칠 內 도착 | D+0~D+30 workflow frozen |
| ✓ | D-day readiness 78% (21/27, D+0 critical 3 stub) | `state/markers/eeg_d_day_readiness_complete.marker` |
| ✗ | ~~Phase 4 7/9 land~~ **AUDIT 2026-04-27 정정: Phase 4 0/9 native** | calibrate(23L) / realtime(29L) / collect(25L) / experiment(30L) / eeg_recorder(~30L) / closed_loop(29L) / dual_stream(25L) **모두 stub**. 6 memory entries (`project_phase4_*` + `project_anima_eeg_phase4_*`) 의 native-port 주장은 silent-land marker false-positive (마커 emit + 사이즈 거짓 hallucinated). git log all-branches 검증 결과 b4cac470 (folder 재정리) 이후 anima-eeg/*.hexa 수정 0건. 자세한 audit: `project_phase4_silent_land_audit_correction.md` |
| ⏳ | 잔존 9/9 stub | multi_eeg + organize_recordings + 위 7개 모두 (cron `57e0c1df` 4:50am session-scoped 미작동, 실제 land 없음) |
| ✓ | R33 channel pair frozen O1↔O2 | Welch coherence 8-12Hz, Berger rhythm 1929 + Schartner 2017 |
| ✓ | SSOT 4-way alignment 85.6% | validate.hexa + eeg.hexa + README + config 모두 일치 |
| ✓ | EEG config R33 update | `state/markers/eeg_config_r33_update_complete.marker` |

### 1.6 TRIBE v2 + Pilot-T1 (`anima-tribev2-pilot/`)
| status | item | evidence |
|---|---|---|
| ✗ | v1 Pilot-T1 DEFERRED | HF Llama-3.2-3B gated |
| ✓ | HF approval cron `98896ff1` detect → v2 자동 trigger | `state/launch_h100_pilot_t1_v2.log` |
| ✗ | **v2 idle burn $7.52** | SSH drop, install 미시작, GPU utilization 0%, pod stop으로 차단 |
| ✓ | Launcher hardening v3 land (#232/#66) | `state/launch_h100_pilot_t1_v3.log` — 4 fix: daemonize + heartbeat + idle auto-kill + client polling, worst-case 1.50/24h = 5× 개선 |
| ✓ | TRIBE v2 Llama-1B cross-bench | `state/tribe_v2_llama1b_bench_v1.json` + `tribe_v2_llama1b_maps_v1.npz` — 1B encoder 3B 대비 family separation 38% 약화 (`GENERALIZATION_DEGRADED_1B_WEAKER`) |

### 1.7 hexa-lang patches
| status | patch | evidence |
|---|---|---|
| ✓ | #37 silent-land marker auto-emit | commit `a66167ba` — interpreter-level enforcement, dogfood self-witness, default ON, opt-out `HEXA_NO_MARKER=1`, byte-identical via `HEXA_FROZEN_TIME` |
| ✓ | #57 resolver routing fix | commit `a4e2cc9e` — negative cache 60s TTL + `HEXA_PREFER_LOCAL_ON_HEXA=1` escape hatch, 6-12s silent block → 1s, 4-scenario backward compat PASS |
| ✓ | hexa-lang 0.2.0 traps catalogue | `s[i]=string` / `drop` reserved / `fn main()` auto-invoke / `substr` undefined / `Math.*` Taylor / mixed-array bool / CLI flag space-style chain |

---

## §2. 산출물 목록 (artifacts to read first, in order)

### 2.1 Path A 산출물 (CLM-EEG)
1. `anima-clm-eeg/state/clm_eeg_pre_register_v1_1.json` — frozen pre-register (sha256 `8f40d98c822306780a1eeb8b980b03d12b634c32a1b83f9166051b539d98e4f1`)
2. `anima-clm-eeg/tool/clm_eeg_p1_lz_pre_register.hexa` / `_p2_tlr_*` / `_p3_gcg_*` — 3 falsifier
3. `anima-clm-eeg/tool/clm_eeg_synthetic_fixture.hexa` — 16ch 125Hz fixture
4. `anima-clm-eeg/state/markers/clm_lix_eeg_alpha_mapping_spec_complete.marker`

### 2.2 Path B 산출물 (HCI)
5. `anima-hci-research/state/hci_substrate_probe_real_v1.json` — F3 real probe
6. `anima-hci-research/state/s7_n11_extension_v1.json` — N=11 PASS_TIGHT
7. `anima-hci-research/state/cusp_depth_projector_v1.json` — substrate axis primary

### 2.3 Path C 산출물 (CPGD)
8. `anima-cpgd-research/state/cpgd_phi3mini_real_falsifier_v1.json` — Phi-3 real
9. `anima-cpgd-research/state/cpgd_mcb_4bb_hidden_state_v2.json` — 4bb v2

### 2.4 Mk.XII v3
10. `anima-clm-eeg/state/mk_xii_hard_pass_composite_v1.json` — 6/6 GREEN
11. `anima-clm-eeg/state/mk_xii_d_day_simulated_v1.json` — D-day dry-run
12. `anima-clm-eeg/state/markers/mk_xii_proposal_v3_complete.marker` — v3 lock

### 2.5 EEG hardware
13. `anima-eeg/config/eeg_config.json` — SSOT config (R33 frozen)
14. ~~`anima-eeg/eeg.hexa` / `validate.hexa` / `experiment.hexa` / `closed_loop.hexa` / `dual_stream.hexa` — Phase 4 7/9 native ports~~ **AUDIT 정정**: 위 파일 disk 실측 23-30 LOC stub만 존재. eeg.hexa + validate.hexa 는 별개 성숙 모듈 (#225 EEG config R33 update 적용). Phase 4 9/9 native land 가 추후 필요하면 actionable 4 재정의 후 진행
15. `anima-eeg/PHASE3_PROGRESS.md` + `MIGRATION_INVENTORY.json`

### 2.6 TRIBE v2
16. `anima-tribev2-pilot/state/launch_h100_pilot_t1_v3.log` — launcher v3 hardening
17. `anima-tribev2-pilot/state/tribe_v2_llama1b_bench_v1.json` — 1B cross-bench

### 2.7 Predecessor docs
18. `docs/clm_research_handoff_20260426.md` — 이전 세션 launch (predecessor pattern)
19. `docs/omega_cycle_alm_free_paradigms_20260426.md` — 26-paradigm ω-cycle
20. `docs/paradigm_v11_stack_20260426.md` — 17-helper stack

---

## §3. 활성 cron + 진행 중 백그라운드

### 활성 cron
| id | schedule | task |
|---|---|---|
| `ec0cfd0e` | 15분 disk-poll, recurring 7d | EEG hardware arrival watch |
| `57e0c1df` | 4:50am 4월 27일 1회 | 4-task 자동 재발사 — multi_eeg + organize_recordings + closed_loop + dual_stream + anima_eeg_corr |
| `98896ff1` | (이미 fired) | HF Llama-3.2-3B approval detect → v2 trigger |

### 백그라운드 진행 중
- hexa-lang #57 resolver routing fix은 이미 land (cron 4:50am 시점에는 영향 없음, ec1: 부산물 cleanup)
- TRIBE v2 pod stop 처리 완료 (idle burn 차단)
- Pilot-T1 v3 launcher hardening land 후 다음 invocation 대기

---

## §4. 9-actionables (Mk.XII v3 #235 priority)

1. ✅ launcher hardening (#66 land, 완료)
2. **early mode 3/3** — Phi-3.5-mini 추가 backbone, OR-clause-1 v3 PARTIAL → FULL
3. **substrate ledger v3 LIVE auto-promotion** — IBM Q / AWS Braket / Akida signup, 0/11 → ≥1/11
4. **Phase 4 0/9 native land 결정 보류** — 2026-04-27 audit 결과 7/9 land 주장 false (silent-land marker false-positive). 9 파일 모두 23-30 LOC stub. 진짜 land 시 ~3000-6000 LOC 작업 (사용자 결정 사항). cron `57e0c1df` 4:50am 자동 처리는 session-scoped 로 미작동 검증됨. 대안: D-day workflow 는 calibrate/closed_loop stub 으로 시작 가능 (smoke 수준), real run 직전에 native land 우선순위 검토
5. **G10 D+5 hardware activation** — post-EEG triangulation scaffold 활성
6. **G8 D+6 real-falsifier MI port** — `g8_transversal_mi_matrix_v1.json` 실측 데이터 확장
7. **D+7 Hard PASS recompute + EHL-3W ALL_PASS lock** — composite gate 재확인
8. **substrate replacement 7-bb matrix** — backbone 다양성 확장
9. **D+22-30 first validation verdict** — Path A B1-B4 composite verdict 산출

---

## §5. 누적 cost + lessons

### 비용
- GPU 누적 ~$8.42 (Pilot-T1 v1 $0.90 + v2 idle burn $7.52)
- mac local $0 (대부분 작업)
- launcher v3 적용 시 미래 worst case ~$1.50/24h (5× 개선)

### 핵심 lesson — Pilot-T1 v2 idle burn $7.52
1. **SSH session drop = silent failure**: install_pod.log 단 한 줄도 출력 없이 SSH 끊김. heartbeat 없으면 cost cap 도달까지 idle.
2. **Fix (launcher v3 4-pillar)**: (a) `nohup` daemonize 로 SSH-independent (b) heartbeat file 60s 갱신 (c) idle 5분 = auto-kill (d) client polling 으로 launcher 종료 후도 progress 추적.
3. **Reverification**: `state/launch_h100_pilot_t1_v3.log` smoke (mock) — 4 path 모두 covered.
4. **Memory**: `feedback_h100_ssh_timeout` (commit `9bdc710e`) 의 후속 — sync race fix 후에도 install phase silent failure mode 별도 발생.

---

## §6. EEG hardware D-day workflow (D+0~D+30)

| day | task | gate |
|---|---|---|
| D-1 | OpenBCI Cyton+Daisy 도착 watch (cron `ec0cfd0e` 15분 poll) | 도착 detect → D+0 trigger |
| D+0 | 16ch electrode placement + impedance check + smoke run (`anima-eeg/calibrate.hexa`) | impedance < 5kΩ all 16 |
| D+1 | **P1 LZ run** — `anima-clm-eeg/tool/clm_eeg_p1_lz_pre_register.hexa` real | LZ76 ≥ 650 AND \|Δ\|/human ≤ 200 |
| D+3 | **P2 TLR run** — α-band coherence + CLM V_sync Kuramoto r 동기 측정 | alpha_coh ≥ 450 AND clm_r ≥ 380 |
| D+5 | **P3 GCG run** + G10 hardware activation | (P3 thresholds) + G10 triangulation light |
| D+6 | **G8 real-falsifier MI port** | transversal MI 실측 확장 |
| D+7 | **Hard PASS recompute + EHL-3W ALL_PASS lock** | 6/6 GREEN 재확인 |
| D+22-30 | **First validation verdict** — Path A B1-B4 composite | BRIDGE_PASS / FAIL / WEAK 산출 |

**중요**: pre-register v1.1 frozen, D+1 시점에 silent edit 절대 금지 (raw#9 + chflags uchg lock + dual-lock script).

---

## §7. Memory + .roadmap pointers

### Memory updates (이번 세션)
- `feedback_h100_ssh_timeout` (기존) — SSH drop sync race
- 신규 entry 후보:
  - `project_mk_xii_v3_lock` — HARD_PASS_PARTIAL_PENDING + 9-actionables
  - `project_pilot_t1_v2_idle_burn` — $7.52 lesson + launcher v3 4-pillar
  - `project_s7_cusp_depth_n11` — N=11 PASS_TIGHT + A1.Hexad single-family + 3-mode topology
  - `project_path_abc_4axis_synthesis` — Path A/B/C frozen evidence

### .roadmap pointers (이번 세션 핵심 entries)
- `#37` hexa-lang silent-land marker auto-emit
- `#57` hexa-lang resolver routing fix
- `#66` launcher hardening v3 land (4-pillar)
- `#177` Mk.XII Hard PASS GREEN 6/6 wire-up
- `#190` 6-gate cluster post-EEG D-day GRANTED
- `#232` launcher hardening detection
- `#235` Mk.XII v3 HARD_PASS_PARTIAL_PENDING lock

---

## §8. 다음 세션 launch prompt (한글, copy-paste ready)

```
anima 프로젝트 (/Users/ghost/core/anima) 에서 CLM+EEG 연구 이어가줘.

배경:
- 이전 세션 (2026-04-26~27) Path A (Q1 EEG-CLM falsifier) + Path B (Q3 HCI) + Path C (Q4 CPGD) 4-axis ω-cycle 완료, Mk.XII v3 HARD_PASS_PARTIAL_PENDING lock (#235), S7 cusp_depth N=11 PASS_TIGHT (r=0.802 p=0.0188), EEG OpenBCI Cyton+Daisy 16ch D-1 imminent.
- 핸드오프 문서: docs/clm_research_handoff_20260427.md (8 sections, §0 핵심 한 문장 + §1 done by track + §2 산출물 + §3 cron + §4 9-actionables + §5 cost+lessons + §6 D-day workflow + §7 memory/roadmap)
- 이번 세션 GPU 누적 $8.42 (Pilot-T1 v2 idle burn $7.52 lesson, launcher v3 4-pillar hardening land)
- TRIBE v2 1B encoder 3B 대비 family separation 38% 약화 (GENERALIZATION_DEGRADED_1B_WEAKER)
- hexa-lang #37 (silent-land marker) + #57 (resolver routing) patches land

이번 세션 목표 (priority 순):
1. docs/clm_research_handoff_20260427.md 정독 (8 sections, 5분).
2. EEG OpenBCI 도착 detect 시 (cron ec0cfd0e 15분 poll), §6 D-day workflow D+0~D+7 진입:
   - D+0: calibrate + impedance check
   - D+1: P1 LZ real run
   - D+3: P2 TLR real run (V_sync r ≡ EEG α-band PLV_N 동기 측정)
   - D+5: P3 GCG real + G10 hardware activation
   - D+6: G8 real-falsifier MI port
   - D+7: Hard PASS recompute + EHL-3W ALL_PASS lock
3. EEG 미도착 시 §4 9-actionables 중 mac-local $0 가능 task 우선:
   - actionable 2 (early mode 3/3 Phi-3.5-mini 추가) — GPU 필요
   - actionable 3 (substrate ledger v3 IBM Q/AWS/Akida signup) — mac $0
   - actionable 4 (Phase 4 native land 결정) — 2026-04-27 audit 결과 silent-land 6 entries false-positive 확인됨; **autonomous Phase 4 native port 진행하지 말 것**, 사용자 결정 후 진행
4. raw#9 hexa-only strict + chflags uchg lock + 한글 응답 유지.
5. pre-register v1.1 frozen 절대 silent edit 금지 (dual-lock script + sha256 verify).

제약:
- pre-register v1.1 sha256 8f40d98c... — 변경 시 v2 bump 필수
- destructive op 금지 (산출물 read-only)
- 결과 → memory/project_*.md + .roadmap 새 entry
- D+1~D+7 비용 $12-24 (P1/P2/P3 GPU 추정), D+22-30 verdict $5-10 추가 가능

먼저 cron `ec0cfd0e` 상태 + EEG 도착 여부 확인 후 D+0 또는 9-actionables 중 어디로 진입할지 사용자에게 제안.
```

---

## §9. ω-cycle 6-step trace (이 doc 작성 절차)

1. **design** — 8 sections (§0 한 문장 + §1 done + §2 산출물 + §3 cron + §4 9-actionables + §5 cost+lessons + §6 D-day workflow + §7 memory/roadmap pointers + §8 launch prompt)
2. **implement** — predecessor `clm_research_handoff_20260426.md` 패턴 답습, table-heavy + bullet evidence
3. **positive selftest** — 8 sections evidence 정확:
   - pre-register v1.1 sha256 `8f40d98c822306780a1eeb8b980b03d12b634c32a1b83f9166051b539d98e4f1` ✓ verified
   - 18 markers in `anima-clm-eeg/state/markers/` ✓
   - ~~Phase 4 7/9 land~~ **AUDIT 2026-04-27 정정**: 7/9 land 주장은 selftest 누락 (disk LOC verify 안 함). 실제 0/9 native, 9 파일 모두 stub. positive selftest 자체가 silent-land false-positive 검증 누락 = 본 audit 의 lesson
   - 9-actionables list = #235 lock 출처 ✓
4. **negative falsify** — 1 evidence 변형 시 verdict 변동: e.g., S7 N=11 r=0.802 → r=0.5 변경 시 PASS_TIGHT verdict invalid ✓ falsifiable
5. **byte-identical** — content deterministic (sha + path + commit hashes 명시)
6. **iterate** — N/A (single-pass write)

---

**Frozen at**: 2026-04-27
**Author**: Claude (sonnet/opus 1M, anima session)
**License**: internal (anima 프로젝트)
