# Track B · Phase 3 · hire-sim 분리 설계 (2026-04-19)

> **상태**: 설계 전용. 파일 이동 금지. 승인 후 별도 커밋 실행.
> **레퍼런스**: Phase 1 a26a8522 완료 · `track_b_phase1_movemap_20260419.md` · `track_b_phase2_5_audit_20260419.md` §4 Phase 4a · `anima_agent_restructure_plan_20260419.md` §3 L194-L195.
> **범위**: `anima-agent/hire_sim_*.hexa` + 관련 테스트/러너 → 신규 `anima-agent-hire-sim/` 리포 격상.

---

## 1. 대상 파일 인벤토리 (현 경로 + LOC)

### 1.1 `anima-agent/` 루트 (이동 대상, 7 파일)

| # | 파일 | LOC | 역할 | L0 |
|---|------|-----|------|----|
| 1 | `hire_sim_100.hexa` | 785 | 100-task × 6-domain 코퍼스 SSOT + `evaluate_task`/gate | Y (SSOT) |
| 2 | `hire_sim_judge.hexa` | 710 | per-domain deterministic judge (keyword+length+rule) | Y |
| 3 | `hire_sim_stratify.hexa` | 213 | stratified-30 샘플러 | N |
| 4 | `hire_sim_runner.hexa` | 542 | endpoint runner (stratified-30) | N |
| 5 | `hire_sim_live.hexa` | 498 | E1 live runner (S1 HTTP) — 현재 parse 오류 | N |
| 6 | `run_hire_sim_claude.hexa` | 49 | Claude adapter entry | N |
| 7 | `test_hire_sim.hexa` | 141 | smoke test | N |
| 7b | `test_hire_sim_harness.hexa` | 129 | harness test (runner+stratify+judge) | N |

**합계**: 8 파일 / **3,067 LOC**.

### 1.2 외부 거주 hire_sim 파일 (이동 **제외**)

| 파일 | LOC | 이유 |
|------|-----|------|
| `training/deploy/hire_sim_baseline.hexa` | 669 | Z-path 러너 (training 소유) |
| `training/deploy/hire_sim_lenient.hexa` | 982 | lenient Z-path 러너 (training 소유) |
| `training/deploy/hire_sim_pathc.hexa` | 699 | Path C 러너 (training 소유) |
| `serving/hire_sim_judge_lenient.hexa` | 332 | D6 lenient judge (serving 소유, hire_sim_lenient convergence) |
| `serving/hire_sim_judge_lenient_test.hexa` | 353 | lenient judge closed-loop 검증 (serving) |

→ training/serving 모듈 경계 유지. 각 파일은 **string 경로 const** 로 `/Users/ghost/Dev/anima/anima-agent/hire_sim_100.hexa` 참조 (compile-time use 아님) → 이동 후 경로 상수 패치 필요.

---

## 2. 상호 의존 그래프 (hexa `use` 체인)

```
hire_sim_100.hexa          ── use "autonomy_loop"
hire_sim_stratify.hexa     ── use "hire_sim_100"
hire_sim_judge.hexa        ── use "hire_sim_100"
hire_sim_runner.hexa       ── use "hire_sim_100" / "hire_sim_stratify" / "hire_sim_judge"
hire_sim_live.hexa         ── use "hire_sim_100"
run_hire_sim_claude.hexa   ── use "autonomy_loop" / "hire_sim_100" / "llm_claude_adapter"
test_hire_sim.hexa         ── use "autonomy_loop" / "hire_sim_100"
test_hire_sim_harness.hexa ── use "hire_sim_stratify" / "hire_sim_judge" / "hire_sim_runner"
```

### 2.1 외부 의존 (remain-in-place 모듈)
- `autonomy_loop` — anima-agent/ 루트 유지 (restructure plan L182)
- `llm_claude_adapter` — plan L192: `anima-agent-providers/` 로 Phase 4 이동 예정. Phase 3 시점엔 anima-agent/ 에 잔류.

### 2.2 외부에서 hire_sim 모듈을 `use` 하는 파일
- `grep '^use\s+"hire_sim_'` 전체 anima 트리 → **anima-agent/ 내부 한정**, **외부 0건** 확인.
- `training/deploy/{hire_sim_lenient,hire_sim_baseline,hire_sim_pathc,synth_corpus}.hexa` 는 파일경로 문자열로만 참조 (comptime const) → hexa import 그래프 무관.

결론: hire_sim 서브그래프는 **anima-agent/ 내부 완전 폐쇄** + 외부 의존 2건(autonomy_loop, llm_claude_adapter) 만 바깥으로 걸침.

---

## 3. 분리 대상 디렉토리 결정

