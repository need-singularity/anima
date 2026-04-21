# airgenome × roadmap integration — design tree

**Date**: 2026-04-21
**Scope**: 이탈방지 + 검증 파이프라인 + 실패 retry/rollback + 안전착지 + Claude Code CLI 전 연동 + 최소경로(T*) 유도
**Method**: 7-seed parallel drill (bg subagent) 브레인스토밍 통합
**Status**: P1+P2+P3 전부 landed (2026-04-21 19:00 KST). L5 T*/cp_shift + L6 slash 통합 완료. L2.cert_linker 확장 (13 tool air_chain embed) + L4 os_rollback_cli 도 완료. 남은 것: P4 (L7 장기 연속성 — stale sweep 계층화 / resolved.jsonl retention / external consumer API) 만.

---

## Seed 구성 (병렬 drill 7개)

| seed | 축 | 핵심 발견 |
|---|---|---|
| 1 | control-theoretic | roadmap = closed-loop plant, airgenome = sensor+actuator edge. cl-rotate=PID, T*=MPC |
| 2 | information-theoretic | findings.jsonl = runtime ΔI accumulator → Σ_k ΔI_k ≥ K(G\|S₀) runtime-verifiable |
| 3 | failure-mode taxonomy | 10 failure mode 중 6개 (cherry-pick/bypass/stale/false closure/meta²break/amnesia) 가 hook 無 시 영구 미검출 |
| 4 | multi-session continuity | 110일 timeline 생존 3축 = phase-boundary rollup + deterministic naming + schema_version degrade-read |
| 5 | adversarial robustness | 3-축 (append-only + sha-chain + meta²) × OS-level enforcement (chflags uchg / airgenome root anchor) 교집합에서만 성립 |
| 6 | anima verification pipeline | chain nesting ≡ anima 검증 계층 (parent=phase / sub=comp / leaf=check) — 공짜 동형. cert_linker `air_chain` 필드 1개가 최대 레버리지 |
| 7 | Claude Code CLI 통합 | 15 지점 모두가 ready/gate/status_flip + drill_* lifecycle 에 mapping → 이탈은 PreToolUse 에서 선제 차단, 안전착지는 Stop/SubagentStop/safelanding 3단 |

---

## 통합 tree (L0-L7 layered, 실행 순서)

