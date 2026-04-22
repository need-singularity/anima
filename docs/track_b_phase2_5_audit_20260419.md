# Track B · Phase 2–5 Pre-Audit (2026-04-19)

> **상태**: 분석 전용. 파일 이동 금지.
> **레퍼런스**: `docs/anima_agent_restructure_plan_20260419.md` §5, `track_b_phase1_movemap_20260419.md`.
> **범위**: Phase 1 (anima-agent-core 분리, a26a8522) 완료 이후 남은 channels/providers/plugins/skills/trading 서브폴더의 승격 영향.

---

## 1. 핵심 결론 (TL;DR)

**import cascade 영향: 0 건.** 5 서브폴더 35 .hexa 파일 전부 `use` 문이 전혀 없는 **zero-dependency stub** 상태. Phase 2 이동은 파일시스템 이동 + 문서/설정 xref 갱신만으로 완결됨. E3 boil 없음.

---

## 2. 서브폴더 인벤토리 (LOC + 파일 수)

| 폴더 | 파일 수 | LOC | 외부 `use` 참조수 | 내부 `use` |
|------|--------|-----|------------------|-----------|
| `channels/` | 7 (__init__ 포함) | 500 | 0 | 0 |
| `providers/` | 6 | 375 | 0 | 0 |
| `plugins/` | 7 | 380 | 0 | 0 |
| `skills/` | 2 + registry.json | 167 | 0 | 0 |
| `trading/` | 14 | 1,695 | 0 | 0 |
| **합계** | **36** | **3,117** | **0** | **0** |

