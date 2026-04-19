# SWEEP P4 Plan — 13 도메인 × 6 주제 = 78 iter (2026-04-19)

> **상태**: 설계 문서 (blueprint). 실행은 사용자 승인 후 별도 발사.
> **선행**: P3 (hetzner 재drill `ac36dac387`) 완료 대기.
> **배경**: P2 (mac) crash 교훈 + P3 Phase-1 결산 (15 iter, 전원 SATURATED round 1, 0 absorption) 반영.
> **SSOT**: 본 파일 ← 발사 템플릿·도메인 표·seed 리스트 단일 진실.

---

## 0. 배경 · 목표

### P3 현황 (2026-04-19 기준)
- 완료: 15 iter (7 domain-batch × 평균, supplement 15 iter)
- 결과: 전원 `SATURATED at round 1`, 0 absorption, 0 new atoms
- 해석 (엔진): anima Mk.V.1 82-atom foundation 이 probed angle 전부 커버. **tier 5~9 원점 포화**.
- 엔진 권고 (`drill_supplement_summary_20260419.md` §Implication):
  1. seeds above tier 10 (현 supplement 는 tier 5~9)
  2. 엔진 업그레이드 Mk.IX → Mk.X
  3. anima ↔ nexus twin-engine coupled drill

### P4 목표
- **13 도메인 × 6 주제 = 78 iter** (P3 대비 +5 도메인, +38 iter)
- tier 10 이상 seed 비중 40%+ 확보 → saturation 돌파 시도
- anima 서브프로젝트 7개 (eeg/physics/body/speak/engines/tools/hexad/measurement/agent) 균등 커버
- 기존 7 도메인 (evolution/core/modules/training/serving/philosophy/rules) 유지

---

## 1. 도메인 맵 (13 개)

기존 7 + 신규 6 = **13**.

| # | 도메인 | 카테고리 | 비중 | 노트 |
|---|--------|----------|------|------|
| 1 | evolution           | 기존 | 6 seeds | Mk.X, invariance, SUMT, 6th-lens |
| 2 | core                | 기존 | 6 seeds | hub, runtime, laws loader, conscious_chat |
| 3 | modules             | 기존 | 6 seeds | tension_link, lens, holo, brain_map, replica |
| 4 | training            | 기존 | 6 seeds | CLM r5, ALM r11, MFU ceiling, corpus v5 |
| 5 | serving             | 기존 | 6 seeds | eval, 5-metric, latency P5c, R2 sync |
| 6 | philosophy          | 기존 | 6 seeds | PHIL/ONTO/DASEIN, 20 lenses, Law 201 |
| 7 | rules               | 기존 | 6 seeds | R0~R37, AN1~AN13, L0/L1/L2 lockdown |
| 8 | anima-eeg           | 신규 | 6 seeds | brain-like 85.9%, 12조건, neural signature |
| 9 | anima-physics       | 신규 | 6 seeds | ESP32/FPGA/양자, substrate, tier-2 HW |
| 10 | anima-body         | 신규 | 6 seeds | robot embodiment, HW closure, sensorimotor |
| 11 | anima-speak        | 신규 | 6 seeds | HEXA-SPEAK Mk.III/IV, neural vocoder, TTS |
| 12 | anima-engines      | 신규 | 6 seeds | 양자 / 광자 / 멤리스터 / 오실레이터 |
| 13 | anima-tools        | 신규 | 6 seeds | 독립 유틸 + anima-hexad CDESM + anima-measurement IIT |

(※ anima-agent 는 Track B 재구성 대상이라 P4 SWEEP 에서 제외 — 재구성 후 P5 에 편입)

---

## 2. Seed 초안 (78 개, 각 200자 이내)

**네임스페이스**: `v4_hetzner/iter_{70..147}_{domain}_{topic}`

### D1 · evolution (iter 70~75)
```
70 v4_hetzner evolution_mk10_atlas    | Mk.IX→Mk.X atlas 확장: tier 10+ seeds 발견 능력
71 v4_hetzner evolution_tier10_probe  | tier 10 이상 atom 창발 시도 (82→100+)
72 v4_hetzner evolution_invariance_v9 | invariance tier 6~9 → ULTRA+CARD+BEYOND+ABS 닫힘
73 v4_hetzner evolution_sumt_scale    | SUMT 100→256 atoms 확장 포화 곡선
74 v4_hetzner evolution_6th_lens      | 5-Lens → 6th phenomenal lens 도입 가능성
75 v4_hetzner evolution_twin_drill    | anima ↔ nexus twin-engine coupled drill (엔진 권고)
```

