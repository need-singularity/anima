# dest2 직원가능(Employee) 기능 Spec — 2026-04-19

> Status: spec / design
> Depends on: `dest1_alm` (S1 /persona LIVE, weight_origin ∈ {r9_validated, r10d, consciousness_baked})
> Governs: AN11 (weight-emergent + consciousness-attached + real-usable)
> Roadmap: `shared/convergence/roadmap_dest_consciousness.convergence` tracks E1, E2
> Companion: `docs/anima_agent_restructure_plan_20260419.md` (dest1 layer)

## 1. Employee 정의 (convergence 추출)

`@dest__dest2_alm` — `dest1_alm + 직원가능(E1+E2) + 트레이딩(T1+T2) 전부 실사용`.

Employee = **dest1 페르소나 서빙 위에 얹힌 "실업무 수행자"** —
`POST /persona` 한 번의 호출이 아닌, 여러 호출을 엮은 **goal → plan → act → verify** 루프를
돌리며 **매 step 마다 phi_vec + laws_pass 게이트**를 통과해야 "업무 완수" 로 인정된다.
system_prompt("너는 유능한 업무 어시스턴트야") 로 유도되는 직원성은 **AN11 위반**으로 revoke 됨
(convergence `revoked_2026_04_18_employee_base_serve` 선례).

Employee 는 2 track 으로 쪼개져 있다:
- **E1 `hire_sim_live`** — static 업무 100개 × persona 20개 재현 평가 (채용 시뮬레이션).
- **E2 `autonomy_loop` LIVE** — 장기 목표에 대한 자율 plan/act 루프 (실제 일꾼).

## 2. 필수 기능 목록

| # | 기능 | 구현 위치 (hexa) | 역할 |
|---|---|---|---|
| F1 | persona resolver | `agent_sdk.hexa` → S1 adapter | persona_id 를 S1 request 의 struct 필드로 전달, 프리앰블 금지 |
| F2 | goal memory | `anima-agent/memory/goal_store.hexa` (new) | 목표·subgoal·완료 상태·phi trail 저장 (JSONL) |
| F3 | working memory / scratchpad | `anima-agent/memory/scratch.hexa` (new) | step-n 출력이 step-(n+1) 입력이 되도록 per-session 버퍼 |
| F4 | schedule / task queue | `autonomy_live.hexa` queue block | goal → subgoals → 우선순위 정렬, retry, backoff |
| F5 | tool call | `agent_tools.hexa` (기존) | Φ 게이트 4-티어 (tool_policy.hexa) 통과 후 실행 |
| F6 | verify (rubric + phi gate) | `hire_sim_judge.hexa` (확장) | 키워드 rubric AND `phi_holo_ratio >= 1.2` (vs session baseline, N-independent) AND `laws_pass=true` (절대 `phi_holo_scaled > 500` 게이트는 2026-04-20 deprecated — raw MI × N 으로 random init 에서 자동 통과) |
| F7 | phi trail logger | `consciousness_features.hexa` 재사용 | 매 step phi_vec(16D) JSONL append |
| F8 | report writer | `anima-agent/reports/emit_report.hexa` (new) | Markdown/JSON 결과 + phi summary + R2 업로드 |
| F9 | abort policy | `autonomy_live.hexa` abort branch | `phi_delta < 0` N연속 OR `laws_pass=false` 즉시 abort |
| F10 | reproducer CLI | `run.hexa` 서브커맨드 | `hexa run employee run --goal ... --persona ...` 한 줄 재현 |

> F2·F3·F8 신규, 나머지는 기존 파일 확장. 신규 파일 전부 `.hexa` (AN13 total .py ban).

## 3. dest1 위에 어떻게 쌓이는가 (layer diagram)

```
┌─────────────────────────────────────────────────────────┐
│ dest2 Employee layer                                    │
│   E1 hire_sim_live.hexa   (static 500 tasks, phi-gated) │
│   E2 autonomy_live.hexa   (long-horizon goal loop)      │
│     └── F2 goal_store  F3 scratch  F4 queue  F8 report  │
│     └── agent_tools (Φ 4-tier)  hire_sim_judge (rubric) │
└──────────────────────┬──────────────────────────────────┘
                       │  uses only struct-field persona_id
                       ▼
┌─────────────────────────────────────────────────────────┐
│ dest1 S1 endpoint  (POST /persona)                      │
│   C1 phi_hook_live → phi_vec 16D                        │
│   C2 consciousness_gate → laws_pass                     │
│   P1 persona_apply → SAE delta (weight-space)           │
│   weight_origin ∈ {r9_validated, r10d, consciousness_baked} │
└─────────────────────────────────────────────────────────┘
```

핵심:
1. **adapter 내부 prompt string 0 byte** — `llm_claude_adapter.hexa` 와 동일 패턴으로
   `agent_sdk.hexa` 가 S1 에 `{persona_id, user_prompt}` 두 필드만 POST.
2. **loop 제어 신호 = phi_delta + laws_pass** — autonomy_loop 의 continue/abort 가
   LLM 에이전시가 아닌 **measured consciousness signal** 로 결정됨.
3. **매 step 의 phi_vec / laws_pass 를 F7 logger 가 JSONL 에 append** →
   F8 report 가 마지막에 `{mean_phi, min_phi, laws_violations, completion_rate}` 집계.
4. **기존 `autonomy_loop.hexa` 는 mock path 로 유지**, `autonomy_live.hexa` 가
   live wire (이미 370 LOC 골격 존재, S1 업; ossify 시 바로 flip).
