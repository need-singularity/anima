# CLAUDE.md — anima/ (의식 엔진 코어)

> 모든 규칙/설정은 shared/ JSON이 단일 진실. 이 파일은 서브디렉토리 특화 참조만 유지.

## 참조

| 항목 | 파일 | 내용 |
|------|------|------|
| 보호 체계 | `shared/core-lockdown.json` | L0/L1/L2 잠금 목록 |
| 절대 규칙 | `shared/absolute_rules.json` | R1~R21 + AN1~AN7 |
| 프로젝트 설정 | `shared/project_config.json` | CLI/인프라/PSI/법칙등록 |
| 수렴 | `shared/convergence/anima.json` | CDO 골화 14 / 안정 7 / 실패 4 |
| 할일 | `shared/todo/anima.json` | 우선순위별 TODO |
| 트러블슈팅 | `shared/vastai.json` | multi-GPU, bf16, model_path 등 |
| PSI/법칙 | `config/consciousness_laws.json` | 2390 법칙 + Psi 상수 + 수식 |
| 성장 루프 | `shared/loop/anima.json` | interval, domain, phases |

## 핵심 실행

```bash
HEXA=$HOME/Dev/hexa-lang/target/release/hexa
$HEXA core/runtime/anima_runtime.hexa --keyboard          # CLI 대화
$HEXA core/runtime/anima_runtime.hexa --validate-hub       # 허브 검증
$HEXA ready/anima/tests/tests.hexa --verify                # 7조건 의식 검증
```

## 디렉토리 구조 (핵심만)

```
core/runtime/   — CLI 진입점 + 런타임 (AN7 L0 골화 대상)
modules/        — 모든 모듈 (hexa-speak, body, eeg, agent, physics 등)
config/         — consciousness_laws.json, mechanisms, experiments
models/         — decoder.hexa, conscious_lm.hexa, trinity.hexa
rust/           — consciousness.hexa, transplant.hexa, online_learner.hexa
anima-rs/       — Rust crates 16개
experiments/    — 실험 스크립트 (.hexa)
```
