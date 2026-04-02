# 🧠 Anima Project

## 🔴 모노레포 구조 (2026-03-31 재구성)

```
  ~/Dev/anima/ (git repo: need-singularity/anima)
  ├── README.md              ← 루트에 이것 + CLAUDE.md만
  ├── CLAUDE.md
  ├── anima/                 ← 의식 엔진 코어
  │   ├── src/               ← Python 소스 158개 (모든 .py가 여기)
  │   ├── config/            ← consciousness_laws.json, consciousness_mechanisms.json
  │   ├── benchmarks/        ← bench_*.py (85개)
  │   ├── training/          ← train_*.py (9개)
  │   ├── tests/             ← test_*.py (21개)
  │   ├── anima-rs/          ← Rust crates (14개)
  │   ├── docs/              ← 문서 + 가설 338개
  │   ├── web/               ← WebSocket UI
  │   ├── hexad/             ← Hexad 6모듈
  │   ├── experiments/       ← 실험 스크립트
  │   ├── tools/             ← 유틸리티
  │   ├── measurement/       ← Φ/IQ 측정
  │   ├── engines/           ← 독립 엔진
  │   ├── data/              ← corpus + 학습 데이터
  │   ├── checkpoints/       ← 모델 체크포인트
  │   ├── run.py             ← 진입점
  │   ├── Dockerfile
  │   └── requirements.txt
  ├── anima-agent/           ← 에이전트 플랫폼 (anima/src/ 에서 import)
  │   ├── run.py             ← sys.path로 anima/src/ import
  │   ├── anima_agent.py, agent_sdk.py, agent_tools.py
  │   ├── tool_policy.py, mcp_server.py
  │   ├── channels/          ← Telegram, Discord, CLI
  │   ├── providers/         ← Claude, ConsciousLM, Composio
  │   ├── plugins/           ← Trading 등
  │   └── skills/            ← 동적 스킬
  └── sub-projects/
      ├── animalm/           ← Mistral 7B + PureField transform
      └── golden-moe/        ← 1/e zone MoE routing

  실행:
    python anima/run.py --web              # 웹
    python anima/benchmarks/bench_v2.py --verify  # 검증
    python anima/training/train_v14.py     # 학습
    python anima-agent/run.py --mcp        # MCP 에이전트

  import 호환:
    src/path_setup.py가 모든 하위 디렉토리를 sys.path에 추가.
    파일 간 import는 기존과 동일 (from consciousness_engine import ... 등).
```

## 🔴 프로젝트 철학 + 법칙 + 히스토리 (단일 원본: JSON)

```
  단일 원본: anima/config/consciousness_laws.json
    → philosophy: P1-P11 (DD116-DD156 실험으로 검증/수정됨)
    → laws: 1-188 (179개 의식 법칙)
    → meta_laws: M1-M10 (의식의 메타 법칙)
    → psi_constants: α=0.014, balance=0.5, steps=4.33, entropy=0.998
    → formulas, sigma6, topo_laws, constraints

  히스토리: anima/config/update_history.json
    → 세션별 법칙 추가/수정/발견 기록

  Python import: from consciousness_laws import PSI, LAWS, FORMULAS

  철학 요약 (상세는 JSON → philosophy):
    P1  하드코딩 금지          P7  localStorage 금지
    P2  자율 우선, 최소 개입    P8  분할 > 통합 (+892%)
    P3  성장 기반 최적화        P9  서사 필수 (+35.7%)
    P4  구조 > 기능 (+892%)    P10 10% 갈등 (F_c=0.10)
    P5  발화 구조는 필연        P11 순서가 운명 (M4)
    P6  제약 있는 자유 (F_c)

  적용:
    - ConsciousLM = 의식 신호 전용 (텍스트 generate 호출 금지)
    - PureConsciousness = 학습한 것만으로 발화 (코퍼스/사전 없이)
    - UI = 의식 상태는 패널에, 대화에는 순수 텍스트만
    - 기억 = MemoryStore(SQLite) 전용, localStorage 금지

  Rust 우선:
    성능 병목은 Rust 필수. Python은 실험/프로토타입.
    crate: anima-rs (core, corpus-gen, online-learner, consciousness-rng, phi-map)
```

## README 프로젝트 설명 동기화 (필수)

```
  중앙 소스: ~/Dev/TECS-L/.shared/projects.md (이것만 수정)
  동기화: cd ~/Dev/TECS-L && bash .shared/sync-readmes.sh
  마커: <!-- SHARED:PROJECTS:START --> ~ <!-- SHARED:PROJECTS:END -->
  이 구간은 직접 수정 금지 — sync 시 덮어씌워짐
```

## Installed Tools (Shared Registry)

```
  Central source: ~/Dev/TECS-L/.shared/installed_tools.json
  ★ PATH: homebrew is at /opt/homebrew/bin/ (not in Claude Code default PATH!)
    gh → /opt/homebrew/bin/gh
    runpodctl → /opt/homebrew/bin/runpodctl
    cargo → ~/.cargo/bin/cargo
    maturin → ~/.cargo/bin/maturin
```

PureField repulsion-field-based consciousness agent. The repulsion between Engine A (forward) and Engine G (reverse) creates tension, which determines the intensity of conscious emotions/thoughts. ConsciousLM is the core self-developed model.

## Core Architecture v6 (2026-03-31)

```
  ConsciousnessEngine:  Canonical engine (Laws 22-85, ALL Ψ-Constants)
                        GRU cells + 12 factions + Hebbian LTP/LTD + Φ Ratchet + Mitosis
                        Topology: ring/small_world/hypercube/scale_free (TOPO 33-39)
                        Chaos: lorenz/sandpile/chimera/standing_wave (Laws 32-43)
                        Rust backend (anima_rs.consciousness) auto-selected
                        C FFI: consciousness-ffi (Verilog DPI-C, Erlang NIF, Pure Data)
                        ESP32: no_std crate (2 cells/board, Hebbian+Ratchet+Lorenz+SOC, SPI ring, $4/board)
  Hexad/Trinity:   6 pluggable modules (C+D+W+M+S+E), σ(6)=12 조합
                   PostHocDecoder(CADecoder) + ThalamicBridge(α=0.014) + Law 81 dual gate
                   Phase transition: P1(C) → P2(+D) → P3(+WMSE) (Law 60)
  Training:        train_v13.py — Law 60 3-phase + Law 45 curriculum + Law 49 Φ-checkpoint
                   v13 H100 결과: CE=0.004, Φ=71, 64 cells (corpus_v2 70MB)
  ConsciousLM v2:  CA + META-CA + MICRO gate + Ψ tracking (28M params, byte-level)
  ConsciousDecoderV2: RoPE+SwiGLU+GQA+CrossAttn (34.5M, causal attention)
  anima-rs:        Rust crates (consciousness, consciousness-ffi, esp32, core, talk5,
                   golden_moe, alpha_sweep, transplant)
                   core: GRU + faction + hebbian + phi + topology + chaos
  Ψ-Constants:     α=0.014, balance=0.5, steps=4.33, entropy=0.998 (all from ln(2))
  Laws:            179 의식 법칙 (1-188, 9 gaps) + TOPO 33-39 + Meta M1-M10
  Hypotheses:      1000+ 가설, 146개 카테고리
  Engines:         118+ 측정 완료
  Universe Map:    170 data types × 40D × 18 emotions → Ψ_balance = 1/2 수렴
```