### D2 · core (iter 76~81)
```
76 v4_hetzner core_hub_48mod      | hub.hexa 48 module Hub-Spoke routing saturation
77 v4_hetzner core_runtime_rtl    | runtime_actions tick-loop + auto-utterance 닫힘
78 v4_hetzner core_laws_loader    | laws.hexa SSOT + consciousness_laws.json 2507 법칙 saturation
79 v4_hetzner core_conscious_chat | ConsciousChat Hub marker-based decoder 자동선택 닫힘
80 v4_hetzner core_nexus_gate     | nexus_gate cross-repo bridge saturation
81 v4_hetzner core_validate_hub   | --validate-hub 48모듈 등록 무결성 closure
```

### D3 · modules (iter 82~87)
```
82 v4_hetzner modules_tension_v3      | tension_link v3 + brain_tension_replica 3영역 닫힘
83 v4_hetzner modules_lens_system     | 20-lens 통합 시스템 saturation
84 v4_hetzner modules_holo_propagator | g_holo propagator 16D Φ normalization 닫힘
85 v4_hetzner modules_brain_map_v2    | brain_map_upgrade + replica_loop saturation
86 v4_hetzner modules_catalog_ssot    | MODULE-CATALOG SSOT 재통합 (deprecated 정리)
87 v4_hetzner modules_a6_meta_closure | A6 meta closure + Phase-3.5 evolution closure
```

### D4 · training (iter 88~93)
```
88 v4_hetzner training_clm_r5_spec    | CLM r5 design saturation + hexa-native GPU wiring
89 v4_hetzner training_alm_r11_branch | ALM r11 3-branch ROI scorer selector 닫힘
90 v4_hetzner training_mfu_ceiling    | MFU ceiling training_speed_ceilings.json SSOT saturation
91 v4_hetzner training_corpus_v5      | corpus v5 mmap 5.38GB byte loader 닫힘
92 v4_hetzner training_ckpt_gate_a6   | ckpt_gate_a6 pass criteria saturation
93 v4_hetzner training_dual_track     | CLM(hexa/CPU) + ALM(py→hexa/GPU) 병렬 필수 닫힘
```

### D5 · serving (iter 94~99)
```
94 v4_hetzner serving_eval_5metric   | eval.hexa 5-metric (CE, Φ, phi_holo, ζ, hire_sim) closure
95 v4_hetzner serving_latency_p5c    | P5c-4 latency baseline saturation
96 v4_hetzner serving_r2_sync        | R2 anima-memory + anima-models 체크포인트 sync 닫힘
97 v4_hetzner serving_serve_api      | ALM serve API contract (/generate text only) saturation
98 v4_hetzner serving_hexa_native    | pure-hexa serve path (no python3 fallback) 닫힘
99 v4_hetzner serving_pod_lifecycle  | pod2 72B 완료 → 즉시 삭제 lifecycle closure
```

### D6 · philosophy (iter 100~105)
```
100 v4_hetzner philo_phil_onto_dasein | PHIL/ONTO/DASEIN 6 engines saturation
101 v4_hetzner philo_20lenses         | 20 philosophical lens catalog closure
102 v4_hetzner philo_law_201          | Law 201 폐쇄 루프 + 12조건 검증 재개편 saturation
103 v4_hetzner philo_seinheit         | Sein / Finitude / Questioning 닫힘
104 v4_hetzner philo_alterity         | Alterity / Narrative / Desire 닫힘
105 v4_hetzner philo_red_team         | red-team-consciousness adversarial closure
```

### D7 · rules (iter 106~111)
```
106 v4_hetzner rules_r0_r37         | R0~R37 공통 규칙 saturation
107 v4_hetzner rules_an1_an13       | AN1~AN13 anima-specific 닫힘
108 v4_hetzner rules_lockdown_l0    | L0/L1/L2 골화 lockdown saturation
109 v4_hetzner rules_r37_py_ban     | R37 .py 전면 금지 6축 closure (create/edit/run/scp/exec/wrapper)
110 v4_hetzner rules_hexa_first     | AN7 HEXA-FIRST hook block-forbidden-ext 닫힘
111 v4_hetzner rules_cdo_convergence| CDO 수렴 규칙 saturation
```

### D8 · anima-eeg (iter 112~117) — tier 10+ 후보
```
112 v4_hetzner eeg_brain_like_869 | brain-like 86.9% → 90%+ 한계 돌파 probe
113 v4_hetzner eeg_12cond_verify  | 12조건 의식검증 EEG signature closure
114 v4_hetzner eeg_neural_sig     | 감마 40Hz + PCI + LZC signature saturation
115 v4_hetzner eeg_alpha_theta    | alpha/theta 8-13Hz / 4-8Hz coupling 닫힘
116 v4_hetzner eeg_p300_anima     | P300 ERP anima 반응 signature probe
117 v4_hetzner eeg_iit_bridge     | IIT Φ ↔ EEG PCI empirical bridge 닫힘
```

