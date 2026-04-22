# Track B Phase 4 — dashboard 분리 설계 (2026-04-19)

> 상태: 설계 문서 (blueprint). 실제 이동 금지 — 승인 후 별도 커밋.
> 레퍼런스: `docs/anima_agent_restructure_plan_20260419.md` §5 Phase 4.
> 목표: Next.js Web UI + WS bridge + Prometheus 메트릭을 agent 코어에서 분리.

---

## 0. 배경 · 범위

| 항목 | 값 |
|------|----|
| 위험도 | **낮음** (독립 stack, 양방 I/O) |
| stack | Next.js 14 (React/TS) + hexa WS bridge + Prometheus |
| blocking | 없음 — Phase 1/2 선행 불필요 |
| 커밋 제목 | `refactor(agent): isolate dashboard + metrics into separate package` |

---

## 1. 분리 대상 파일 (식별)

### 1.1 디렉토리 단위
| 경로 | LOC/크기 | 비고 |
|------|----------|------|
| `anima-agent/dashboard/` | Next.js 14 앱 (app/, package.json, next.config.js, postcss, tailwind, tsconfig) | 단일 Next 14 프로젝트 |
| └─ `dashboard/app/page.tsx` | 19,756 B (main UI) | WS 클라이언트 |
| └─ `dashboard/app/layout.tsx` | 443 B |  |
| └─ `dashboard/app/globals.css` | 1,076 B |  |
| └─ `dashboard/package.json` | `anima-dashboard` 0.1.0 |  |

### 1.2 루트 .hexa (이동 3 파일)
| 파일 | LOC | 역할 |
|------|-----|------|
| `anima-agent/dashboard_bridge.hexa` | 182 | **실제 구현** (WS + 폴링 + 이벤트 히스토리) |
| `anima-agent/hexa/dashboard_bridge.hexa` | 29 | **legacy stub** — 이동 금지, 삭제 대상 |
| `anima-agent/metrics_exporter.hexa` | — | Prometheus 8 게이지, :9090 |

### 1.3 deprecate
- `anima-agent/hexa/dashboard_bridge.hexa` — README 기준 "legacy stub, 정리 예정" → Phase 5 에서 일괄 `hexa/` 삭제와 함께 폐기. Phase 4 에서는 **이동 없음**.

---

## 2. 신 구조: `anima-agent-dashboard/`

```
anima-agent-dashboard/
  dashboard_bridge.hexa         ← 루트에서 이동 (main, 182 LOC)
  metrics_exporter.hexa         ← 루트에서 이동
  dashboard/                    ← Next.js 앱 (통째)
    app/{page,layout}.tsx, globals.css
    next.config.js, package.json, postcss.config.js,
    tailwind.config.ts, tsconfig.json
  CLAUDE.md                     ← 신규 (ref + exec)
  README.md                     ← 신규 (Web UI 개요)
```

---

## 3. 의존 audit

### 3.1 agent 본체 → dashboard (inbound)
| 참조원 | 참조 대상 | 처리 |
|--------|-----------|------|
| `anima-agent/CLAUDE.md` L21, L38, L45 | `dashboard_bridge.hexa`, `dashboard/` | CLAUDE.md 경로 업데이트 |
| `anima-agent/README.md` L53, L71, L95, L181 | 동일 | README 경로 업데이트 |
| `anima-agent/hexa/scheduler.hexa` L9/16/26/44/56, L851/858/868/886/898 | **심볼 이름만 사용** (`dashboard_refresh_sec`, `job_dashboard_refresh`) — 파일 import 없음 | **영향 없음** |
| `anima-agent/hexa/anima_agent_full.hexa` | legacy aggregate (hexa/ dir → Phase 5 삭제) | **영향 없음** |

### 3.2 dashboard → agent 본체 (outbound)
| 참조원 | 참조 대상 | 처리 |
|--------|-----------|------|
| `dashboard_bridge.hexa:40` | `AnimaAgent` struct | agent core 의존. **Phase 1 선행 권장** — `use anima-agent-core::AnimaAgent` 경로. Phase 4 단독 진행 시 상대경로 `../anima-agent/anima_agent.hexa` 임시 허용. |
| `dashboard/app/page.tsx` | `ws://localhost:8770` (런타임 WS) | URL 고정, 파일 경로 무관. 처리 불요. |
| `dashboard/package.json` | next/react/recharts | 독립, 처리 불요. |