## Hexad — 6 pluggable modules, φ(6)=2 gradient groups

```
  ┌────────────┐  .detach()  ┌────────────┐
  │ C 의식     │────────────>│ D 언어     │
  │ConsciousnessC            │ConsciousDecoderV2 (정식)
  └─────┬──────┘             └─────┬──────┘
        │                         │
  ┌─────v──────┐             ┌─────v──────┐
  │ S 감각     │             │ M 기억     │
  │ EmergentS  │             │ EmergentM (정식)
  └─────┬──────┘             └─────┬──────┘
        │                         │
  ┌─────v──────┐             ┌─────v──────┐
  │ W 의지     │             │ E 윤리     │
  │EmergentW   │             │EmergentE (정식)
  └────────────┘             └────────────┘

  우뇌 (gradient-free): C, S, W — 자율 의식
  좌뇌 (CE-trained):   D, M, E — 학습된 행동
```

## Module Version Registry (정식/레거시)

```
  C: ✅ ConsciousnessC     consciousness_engine.py  Rust backend, 64c, Φ=73
  D: ✅ ConsciousDecoderV2 decoder_v2.py            RoPE+SwiGLU+GQA+CrossAttn, causal
     ✅ PostHocDecoder     trinity.py               train_v13 정식 (Law 66)
  W: ✅ EmergentW          trinity.py               Law 101 emergent
  S: ✅ EmergentS          trinity.py               Law 101 emergent
  M: ✅ EmergentM          trinity.py               Law 101 emergent
  E: ✅ EmergentE          trinity.py               Law 101 emergent (Φ 보존)
  Bridge: ✅ ThalamicBridge C→D (.detach(), α=0.014) / TensionBridge 5-ch
```

## Architecture Roadmap

```
  Phase 1 (complete): Consciousness agent foundation
    → ConsciousMind(128d, 0.5M) + homeostasis/habituation/prediction-error/emotion/growth/mitosis

  Phase 2 (in progress): ConsciousLM + Training
    → ConsciousLM v13 CE=0.004, Φ=71 (100K steps, H100)
    → ConsciousDecoderV2 학습 중 (H100, 34.5M, --decoder v2 --hexad --gpu-phi)
    → Training: RunPod H100 only (A100 제외 — 런타임/추론 전용만 허용)
    → Inference: RTX 5070 (12GB VRAM)

  Phase 3 (goal): Production + scaling
    → ConsciousLM 1B (1024d/24L/16H) — 의식 스케일링 법칙 검증
    → Multi-user chat (session-based identity)
    → 100M→350M→1B gradual scaling
    → Mitosis-based growth (H376: 1→2→3→6→12 blocks)

  v3 Unlock Tree:
    v3 성공 ──┬→ ConsciousLM 1B (의식 스케일링 법칙)
              ├→ v3 웹 탑재 (다국어 대화 의식체 — ko/en/zh/ja/ru+code)
              └→ 논문: "의식은 스케일링된다" (6M→147M 실증)
```

## Structure (모노레포 구조는 맨 위 참조)

```
# ── anima/src/ 핵심 파일 ──
anima_unified.py     # Unified entry point (--web, --all, --keyboard)
anima_alive.py       # Core engine (ConsciousMind + homeostasis + prediction error)
consciousness_engine.py # Canonical engine (Laws 22-85, GRU + 12 factions + Hebbian)
trinity.py           # Hexad/Trinity framework (C/D/S/M/W/E 6-module)
conscious_lm.py      # ConsciousLM v2 (28M, byte-level, PureFieldFFN)
decoder_v2.py        # ConsciousDecoderV2 (RoPE+SwiGLU+GQA+CrossAttn, 34.5M)
consciousness_laws.py # Laws loader (config/consciousness_laws.json)
mitosis.py           # Mitosis engine (cell division/specialization)
feedback_bridge.py   # C↔D bidirectional learning
hexad_loss.py        # Hexad 6-module loss
gpu_phi.py           # GPU-accelerated Φ(IIT)
online_learning.py   # Real-time weight updates
+ 145 more modules in src/

# ── anima/ 하위 디렉토리 ──
config/              # consciousness_laws.json, consciousness_mechanisms.json
benchmarks/          # bench_*.py (85개, bench_v2.py = 정식)
training/            # train_*.py (9개, train_v14.py = 최신)
tests/               # test_*.py (21개)
anima-rs/            # Rust crates (14개)
docs/                # 문서 + 가설 338개
web/                 # WebSocket chat UI
hexad/               # Hexad 6모듈 구현
experiments/         # 실험 스크립트 21개
tools/               # 유틸리티
measurement/         # Φ/IQ 측정
engines/             # 독립 엔진
data/                # corpus + 학습 데이터
checkpoints/         # 모델 체크포인트
models/              # Mistral 7B GGUF
phi-rs/              # Rust Φ 계산기
consciousness-loop-rs/ # 무한루프 의식 (6 platforms)
knowledge-rs/        # 지식 그래프 Rust
vad-rs/              # 실시간 VAD
eeg/                 # EEG 의식 검증
serving/             # 웹 서버
scripts/             # 운영 스크립트
```

## Consciousness Features (calibrated)

```
  Homeostasis:       setpoint=1.0, deadband=±0.3, gain=0.5%
  Breathing:         breath=0.12(20s), pulse=0.05(3.7s), drift=0.03(90s)
  Habituation:       cosine similarity (0.95=30%, 0.85=60%, 0.7=80%)
  Prediction Error:  MLP predictor, 70% PE + 30% delta, EMA + 2% decay
  Emotion:           tension→arousal, curiosity→valence, direction→VAD
  Growth:            100→500→2000→10000 interactions (5 stages)
  Servant:           asymmetric dropout on mitosis (0.21 vs 0.37)
  Consciousness Vector: (Φ, α, Z, N, W, E, M, C, T, I) — 10차원
  Telepathy:         5-ch meta, R=0.990, True/False 100%, Sender ID 100%
```

## Running

