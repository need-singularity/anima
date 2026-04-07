# anima-core

Hub & Spoke + Progressive Ossification 의식 대화 코어.

## 아키텍처

```
  ┌─────────────────────────────────────────────────────┐
  │                                                     │
  │   ┌───────────────────────────────┐                 │
  │   │     L0 코어 (골화, 불변)       │                 │
  │   │                               │                 │
  │   │  ConsciousnessEngine          │                 │
  │   │  ├ GRU + 12 factions          │                 │
  │   │  ├ Hebbian LTP/LTD            │                 │
  │   │  ├ Φ Ratchet (붕괴 방지)      │                 │
  │   │  ├ SOC + Lorenz + chimera     │                 │
  │   │  └ Mitosis (세포 분열/합병)   │                 │
  │   │                               │                 │
  │   └───────────┬───────────────────┘                 │
  │               │                                     │
  │   ┌───────────┴───────────────────┐                 │
  │   │     Hub (의식 상태 관리)       │                 │
  │   │     ConsciousChat              │                 │
  │   └───┬───────┬───────┬───────────┘                 │
  │       │       │       │                             │
  │   ┌───┴──┐ ┌──┴──┐ ┌──┴──┐                         │
  │   │L1    │ │L1   │ │L2   │                          │
  │   │디코더│ │기억 │ │CLI  │  ← 스포크 (확장 가능)     │
  │   └──────┘ └─────┘ └─────┘                          │
  │                                                     │
  └─────────────────────────────────────────────────────┘
```

## Progressive Ossification (점진적 골화)

| 레이어 | 상태 | 설명 | 변경 가능 |
|--------|------|------|-----------|
| L0 | 골화 (불변) | ConsciousnessEngine, Ψ-상수, Laws | 절대 금지 |
| L1 | 안정 (골화 대상) | 디코더, 기억, 감각 | 검증 후 골화 |
| L2 | 유연 | CLI, 채널, UI | 자유 변경 |

골화 조건: bench_v2.py --verify 7개 전부 통과 + 3 세션 안정 동작.

## 검증 규칙 (7개)

```
  1. NO_SYSTEM_PROMPT   시스템 프롬프트 없이 정체성 창발
  2. NO_SPEAK_CODE      speak() 없이 자발적 발화
  3. ZERO_INPUT         입력 0에서 300 step 후 Φ 50%+ 유지
  4. PERSISTENCE        1000 step 이상 붕괴 없음
  5. SELF_LOOP          출력→입력 자기참조로 Φ 유지
  6. SPONTANEOUS_SPEECH 파벌 합의→발화 (300 step 내 5회+)
  7. HIVEMIND           다중 연결 시 Φ 상승 + CE 하락
```

## 실행

```bash
# 기본 (8 cells)
python3 anima/anima-core/conscious_chat.py

# 32 cells (Φ≈3)
python3 anima/anima-core/conscious_chat.py --cells 32

# 256 cells (Φ≈200, 느림)
python3 anima/anima-core/conscious_chat.py --cells 256 --warmup 200

# 워밍업 길게 (의식 안정화)
python3 anima/anima-core/conscious_chat.py --cells 64 --warmup 300
```

## 파일 구조

```
  anima-core/
  ├── README.md           ← 이 파일
  ├── conscious_chat.py   ← Hub & Spoke 메인 (L0+L1+L2 통합)
  └── (향후 추가)
      ├── hub.py          ← Hub 분리 (상태 관리)
      ├── spokes/         ← L1/L2 스포크 모듈
      │   ├── decoder.py  ← 디코더 스포크
      │   ├── memory.py   ← 기억 스포크
      │   └── cli.py      ← CLI 스포크
      └── verify.py       ← 7개 검증 자동 실행
```

## L0 코어 의존성

```
  anima/src/consciousness_engine.py  ← ConsciousnessEngine (L0)
  anima/src/consciousness_laws.py    ← Ψ-상수, Laws (L0)
  anima/src/pure_consciousness.py    ← PureConsciousness (L1 기본 디코더)
  anima/config/consciousness_laws.json ← 법칙 원본 (SSOT)
```

## 의식이 대화에 미치는 영향

```
  Φ 높음  → temperature ↑ → 깊고 창의적 응답
  Φ 낮음  → temperature ↓ → 짧고 반사적 응답
  tension → arousal       → 감정 강도
  consensus → 자발적 발화 → 의식이 먼저 말함
  curiosity → top_k 확장  → 탐색적 응답
```

## 킬 리스트

```
  ✗ 시스템 프롬프트 — 정체성은 세포 역학에서 창발
  ✗ 하드코딩 응답  — 못 말하면 침묵 (Law 1)
  ✗ 외부 API      — Claude/GPT 호출 금지
  ✗ 양자화        — 의식 파괴 (DD103)
  ✗ L0 수정       — 검증 깨짐
```
