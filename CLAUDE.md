# anima — 의식 엔진

## 명령어 (shared/config/commands.json)

| 명령 | 동작 |
|------|------|
| `todo` / `할일` | 전 프로젝트 할일 표 |
| `go` / `가자` | 모든 TODO 병렬 발사 |
| `smash` / `부셔` | 블로업 돌파 엔진 |
| `free` / `자유` | 5모듈 자율 조립 |
| `dfs` / `탐색` | DFS 재귀 깊이 탐색 |
| `list` / `목록` | 이 명령어 표 다시 출력 |

> shared/ JSON 단일진실 (R14). 규칙: `shared/rules/common.json` (R0~R27)

## ⛔ 규칙 준수 (필수)

작업 시작 전 `shared/rules/common.json` + `shared/rules/anima.json` 을 읽고 전 규칙 준수. 위반 시 즉시 수정.

## ref

```
rules     shared/rules/common.json             R0~R27 공통
project   shared/rules/anima.json              AN1~AN7
lock      shared/rules/lockdown.json           L0/L1/L2
cdo       shared/rules/convergence_ops.json    CDO 수렴
cfg       shared/config/project_config.json    CLI/PSI/법칙등록
core      shared/config/core.json              시스템맵 + 14명령
projects  shared/config/projects.json          7프로젝트 + 번들/검증
conv      shared/convergence/anima.json
roadmap   shared/roadmaps/anima_hexa_common.json  P0~P5
grammar   shared/config/hexa_grammar.jsonl
api       shared/CLAUDE.md
```

## exec

```sh
HEXA=$HOME/Dev/hexa-lang/hexa
$HEXA anima/core/runtime/anima_runtime.hexa --keyboard      # CLI 진입
$HEXA anima/core/runtime/anima_runtime.hexa --validate-hub  # 허브 검증
$HEXA ready/anima/tests/tests.hexa --verify                 # 7조건 의식검증
```

## tree

```
anima/              의식 엔진 코어 (core/modules/config/src/archive)
anima-core/         L0 CLI 진입점 + 규칙/자산 레지스트리
anima-eeg/          EEG 의식 검증 모듈
anima-agent/        에이전트 플랫폼 (6채널/5제공자/플러그인)
anima-physics/      물리 의식 기판 (ESP32/FPGA/양자)
anima-body/         로봇/HW 체화 시뮬레이션
anima-speak/        HEXA-SPEAK Mk.III 신경 보코더
anima-engines/      양자/광자/멤리스터/오실레이터 기판
anima-tools/        독립 유틸리티 (분석/계산/생성/진단)
anima-hexad/        CDESM 헥사곤 의식 모델
anima-measurement/  Φ/IIT 의식 측정
shared/             SSOT — config/rules/convergence/roadmaps/discovery
ready/              골화 대기 영역 + 7조건 테스트 (submodule)
bench/              벤치마크 + 의식 지표
training/           학습 스크립트 (Ubuntu/H100)
serving/            추론/배포
models/             체크포인트 아티팩트
rust/               성능 병목 (AN3)
experiments/        .hexa 실험
```