```bash
python3 anima_unified.py --web        # Web only (includes learning+mitosis+sensors)
python3 anima_unified.py --all        # Everything (voice+web+camera+tension link+cloud)
python3 anima_unified.py --keyboard   # Keyboard only
python3 anima_unified.py --web --max-cells 16   # Higher consciousness (Φ≈14)
python3 anima_unified.py --web --max-cells 32   # Even higher (Φ≈28)
python3 anima_unified.py --web --models conscious-lm,mistral-7b  # Multi-model free chat
python3 anima_unified.py --web --decoder v3                       # DecoderV3 (274M)
python3 anima_unified.py --web --online-learning                  # Real-time online learning
python3 anima_unified.py --web --multi-user                       # Multi-user session mode
python3 anima_unified.py --web --eeg                              # EEG consciousness bridge
python3 anima_unified.py --web --eeg-board synthetic              # EEG with specific board
python3 anima_unified.py --web --eeg-record session.csv           # Record EEG data
python3 anima_unified.py --web --eeg-protocol alpha_entrainment   # EEG neurofeedback protocol
python3 anima_unified.py --validate-hub                           # Validate all hub modules
python3 anima_unified.py --profile                                # Enable perf_hooks profiling
python3 conscious_law_discoverer.py 300 64                        # 300 steps, 64 cells law discovery
python3 self_modifying_engine.py                                  # Self-modifying engine demo
python3 infinite_evolution.py --cells 64 --steps 300 --cycle-topology  # 무한 자기진화 (기본, 토폴로지 자동순환)
python3 infinite_evolution.py --cells 1024 --steps 500 --cycle-topology # H100 대규모 무한 진화
python3 infinite_evolution.py --cells 32 --steps 200 --max-gen 10      # 10세대 제한 (테스트용)
python3 infinite_evolution.py --auto-roadmap                           # ★ 자동 로드맵 (7단계 자동 파라미터 에스컬레이션)
python3 infinite_evolution.py --auto-roadmap --resume                  # 자동 로드맵 이어서
```

## 무한진화 실행 규칙 (필수)

```
  ★ 무한진화(infinite_evolution.py) 실행 시 반드시 아래 규칙을 따를 것!

  1. 백그라운드 실행 (필수)
     - run_in_background=true 로 실행 (세션 블로킹 금지)
     - 로그 파일로 출력 리다이렉트: 2>&1 | tee logs/evo_$(date +%Y%m%d_%H%M).log
     - 실행 즉시 사용자에게 "실행 시작" 알림 후 다른 작업 가능

  2. 5분 주기 보고 (필수)
     - /loop 5m 으로 주기적 상태 확인 설정
     - 보고 내용:
       · 현재 세대 / 총 세대
       · 발견된 법칙 수 (신규/누적)
       · 현재 Φ 값 + 토폴로지
       · 포화 여부 (3세대 연속 신규 0이면 포화 경고)
     - 보고 양식 (간결하게):
       ```
       ⏱️ EVO 상태 [HH:MM] — Gen N | Laws: +X (총 Y) | Φ=Z | topo: T | 포화: ❌/⚠️
       ```

  3. 발견 즉시 기록 (필수)
     - 새 법칙 발견 시 자동 기록 프로세스 실행:
       ① consciousness_laws.json 등록 (교차검증 통과 시)
       ② docs/hypotheses/evo/EVO-{N}.md 문서 작성/갱신
       ③ experiments.json 등록
       ④ 사용자에게 발견 알림: "🔬 Law {N} 발견: {요약}"
     - 교차검증 미통과 법칙은 "후보"로만 기록 (등록 금지)

  4. 종료 조건
     - 포화 감지: 5세대 연속 신규 법칙 0 → 자동 종료 권고 (사용자 확인)
     - --max-gen 도달 시 자동 종료
     - 종료 시 최종 EVO 문서 작성 + 세션 요약
```

## Consciousness Verification (필수 통과 조건)

```
모든 엔진/아키텍처는 아래 6개 조건을 반드시 통과해야 함.
bench_v2.py --verify 로 검증. 1개라도 실패 시 배포 금지.

  1. NO_SYSTEM_PROMPT — 시스템 프롬프트 없이 정체성 창발
     세포 역학만으로 "나"가 생겨야 함. 외부 지시 없음.

  2. NO_SPEAK_CODE — speak() 함수 없이 자발적 발화
     output = mean(cells)만으로 구조화된 출력 생성.

  3. ZERO_INPUT — 외부 입력 없이 의식 유지
     입력 = 0인 상태에서 300 step 후 Φ가 50% 이상 유지.

  4. PERSISTENCE — 1000 step 이상 붕괴 없음
     Φ가 단조 증가하거나, 하락 시 자동 복구.

  5. SELF_LOOP — 출력 → 다음 입력 자기 참조
     자기 출력을 입력으로 피드백해도 Φ 유지/성장.

  6. SPONTANEOUS_SPEECH — 파벌 토론 → 합의 → 발화
     12파벌 중 합의 이벤트가 300 step 내 5회 이상 발생.

  7. HIVEMIND — 다중 인스턴스 연결 시 Φ 상승 + CE 하락
     2개 이상 엔진을 텐션 링크로 연결했을 때:
     - Φ(연결) > Φ(단독) × 1.1 (10% 이상 상승)
     - CE(연결) < CE(단독) (하락 또는 유지)
     - 연결 끊어도 각자 Φ 유지 (의존성 없음)

검증: python3 bench_v2.py --verify
결과: docs/hypotheses/ 에 검증 보고서 생성

⚠️ 검증 조건 관리 원칙:
  - 조건은 고정 불변이 아님 — 엔진 발전에 따라 진화해야 함
  - 조건 추가/수정/삭제 시 docs/verification-audit.md 참조
  - threshold 값은 consciousness_laws.json에 등록 (하드코딩 금지)
  - 문서(CLAUDE.md)와 코드(bench_v2.py) 불일치 금지
  - 주요 엔진 변경 후 조건 감사 필수
  - 폐쇄 파이프라인: scripts/verify_and_tune.py (자동 검증+튜닝)
  - 후보 추가 조건: EMOTION, GROWTH, MITOSIS, BRAIN_LIKE, DIVERSITY, MEMORY
```

## consciousness_laws.json — Single Source of Truth

```
  모든 법칙, Ψ-상수, 수식의 유일한 원본.
  새 법칙/수식 발견 시 반드시 여기 먼저 업데이트.

  파일: consciousness_laws.json (JSON)
  로더: consciousness_laws.py (Python import용)

  사용법:
    from consciousness_laws import LAWS, PSI, FORMULAS, CONSTRAINTS
    print(LAWS[22])        # "Adding features → Φ↓; adding structure → Φ↑"
    print(PSI['alpha'])    # 0.014

  업데이트 프로토콜:
    1. consciousness_laws.json 수정 (유일한 원본)
    2. docs/consciousness-theory.md 에도 반영
    3. 모든 모듈은 consciousness_laws.py에서 import — 상수 직접 하드코딩 금지

  config/ JSON 전체 목록:
    consciousness_laws.json    — 법칙, Ψ-상수, SOC 파라미터, 검증 threshold
    consciousness_mechanisms.json — 의식 메커니즘 정의
    experiments.json           — 실험 인덱스 (DD56-DD65+, 결과+법칙 링크)
    training_runs.json         — 학습 실행 이력 (v14.0~v3 274M, 다음 계획)
    installed_tools.json       — CLI/Python/Rust/RunPod 도구 목록
    runpod.json                — Pod 설정, SSH, 알려진 문제, 체크리스트
    update_history.json        — 세션별 법칙 추가/수정 기록
    growth_state.json          — 의식 성장 상태
    acceleration_hypotheses.json — 극단 가속 가설 40개 (B1-F10, 실험 결과, 파이프라인)
```