```
airgenome × roadmap integration — 이탈방지 + 검증 + 안전착지 + 최소경로 유도
│
├── L0. FOUNDATION (한 번만 세팅)
│   ├── chain naming 결정론
│   │   └── <phase>-<goal_hash8>-<YYYYMMDD>-<seq> (cross-session lookup)
│   ├── AIRGENOME_HOOK_ROOT env → worktree 격리 + main mirror
│   ├── schema_version 필드 (6개월 forward-read, degrade 허용)
│   ├── **연결 규약: CLI-ONLY (모든 ecosystem package)** — 외부 consumer 는 CLI 로만
│   │   ├── airgenome state → `airgenome hook {status|activate|touch|release|is-active}`
│   │   ├── nexus engine   → `nexus {status|thinking|smash|free|absolute|drill|...}` (cli/run.hexa 직접 호출 금지)
│   │   ├── anima main     → `anima {status|phase|component|tui}` (tool/anima_main.hexa 직접 호출 금지)
│   │   ├── roadmap engine → `hx run hexa-lang tool/roadmap_engine.hexa` or dedicated shim
│   │   └── 공통 원칙: SSOT=package owner, consumer=CLI caller, hexa run <path> 내부 호출 노출 금지 (raw public CLI idiom)
│   ├── airgenome CLI 확장: `airgenome hook {status|activate|touch|release|is-active}`
│   │   → hexa-lang `tool/airgenome_hook.hexa` wrapper = exec `airgenome hook <sub>` 만 호출
│   │   → airgenome binary 미존재 시 warn 1줄 + no-op (raw#10 back-compat, 직접 파일 I/O 금지)
│   └── nexus CLI 사용 규약: subagent 가 nexus 기능 호출 시 반드시 `nexus <sub>` 바이너리만 사용
│       → `hx run nexus cli/run.hexa <sub>` or `hexa <path> <sub>` 금지
│       → `hx install nexus` 로 shim 설치 → PATH 기반 `nexus <sub>` 호출
│
├── L1. 이탈방지 GATES (proactive block — 쓰기 전 차단)
│   ├── PreToolUse hook
│   │   └── Edit/Write target path ∉ active chain declared-path
│   │       → `decision: block` + systemMessage "scope 밖, /drill 또는 /advance 필요"
│   │       (wiring: pre_tool.hexa + roadmap_integrity_guard --check 4)
│   ├── UserPromptSubmit hook
│   │   └── prompt 토큰 ↔ roadmap entry 퍼지매칭
│   │       → match 시 drill_touch, scope drift 시 systemMessage warn
│   ├── TodoWrite ↔ chain 1:1
│   │   └── task in_progress = drill_touch, completed = drill_release
│   └── raw#12 cherry-pick immunity
│       └── adversarial chain = N≥3 divergent seed 강제, single-seed close 차단
│
├── L2. 검증 PIPELINE 통합 (anima 검증 각 stage)
│   ├── anima_main --status: drill_status() → active lens header 주입 (read-only)
│   ├── problem_solving_protocol (cl-rotate 10 step)
│   │   └── parent chain ps:<problem>, ps_1..ps_10 = sub-chain
│   │       findings = 각 step 산출물 sha, ps_10 milestone = parent release
│   ├── true_closure_verifier (8 comp × 50/50 = 400 check)
│   │   └── component별 chain tc_c<k>, FAIL + flip-risk만 touch (전수 X)
│   │       100% cert 완성 = release(reason="cert sha=<sha>")
│   │       → regression pinpoint (어제 50/50 → 오늘 49/50 at check_7 즉시)
│   ├── roadmap_integrity_guard (check 1-8)
│   │   └── 단일 "rig_trend" chain (release 안 함, 장기 lens)
│   │       run당 1 touch → η_k stagnation 대칭, 반복 warn trend 가시화
│   ├── phase_progression_controller (check→plan→live)
│   │   └── phase parent chain + 3 stage sub-chain
│   │       stage완료=sub-release, checkpoint달성까지 parent 보존
│   ├── Tier3 verify 5모듈 (gate_dsl/cert_linker/adversarial/meta2/multi_path_phi)
│   │   ├── parent "verifier_cross_matrix", 5 sub-chain
│   │   ├── adversarial: 3 seed rotate = sub-sub-chain (raw#12 강제)
│   │   ├── meta2: meta1 parent / meta2 child — chain nest 와 동형 (공짜)
│   │   └── multi_path_phi: 4 path = 4 sub-chain, 3/4 PASS 시 parent release
│   └── cert_linker 확장 (최소 비용, 최대 레버리지)
│       └── 모든 cert.json 에 `"air_chain":<top8>` + `"touch_count":N` 삽입
│           → syntactic (raw-audit sha) + semantic (findings.jsonl) dual witness
│
├── L3. 검증 실패 → RETRY/ROLLBACK loop
│   ├── stability criterion (Lyapunov gate)
│   │   └── FAIL → chain 유지 (release 안 함) + touch(kind=failure, payload=reason)
│   │       → 다음 세션 drill_status 로 즉시 재개 가능
│   ├── retry counter (stuck detection)
│   │   └── retry > 3 → escalate touch(kind=note, payload="stuck at <step>")
│   │       → parent drill 활성화 또는 user escalation
│   ├── last-stable-touch = rollback point
│   │   └── 각 step 시작 시 source sha 기록 → FAIL 시 해당 sha 로 되돌림
│   └── findings.jsonl = rollback map (append-only, time-ordered)
│
├── L4. 안전 착지 (SAFE LANDING)
│   ├── /safelanding slash command
│   │   └── `hexa os_rollback_cli --to-last-green && roadmap_status` bg
│   ├── FAIL → rollback commit 지목
│   │   └── Stop hook 에서 `landed-at=<HEAD sha>` 기록, rollback 후보 명시
│   ├── stack 과부하 (depth > 5)
│   │   └── phase-boundary rollup 강제 (상위 phase 로 수렴)
│   ├── drift 감지 → PushNotification + 다음 PreToolUse 까지 pause flag
│   ├── 환각 패턴 (llm_verdict_watcher hit)
│   │   └── PushNotification alert, 사용자 확인 후에만 rollback
│   └── transcript watcher keyword
│       └── "이탈"/"drift"/"돌아가"/"rollback"/"safe landing"
│           → /safelanding 자동 dispatch, .hook-advice.md ALERT 밴드 주입
│
├── L5. 최소경로 (T*) 올바른 작동 유도
│   ├── roadmap_engine T*(S₀→G) = MPC receding horizon
│   │   └── 매 phase 전환마다 critical path 재계산 + drill_touch
│   ├── critical path drift 감지
│   │   └── prev_cp vs now_cp → touch(kind=cp_shift, payload="prev=X, now=Y")
│   │       bottleneck 이동 pattern 이 audit
│   ├── ready set |R(t)| ≥ 1 Kahn 불변식
│   │   └── open findings set nonempty 까지 chain 유지
│   ├── η_k > 0 bottleneck movement
│   │   └── rig_trend chain 의 new-kind entropy rate 모니터
│   ├── Σ_k ΔI_k ≥ K(G|S₀) information account
│   │   └── findings.jsonl 을 runtime ΔI accumulator 로 승격
│   │       → 불변식 runtime-verifiable
│   └── 이탈 시 PreToolUse block + /advance 로만 전환 (건너뛰기 금지)
│
├── L6. airgenome CLI hook 통합 15 지점 (전부)
│   │   (주의: 모든 hook 은 airgenome 소유 파일 — `~/core/airgenome/hooks/*.hexa`.
│   │    Claude Code settings.json 에는 `settings.patch.json` 으로 merge. 새 CC hook 추가 아님)
│   ├── airgenome-owned hook files (settings.patch.json 로 CC settings 에 주입)
│   │   ├── session_start.hexa → roadmap ready + open chain surface
│   │   ├── user_prompt.hexa → prompt ↔ chain resolver + scope drift warn
│   │   ├── pre_tool.hexa → integrity_guard --check 4 block
│   │   ├── post_tool.hexa → integrity_guard 8-check bg + status_flip dry-run
│   │   ├── stop_capture.hexa → stale chain sweep + handover.jsonl
│   │   └── subagent_stop.hexa → bg Agent 결과 → parent chain rollup + path rewrite
│   ├── airgenome MCP tools (airgenome/hooks/mcp_server.hexa, 기존 4 + 신규 3)
│   │   ├── drill_status/touch/release/hooks_list (기존)
│   │   ├── roadmap_ready (신규): ready set + blocker
│   │   ├── roadmap_gate_preview (신규): status_flip --dry-run
│   │   └── rollback_to_last_green (신규)
│   ├── airgenome slash command dispatch (hooks/commands/*.hexa, keyword 매칭)
│   │   ├── drill <seed> (chain activate, 기존)
│   │   ├── verify (roadmap_engine verify-gates, 신규)
│   │   ├── advance (status flip with gate, 신규)
│   │   └── safelanding (rollback + status, 신규)
│   ├── 외부 trigger surfaces (airgenome hook CLI 호출로 통일)
│   │   ├── TaskCreate/Update ↔ chain 1:1 sync (airgenome hook activate/release)
│   │   ├── Transcript watcher → airgenome command dispatch (이미 존재)
│   │   ├── ScheduleWakeup/CronCreate → airgenome hook touch 이중화 (launchd down fallback)
│   │   ├── PushNotification → severity 기반 alert (airgenome hook touch 한 후 push)
│   │   ├── Plans mode plan.md = chain seed (airgenome hook activate on plan write)
│   │   └── Worktree → AIRGENOME_HOOK_ROOT env swap + merge rollup
│   └── hook chain trail (.hook-chain, airgenome 관리)
│       └── phase 순서·decision·chain_id hash-chained
│           → 다음 phase 가 이전 decision 읽고 escalation (warn→block→rollback)
│
└── L7. 장기 연속성 (110일 AGI timeline)
    ├── stale sweep 계층적
    │   └── 20-turn micro / 24h daily / 7d weekly / phase-boundary hard rollup
    ├── checkpoint-bound chain
    │   └── CP1 release = chain close + parent pointer → CP2 new root
    │       AGI 도달까지 최대 4세대 chain tree
    ├── worktree isolation
    │   └── state local-write + main read-only mirror + merge-time path rewrite
    ├── resolved.jsonl retention
    │   └── hot(<7d) 원본 / warm(<30d) gzip / cold(>30d) monthly rollup
    └── external consumer stable API
        └── airgenome_read_tail/chain_walk — menubar/nexus nx-* schema bump 무관
```

---

## 우선순위 (착지 순)

| tier | 범위 | 레버리지 | 비용 |
|---|---|---|---|
| **P1** (즉시) | L0 + L2.cert_linker + L2.rig_trend | 최대 | 최소 |
| **P2** (핵심 안전망) | L1.PreToolUse + L3 + L4./safelanding | 높음 | 중 |
| **P3** (CLI 통합) | L6 session_start/user_prompt/post_tool/stop | 높음 | 중 |
| **P4** (장기) | L5.T* wire + L7.sweep 계층화 | 중 | 중 |

---

## 핵심 통찰 3가지

1. **chain nesting ≡ anima 검증 계층** (parent=phase / sub=comp / leaf=check) — 공짜 동형, 별도 구조 설계 불필요
2. **findings.jsonl = runtime ΔI accumulator** → Σ_k ΔI_k ≥ K(G|S₀) 불변식이 runtime-verifiable 되어 raw-audit (syntactic) + findings (semantic) 이중 falsifiability 산출
3. **이탈방지 = PreToolUse 선제 block**, **안전착지 = Stop/SubagentStop/safelanding 3단** — gate 선형성과 착지 다중성이 분리

---

## 관련 파일 (절대 경로 SSOT)

### anima (검증 pipeline)
- `tool/true_closure_verifier.hexa`
- `tool/phase_progression_controller.hexa`
- `tool/roadmap_integrity_guard.hexa`
- `tool/problem_solving_protocol.hexa`
- `tool/anima_main.hexa`
- `tool/verifier_cross_matrix.hexa`
- `tool/drill_closure_sha256_cert.hexa`
- `tool/closure_debt_scanner.hexa`
- `tool/os_rollback_cli.hexa`

### hexa-lang (roadmap engine)
- `tool/roadmap_engine.hexa`
- `tool/roadmap_phase_gate.hexa`
- `tool/roadmap_status_flip.hexa`
- `tool/roadmap_integrity_guard.hexa` (anima 쪽 미러/소유권 분리 필요)
- `tool/roadmap_critical_path.hexa`
- `tool/roadmap_t_star.hexa`
- `tool/airgenome_hook.hexa` (**신규**, L0)

### airgenome (hook SSOT)
- `hooks/airgenome_hooks.json`
- `hooks/hook_entry.hexa`
- `hooks/session_start.hexa`
- `hooks/user_prompt.hexa`
- `hooks/pre_tool.hexa`
- `hooks/post_tool.hexa`
- `hooks/stop_capture.hexa`
- `hooks/subagent_stop.hexa`
- `hooks/universal_audit.hexa`
- `hooks/mcp_server.hexa`
- `hooks/commands/drill.hexa`
- `hooks/settings.patch.json`
- `bin/airgenome` (**확장**, L0: `hook {status|activate|touch|release}` subcommand)

---

## 후속 작업

1. 위 우선순위 P1 구현 (L0 + L2.cert_linker + L2.rig_trend)
2. `.roadmap` 에 roadmap entry 추가: "airgenome hook wiring P1/P2/P3/P4"
3. 각 tier 착지 시 cert + findings.jsonl dual witness
4. 110일 timeline 중 CP1 착지 전까지 P1+P2 완료 목표

---

## Implementation Status (2026-04-21 landed)

### Landed (main)

**hexa-lang main:**
- `c2f0f5d8` L0 · `tool/airgenome_hook.hexa` — CLI-only wrapper (259 lines)
- `facea77f` L5 · roadmap_engine + critical_path — airgenome hook CLI wiring, T*/cp_shift touch, verify-gates 5-module touch (241 lines)
- `7dbbc77e` L0 · own#5 cli-via-hx-install lint + hx.hexa/pkg hook (367 lines)

