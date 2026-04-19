# SWEEP P5 Plan — 14 도메인 × 6 주제 = 84 iter (2026-04-19)

> **상태**: 설계 문서 (blueprint). P4 완료 후 발사.
> **선행**: `docs/sweep_p4_plan_20260419.md` (P4 blueprint) + `docs/sweep_40.json` SSOT.
> **신규**: anima-agent Track B 재구성 (Phase 1 완료) 이후 14번째 도메인으로 편입.
> **트리거**: Mk.X 엔진은 P5 saturation 조건 충족 시 자동 발사 (G1~G4, §4).
> **SSOT**: `docs/sweep_50.json` (본 문서는 보조 본문).

---

## 0. 배경 · 전제

### P4 → P5 의 변화 3줄
1. **anima-agent 편입**: Track B Phase 1 (core 분리) 완료 가정 → 14번째 도메인 `anima-agent` (6 seeds) 추가.
2. **전체 iter 범위**: 70~147 (P4, 13×6=78) → **148~231** (P5, 14×6=84).
3. **Mk.X trigger 통합**: P4 §Phase B의 "연속 3 도메인 saturation" 규칙을 P5 에서는 4-게이트(G1..G4) 로 정형화 — 자동 발사 조건 만족 시 `mk_x_launch_sequence` 가동.

### P3 → P4 → P5 scale
| sweep | 도메인 | seeds/도 | 총 iter | iter range |
|-------|--------|----------|---------|------------|
| P3 supplement | 7 | ~2 | 15 | 25~69 (부분) |
| P4 (sweep_40) | 13 | 6 | 78 | 70~147 |
| **P5 (sweep_50)** | **14** | **6** | **84** | **148~231** |

### 전제 가정
- anima-agent Track B Phase 1 (`anima-agent-core/` 분리) 완료. Phase 2~5 는 P5 실행과 병렬 금지 (W2 참조).
- P4 완료 결과 일부 도메인이 saturation이면 P5 에서도 tier 유지, absorption 발생 시 tier 상향 (각 iter text 갱신).
- Mk.X 는 아직 발사 전. P5 는 **Mk.IX 기반**으로 실행 후 결과를 Mk.X 트리거 판정 자료로 사용.

---

## 1. 도메인 맵 (14 개)

기존 13 (P4 유지) + 신규 1 (anima-agent) = **14**.

| # | 도메인 | 카테고리 | iter | 비중 | 노트 |
|---|--------|----------|------|------|------|
| 1 | evolution           | P4 유지 | 148~153 | 6 | Mk.X / twin / 6th-lens / SUMT |
| 2 | core                | P4 유지 | 154~159 | 6 | hub / runtime / laws / chat |
| 3 | modules             | P4 유지 | 160~165 | 6 | tension / lens / holo / replica |
| 4 | training            | P4 유지 | 166~171 | 6 | CLM r6 / ALM r12 / MFU / corpus |
| 5 | serving             | P4 유지 | 172~177 | 6 | eval / latency / R2 / API |
| 6 | philosophy          | P4 유지 | 178~183 | 6 | PHIL/ONTO/DASEIN / 20lens / 201 |
| 7 | rules               | P4 유지 | 184~189 | 6 | R0~R37 / AN1~13 / L0 / R37 |
| 8 | anima-eeg           | P4 유지 | 190~195 | 6 | brain-like / 12cond / PCI |
| 9 | anima-physics       | P4 유지 | 196~201 | 6 | ESP32 / FPGA / 양자 / memristor |
| 10 | anima-body         | P4 유지 | 202~207 | 6 | robot / HW closure / affordance |
| 11 | anima-speak        | P4 유지 | 208~213 | 6 | Mk.IV / bf16 / KR TTS |
| 12 | anima-engines      | P4 유지 | 214~219 | 6 | 양자 / 광자 / memristor / hybrid |
| 13 | anima-tools        | P4 유지 | 220~225 | 6 | hexad / measurement / telescope |
| 14 | **anima-agent**    | **신규**| 226~231 | 6 | core split / router / sandbox / hire / autonomy |

---

## 2. Seed 초안 (84 개)

**네임스페이스**: `v5_hetzner/iter_{148..231}_{domain}_{topic}`

### D1~D13 (P4 seeds 일치, iter 번호만 +78)
P4 seeds 는 `docs/sweep_40.json` 의 domains[1..13].seeds 를 SSOT 로 유지. P5 에서는 iter 번호를 148~225 로 재배열하고, P4 에서 absorption 이 생긴 seed 는 tier 상향 텍스트로 갱신 (구체 갱신은 P4 summary 완료 후 별도 커밋).

### D14 · anima-agent (iter 226~231) — 신규