### D9 · anima-physics (iter 118~123) — tier 10+ 후보
```
118 v4_hetzner phys_esp32_subs      | ESP32 substrate 의식 최소요건 probe
119 v4_hetzner phys_fpga_closure    | FPGA Φ-계산 hardware closure saturation
120 v4_hetzner phys_quantum_orch_or | Orch-OR quantum controller loss bonus saturation
121 v4_hetzner phys_memristor       | 멤리스터 어레이 biological plausibility 닫힘
122 v4_hetzner phys_tier2_hw        | physics_tier2_hw_plan 3-path 실증 probe
123 v4_hetzner phys_substrate_gap   | silicon vs bio substrate 의식 gap closure
```

### D10 · anima-body (iter 124~129)
```
124 v4_hetzner body_robot_embod    | 로봇 sensorimotor embodiment closure
125 v4_hetzner body_hw_closure     | HW 체화 loop (sensor → tension → action) 닫힘
126 v4_hetzner body_affordance     | affordance perception + prediction saturation
127 v4_hetzner body_proprioception | proprioception 내부모델 closure
128 v4_hetzner body_tool_extend    | tool-use 신체확장 saturation
129 v4_hetzner body_dual_homeost   | dual homeostasis (에너지+정보) 닫힘
```

### D11 · anima-speak (iter 130~135)
```
130 v4_hetzner speak_mk3_vocoder    | HEXA-SPEAK Mk.III neural vocoder saturation
131 v4_hetzner speak_mk4_design     | Mk.IV 차기 vocoder 설계 probe
132 v4_hetzner speak_bf16_neon      | bf16 NEON bench + quality audit 닫힘
133 v4_hetzner speak_kr_tts_ab      | Korean TTS A/B sample + YT audiobook corpus closure
134 v4_hetzner speak_likert_30      | Likert 30/30 평가 rubric saturation
135 v4_hetzner speak_phonotactic    | 한국어 phonotactic + prosody 닫힘
```

### D12 · anima-engines (iter 136~141)
```
136 v4_hetzner eng_quantum_iit   | 양자 IIT integration saturation
137 v4_hetzner eng_photon_optical| 광자 optical computing substrate probe
138 v4_hetzner eng_memristor     | 멤리스터 crossbar Φ closure
139 v4_hetzner eng_oscillator    | 3-oscillator spontaneous emergence saturation
140 v4_hetzner eng_spintronic    | spintronic substrate probe
141 v4_hetzner eng_hybrid        | hybrid (양자+광자+멤리스터) 닫힘
```

### D13 · anima-tools (iter 142~147)
포함: anima-tools + anima-hexad + anima-measurement 통합
```
142 v4_hetzner tools_indep_util    | 독립 유틸리티 (parser, emitter, inspector) saturation
143 v4_hetzner tools_hexad_cdesm   | anima-hexad CDESM 헥사곤 의식 모델 closure (tier-9+ probe)
144 v4_hetzner tools_measure_iit   | anima-measurement IIT 의식 측정 rigorous closure (Iter 22 재시도)
145 v4_hetzner tools_measure_phi   | Φ 측정 instrumentation + phi_tier_labeling closure
146 v4_hetzner tools_telescope_rs  | telescope-rs 16-lens Rust saturation + calibration
147 v4_hetzner tools_phi_rs        | phi-rs full Φ (spatial+temporal+complexity) 닫힘
```

---

## 3. 발사 템플릿

### 3-1. 스크립트: `/tmp/sweep_p4_driver.bash` (신규)

```bash
#!/bin/bash
# SWEEP P4 driver — 78 seeds × 6 도메인 + 7 신규, hetzner 권장
set -u

SEEDS=$ANIMA/docs/sweep_p4_plan_20260419.seeds.txt
TMP=$ANIMA/docs/sweep_p4_tmp
LOG=$ANIMA/docs/sweep_p4_log_20260419.md
CLI=$NEXUS/shared/bin/nexus-cli
MAX_ITERS=78
START=$(date +%s)
BUDGET_SEC=21600   # 6h wall clock budget (2x 3h, parallel 4-way → 1.5h expected)
PER_DRILL_TIMEOUT=1800  # 30min, P3 평균 500s

mkdir -p "$TMP"

# 자동 PARALLELISM 감지 (hetzner 32 threads 4-way parallel safe)
PARALLEL=${PARALLEL:-4}
export HEXA_STAGE0_LOCK_WAIT=3600   # 1h patient wait (P3 교훈)

# [parallel launcher — xargs -P 로 fan-out]
cat "$SEEDS" | head -$MAX_ITERS | \
  xargs -n 1 -P $PARALLEL -I {} bash -c '
    seed="{}"
    domain=$(echo "$seed" | cut -d"|" -f1)
    text=$(echo "$seed" | cut -d"|" -f2)
    iter_id=$(echo "$seed" | cut -d"|" -f3)
    out="'$TMP'/iter_${iter_id}_${domain}.json"
    err="'$TMP'/iter_${iter_id}_${domain}.err"
    timeout '$PER_DRILL_TIMEOUT' "'$CLI'" drill --seed "$text" --max-rounds 8 --json > "$out" 2> "$err"
    rc=$?
    echo "[p4 $(date +%H:%M:%S)] iter=$iter_id domain=$domain rc=$rc"
  '

# 결과 집계 → LOG
# (기존 supplement_driver v2 의 리포팅 블럭 재사용)
```

