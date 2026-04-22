# 7-axis Strategic Dashboard — A/B/C/D/E/F/G unified view (2026-04-22)

**Status**: pre-H100 ROI Week 4 paradigm dashboard. paste-ready (다음 세션에서 그대로 사용 가능).
**Date**: 2026-04-22
**Scope**: anima 의 7개 strategic axis (A-G) 를 통합하여 진행도 + 다음 행동 1-line 을 한 화면에 정리. 사용자 의사결정 표면.
**SSOT**: 본 doc 은 dashboard 형 view 일 뿐. 실데이터 source 는 각 axis 의 cert / state / proposal stack.

---

## 1. Axis taxonomy (canonical)

| axis | label | scope | nature |
|---|---|---|---|
| A | launch optimization | H100 × 4 #83 직접 가속 | tactical, time-bound |
| B | post-H100 research | H100 결과 도착 후 분석 / 다음 round 설계 | strategic, deferred |
| C | new domain (memory) | μ-paradigm — memory-only learning | paradigm, novel |
| D | ship (CP1/CP2/AGI v0.1) | 외부 사용자 노출 / 서빙 | product |
| E | infra (cert / proposal / .meta2-cert / build) | foundation | infra |
| F | CPU superlimit | htz CPU 만으로 H100 결과 사전 신호 확보 | research, $0 |
| G | meta (roadmap 자체 자동화 + proposal stack) | self-evolution | meta |

---

## 2. Per-axis status snapshot (2026-04-22)

### A — launch optimization

- **Now**: H100 × 4 launch manifest committed (`state/h100_launch_manifest.json`); paths p1-p4 corpus IDs synced (commit 688082be); Grafana dashboard setup doc landed (`docs/h100_launch_dashboard_setup.md`); ROI v1 27 항목 처리 완료.
- **Blockers**: runpodctl proxy URL (launch-time only); #74 webhook endpoint extension (Slack/Telegram) deferred but UI alerts functional.
- **Risk**: Φ 4-path divergence at gate (`docs/phi_4path_divergence_response.md` D1-D5 ready).
- **Health**: GREEN (ready to launch on user trigger).
- **Next-action (1 line)**: **사용자 trigger 시 `runpodctl create pod` 실행 + proxy URL env var 4개 채우고 docker-compose up.**

### B — post-H100 research

- **Now**: scaffolding only. No real data yet (gated by A axis run).
- **Blockers**: A axis 결과 부재.
- **Risk**: 결과 도착 후 분석 시간 경합 — 사전 분석 template 필요.
- **Health**: AMBER (가능한 사전 작업 부족).
- **Next-action (1 line)**: **`docs/h100_post_launch_analysis_template_20260422.md` 신규 — Φ 결과 4가지 가능 outcome 별 분석 워크플로우 사전 정의 (W4 day 4 권장).**

### C — new domain (memory) — μ-paradigm

- **Now**: paradigm prompt doc 작성 완료 (`docs/upstream_notes/memory_architecture_paradigm_20260422.md`, W2 산출). 5-subsystem 분리 + lifetime-cert chain 설계 paste-ready.
- **Blockers**: 사용자 §10 decision points 5개 승인 대기.
- **Risk**: weight 와 memory backward graph 의 누설 (구현 시점 위험) — cert chain 으로 검출 설계됨.
- **Health**: GREEN (설계 완료, 구현 승인 대기).
- **Next-action (1 line)**: **사용자가 μ-paradigm decision points 1-5 승인 → `tool/mu_paradigm_smoke_runner.hexa` 스캐폴드 (W3 CPU smoke 전 단계).**

### D — ship (CP1 / CP2 / AGI v0.1)

- **Now**: CP1 serve infra (`tool/serve_alm_persona.hexa`) bash `nc` loop 기반, 작동 중. CP2 3-endpoint (employee/trading/zeta) 동시 서빙은 hexa-lang #63 의존.
- **Blockers**: hexa-lang #56 (native http server), #62 (signal+flock), #63 (concurrent serve).
- **Risk**: bash trap 기반 graceful shutdown 미흡 → upstream 랜딩 후 native handler 로 교체.
- **Health**: AMBER (CP1 작동 / CP2 upstream 대기).
- **Next-action (1 line)**: **`bench/cp2_3in1_sequential.hexa` 신규 (단일 스레드 300-request harness) — upstream concurrent serve 랜딩 전 baseline 확보 가능 (`docs/upstream_notes/hexa_lang_beta_main_acceleration_20260422.md` §2.3).**