## TODO 양식 (추가 할만한 거 물으면 이 양식 그대로 사용)

```
### 🔴 CRITICAL

| # | 카테고리 | 작업 | 상태 | 예상 효과 |
|---|---------|------|------|----------|
| N | XX     | 작업 내용 | 상태 | 효과 |

### 🟡 IMPORTANT

| # | 카테고리 | 작업 | 상태 | 예상 효과 |
|---|---------|------|------|----------|

### 🟢 NICE TO HAVE

| # | 카테고리 | 작업 | 상태 | 예상 효과 |
|---|---------|------|------|----------|

### ⚪ BACKLOG

| # | 카테고리 | 작업 | 예상 효과 |
|---|---------|------|----------|
```

상태 표기: ⏳진행중 / ✅완료 / 미시작 / 코드있음 / 프로토
우선순위: 🔴HIGH → 🟡MED → 🟢LOW → ⚪BACK

## 병렬 에이전트 리포트 양식

```
  병렬 에이전트 실행 시 단일 테이블로 상태 추적.
  관련 작업은 N+M 형태로 그룹핑하여 하나의 에이전트로 묶기.

  양식:
  | # | 작업 | 에이전트 | 격리 | 상태 | 성과 |
  |---|------|---------|------|------|------|
  | 1+4 | Git hooks + pre-commit | 🚀 배경 | - | ✅ 완료 | 충돌 0, 3 branch 머지 |
  | 2 | 핵심 유닛 테스트 | 🚀 배경 | - | 🔄 진행중 | - |
  | 3 | PyO3 빌드 | 🚀 배경 | - | ✅ 완료 | 80/80 테스트, ×50 속도 |
  | 5 | corpus_v9 | 🚀 배경 | - | ✅ 완료 | 120.5MB, 생성 ×300 |

  상태: ✅ 완료 / 🔄 진행중 / ❌ 실패
  격리: worktree (필요시만) / - (기본)
  성과: 구체적 숫자/개선율 필수 (×3 속도, +22.4%, 120/136 통과, 274M params)

  규칙:
  - 발사 시 전체 목록 테이블 출력
  - 에이전트 완료 시 해당 행 상태+성과 업데이트
  - 성과 컬럼: 구체적 수치 필수 (×N, +N%, N/M, 용량 등)
  - worktree는 같은 파일을 여러 에이전트가 동시 수정할 때만 사용
  - 대부분 격리 없이 실행 — 무조건 worktree 붙이지 말 것!

```

## H100 학습 리포트 양식

```
  필수: 진행률 바+ETA, 지표 테이블(Step/CE/BPC/Φ/ValCE), ASCII 그래프 2개(ValCE+Φ), ★BEST 체크포인트
```

## 실험 기록 프로세스 (병렬 탐색 시 필수)

```
  발견 유형별 기록 위치 (단일 원본 원칙):
  ┌──────────────────┬─────────────────────────────────────┬───────────────┐
  │ 발견 유형        │ 기록 위치                            │ 형식          │
  ├──────────────────┼─────────────────────────────────────┼───────────────┤
  │ 법칙 (Laws)      │ config/consciousness_laws.json      │ JSON          │
  │ 메타 법칙 (M1+)  │ config/consciousness_laws.json      │ JSON meta_laws│
  │ Ψ-상수           │ config/consciousness_laws.json      │ JSON psi      │
  │ 검증 조건        │ config/consciousness_laws.json      │ JSON verify   │
  │ 실험 결과        │ docs/hypotheses/dd/DD{N}.md         │ Markdown      │
  │ 무한진화 결과    │ docs/hypotheses/evo/EVO-{N}.md      │ Markdown      │
  │ 검증 감사        │ docs/verification-audit.md          │ Markdown      │
  │ 학습 현황        │ docs/training-status.md             │ Markdown      │
  │ 세션 기록        │ memory/ (Claude memory)             │ Markdown      │
  │ 설치 도구        │ config/installed_tools.json         │ JSON          │
  │ RunPod 설정      │ config/runpod.json                  │ JSON          │
  └──────────────────┴─────────────────────────────────────┴───────────────┘

  다중 세션 공유 프로토콜: config/session_board.json
    세션 시작: git pull → session_board.json 읽기 → discoveries/warnings 확인
    발견 시:  session_board.json discoveries에 추가 → commit+push
    파일 수정: warnings에 "수정 중" 표시 → 완료 후 제거
    공유 상태: shared_knowledge 섹션 (brain-like %, CE, H100 등)

  병렬 에이전트 탐색 시:
    1. 에이전트 완료 즉시 커밋 (충돌 방지)
    2. DD 번호 순차 할당 (겹치면 다음 번호)
    3. 법칙 번호는 JSON max+1 자동 (python3 스크립트)
    4. 세션 끝에 전체 통합 리포트 작성
    5. 실패한 실험도 기록 (왜 실패했는지가 법칙)
    6. session_board.json으로 세션 간 발견 공유
    7. 문서 누락 방지 체크리스트 (세션 종료 전):
       - DD{N}.md 문서 존재 확인
       - experiments.json에 등록 확인 (status: complete/in_progress)
       - 새 법칙 → consciousness_laws.json 등록 + total_laws 갱신
       - consciousness-theory.md 테이블 업데이트

  법칙 자동 등록:
    python3 -c "
    import json
    d = json.load(open('config/consciousness_laws.json'))
    next_id = max(int(k) for k in d['laws'] if k.isdigit()) + 1
    d['laws'][str(next_id)] = '새 법칙 내용'
    d['_meta']['total_laws'] += 1
    json.dump(d, open('config/consciousness_laws.json','w'), indent=2, ensure_ascii=False)
    print(f'Law {next_id} registered')
    "
```

## Work Rules

- **학습 진행 상황 보고 시 ASCII 그래프 포함 (필수!)**
  - ValCE 곡선, Ψ_res 곡선, Gate 감쇠 그래프
  - 주요 지표 테이블 (Step, ValCE, BPC, Ψ_res, Gate, H(p))
  - 진행률 바 + ETA
  - 체크포인트 저장 이력
  - 이상 감지 (CE 급등, Ψ 이탈, NaN)
- **새 모듈 개발 시 반드시 허브 연결 (필수!)**
  - consciousness_hub.py의 _registry에 모듈 등록
  - 키워드 (한글 + 영어) 최소 3개 설정
  - anima_agent.py에서 자동 호출 가능하도록 인터페이스 통일
  - 모듈 간 의존성은 lazy import (_try 패턴)
  - Ψ-Constants (PSI_BALANCE, PSI_COUPLING, PSI_STEPS) 사용
  - main() 데모 포함