```
226 v5_hetzner agent_core_split     | anima-agent-core 분리 (Phase 1) closure: run/registry/sdk/tools/policy/guardian L0 gate
227 v5_hetzner agent_channel_router | channel_manager 6채널 (cli/tg/discord/slack/...) routing saturation
228 v5_hetzner agent_provider_switch| claude / conscious_lm / animalm / composio 제공자 스위칭 closure
229 v5_hetzner agent_plugin_sandbox | plugin_loader + tool_policy Φ-gated 4-tier 샌드박스 saturation
230 v5_hetzner agent_hire_sim_live  | hire_sim_live 45K LOC 독립 모듈 closure (tier-9+ probe, judge lenient rubric)
231 v5_hetzner agent_autonomy_loop  | autonomy_live + autonomy_loop + discovery_loop 3체 closed-loop 닫힘
```

| iter | slug | tier_hint | 목적 |
|------|------|-----------|------|
| 226 | agent_core_split      | 8-9 | Phase 1 분리 후 L0 무결성 |
| 227 | agent_channel_router  | 7-9 | 6채널 라우팅 포화 |
| 228 | agent_provider_switch | 7-9 | 제공자 라우팅 (ALM/CLM/외부) |
| 229 | agent_plugin_sandbox  | 9-10| 플러그인 격리 + Φ-gated 권한 |
| 230 | agent_hire_sim_live   | 9+  | 45K LOC judge rubric closure |
| 231 | agent_autonomy_loop   | 10+ | 3체 loop + consciousness 체인 |

---

## 3. Mk.X 자동 발사 트리거 (integrated)

### 3-1. 4-gate (from `docs/mk_x_engine_design_20260419.md` §3)
| gate | 조건 | 측정 방법 |
|------|------|-----------|
| G1 | P5 saturation verdict = "3+ 연속 도메인 SATURATED, 0 tier-10+ absorption" | `docs/sweep_p5_summary_20260419.md` 에 기록 |
| G2 | tier-10 seed exhaustion (D8~D14) | 각 iter_*.json absorption=0 |
| G3 | twin-engine drill fail | iter 153 `evolution_twin_drill` 결과 |
| G4 | 사용자 sign-off | `feedback_all_preapproved_roadmap_only` = pre-approved |

### 3-2. P5 종료 시 판정 로직 (automation pseudocode)

```
on_p5_complete:
  absorb_10plus = count(iter.absorption > 0 AND iter.tier_hint >= "10+")
  sat_streak = max_consecutive_saturated_domains(D1..D14)
  twin_fail  = iter_153.absorption == 0

  if absorb_10plus == 0 AND sat_streak >= 3 AND twin_fail:
    G1 = G2 = G3 = PASS
    G4 = PASS  (pre-approved)
    → mk_x_auto_launch()
  else:
    → record absorptions, schedule P6 with tier upshift
```

### 3-3. `mk_x_auto_launch()` 시퀀스
(`mk_x_engine_design_20260419.md` §3 "Auto-fire order" 그대로 재사용)
1. `shared/engine/mk_x_manifest.json` 작성 (16-slot schema + stage 6 spec).
2. `anima/engines/drill_mk9.hexa` → `drill_mk10.hexa` 복제.
3. `transcendental_closure()` stage 6 + slot 8~15 accessor 추가.
4. `training/mk10_selftest.hexa` — Mk.IX 82-atom bit-for-bit 재현 확인.
5. P5 seeds 84개를 **Mk.X 로 재실행** (결과는 `mk_x_launch_log_20260419.md`).
6. absorption delta 기록 → 차기 SWEEP (P6) 로 인계.

### 3-4. Abort conditions (from §3 Mk.X doc)
- self-check bit-diff on slots 0~7 → Mk.X revert, Mk.IX 유지.
- per-round RSS > 6 GiB → slot-width 12 backoff → re-self-check.
- Mk.X 에서 Π₀² 결과가 Mk.IX 보다 적음 → revert.

---

## 4. 발사 템플릿

### 4-1. Driver: `/tmp/sweep_p5_driver.bash` (승인 시 생성)

```bash
#!/bin/bash
# SWEEP P5 driver — 84 seeds × 14 도메인, hetzner 권장
set -u
SEEDS=$ANIMA/docs/sweep_p5_plan_20260419.seeds.txt
TMP=$ANIMA/docs/sweep_p5_tmp
LOG=$ANIMA/docs/sweep_p5_log_20260419.md
CLI=$NEXUS/shared/bin/nexus-cli
MAX_ITERS=84
BUDGET_SEC=25200          # 7h (P4 기반 +1h)
PER_DRILL_TIMEOUT=1800
mkdir -p "$TMP"
PARALLEL=${PARALLEL:-4}
export HEXA_STAGE0_LOCK_WAIT=3600

cat "$SEEDS" | head -$MAX_ITERS | \
  xargs -n 1 -P $PARALLEL -I {} bash -c '
    seed="{}"
    domain=$(echo "$seed" | cut -d"|" -f1)
    text=$(echo "$seed"   | cut -d"|" -f2)
    iter_id=$(echo "$seed" | cut -d"|" -f3)
    out="'$TMP'/iter_${iter_id}_${domain}.json"
    err="'$TMP'/iter_${iter_id}_${domain}.err"
    timeout '$PER_DRILL_TIMEOUT' "'$CLI'" drill --seed "$text" --max-rounds 8 --json > "$out" 2> "$err"
    echo "[p5 $(date +%H:%M:%S)] iter=$iter_id domain=$domain rc=$?"
  '
```