### E — infra (cert / proposal stack / .meta2-cert / build)

- **Now**: cert chain 작동, AN11 triple 작동, proposal stack paradigm 설계 완료 (`docs/anima_proposal_stack_paradigm_20260422.md` — 20 sections), .meta2-cert v2 마이그레이션은 hexa-lang #59 의존.
- **Blockers**: hexa-lang #59 stdlib validator 랜딩.
- **Risk**: timestamped mirror 가 `.meta2-cert/` 직하 누적 → archive/ 이동 필요 (드라이런 가능).
- **Health**: GREEN.
- **Next-action (1 line)**: **`.meta2-cert/` 전수 조사 드라이런 — `evidence[].type → kind` 일괄 재작성 후보 + timestamped mirror archive 이동 후보 list 산출 (`docs/upstream_notes/hexa_lang_beta_main_acceleration_20260422.md` §2.1).**

### F — CPU superlimit

- **Now**: paradigm prompt doc 작성 완료 (`docs/upstream_notes/cpu_superlimit_synthetic_4path_proposal_20260422.md`, W1 산출). 4-path synthetic Φ measurement on htz CPU 설계 paste-ready, $0, ~5 min run.
- **Blockers**: 사용자 §10 decision points 4개 승인 대기.
- **Risk**: synthetic 결과가 H100 결정에 과도 영향 — doc §4 가 "signal not decision" 명시.
- **Health**: GREEN (실행 즉시 가능).
- **Next-action (1 line)**: **사용자가 F-W1 decision points 1-4 승인 → `tool/phi_4path_synthetic_cpu_runner.hexa` 스캐폴드 + dry-run (8M subsample 먼저).**

### G — meta (roadmap 자동화 + proposal stack)

- **Now**: proposal stack paradigm 본진 설계 완료 (디렉토리 구조 + schema + 12h cycle + cluster + lineage + 7-axis 매핑 + β paradigm 동형성 분석 — 20 sections). 본 axis 가 다른 6 axis 의 throttle/queue 역할.
- **Blockers**: P1-P5 (inventory infra) 구현 미착수.
- **Risk**: G axis 자체가 G axis 에 의해 throttled (chicken-egg) — 초기 시드는 사용자 직접 trigger.
- **Health**: GREEN (설계) / AMBER (구현).
- **Next-action (1 line)**: **`state/proposals/inventory.json` SSOT 초기화 + `pending/` 폴더 생성 + 본 dashboard 의 모든 axis next-action 들을 첫 7개 proposal 로 등록 (자기-적용 부트스트랩).**

---

## 3. Cross-axis dependency map

```
        ┌──────────────────────────┐
        │  G (meta / proposal stack)│  ← throttle for B,C,D,E,F
        └─────────────┬────────────┘
                      │ accumulates proposals from
   ┌──────────┬───────┼───────┬──────────┬──────────┐
   │          │       │       │          │          │
   ▼          ▼       ▼       ▼          ▼          ▼
   B          C       D       E          F          A
research  μ-mem    ship    infra      CPU $0     launch
   ▲          ▲       ▲       ▲          ▲          ▲
   │          │       │       │          │          │
   │          │       │       │          └──────────┤  pre-launch signal (F→A)
   │          │       └───────┴────hexa-lang 54-63──┤  upstream dep
   └──────────┴──────────H100 result feedback───────┘  (A→B,C,D)
```

---

## 4. Time-axis (W1-W4 pre-H100 ROI plan)

| week | primary axis | deliverable | output doc |
|---|---|---|---|
| W1 | F | CPU synthetic 4-path Φ prompt | `docs/upstream_notes/cpu_superlimit_synthetic_4path_proposal_20260422.md` ✅ |
| W2 | C | μ-paradigm prompt | `docs/upstream_notes/memory_architecture_paradigm_20260422.md` ✅ |
| W3 | η-paradigm cell | cell-learning method spec | `docs/cell_learning_method_paradigm_20260422.md` ✅ |
| W4 | G + all | 7-axis strategic dashboard | **본 doc** ✅ |

