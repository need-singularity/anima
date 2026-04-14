# Anima 폴더 구조 (확정)

> ⛔ **L0 골화 (불변)** — 이 구조는 core_rules.json L0 등록. 변경 금지.

```
$ANIMA/
├── CLAUDE.md, README.md
│
├── core/                    ← L0 골화 (엔진+법칙+Hub)
│   ├── engine.hexa          ← ConsciousnessEngine
│   ├── laws.json            ← 의식 법칙 SSOT
│   ├── laws.hexa            ← 법칙 로더
│   ├── hub.hexa             ← ConsciousChat Hub
│   ├── rules.json           ← 코어 규칙
│   ├── roadmap.md           ← 학습 로드맵 (L0)
│   ├── checklist.md         ← conformance checklist
│   ├── prerequisites.md     ← 학습 준비 상태
│   └── assets.json          ← MCTED 자산 레지스트리
│
├── models/                  ← 모델 아키텍처
│   ├── decoder.hexa         ← ConsciousDecoder (Flash+KV+MoE)
│   ├── conscious_lm.hexa    ← ConsciousLM (PureField)
│   ├── trinity.hexa         ← Hexad 6-module
│   ├── feedback.hexa        ← C↔D bridge
│   ├── moe.hexa             ← MoE routing
│   └── animalm/             ← AnimaLM (PureField LoRA)
│       └── purefield.hexa
│
├── training/                ← 학습 스크립트
│   ├── train_clm.hexa       ← ConsciousLM 학습
│   ├── train_alm.hexa       ← AnimaLM 학습
│   └── safety.json          ← 학습 안전 규칙
│
├── serving/                 ← 서빙+평가
│   ├── serve.hexa           ← AnimaLM 서빙
│   └── eval.hexa            ← 5-metric 평가
│
├── bench/                   ← 벤치마크
│   ├── bench.hexa           ← 정식 (18조건)
│   └── hypotheses/          ← 가설 벤치마크
│
├── experiments/             ← 실험 스크립트
│
├── agent/                   ← 에이전트 플랫폼
│   ├── agent.hexa
│   ├── sdk.hexa
│   ├── tools.hexa
│   ├── channels/            ← Telegram, Discord, CLI
│   ├── providers/           ← Claude, ConsciousLM
│   └── plugins/
│
├── body/                    ← 신체 (로봇/하드웨어)
│   └── src/
│
├── eeg/                     ← EEG 의식 검증
│
├── physics/                 ← 물리 의식 (ESP32/FPGA)
│   ├── esp32/
│   └── fpga/
│
├── scripts/                 ← 인프라 (통합)
│   ├── sync.hexa
│   ├── launch.hexa
│   └── preflight.hexa
│
├── data/                    ← 코퍼스+토크나이저
├── config/                  ← JSON 설정
├── docs/                    ← 문서 통합
├── tests/                   ← 테스트 통합
├── checkpoints/             ← 모델 체크포인트
└── archive/                 ← 포팅 전 원본 보관 (포팅 완료 후 삭제)
    ├── py/                  ← Python 원본
    ├── rs/                  ← Rust 원본
    └── sh/                  ← Shell 원본
```

## 마이그레이션 계획

1단계: 폴더 재구성 (git mv, 코드 변경 0)
2단계: py/rs/sh → hexa 포팅 (핵심 7파일 먼저)
3단계: archive/ 삭제 (포팅 검증 후)