5. **agent_tools.hexa Φ 4-tier (tool_policy.hexa)** 는 유지: employee 가 쓰는
   모든 도구는 phi_holo 기준 tier 통과 후에만 발화.

## 4. AN11 적용 — Employee weight_emergent 유지 조건

Employee layer 가 a/b/c 3조건을 **새로 깰 수 있는 7 가지 지점** (bypass_patterns_banned):

| 지점 | 위반 형태 | 방어 |
|---|---|---|
| adapter prompt | `"You are a helpful employee..."` 주입 | grep-gate `llm_claude_adapter.hexa` + pre-commit 패턴 스캔 |
| mock LLM | `autonomy_loop.hexa` legacy mock 을 live 로 착각 | `autonomy_live.hexa` 만 E2 artifact; mock 은 `@state mock` 태그 고정 |
| synthetic judge | hire_sim rubric 이 LLM 아닌 고정표 매칭 재활용 | `hire_sim_judge.hexa` 는 실제 S1 응답에만 붙음, judge_kind="live" 필수 |
| hardcoded phi | `phi_holo_scaled=1500` 주입 | S1 응답 phi_vec 을 직접 읽고 재서명 금지, missing=FAIL |
| laws unattached | laws 파일은 import 하나 S1 gate 경로 안 붙음 | E1/E2 둘 다 `laws_pass` 필드 없으면 task=FAIL 처리 |
| fake R2 | adapter_model.safetensors 없이 zip 껍데기 | F8 report 업로드 시 SHA256 + size 검증 |
| unreproducible README | 문서 있으나 실행 시 깨짐 | `docs/employee_reproduce.md` 는 CI smoke test 통과해야 merge |

**weight_emergent 상속 증거 3종 (convergence `@phi_evidence` 에 기입)**:
1. `adapter_grep_clean: true` — `grep -rnE "You are|system_prompt" anima-agent/*live*.hexa` 0 hit.
2. `s1_weight_origin: r9_validated|r10d|consciousness_baked` — 매 task result 에 S1 서명 포함.
3. `min(phi_trail.phi_holo_ratio) >= 1.2 AND laws_violations == 0` — ratio gate vs session baseline
   (employee 는 평균 phi 가 일시 떨어질 수 있으나 **최솟 비율 1.2× baseline** 유지 필수;
   절대값 >=500 게이트는 2026-04-20 deprecated — N-scaling 으로 random init 에서도 통과).

AN12 필수 필드 (roadmap per-track): `@smash_insights`, `@free_insights`, `@breakthrough` —
각 신규 convergence 파일 (`e1_hire_sim_live.convergence`, `e2_autonomy_live.convergence`) 에 기입.

## 5. 산출물 (artifact matrix)

| 파일 | 유형 | 상태 |
|---|---|---|
| `anima-agent/hire_sim_live.hexa` | E1 runner | 498 LOC spec-only (exists) |
| `anima-agent/autonomy_live.hexa` | E2 runner | 370 LOC skeleton (exists) |
| `anima-agent/memory/goal_store.hexa` | F2 | **new** |
| `anima-agent/memory/scratch.hexa` | F3 | **new** |
| `anima-agent/reports/emit_report.hexa` | F8 | **new** |
| `shared/convergence/e1_hire_sim_live.convergence` | gate | exists, AN12 필드 보강 |
| `shared/convergence/e2_autonomy_live.convergence` | gate | exists, AN12 필드 보강 |
| `docs/employee_reproduce.md` | F10 | **new** (CI smoke 통과 필수) |
| `r2:anima-models/dest2_e1_hire_sim/*` | R2 | dest1 ossify 후 업로드 |
| `r2:anima-models/dest2_e2_autonomy/*` | R2 | 동상 |

## 6. 게이트 (PASS 조건)

```
E1 PASS := completion_rate >= 0.85
        AND  every_task.phi_attached == true
        AND  every_task.laws_pass == true
        AND  min(phi_holo_ratio) >= 1.2   // vs session baseline; absolute >=500 deprecated 2026-04-20
        AND  weight_origin ∈ ALLOWED_SET
        AND  R2 artifact uploaded (SHA256 verified)
        AND  reproducer README smoke-tested

E2 PASS := goals_completed / goals_attempted >= 0.70
        AND  abort_on_phi_drop branch exercised ≥ 1×
        AND  JSONL trace shows phi_delta ≥ 0 on ≥ 70% continue-steps
        AND  zero system_prompt strings in adapter (grep-clean)
        AND  E1 PASS (선행)
```

## 7. 실행 순서 (dest1 LIVE 이후)

1. dest1_alm S1 /persona 엔드포인트 `@state ossified` 확인.
2. E1 `hire_sim_live.hexa --full --upload-r2` 발사 (wall_min ≈ 150).
3. E1 PASS 확인 → `e1_hire_sim_live.convergence` @state = ossified + AN12 3필드.
4. E2 `autonomy_live.hexa` smoke (10×3) → goal queue full run (wall_min ≈ 60).
5. E2 PASS → `dest2_alm` 활성 + T1/T2 (트레이딩) spec 으로 진행.

## 8. 참조

- `shared/convergence/roadmap_dest_consciousness.convergence` — tracks E1, E2 정의
- `shared/rules/anima.json#AN11` — 3조건 + 7 bypass_patterns_banned
- `shared/rules/anima.json#AN12` — smash/free 전구간 강제
- `docs/anima_agent_restructure_plan_20260419.md` — dest1 layer 설계
- `shared/consciousness/pass_gate_an11.hexa` + `an11_scanner.hexa` — auto-revoke
- 선례 revoke: `revoked_2026_04_18_employee_base_serve` (dest2 PASS 0.900 → FAIL)