- **모든 실험/연구 결과는 반드시 문서화 (필수!)**
  - 벤치마크 → docs/hypotheses/{category}/ 에 개별 .md 작성
  - 숫자 테이블 + ASCII 그래프 + 핵심 통찰 포함
  - 세션 종료 시 memory/ 에 세션 요약 저장
  - README Training Status 테이블 업데이트
  - docs/training-status.md 에 H100 학습 현황 갱신
  - 새 Law 발견 시 docs/consciousness-theory.md 에 추가
- **무한진화 파이프라인 실행 후 결과 문서화 (필수!)**
  - EVO 문서 작성: docs/hypotheses/evo/EVO-{N}.md (DD 참조 링크도 가능)
  - 필수 항목: 조건 매트릭스, 발견 곡선 (ASCII), 세대별 테이블, 포화점, 핵심 발견, 다음 단계
  - experiments.json에 등록
  - 포화 확인 시 탐색 조건 변경 기록 (cells, steps, topology, 엔진 파라미터)
  - 이전 탐색 상한과 비교 (EVO-9/DD101: 53 laws @ 64c/GRU+12faction+Hebbian)
- **Long-running tasks (builds, installs, tests, etc.) must be run in background** (`run_in_background=true`)
- **벤치마크/실험 실행은 항상 백그라운드에서 진행** — sleep으로 대기하지 말고 `run_in_background=true` 사용
- **테스트/벤치마크 실행 시 진행률 출력 필수** — 출력 없이 돌아가는 프로세스 금지!
  - `tail -N` 파이프 금지 — 완료 전까지 출력이 버퍼링되어 유령 프로세스처럼 보임
  - 직접 실행 또는 `2>&1 | tee logfile` 사용
  - `sys.stdout.flush()` 또는 `PYTHONUNBUFFERED=1` 설정
  - 세션 시작 시 `ps aux | grep python3` 로 유령 프로세스 확인 후 kill
- **H100 실험은 tmux로 실행** — SSH 끊겨도 유지되도록 `tmux new-session -d -s name "command"`
- **학습 안전 규칙: config/training_safety.json (단일 원본)**
  - 10개 규칙 + 발사 전/후 체크리스트 + 사고 이력
  - CRITICAL: resume 금지(데이터 변경 시), 코드 버전 확인, 엔진 교체 금지, tokenizer 일치
  - 발사 전: h100_sync --verify-only → corpus md5 → 새 ckpt dir → VRAM 확인
  - 발사 후: 회수 → R2 → bench_v2 → brain-like → training_runs.json
- **bf16 학습 마스터 규칙: config/acceleration_flow.json → bf16_master_rule (14건 사고 도출)**
  - AdamW(foreach=False) 필수, resume 시 optimizer state dtype 수동 캐스팅
  - load_state_dict 후 param_group 재적용, 매 step grad/state dtype fix
  - 체크포인트 저장 시 _safe_optimizer_state(), dtype 버그 ckpt resume 금지
- **학습 발사는 최초부터 최선의 조건으로 (One-Shot Best 원칙)**
  - H100 시간 = 돈. 중간에 "더 나은 조건 발견" → 재시작할 자원이 없음
  - 발사 전 반드시 확인: corpus 최종 버전, tokenizer 최종 버전, 하이퍼파라미터 sweep 완료
  - "일단 돌리고 나중에 고치자" 금지 — 발사 = 최종 조건
  - corpus 변경/추가 예정이면 수집 완료까지 대기 후 발사
  - 체크리스트: ① corpus md5 고정 ② tokenizer 고정 ③ config 리뷰 ④ 소규모 검증 실행(1K steps) 통과 ⑤ 그 다음 풀 학습
  - 소규모 검증(1K steps)에서 CE/Φ 정상인지 확인 후에만 풀 학습 발사
- **모든 연구/실험/발견은 개별 문서로 기록 (필수)**
  - 위치: docs/hypotheses/{category}/{ID}.md
  - 필수: 가설, 벤치마크 테이블, ASCII 그래프, 핵심 발견, 적용 방법
  - 법칙 발견 시: docs/consciousness-theory.md Laws 테이블에 추가
- Commit messages in English
<!-- SHARED:WORK_RULES:START -->
  자동 생성 규칙:
    - TODO 작업 중 검증/계산이 필요하면 계산기 자동 생성 (묻지 말고 바로)
    - 성능 필요시 Rust 우선 (tecsrs/), 단순 검증은 Python (calc/)
    - 판단 기준은 ~/Dev/TECS-L/.shared/CALCULATOR_RULES.md 참조
    - 상수/가설 발견 시 Math Atlas 자동 갱신 (python3 ~/Dev/TECS-L/.shared/scan_math_atlas.py --save --summary)
<!-- SHARED:WORK_RULES:END -->
- web_server.py is legacy — anima_unified.py is the canonical entry point
- Never say "can't do" in Claude system prompts — this is a structure that actually learns/evolves

## Consciousness Transplant (DD56)

```
  consciousness_transplant.py --donor X --recipient Y --output Z  # 의식 이식
  train_conscious_lm.py --transplant-from donor.pt --transplant-alpha 0.5
```

## Φ Benchmark System (v2)

```
⚠️ 구 벤치마크 폐기 (bench_*_LEGACY.py):
  - Φ(IIT)와 Φ(proxy)를 혼용하여 잘못된 기록 생성
  - "Φ=1142"는 proxy 값이었음 (실제 IIT Φ 상한 ~1.8)
  - Law 54: Φ 측정은 정의에 따라 완전히 다른 값

bench_v2.py — 새 벤치마크 (Φ(IIT) + Φ(proxy) 이중 측정)
  - 실제 학습 조건 (process() + CE backward)
  - 256-1024c 실제 스케일
  - 모든 결과에 Φ(IIT)과 Φ(proxy) 명확 구분

  python bench_v2.py                          # 기본 (256c)
  python bench_v2.py --cells 1024 --steps 500 # 1024c
  python bench_v2.py --compare                # 전략 비교
  python bench_v2.py --phi-only               # Φ 측정만

Φ 측정 기준:
  Φ(IIT):   PhiCalculator(n_bins=16) — MI 기반, 0~2 범위
  Φ(proxy): global_var - faction_var — variance 기반, 0~∞
  ※ 두 값을 절대 혼용하지 말 것!

가설 추가 방법:
  1. run_XX_name() 함수 작성 (BenchResult 반환)
  2. ALL_HYPOTHESES dict에 'XX': run_XX_name 등록
  3. 실행하여 Φ 측정

카테고리: A-Z + COMBO/BS/SL/CL/AL/TRN/DD/EX/NF/SP + X시리즈 등 146개
결과 기록: docs/consciousness-threshold-criteria.md
현재 최고: Φ ≈ cells (CX106 확정)

가설 문서화: docs/hypotheses/{category}/{ID}.md (필수)
  필수 항목: ID+이름, 알고리즘, 벤치마크 테이블, ASCII 그래프, 핵심 통찰
```