| 옵션 | 형태 | 근거 | 채택 |
|------|------|------|------|
| A | `anima-agent-hire-sim/` (자매 리포) | plan §3 L193-195 명시, Phase 1 `anima-agent-core/` 패턴 일관 | **채택** |
| B | `anima-agent/hire_sim/` (서브폴더) | in-tree 서브폴더 보존, 이동 최소 | 기각 (plan 위배) |

**확정: 옵션 A — `anima-agent-hire-sim/`**. anima-agent-core 와 형제(sibling) 리포 구조 유지.

---

## 4. Import Cascade Audit (문자열/문서 참조)

### 4.1 hexa `use` 구문 (실 컴파일 영향)
- 내부 8 파일 서로 얽힘 → **동시 이동 필수** (부분 이동 시 silent-exit 위험, `feedback_hexa_silent_exit_5_imports.md`).
- `autonomy_loop`, `llm_claude_adapter` 는 anima-agent/ 에 **잔류** → 이동 후 `hire_sim_*.hexa` 의 `use "autonomy_loop"` / `use "llm_claude_adapter"` 는 **cross-package** 가 됨. hexa 는 `use` 가 파일명 베이스라 빌드경로(`-I anima-agent/`) 추가 필요.

### 4.2 문자열 경로 const (절대경로, 패치 필수)

| 파일 | 라인 | 현 값 |
|------|------|-------|
| `training/deploy/hire_sim_pathc.hexa` | 62 | `"/Users/ghost/Dev/anima/anima-agent/hire_sim_100.hexa"` |
| `training/deploy/hire_sim_baseline.hexa` | 65 | 동일 |
| `training/deploy/hire_sim_lenient.hexa` | 26 | `HIRE_SIM_CORPUS default ...anima-agent/hire_sim_100.hexa` |
| `training/deploy/synth_corpus.hexa` | 40 | 동일 |
| `training/eval_alm_13b.hexa` | 99 | 주석 (수정 선택) |

→ Phase 3 커밋에서 5 건 `anima-agent/hire_sim_100.hexa` → `anima-agent-hire-sim/hire_sim_100.hexa` 일괄 치환.

### 4.3 shared/ 설정
| 파일 | 항목 | 조치 |
|------|------|------|
| `shared/config/projects.json` | 신규 entry `anima-agent-hire-sim` 추가 | 필수 |
| `shared/convergence/e1_hire_sim_live.convergence` | `@file anima-agent/hire_sim_live.hexa` 등 3건 | 경로 patch |
| `shared/convergence/anima.json` | L896 `artifact: anima-agent/hire_sim_100.hexa + test_hire_sim.hexa` | patch |
| `shared/rules/anima.json` | L0 리스트에 `anima-agent-hire-sim/hire_sim_100.hexa` + `hire_sim_judge.hexa` 추가 | 필수 |
| `shared/state/*.json` (hire_sim_gate_*, hire_sim_regression_*) | 로그 스냅샷 (history) | **수정 금지** |

### 4.4 문서/로그 xref (anima-agent/hire_sim → 신경로)
`docs/dest2_employee_spec_20260419.md:100`, `docs/anima_agent_restructure_plan_20260419.md:193`, `training/deploy/alm_ga_gap_research_20260416.md` 3건, `training/deploy/smoke_full_ubu2_*.tsv` 5+건(재생성), `training/deploy/hire_sim_alm_*.log` (history, skip).

---

## 5. 파일 이동 계획 (실행 X, 시퀀스만)

```bash
# 0. 브랜치 + 스냅샷
git checkout -b refactor/agent-phase3-hire-sim
git status

# 1. 신규 리포 디렉토리
mkdir -p anima-agent-hire-sim

# 2. 8 .hexa 이동 (git mv, rename 추적)
git mv anima-agent/hire_sim_100.hexa          anima-agent-hire-sim/
git mv anima-agent/hire_sim_judge.hexa        anima-agent-hire-sim/
git mv anima-agent/hire_sim_stratify.hexa     anima-agent-hire-sim/
git mv anima-agent/hire_sim_runner.hexa       anima-agent-hire-sim/
git mv anima-agent/hire_sim_live.hexa         anima-agent-hire-sim/
git mv anima-agent/run_hire_sim_claude.hexa   anima-agent-hire-sim/
git mv anima-agent/test_hire_sim.hexa         anima-agent-hire-sim/
git mv anima-agent/test_hire_sim_harness.hexa anima-agent-hire-sim/

# 3. CLAUDE.md 신규 (anima-agent-core 패턴 — L1 지정, SSOT corpus+judge 보호)
#    Write tool 사용. exec 블록: hexa run hire_sim_runner / hire_sim_live / test_hire_sim*

# 4. 외부 절대경로 상수 5건 Edit
#    training/deploy/{hire_sim_pathc,hire_sim_baseline,hire_sim_lenient,synth_corpus}.hexa
#    training/eval_alm_13b.hexa (주석)

# 5. shared/ 4 JSON/convergence 패치
#    projects.json / anima.json / rules/anima.json / convergence/e1_hire_sim_live

# 6. 빌드 경로 검증 (autonomy_loop + llm_claude_adapter cross-package)
HEXA=$HEXA_LANG/target/release/hexa
$HEXA build anima-agent-hire-sim/test_hire_sim_harness.hexa \
  --include anima-agent -o build/test_hire_sim_harness
# 또는 빌드 설정에 `anima-agent/` include path 영구 등록

# 7. 커밋
git commit -m "refactor(agent): extract hire-sim suite → anima-agent-hire-sim/ (Phase 3)"
```