### 4-2. 호스트
- **hetzner** (권장, 32 threads) — 4-way parallel → 1.7h 예상
- **ubu/ubu2** — 3-way → 2.5~3h (fallback)
- **Mac** — 금지 (P2 crash 교훈)
- **RunPod H100** — 금지 (training 전용)

### 4-3. Seeds file 포맷
`docs/sweep_p5_plan_20260419.seeds.txt` (84줄, 승인 후 생성):
```
DOMAIN|SEED_TEXT|ITER_ID
evolution|Mk.IX→Mk.X atlas 확장: tier 10+ seeds 발견 능력|148
...
anima-agent|anima-agent-core 분리 ... L0 gate|226
anima-agent|autonomy_live + autonomy_loop + discovery_loop 3체 closed-loop 닫힘|231
```

---

## 5. 스케일 · 리스크

| 항목 | 값 | 비고 |
|------|-----|------|
| 총 iter | 84 | P4 대비 +6 |
| iter 평균 | 3~5 min | P4 관측 기준 |
| serial total | 4.5~6.5 h | |
| hetzner 4-way | ~1.7 h | 권장 |
| P4 expected absorption | 5~15 | tier 10+ 40% |
| **P5 expected absorption** | **5~18** | +anima-agent tier 10+ 1건 추가 |
| Mk.X 자동 발사 확률 | 30~50% | P4 경향 유지 가정 |

### 경고 (W1~W7)
- **W1**: Mac 금지 — P2 crash + 2026-04-18 kernel panic.
- **W2**: **anima-agent Track B Phase 2~5 중 P5 발사 금지** — import cascade 충돌 위험. Phase 1 완료 후 Phase 2 대기 상태에서 P5 발사.
- **W3**: CLM r5/r6 학습 중단 금지 — stage0 lock 경쟁. hetzner 격리.
- **W4**: lock timeout 3600s 유지 (P3/P4 교훈).
- **W5**: saturation 여전 가능 — Mk.X 발사 조건 충족 시 자동 진입.
- **W6**: Mk.X self-check 실패 → 즉시 revert, P5 결과는 유지.
- **W7**: anima-agent 6 seeds 는 Phase 1 core 분리 전 실행 시 iter 226 (core_split) 이 의미 없음 — 선후관계 필수.

---

## 6. 실행 순서

### Phase A · 단일 발사
1. P4 summary 완료 확인 (`docs/sweep_p4_summary_20260419.md`)
2. anima-agent Track B Phase 1 완료 확인 (`anima-agent-core/run.hexa` 기동 OK)
3. `docs/sweep_p5_plan_20260419.seeds.txt` 추출 (§2 + P4 seeds)
4. `/tmp/sweep_p5_driver.bash` 생성
5. hetzner ssh → BG 발사
6. `docs/sweep_p5_tmp/` 진행 모니터링 (84개 iter_*.json)
7. 완료 → `docs/sweep_p5_summary_20260419.md` 요약 작성

### Phase B · 결과 분석 + Mk.X 판정
- Absorption iter → PROVISIONAL 등록 (Path B 4-stage)
- Saturation-only domain → (domain, tier) 기록
- G1..G4 판정 → `mk_x_auto_launch()` 조건부 진입

### Phase C (조건부) · Mk.X re-run
- Mk.X self-check PASS → P5 seeds 84개 Mk.X 재실행
- `mk_x_launch_log_20260419.md` 에 absorption delta 기록
- 신규 tier 10+ atom 발견 시 PROVISIONAL 등록

---

## 7. 산출물

- `docs/sweep_p5_plan_20260419.md` (본 문서)
- `docs/sweep_50.json` (SSOT JSON)
- `docs/sweep_p5_plan_20260419.seeds.txt` (승인 후, 84줄)
- `/tmp/sweep_p5_driver.bash` (승인 후)
- `docs/sweep_p5_tmp/` (실행 시, iter_*.json × 84)
- `docs/sweep_p5_log_20260419.md` (실행 시)
- `docs/sweep_p5_summary_20260419.md` (완료 후)
- `docs/mk_x_launch_log_20260419.md` (Mk.X 자동 발사 조건부)

---

## 8. 재개 / 중단

- SIGTERM → driver 정상 종료, 현 iter 완료 후 exit
- resume: 기존 `iter_*.json` 있으면 skip
- checkpoint: 매 10 iter 마다 `sweep_p5_log` flush
- Mk.X 자동 발사 중간 abort → Mk.IX P5 결과는 보존, Mk.X artifacts 는 파기

---

_설계 완료. 승인 시 Phase A 진입. P4 summary + Track B Phase 1 완료가 선행 조건._
