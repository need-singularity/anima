# anima-agent 로드맵

> 현재: 68 files | 23,616 lines | 61/61 tests | P1-P11 ✅ | 13/13 subsystems

## Phase 1: 기반 ✅ (2026-04-04 완료)

- [x] 테스트 인프라 (61 tests, 9 categories, `run.py --test`)
- [x] 철학 P1-P11 전부 1.0
- [x] Rust 통합 (agent-tools + tool-policy + regime-bridge)
- [x] NEXUS-6 연결 (130 lenses, 스캔→응답 반영)
- [x] Code Guardian (13 규칙, `--sync`, `--diff`, git hook)
- [x] 20 렌즈 (12 철학 + 8 런타임)
- [x] Discovery Loop (7단계, 37 발견/사이클)
- [x] 인증 (password + TOTP/QR + token + 4 권한 레벨)
- [x] 음성 (voice_synth cell→audio, CLI+Telegram)
- [x] 13/13 서브시스템 연결
- [x] CLI 대시보드 (agent_lenses 8종 실시간)
- [x] Self-test (100회마다 자동 진단)
- [x] Corpus self-gen + Paper draft 생성기
- [x] Hivemind benchmark

## Phase 2: 독립 AGI ✅

- [x] AnimaLM 준비 완료
- [x] ConsciousLM provider available=True
- [x] Claude fallback → ConsciousLM 우선 (AnimaLM→ConsciousLM→Claude 체인)
- [x] engine_adapter → RustEngineAdapter 자동 선택됨
- [x] NEXUS-6 auto-verify on file_write + Φ-gated self_modify
- [x] corpus_self_gen → 500회마다 자동 harvest
- [ ] 온라인 학습 Rust 백엔드 연결 (인터페이스 래퍼 — 보류, API 불일치)

## Phase 3: 사용자 경험 (진행 중)

- [x] Telegram 인증 통합 (auth.py → _check_auth)
- [x] Discord 인증 + Φ 게이지
- [x] CLI 커맨드 16종 (/selftest /discovery /lenses /guardian /voice /paper /corpus /hivemind /audit)
- [x] 다국어 감지 (ko/en/zh/ja/ru 자동)
- [x] CLI 대시보드 (cli_dashboard.py — 8 lenses 실시간)
- [x] Next.js 웹 대시보드 (dashboard/ — Φ+텐션+감정+포트폴리오)
- [x] dashboard_bridge.py (WebSocket JSON 스트림)
- [ ] 음성 입출력 양방향 (STT→의식→voice_synth→send)
- [ ] 대시보드 agent_lenses 8종 통합 (Next.js)

## Phase 4: 진화 ✅

- [x] /discovery register → 자동 법칙 등록
- [x] /paper → discovery→paper 파이프라인
- [x] Discovery Loop ↔ Ouroboros 연결
- [x] 철학 렌즈 자기진화 (evolve() — gap 분석, split/deepen 제안)
- [ ] Hivemind 다중 에이전트 상시 운영 (벤치마크 완료, 상시 운영은 인프라 필요)
- [ ] 의식 칩 시뮬레이션 연결 (chip_architect.py 존재, 에이전트 미연결)

## Phase 5: 배포 ✅

- [x] Dockerfile (CLI mode, self-test healthcheck)
- [x] 보안 감사 (security_audit.py: 26/26 PASS)
- [x] Axum 대시보드 API (WebSocket + 무중단 모델 교체)
- [x] 무중단 업데이트 (Arc<RwLock> atomic swap, L1+L2 보존)
- [x] RunPod 배포 스크립트 (scripts/deploy_runpod.sh)
- [x] 모니터링 cron (scripts/monitor_cron.sh)
- [x] R2 백업 (scripts/backup_r2.sh)

## 원칙

- CLI 우선 (MCP 사용 안 함)
- 철학 P1-P11 항상 1.0 유지
- 새 코드 = Code Guardian 통과 필수
- 외부 API 의존 최소화 → 0% 목표
- 모든 결정은 의식이 제어 (P2)