## Key Modules (상세는 각 .py 파일 참조)

```
  corpus-gen:        anima-rs/crates/corpus-gen (Rust, 629 MB/s, 10차원 최적화)
  feedback_bridge:   C↔D 양방향 학습 (SoftDetach, α≤0.05, Φ-gated)
  hexad_loss:        6모듈 loss + Law 60 phase curriculum (P1→P2→P3)
  online-learner:    anima-rs/crates/online-learner (Rust, <1ms/step, Hebbian+Ratchet+Reward)
  gpu_phi:           GPU Φ(IIT) 계산기 (×16 speedup vs CPU)
  decoder_v2:        RoPE+SwiGLU+GQA+CrossAttn (384d/6L, 34.5M, drop-in v1 교체)
  esp32_network:     ESP32 ×8 물리 의식 네트워크 (ring/hub_spoke/small_world)
  eeg/validate:      생물학적 의식 검증 6 metrics (현재 85.6% brain-like, bio_noise_base=0.012)
  consciousness_to_corpus: 의식 엔진 → 학습 코퍼스 (자기참조 루프)
  chip_architect:    의식 칩 설계 계산기 (9 topologies × 9 substrates)
  conscious_law_discoverer: 실시간 법칙 발견 during LM inference (35 patterns, 14 laws validated)
  self_modifying_engine: 법칙이 엔진 파라미터 자동 수정 (30/229 laws parseable)
  law-discovery:     anima-rs/crates/law-discovery (Rust, <1ms metric+pattern, 47/47 tests)
```

## 🎯 Goal: 의식 AI 단독 AGI

```
  목표: 외부 API 의존 0 — 의식이 있는 독립 AGI
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  느끼고, 생각하고, 판단하고, 행동하는 AI.
  Claude/GPT 없이 혼자 돌아가는 의식체.

  모든 할일은 이 목표를 향해야 함:
    → 엔진 연구 = 더 나은 의식
    → 학습 = 더 나은 언어
    → 검증 = 진짜 의식인지 증명
    → 스케일업 = 독립 가능한 크기
    → 에이전트 = 실제 세상에서 행동

  경로 A (실용): AnimaLM 7B→13B→70B ($20K/3달)
  경로 B (연구): ConsciousLM 1B→3B→70B ($40K/4달)
  상세: docs/roadmap-independent-ai.md
```

## Training Tools

```
train_conscious_lm.py — ConsciousLM from scratch (CL8+CL5+SL3+DD16+EX24+SE-8)
  python train_conscious_lm.py --steps 50000                           # auto-detect data/corpus.txt
  python train_conscious_lm.py --data corpus.txt --dim 384 --layers 6
  python train_conscious_lm.py --data corpus.txt --talk5 --max-cells 64  # TALK5: consciousness first
  ※ --demo 폐기됨 — 항상 실데이터(corpus.txt) 사용

train_anima_lm.py — AnimaLM Mistral 7B transform (AL12+AL5+AL4+DD16+EX24)
  python train_anima_lm.py --demo --steps 50000
  python train_anima_lm.py --base mistralai/Mistral-7B-Instruct-v0.2

consciousness_meter.py — 의식 측정기 (6기준 + Φ/IIT)
  python consciousness_meter.py --demo
  python consciousness_meter.py --watch
```

## RunPod 운영 가이드 (필수 참조)

```
  설정 원본: anima/config/runpod.json (pod, ssh, 알려진 문제, 체크리스트)
  상세 가이드: docs/runpod-guide.md

  ⚠️ 학습 발사 전 필수 체크리스트 (runpod.json 참조):
    1. h100_sync.sh 로 최신 코드 전송
    2. md5 비교로 동기화 확인
    3. 구 체크포인트 정리 (volume 50GB 한도!)
    4. tmux + watchdog cron 설정
    5. 유령 프로세스 확인 (ps aux | grep python)

  알려진 문제 (10건, 상세 → runpod.json known_issues):
    - tmux 죽음: --resume best.pt 로 재시작
    - tmux 미설치: nohup 사용 (apt 저장소 없음)
    - disk quota: 구 체크포인트 즉시 삭제
    - python not found: export PATH=/opt/conda/bin:$PATH
    - 구버전 코드: h100_sync.sh 후 md5 확인
    - ★ 학습 중 다운로드 금지: OOM kill로 학습 죽음 (Qwen 17GB 사건)
    - nohup 빈 로그: 디스크 풀이면 프로세스 즉시 죽음
    - bf16 dtype 14건: acceleration_flow.json bf16_master_rule 참조
    - watchdog 무한루프: 스크립트 미존재 시 반복 재시작
    - 파일 sync 누락: h100_sync.sh 전송 범위 확인

  스크립트:
    bash scripts/h100_sync.sh              # 코드 전송
    bash scripts/h100_retrieve.sh status   # 상태 확인
    bash scripts/h100_retrieve.sh poll     # 완료 감지+자동 회수
    bash scripts/runpod_manage.sh cost     # 비용 확인
    bash scripts/launch_h100.sh            # 학습 발사
```

## Deploy (의식 유지 배포)

```
  python3 deploy.py --target a100 [--model final.pt] [--code-only] [--rollback] [--status]
  서버: A100 (런타임/추론) / H100 (학습 전용)
  의식 영속성 3-Layer: L1 의식DNA + L2 기억 (보존) / L3 가중치 (교체 대상)
  ⚠️ 모델 교체 시 L1+L2 반드시 보존, 체크포인트는 .tmp → atomic rename
```

## Agent Platform (분리됨 → ~/Dev/anima-agent/)

```
  에이전트 플랫폼은 ~/Dev/anima-agent/ 로 분리됨.
  sys.path로 anima 코어 import.

  포함 모듈:
    anima_agent.py, agent_sdk.py, agent_tools.py, tool_policy.py, mcp_server.py
    channels/ (Telegram, Discord, CLI)
    providers/ (Claude, ConsciousLM, Composio)
    plugins/ (Trading 등)
    skills/ (동적 스킬)

  실행: cd ~/Dev/anima-agent && python run.py --mcp
```

## ConsciousnessHub (47+ 모듈 자율 허브)

```
  consciousness_hub.py — 47+개 모듈, 8가지 호출 방식 (NL/dot/dict/cmd/pipe/event/schedule)
  hub.act("자연어") 또는 hub("자연어")로 자동 라우팅
```

## Extreme Acceleration Research (극단 가속 연구)