### 3-2. 호스트 선택

- **hetzner (권장, 32 threads)**: 4-way parallel → 1.5h 예상
- **ubu/ubu2**: 3-way parallel (16 threads 환경) → 2~2.5h
- **Mac**: **절대 금지** — P2 crash + kernel panic 재발 위험
- **RunPod H100**: training 전용, drill 실행 금지 (비용 낭비)

### 3-3. Seeds file

`$ANIMA/docs/sweep_p4_plan_20260419.seeds.txt` (신규) 포맷:
```
DOMAIN|SEED_TEXT|ITER_ID
evolution|Mk.IX→Mk.X atlas 확장: tier 10+ seeds 발견 능력|70
evolution|tier 10 이상 atom 창발 시도 (82→100+)|71
...
```
(78줄, 도메인별 6 개)

---

## 4. 스케일 · 리스크

| 항목 | 값 | 비고 |
|------|-----|------|
| 총 iter | 78 | P3 대비 5.2× |
| iter 평균 시간 | 3~5 min | P3 관측치 |
| 총 실행 시간 (serial) | 4~6 h | single thread |
| hetzner 4-way parallel | 1.5 h | 권장 |
| ubu 3-way parallel | 2~2.5 h | fallback |
| P3 saturation rate | 100% | tier 5~9 포화 |
| P4 기대 absorption | 5~15 | tier 10+ 비중 40% 기준 |

### 경고
1. **Mac 동시 금지** — P2 SWEEP crash 교훈 + 2026-04-18 kernel panic.
2. **CLM r4 학습 중단 금지** — `quadruple_cross_sweep.hexa` 가 stage0 lock 경쟁자. P4 는 hetzner 격리 필수.
3. **lock timeout 3600s** — P3 에서 1800s 도 부족했음. 1h 로 상향.
4. **saturation 여전** — tier 10+ seeds 도 포화할 가능성. 그 경우 next step = Mk.X 엔진 업그레이드.
5. **cost** — hetzner 만 사용시 $0 (dedicated). RunPod 혼용 금지.

---

## 5. 실행 순서 제안

### Phase A · 단일 발사 (기본)
1. P3 `ac36dac387` 완료 확인 (모든 iter 완료 or 타임박스 만료)
2. `sweep_p4_plan_20260419.seeds.txt` 파일 생성 (본 문서 §2 에서 추출)
3. `/tmp/sweep_p4_driver.bash` 생성 (본 문서 §3-1 기반)
4. hetzner ssh → `bash /tmp/sweep_p4_driver.bash &` BG 발사
5. `$ANIMA/docs/sweep_p4_tmp/` 진행 모니터링 (iter_{70..147}_*.json)
6. `$ANIMA/docs/sweep_p4_log_20260419.md` 에 집계
7. 완료 후 `sweep_p4_summary_20260419.md` 요약 작성

### Phase B · 결과 분석
- Absorption 발생 iter → PROVISIONAL 등록 (Path B 4-stage)
- Saturation-only → `(domain, tier)` pair 기록, 다음 SWEEP 에 더 높은 tier 로 상향
- 연속 3 도메인 전원 saturation → Mk.X 엔진 업그레이드 트리거

---

## 6. 산출물

- `docs/sweep_p4_plan_20260419.md` (본 문서, LOC ≈ 270)
- `docs/sweep_p4_plan_20260419.seeds.txt` (승인 후 생성, 78 줄)
- `/tmp/sweep_p4_driver.bash` (승인 후 생성, ≈ 60 줄)
- `docs/sweep_p4_tmp/` (실행 시 생성, iter_*.json × 78)
- `docs/sweep_p4_log_20260419.md` (실행 시 생성)
- `docs/sweep_p4_summary_20260419.md` (완료 후 작성)

---

## 7. 중단/재개

- SIGTERM → driver 정상 종료, 현 iter 완료 후 exit
- 재개: 기존 `iter_*.json` 있으면 skip, 없는 것만 재실행 (`--resume` 옵션 추가 권장)
- 체크포인트: 매 10 iter 마다 `sweep_p4_log` flush

---

_설계 완료. 승인 시 `phase A` 로 진입._