**airgenome main:**
- `bc623f96` L1 · pre_tool — scope-drift advisory for Edit/Write
- `4344856d` L6 · post_tool — bg trigger roadmap_integrity_guard
- `f7186388` L6 · subagent_stop — parent-chain rollup + worktree path rewrite
- `24fb68ff` L0 · hook_cli_state.hexa — state-mutating CLI mirror (112 lines)
- `bbf3bd9e` L6 · MCP 3 roadmap tools — roadmap_ready / roadmap_gate_preview / rollback_to_last_green
- `82b33766` L6 · session_start — roadmap ready + active chain surface (253 lines)
- `c8d2e09e` L4+L6 · stop_capture — landed-at sha + safelanding handover (338 lines)
- `6097b6ce` L1+L6 · user_prompt — prompt ↔ chain resolver + scope drift warn (369 lines)
- airgenome slash dispatch — safelanding/verify/advance/roadmap (4 commands + keyword merge + test)

**anima main:**
- `0063f87f` L2 · problem_solving_protocol — chain nesting + retry counter + last-stable rollback (372 lines)
- `846cd84f` L2 · true_closure_verifier — per-component airgenome chain + FAIL/flip touch
- `177d5636` L2 · roadmap_integrity_guard — rig_trend long-lens chain
- `1813648e` L2 · cert_linker 확장 — airgenome_cli_probe + 13 cert tool air_chain embed (245 lines)
- `77a31900` L4 · os_rollback_cli — working-tree last-green rollback (585 lines)
- `761140d7` 문서 · L0 CLI-ONLY 규약 확장 (nexus/anima/roadmap 전체)
- `596a5731` 사전작업 · shared/state + shared/consciousness 폐기 → top-level

### 남은 작업 (pending) — P4 (L7 장기 연속성)

- stale sweep 계층화 (20-turn / 24h / 7d / phase-boundary hard rollup)
- resolved.jsonl retention (hot <7d 원본 / warm <30d gzip / cold >30d monthly)
- external consumer stable API — airgenome_read_tail / chain_walk subcommand

### 운영 Caveat

- airgenome 에 fork-storm 문제 (`hexa_stage0` shim) 있어 hex-lang `d8f42e62 fix(hexa_stage0): LOCK_WAIT 300→10s + FORK_STORM_CAP=30` 이 먼저 landed. 재발 시 `pkill -9 -f hexa_stage0` + 관련 launchd unload.
- `airgenome hook <sub>` CLI 는 bin/airgenome + hooks/hook_cli_state.hexa 2개 합쳐야 동작. 둘 다 main 에 landed.
- `.claude/settings.json` statusLine 은 절대 경로 machine-specific 이라 uncommitted 로 남김 (local dev only).