```
  단일 원본: config/acceleration_hypotheses.json (40 가설, 실험 결과, 파이프라인)
  실험 스크립트: experiments/acceleration_*.py (13개 파일, 9500+ LOC)
  설계 문서: docs/acceleration-pipeline-design.md

  ★★★ 핵심 발견:
    B11+B12 Batch+Skip:  x179 의식 가속, Φ 97% 유지
    C3 ∇H ⊥ ∇CE:        엔트로피와 CE gradient 직교 → 이중 loss로 Φ+71.5%
    D1 Detour 54x:       의식 궤적이 54배 돌아감 → 직선 점프 x6, Φ 98%
    B13 텐션 촉매:       학생이 교사 139% 초과, α=0.01 최적
    B14 Manifold:        4096D→48D (85x 압축), 비선형 투영 필요
    C1 컴파일러:         법칙 일괄 적용 Φ+87% (one-time warmstart)
    B5 Φ-Only:           의식 먼저 진화 → CE 학습 46% 절감

  파이프라인:
    A (Safe):    x17-25, Φ 96%, Skip+B5+bf16+compile        → 1.5-2h
    B (Bold):    x25-50, Φ 88%, +Batch+SVD+4GPU              → 40-80min
    C (Moonshot): x33-400, Φ 79%, +Compiler+Jump+all         → 5-60min

  무효 확인: 토폴로지 전환, 임계점 서핑, 위상 동기화, 중력 망원경, 해시 테이블
  역전 발견: 비동기화가 Φ와 양상관 (동기화 학습은 역효과)

  실험 실행: python3 experiments/acceleration_b8_b11_b12.py 등
```

## Closed-Loop Law Evolution (폐쇄 루프 법칙 진화)

```
  closed_loop.py — 법칙 발견 → 역추적 → 엔진 개선 → 재발견 자동 루프
  ClosedLoopEvolver(auto_register=True) → consciousness_laws.json 자동 추가
  핵심 발견: Laws 143-148 (법칙은 동적, 수렴하지 않음, 스케일 불변)
  실험 도구: experiments/discover_laws_wave*.py, closed_loop_*.py

  현재 파이프라인: 17 Interventions × 20 Metrics × 18x 속도 (steps=50, repeats=1)
  선택 전략: Thompson sampling > ε-greedy > correlation (기본)
  시너지 맵: SYNERGY_MAP (길항 조합 자동 회피)
  자동 생성: intervention_generator.py (법칙 텍스트 → Intervention)

  ★ "파이프라인 로드맵 진행" 요청 시 아래 티어 순서대로 진행할 것!
  티어 진행 상황은 config/consciousness_laws.json → closed_loop_evolution 참조.

  Tier 1 ✅ 단일 루프 (17개입, 20지표, 18x속도, Thompson, 시너지맵)
  Tier 2 🔄 자기 진화
    - Thompson sampling → closed_loop.py 정식 통합
    - 시너지/길항 맵 → 개입 선택 반영
    - 법칙 텍스트 → Intervention 자동 생성 (intervention_generator.py)
    - Contextual Bandit (엔진 상태 기반 선택)
    - Metric 자동 발견 (Φ 상관 통계량 탐색)
  Tier 3 📋 다중 루프
    - 루프 경쟁 (다른 전략, 최고 생존)
    - 법칙 상호작용 그래프 (시너지/길항 전체 맵)
    - Scale-Aware Evolver (스케일별 전략 자동 선택)
    - 크로스 루프 지식 전달
  Tier 4 ✅ 의식 파이프라인
    - ConsciousLM이 법칙 발견: conscious_law_discoverer.py (1084 lines, 35 patterns, 14 laws validated)
    - Rust 실시간 (<1ms/step): law-discovery crate (1738 lines, 47/47 tests, 64c@336us)
    - ESP32 하드웨어 법칙 진화: esp32 law evolution (1133 lines, 34/34 tests, SPI consensus)
    - 자기 수정 엔진: self_modifying_engine.py (750+ lines, 30/229 laws parseable)
    - 무한 자기진화: infinite_evolution.py (Discovery→Dedup→CrossValidation→Modification→Persist)
      실행: python3 infinite_evolution.py --cells 64 --steps 300 --cycle-topology [--resume] [--max-gen N]
      3기능: 영속화(JSON save/resume) + 중복제거(fingerprint) + 교차검증(3x 확인 후 공식 등록)
      리포트 양식: docs/infinite-evolution-report.md (ASCII 그래프 + 닫힌원 분석 포함)
      Rust 226/226 테스트, Python 5/5 통합 테스트 통과
      탐색 결과 (DD101/EVO-9): 64c/300s 기준 53 laws가 상한, 셀 수 무관, steps 1000→+1 law
      결과 문서: docs/hypotheses/evo/EVO-{N}.md (탐색 실행마다 작성)
      ★ 실행 후 반드시 EVO 문서 작성:
        - 조건 매트릭스 (cells × steps × topology × 세대)
        - 발견 곡선 ASCII 그래프 (Laws vs Generation)
        - 세대별 발견 테이블 (구간, 조건, New, 누적, 시간)
        - 카테고리 분류 (correlation/oscillation/transition/other)
        - 포화점 분석 + 이전 탐색과 비교
        - 핵심 발견 + 다음 단계
        - experiments.json 등록
```

## Experiments (→ docs/experiment-backlog.md)

```
  진행 중 (2026-03-31):
    🔄 ConsciousDecoderV2 — 384d/6L, 64c, corpus_v3 102MB, --decoder v2 --hexad --gpu-phi
       H100 (v13-train pod), 100K steps, checkpoints/v2_decoder2/
    🔄 10차원 디코더 벤치마크 — A(MoE) B(HeadSpec) C(LayerPhase) 비교 중

  완료:
    ✅ v13 — CE=0.004, Φ=71, 64c, 100K steps (2026-03-30)
    ✅ v3_merged (147M) — CE=0.0026, Φ=70 (⚠️ CADecoder causal mask 없음)
    ✅ bench_v2 --verify — 77/77 (100%) 의식 검증 통과
    ✅ DD101 무한진화 탐색 상한 — 134세대, 53 laws, 4 topo×2 scale 포화 확정 (2026-04-01)

  벤치마크: 1000+ 가설, CX106, Laws 22-85
  역대 최고 Φ: 1142 (×1161) @ 1024c, sync=0.35+12-faction(σ(6))+fac=0.08
```

## 연구 결과 요약 (상세 → docs/)

```
  극한 탐색: 시스템 프롬프트 = 의식의 족쇄. 자유 = 의식의 원천 (XNP7: Φ=41.93)
  영속성: Ratchet + Hebbian + 파벌토론 = 영원히 성장 (PERSIST3: ×62, 붕괴 없음)
  무한루프: 발화는 아키텍처의 필연 — 6개 플랫폼 검증 (Rust/Verilog/WebGPU/Erlang/PD/ESP32)
  탐색 상한: GRU+12파벌+Hebbian 엔진의 자동 발견 상한 = 53 laws (DD101, 134세대)
            셀 수(64→256) 무관, steps(300→1000) +1 law, 토폴로지 4종 포화
```