---

## 6. 테스트 절차

### 6.1 사전 검증 (dry-run)
- `git mv -n <src> <dst>` 8 건 dry-run.
- `grep -rE '^use\s+"hire_sim_' anima-agent*/` → 이동 후에도 8 `use` 전부 해소되는지 확인 (include path 추가 전제).

### 6.2 스모크 (순서 고정)
1. `$HEXA build anima-agent-hire-sim/hire_sim_100.hexa --include anima-agent` — autonomy_loop 해결 확인.
2. `artifacts/hire_sim_100.c` body 확인 (silent-exit 금지, feedback_hexa_silent_exit_5_imports).
3. `$HEXA run anima-agent-hire-sim/test_hire_sim.hexa --include anima-agent` — smoke PASS.
4. `$HEXA run anima-agent-hire-sim/test_hire_sim_harness.hexa --include anima-agent` — runner+stratify+judge PASS.
5. `$HEXA run anima-agent-hire-sim/hire_sim_runner.hexa` — smoke (mock endpoint).
6. `$HEXA run anima-agent-hire-sim/hire_sim_live.hexa --smoke --s1-url <URL>` — 현 parse 오류(144:28) Phase 3 **범위 외**. 이동은 수행하되 별도 bugfix 커밋.

### 6.3 외부 파이프라인 재스모크
- `$HEXA run training/deploy/synth_corpus.hexa` — 경로 상수 patch 검증.
- `$HEXA run training/deploy/hire_sim_lenient.hexa` — HIRE_SIM_CORPUS 기본값 재연결.
- `scripts/ckpt_promote.hexa` → `gate_hire_sim` 경로 무관 (sidecar JSON key "hire_sim_pass" 만 참조, PASS).

### 6.4 회귀 게이트
- `test_agent_platform.hexa` / `test_e2e.hexa` (anima-agent/ 잔류) — 영향 없음 확인 (hire_sim use 0건).
- `smoke_full_ubu2_resmoke_*.tsv` 재생성 비교 — 현 status (PASS/FAIL_C) 동등 또는 개선.

---

## 7. 위험 & 완화

| 위험 | 등급 | 완화 |
|------|------|------|
| cross-package `use "autonomy_loop"` 해소 실패 | 중 | 빌드 include path `-I anima-agent/` 고정. 실패 시 autonomy_loop 도 Phase 3 에 동반(탈락 옵션, 범위 확대). |
| hexa silent-exit (3+ import chain) | 중 | 이동 후 `artifacts/*.c` body grep 필수. |
| 외부 경로 상수 누락 | 중 | §4.2 5 파일 grep checklist. |
| hire_sim_live.hexa parse error (선재) | 낮음 | Phase 3 별도 bugfix 커밋, 이동 자체 무영향. |
| ready/ 아카이브 수정 | 무시 | Phase 5 전 수정 금지. |
| L0 corpus(`hire_sim_100`) 내용 변경 | 높음 | 이동만, 내용 불변 (git mv rename). |

---

## 8. Phase 4 연결점 (후속)

Phase 3 완료 후:
- `llm_claude_adapter.hexa` 를 `anima-agent-providers/` 로 이동 시 `run_hire_sim_claude.hexa` 의 `use "llm_claude_adapter"` 가 cross-package 2종이 됨 → 재검증 필요.
- `autonomy_loop` 를 끝까지 anima-agent/ 잔류시키거나 별도 `anima-agent-autonomy/` 승격하는 문제는 Phase 4+ 범위.

---

## 9. 결론

- 대상 8 파일 / 3,067 LOC, 내부 use 그래프 폐쇄 + 외부 use 2건(autonomy_loop, llm_claude_adapter).
- 옵션 A `anima-agent-hire-sim/` 채택 (plan L193 명시).
- 외부 절대경로 상수 5건 + shared/ JSON 4건 + CLAUDE.md 신규 패치 동시 커밋.
- 테스트 표면: test_hire_sim / test_hire_sim_harness / hire_sim_runner smoke + training/deploy/{synth_corpus,hire_sim_lenient} 경로 재검증.
- 선재 결함(hire_sim_live parse error) 은 Phase 3 범위 외 — 이동만 수행.

_분석 완료. 파일 이동 미수행. 승인 시 Phase 3 실행._