### 검증 근거
- `grep -rn "^use " anima-agent/{channels,providers,plugins,skills,trading}` → **matches 0**
- `grep -rn "use .*channels\." anima` → 주석만 (anima-engines 내부 자연어 문장)
- `grep -rn "use .*providers\.|plugins\.|trading\.|skills\." anima-agent` → **0**
- anima-agent/*.hexa 루트 use 맵: 전부 `autonomy_loop / hire_sim_* / llm_claude_adapter` 에만 걸림 (서브폴더 참조 0)
- anima-agent-core/*.hexa: 서브폴더 이름이 comment + TODO 스텁 + string-id (`trading_backtest` 등) 로만 등장

### 왜 0인가
README 주석: "레거시 스텁 .hexa (교체 완료, 정리 예정)" + 각 파일 본문 `TODO[python-sdk]:` 마커 다수. **.py → .hexa 포팅은 껍데기만 완료** — 본격 의존 배선은 대기 상태.

---

## 3. 잠재 참조 (실제 코드 경로 기준)

### 3.1 문서/주석
| 위치 | 형태 | 처리 |
|------|------|------|
| `docs/AGENT-ARCHITECTURE.md:173,177,181` | `python -m channels.X` (3건) | Phase 2 xref 패치 |
| `ready/anima/modules/agent/**` | legacy .py `from channels/providers/trading.X` (≈ 50건) | Phase 5 청소 또는 그대로 방치 (ready/ 는 archive) |
| `ready/docs/AGENT-ARCHITECTURE.md` | 동일 3건 | 아카이브, 수정 불필요 |
| `anima-agent/CLAUDE.md` | tree 블록 (channels/…/trading/ 5행) | Phase 2 커밋 |
| `anima-agent/README.md:122` | "plugins/trading.hexa" 한 줄 | Phase 2 커밋 |
| `anima-agent-core/CLAUDE.md:39,41` | Phase 2–5 로드맵 문장 2행 | Phase 2 커밋 |

### 3.2 런타임 문자열 ID (컴파일-타임 import 아님)
- `anima-agent-core/agent_tools.hexa`: `tool_trading_backtest/scan/execute/balance` (string tool-name)
- `anima-agent-core/tool_policy.hexa`: `TIER_*` 매핑 키 (string)
- `anima-agent-core/unified_registry.hexa:65`: `TODO[python-sdk]: plugin_loader.discover_plugins` 주석만

문자열 ID 는 폴더명 변경과 무관 — tool-name 은 그대로 유지(`trading_backtest`).

### 3.3 shared/ JSON (Phase 1 동일 패턴)
| 파일 | 변경 내용 |
|------|-----------|
| `shared/config/projects.json` | 신규 entry 4개: anima-agent-channels/providers/plugins/trading |
| `shared/config/project_config.json` | 해당 없음 (CLI entry 는 core 이미 완료) |
| `shared/config/infrastructure.json` | pod mount 경로 확장 (선택) |
| `shared/rules/anima.json` | L0 미지정 — 본 승격 대상은 모두 교체가능한 어댑터 |

### 3.4 `skills/registry.json`
`file_path: "$ANIMA/.anima/skills/research_topic.md"` — 절대경로라 영향 없음.

---

## 4. Phase 별 이동 계획

### Phase 2 · channels + providers + plugins + skills 동시 승격
- 단일 커밋 권장 (상호 의존 0, 테스트 표면 공유: `test_plugin_routing.hexa`, `test_e2e.hexa`)
- 이동: `git mv anima-agent/{channels,providers,plugins,skills} anima-agent-{name}/`
- `__init__.hexa` 4개 삭제 (hexa 는 flat-package)
- 위험도: **낮음** (zero use chain)
- 후속: `docs/AGENT-ARCHITECTURE.md` 3줄 + anima-agent/CLAUDE.md tree + README 1줄 패치

### Phase 3 · trading 승격
- 별도 커밋 (LOC 가 가장 크고 `phi_weighted_trading.hexa` 432 LOC 가 의식-트레이딩 브릿지)
- 이동: `git mv anima-agent/trading anima-agent-trading/`
- `test_ensemble.hexa` 는 hire-sim 분리(Phase 3.5) 전까지 trading 내부에 유지
- 위험도: **낮음**

### Phase 4 · hire-sim + dashboard + tests 분리
- plan §5 Phase 3/4/5 유지 (본 문서 범위 외, 단 Phase 번호 조정)
- hire-sim 은 루트 .hexa 이동이라 use chain **있음**: `autonomy_loop`/`hire_sim_100` 내부 사슬 → 이동 시 동반 이동 필수
- Phase 4a(hire-sim) / 4b(dashboard) / 4c(tests) 3단계

### Phase 5 · legacy 청소
- `anima-agent/hexa/` 전체 삭제 (README 기준 deprecated)
- `pyproject.toml` 삭제 (R37)

---

## 5. 권장 실행 순서

```
Phase 2  channels + providers + plugins + skills  (1 커밋, LOC 1,422)
Phase 3  trading                                   (1 커밋, LOC 1,695)
Phase 4a hire-sim                                  (1 커밋, LOC ≈ 45 KB)
Phase 4b dashboard                                 (1 커밋)
Phase 4c tests                                     (1 커밋)
Phase 5  legacy purge (hexa/ + pyproject.toml)     (1 커밋)
```

### 근거
1. **Phase 2 통합**: 4 폴더 모두 use-chain 0, 테스트 1~2 개 공유 → 단일 커밋이 리뷰/롤백 용이.
2. **Phase 3 분리**: trading 은 LOC 가 크고 `phi_weighted_trading` 이 의식-시그널 결합부라 별도 커밋에서 스모크 테스트.
3. **Phase 4 → 5 순서**: hire-sim use chain 은 anima-agent 루트에 얽혀있어 Phase 2/3 먼저 끝내면 의존 표면이 단순해짐.

---

## 6. 각 Phase 체크리스트 (Phase 1 양식 재사용)

- [ ] `git mv` 로 이동 (rename 추적 보존)
- [ ] `hexa build` 로 artifacts/*.c 재생성 확인 — empty main 검출 금지
- [ ] `test_agent_platform.hexa` / `test_e2e.hexa` / `test_plugin_routing.hexa` PASS
- [ ] `--validate-hub` 48 modules 등록 확인
- [ ] `shared/config/projects.json` 신규 entry 추가
- [ ] pre-commit hook 통과 (ghost/.claude/hooks/block-forbidden-ext.sh)
- [ ] `grep "anima-agent/" docs/` 결과가 의도한 파일만
- [ ] anima-agent-{name}/CLAUDE.md 신규 (anima-core 패턴 준용)

---

## 7. 위험 요약

| 위험 | 등급 | 완화 |
|------|------|------|
| import cascade 전파 | **없음** | use 0건, 파일 이동만 |
| string tool-id 깨짐 | 없음 | tool-name 은 폴더명 무관 |
| docs xref 누락 | 중 | Phase 2 커밋에 §3.1 3 건 포함 |
| shared/projects.json 누락 | 중 | 체크리스트 강제 |
| ready/ legacy 아카이브 | 무시 | Phase 5 외 수정 금지 |
| hexa build 빈 main (silent-exit) | 중 | 이동 후 artifacts/*.c 본문 검증 |
| Docker/compose 경로 | 낮음 | 본 5개 폴더는 compose 마운트 대상 아님 |
| Growth Registry `.growth/` | 낮음 | anima-agent 단일 리포라 분기 불요 |

---

## 8. 의존 그래프 (zero 상태)

```
anima-agent-core/  ─────── (string ID 참조) ───────┐
   run.hexa                                        │
   agent_tools.hexa     "trading_*" "plugin_*"    │
   tool_policy.hexa     (폴더명 무관, string only) │
                                                   │
anima-agent/                                       │
   anima_agent.hexa  (TODO 스텁)   ◄───────────────┤
   autonomy_*.hexa                                │
   hire_sim_*.hexa   ◄─── 루트 내부 use 사슬       │
                                                   │
channels/   providers/   plugins/   skills/   trading/   ← 이 폴더들은 상호 무연결
 (7)         (6)         (7)        (2)       (14)
 isolate    isolate     isolate    isolate    isolate
```

---

## 9. 결론

Phase 2–5 는 **코드 의존성 교정이 불필요한 순수 리디렉토리 작업**. 본 아키텍처가 .py→.hexa 포팅을 스텁 단계까지만 진행한 "cold" 상태이기 때문. 후속 porting (TODO[python-sdk] 해소) 은 승격 **이후** 새 경로에서 진행하는 것이 재작업 최소화.

**권장**: Phase 2 (4 폴더 통합) 를 단일 커밋으로 발사 → Phase 3 trading → Phase 4abc → Phase 5 청소.

---

_분석 완료. 파일 이동 미수행. 승인 시 Phase 2 부터._