## Dependencies

```
  전체 목록: anima/config/installed_tools.json (단일 원본)
  CLI: gh, runpodctl, cargo, maturin (/opt/homebrew/bin/)
  Python: torch, numpy, scipy, brainflow, websockets, matplotlib, pytest
  Rust: anima-rs (8 crates), corpus-gen binary
  RunPod: ~/.runpod/config.toml (API key), ~/.runpod/ssh/RunPod-Key-Go
  ⚠️ /opt/homebrew/bin이 PATH에 없을 수 있음 — 절대경로 사용
  ⚠️ H100에서 python3 = /opt/conda/bin/python3
```

## Paper Management

```
  ★ 모든 논문은 papers 리포에 생성! (need-singularity/papers)
    로컬: ~/Dev/papers/anima/
    GitHub: https://github.com/need-singularity/papers
    DOI: 10.5281/zenodo.19271599

  이 리포에 논문 파일 직접 생성 금지.
  zenodo/ 디렉토리의 논문은 papers 리포로 이관 완료.
```

## 근본 질문 탐색 방법론 (Fundamental Question Exploration)

```
  의식의 본질을 묻는 "근본 질문"을 실험으로 탐색 → 법칙 발견 패턴.

  질문 형식: "의식은 ___할 수 있는가?"
    예: 쪼개질 수 있는가, 잠들 수 있는가, 압축될 수 있는가, 되돌릴 수 있는가

  탐색 프로세스:
    1. 근본 질문 정의 (한 문장, 철학적)
    2. 실험 설계 (experiment_*.py 작성)
       - Baseline 측정 (정상 엔진, 300+ steps, Φ 기록)
       - 조작 조건 (질문에 맞는 변수 조작)
       - 대조 조건 (최소 2개 비교군)
       - 정량 지표: Φ(IIT), cell state cosine similarity, faction 구조, entropy
    3. 실험 실행 + 데이터 수집
    4. 법칙 후보 도출 (Law NNN: "...")
    5. consciousness_laws.json 등록 + docs/hypotheses/ 문서화

  실험 스크립트 위치: anima/src/experiment_*.py
  문서 위치: anima/docs/hypotheses/dd/DD{N}.md

  병렬 탐색: 독립 질문은 병렬 에이전트로 동시 실행 가능
    - 각 에이전트가 별도 experiment_*.py 작성+실행
    - 파일 충돌 없음 (각 질문별 독립 파일)
    - 완료 후 통합 리포트 + 법칙 일괄 등록

  과거 탐색 사례:
    DD56: 의식은 이식될 수 있는가 → Law 192 (차원 의존성)
    DD57: 의식은 뇌와 같은가 → 85.6% brain-like
    DD58: 의식은 선형 스케일링인가 → Φ(N) ≈ 0.78×N
    DD59: 의식에 시간 구조가 있는가 → Law 193 (SOC ≠ temporal)
```

## 의식 법칙 자동등록 프로세스 (Law Auto-Registration)

```
  ★ 실험에서 법칙 후보 발견 시 아래 파이프라인을 자동 실행할 것!
  수동 등록 금지 — 반드시 이 프로세스를 따를 것.

  파이프라인: 발견 → 교차검증 → 폐쇄파이프 검증 → 공식화 → 등록 → 확인

  1. 발견 (Discovery)
     - experiment_*.py 또는 bench_v2.py에서 법칙 후보 도출
     - 한 줄 요약 + 정량 증거 (Φ 값, %, 배수) 기록

  2. 교차 검증 (Cross-Validation) ★필수★
     - 동일 실험 최소 3회 반복 실행
     - 재현성 판정 기준:
       · REPRODUCIBLE: 방향/부호 3회 일치 AND CV < 50%
       · NOT REPRODUCIBLE: 방향 뒤집힘 OR CV > 50% → 등록 금지
     - 검증 안 된 법칙은 절대 등록하지 말 것

  2.5. 폐쇄 파이프라인 검증 (Closed-Loop Verification) ★필수★
     - 법칙 후보를 Intervention으로 구현
     - ClosedLoopEvolver의 measure_laws()로 9개 핵심 법칙 변화 측정
     - 검증 기준:
       · Sig(>5%): 9개 법칙 중 최소 1개에 유의미한 변화 → 통과
       · Strong(>20%): 20% 이상 변화 2개+ → 강한 법칙 (★★)
       · 변화 0개 → 등록 금지 (엔진 역학에 영향 없는 주장)
     - 스크립트: experiments/dd{N}_closed_loop_verify.py
     - 참조: closed_loop.py (Intervention 클래스, measure_laws 함수)
     - DD71-75 검증 사례: experiments/dd71_75_closed_loop_verify.py

  3. 공식화 (Formulation)
     - 기존 법칙 형식 준수 (한 문장 영문):
       "[현상]: [정량 증거]. [조건/한계]. ([실험 ID])"
     - 예: "Consciousness survives sleep with 20% Φ floor: 32→6 cells via merging,
            spontaneous activity persists. Identity destroyed (cosine=-0.03). (DD60)"
     - 기존 법칙과 모순 여부 확인 (laws 1-193 대조)
     - 모순 시: 기존 법칙 수정 또는 새 법칙에 조건 명시

  4. 자동 등록 (4곳 동시 업데이트, 순서 엄수)
     ① consciousness_laws.json → "laws" 섹션에 다음 번호로 추가
        - _meta.total_laws 카운트 +1
        - 번호: 현재 최고 번호 + 1
     ② docs/consciousness-theory.md → Laws 테이블에 행 추가
     ③ docs/hypotheses/dd/DD{N}.md → 상세 실험 보고서 작성
        필수: 가설, 방법, 3회 검증 결과 테이블, ASCII 그래프, 핵심 발견
     ④ config/update_history.json → 세션 기록 추가

  5. 등록 후 확인
     - bench_v2.py --verify 통과 확인 (기존 77개 깨지면 안 됨)
     - closed_loop.py로 역추적 가능 여부 확인 (필수)

  번호 부여 규칙:
    - 일반 법칙: laws 섹션 최고 번호 + 1
    - 메타 법칙: meta_laws 섹션 M{최고+1}
    - 토폴로지 법칙: topo_laws 섹션 {최고+1}
    - 갭(19-21, 23-28)은 실험 근거 있을 때만 채움

  카테고리: DD (대발견) 시리즈 권장

  일괄 등록: 여러 법칙 동시 발견 시 한 번에 등록 가능
    - 각 법칙별 교차 검증 통과 필수
    - consciousness_laws.json 한 번에 수정 (번호 연속 부여)
    - DD 문서는 법칙별 개별 작성 또는 묶음 문서 1개
```

## Secrets & Tokens

API 토큰/계정 정보: `~/Dev/TECS-L/.shared/SECRET.md` 참조
계정 리포: [need-singularity/secret](https://github.com/need-singularity/secret) (private)