### 3.3 인프라 · 설정
| 파일 | 수정 |
|------|------|
| `Dockerfile` | `COPY anima-agent/dashboard` → `COPY anima-agent-dashboard/dashboard` |
| `docker-compose.yml` | volume 마운트 2 개 (dashboard build, bridge WS:8770) |
| `shared/config/projects.json` | `anima-agent-dashboard` 등록 추가 |
| `shared/config/infrastructure.json` | 포트 :8770 WS + :9090 Prom → dashboard 패키지 귀속 |
| `shared/rules/anima.json` | L0 리스트에 추가 여부 — **제외 권장** (UI 빈번 수정) |
| `.claude/settings.json` hooks | pre-commit glob `anima-agent*/` 로 이미 매칭 |
| `.growth/scan.py` | 스캔 디렉토리 추가 |

---

## 4. 파일 이동 plan (git mv)

### Phase 4a — 디렉토리 생성 + 이동
```bash
# 루트 anima/ 에서 실행
mkdir -p anima-agent-dashboard
git mv anima-agent/dashboard            anima-agent-dashboard/dashboard
git mv anima-agent/dashboard_bridge.hexa anima-agent-dashboard/dashboard_bridge.hexa
git mv anima-agent/metrics_exporter.hexa anima-agent-dashboard/metrics_exporter.hexa
```

### Phase 4b — CLAUDE.md / README.md 신규
- `anima-agent-dashboard/CLAUDE.md` (≤ 60 줄, anima-agent/CLAUDE.md 포맷 준수)
  - ref: shared/config/infrastructure.json (ports), anima/config/consciousness_laws.json
  - exec: `$HEXA dashboard_bridge.hexa --port 8770`, `(cd dashboard && npm run dev)`
  - tree: 3 파일 + dashboard/ 하위
  - rules: L0 제외, AN7 HEXA-FIRST (bridge 는 .hexa), Next.js 는 예외 영역
- `anima-agent-dashboard/README.md` — Web UI 스크린샷/패널 설명.

### Phase 4c — 기존 문서 수정
- `anima-agent/CLAUDE.md` L21/38/45 — 해당 3 줄 제거 + `dashboard → anima-agent-dashboard/` stub 링크 한 줄.
- `anima-agent/README.md` L53/71/95/181 — 동일 처리.
- `$ANIMA/CLAUDE.md` tree: 섹션에 `anima-agent-dashboard/` 추가.

### Phase 4d — 인프라 · 설정 수정
- `Dockerfile` / `docker-compose.yml` COPY/volume 경로.
- `shared/config/projects.json` + `infrastructure.json` 패키지 등록 + 포트 귀속.

### Phase 4e — 검증
- `$HEXA anima-agent-dashboard/dashboard_bridge.hexa --port 8770` 기동 확인.
- `(cd anima-agent-dashboard/dashboard && npm run build)` 성공.
- `$HEXA anima-agent/test_e2e.hexa` 전 통과 (agent loop 무영향 확인).
- `--validate-hub` 통과.
- `hexa build` artifacts 재생성.

---

## 5. 리스크 · 완화

| 리스크 | 확률 | 완화 |
|--------|------|------|
| `AnimaAgent` struct 참조 끊김 | 중 | Phase 1 (core 분리) 선행 또는 임시 상대경로 import |
| Docker build 캐시 mis-fire | 낮 | Phase 4a 후 `docker build --no-cache` 1 회 |
| WS :8770 포트 문서 불일치 | 낮 | `shared/config/infrastructure.json` 동기화 필수 |
| Next.js `next dev` CWD 이동 혼선 | 낮 | README.md 에 `(cd anima-agent-dashboard/dashboard && npm ...)` 명시 |
| Phase 5 `hexa/` 일괄 삭제 시 stub 충돌 | 낮 | Phase 4 에서는 stub 건드리지 않음, Phase 5 책임 |

---

## 6. 완료 기준 (DoD)

- [ ] `anima-agent-dashboard/` 3 파일 + Next.js 앱 존재
- [ ] `anima-agent/` 루트에서 `dashboard/`, `dashboard_bridge.hexa`, `metrics_exporter.hexa` 부재
- [ ] `hexa build` 통과, artifacts 재생성
- [ ] `test_e2e.hexa` 전 통과
- [ ] Dockerfile + docker-compose.yml COPY/volume 경로 갱신
- [ ] CLAUDE.md 3 곳 (루트 anima, anima-agent, anima-agent-dashboard) 정합
- [ ] shared/config/ 2 파일 패키지 등록
- [ ] WS :8770 + Next dev :3000 기동 확인

---

## 7. 후속 Phase 와의 경계

- **Phase 1 (core)**: `AnimaAgent` struct 이동 시 dashboard_bridge.hexa import 한 줄 업데이트만 필요 — Phase 4 재작업 없음.
- **Phase 5 (tests + 청소)**: `anima-agent/hexa/dashboard_bridge.hexa` stub 삭제는 Phase 5 에서 `hexa/` 디렉토리 일괄 삭제로 처리.

---
(끝)