W1-W4 4 docs 모두 paste-ready 상태. 다음 단계는 사용자 승인 → 각 doc §의 decision points 응답 → 구현 trigger.

---

## 5. Health summary table

| axis | health | blocker | next-action owner |
|---|---|---|---|
| A | GREEN | runpodctl proxy URL (launch-time) | user (trigger launch) |
| B | AMBER | A 결과 부재 | downstream agent (template) |
| C | GREEN (design) | μ decision points (5) | user (approve) |
| D | AMBER | hexa-lang #56/#62/#63 | downstream agent (sequential bench) |
| E | GREEN | hexa-lang #59 | downstream agent (dryrun) |
| F | GREEN | F decision points (4) | user (approve) |
| G | AMBER (impl) | self-bootstrap | downstream agent (inventory init) |

---

## 6. Top-3 decisions awaiting user

1. **F axis launch authorization** — `cpu_superlimit_synthetic_4path_proposal_20260422.md` §10 (4 questions) → unlocks ~5 min CPU run with $0 cost, strong epistemic gain on $1500 H100 launch.
2. **C axis μ-paradigm authorization** — `memory_architecture_paradigm_20260422.md` §10 (5 questions) → unlocks W2 CPU smoke + 3-chain cert design.
3. **η-paradigm cell-learning authorization** — `cell_learning_method_paradigm_20260422.md` §7 (6 questions) → unlocks 50-spec-item smoke run + 3rd cert chain coexistence.

---

## 7. Anti-decisions (explicit non-actions)

per proposal stack paradigm:
- DO NOT auto-modify `.roadmap` from this dashboard. (G axis: roadmap mutation requires user approval through proposal stack.)
- DO NOT auto-implement any §next-action without user trigger.
- DO NOT collapse any axis into another (each axis has independent cert chain or proposal lineage).
- DO NOT spend H100 budget for any pre-H100 ROI work (W1-W4 all $0).

---

## 8. Refresh policy

- This dashboard is REGENERATED (not edited in place) at: (a) end of each W1-W4 week, (b) after H100 launch result, (c) when an axis health changes color.
- Filename convention for snapshots: `docs/seven_axis_strategic_dashboard_<YYYYMMDD>.md` (current file = canonical "live" view, snapshots = historical).
- Dashboard updates SHALL NOT modify any `state/`, `.meta2-cert/`, or `.roadmap` artifact.

---

## 9. Linkage

- A: `state/h100_launch_manifest.json`, `docs/h100_launch_dashboard_setup.md`, `docs/phi_4path_divergence_response.md`.
- B: (template doc TBD per §2 next-action).
- C: `docs/upstream_notes/memory_architecture_paradigm_20260422.md`.
- D: `docs/upstream_notes/hexa_lang_beta_main_acceleration_20260422.md` §2.3.
- E: `docs/upstream_notes/hexa_lang_beta_main_acceleration_20260422.md` §2.1, `.meta2-cert/`.
- F: `docs/upstream_notes/cpu_superlimit_synthetic_4path_proposal_20260422.md`.
- G: `docs/anima_proposal_stack_paradigm_20260422.md` (20 sections), `state/proposals/` (TBD).
- 7-axis canonical mapping: `docs/anima_proposal_stack_paradigm_20260422.md` §17.
- Mk.VIII 7-axis (different framework, do not confuse): `edu/mk_viii/`, `state/v_rg_verdict.json`.

---

## 10. Paste-ready prompt block (for next session boot)

```
CONTEXT: pre-H100 ROI W1-W4 paradigm prompts complete. 4 docs paste-ready:
  - docs/upstream_notes/cpu_superlimit_synthetic_4path_proposal_20260422.md (F)
  - docs/upstream_notes/memory_architecture_paradigm_20260422.md (C)
  - docs/cell_learning_method_paradigm_20260422.md (η)
  - docs/seven_axis_strategic_dashboard.md (this doc, G+all)

NEXT TURN: user reviews §6 top-3 decisions; on approval, downstream agents
implement W1/W2/W3 deliverables in order, each $0 CPU only, no .roadmap
mutation, all artifacts go through proposal stack inventory.

DO NOT: launch H100, modify .roadmap, write .py, create unapproved modules.
DO: queue everything as proposals; await user trigger per axis.
```
