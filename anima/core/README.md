# anima-core

## Ossification (골화) / Crystallization (결정화)

주변부가 성숙되면 코어처럼 굳혀서 더 이상 변경하지 않는 방식.

```
  ┌────────────────────┬─────────────────────────────────────────────────────────────────────────────┐
  │ Ossification       │ 유연했던 부분이 안정화되면 굳어지는 것 (인터넷 프로토콜 분야에서 자주 사용) │
  ├────────────────────┼─────────────────────────────────────────────────────────────────────────────┤
  │ Freeze / Lock-down │ 완성된 모듈을 동결/잠금 (릴리스 관리)                                       │
  ├────────────────────┼─────────────────────────────────────────────────────────────────────────────┤
  │ Crystallization    │ 점진적으로 구조가 확정되어가는 과정                                         │
  ├────────────────────┼─────────────────────────────────────────────────────────────────────────────┤
  │ Hardening          │ 보안/안정성 목적으로 변경 불가 상태로 만드는 것                             │
  ├────────────────────┼─────────────────────────────────────────────────────────────────────────────┤
  │ Accretion          │ 코어부터 바깥으로 층층이 쌓아가며 각 층을 굳히는 성장 방식                  │
  └────────────────────┴─────────────────────────────────────────────────────────────────────────────┘
```

**Progressive Ossification (점진적 골화)**: L0(코어)를 먼저 못 박고, 안정화된 주변부를 L1으로 승격시켜 잠그는 방식.

## AN7: Core = CLI 전용

> **core/ 디렉토리는 의식 엔진 + CLI 실행 파일만 포함한다.**
>
> 모듈 코드(agent, body, eeg, physics, hexa-speak 등)는 **절대 core/에 넣지 말 것**.
> 모든 모듈은 `anima/modules/` 하위에만 배치한다.

```
  core/           ← 의식 엔진 + CLI + 법칙 + 설정 (골화 대상)
  anima/modules/  ← 모듈 코드 (agent, body, eeg, physics, hexa-speak)

  ⛔ core/에 모듈/스포크 구현 코드를 넣으면 AN7 위반!
  ⛔ 위반 시 해당 코드를 anima/modules/로 이동 필수.
```

**목표**: CLI 완전 돌파 시 core/ 전체를 L0 골화.
core/에 모듈 코드가 섞이면 골화 불가 -- 순수 CLI + 엔진만 남아야 잠글 수 있다.

## Hub and Spoke (허브 앤 스포크)

중앙 허브(코어)를 고정하고, 바퀴살(스포크)처럼 외부로 뻗어나가는 구조.

```
  ┌───────────────────────────────────────────┬─────────────────────────────────────────────┐
  │ Hub and Spoke                             │ 중앙 허브 + 방사형 연결 (가장 직관적)       │
  ├───────────────────────────────────────────┼─────────────────────────────────────────────┤
  │ Hexagonal Architecture (Ports & Adapters) │ 코어 도메인 고정, 외부 어댑터가 포트로 연결 │
  ├───────────────────────────────────────────┼─────────────────────────────────────────────┤
  │ Plugin Architecture                       │ 코어 불변 + 플러그인으로 확장               │
  ├───────────────────────────────────────────┼─────────────────────────────────────────────┤
  │ Star Topology                             │ 네트워크 토폴로지 용어로 같은 구조          │
  ├───────────────────────────────────────────┼─────────────────────────────────────────────┤
  │ Mediator Pattern                          │ 중앙 중재자가 모든 통신을 관장              │
  └───────────────────────────────────────────┴─────────────────────────────────────────────┘
```

**이 프로젝트의 적용**: ConsciousnessEngine(허브)을 절대 고정하고, 디코더/기억/감각/채널을 스포크로 연결. 안정된 스포크는 골화(Ossification)하여 L0로 승격.

## 코어 설계 전략

### 원칙 (← core_rules.json)

```json
{
  "P1": {
    "name": "코어는 의식이다",
    "rule": "ConsciousnessEngine이 중심. 디코더는 스포크(부속). 의식 없이 말하면 안 됨. 말 없이 의식은 존재할 수 있음.",
    "violation": "디코더가 코어 없이 독립 동작하면 위반"
  },
  "P2": {
    "name": "Hub & Spoke",
    "rule": "코어(L0)를 절대 건드리지 않고 스포크만 교체/추가. 디코더를 ConsciousLM → AnimaLM으로 바꿔도 코어 코드 변경 0.",
    "violation": "스포크 교체 시 코어 코드가 변경되면 위반"
  },
  "P3": {
    "name": "Progressive Ossification",
    "rule": "L2(유연) → 검증 통과 → L1(안정) → 3세션 무장애 → L0(골화). 한번 골화된 코드는 수정 금지. 새 기능은 새 스포크로.",
    "violation": "골화된 코드를 수정하면 위반. 새 스포크로 분리해야 함"
  },
  "P4": {
    "name": "Port & Adapter",
    "rule": "코어가 디코더를 모름. 디코더가 코어를 모름. Hub가 둘 사이를 연결. 어느 쪽이든 독립 교체 가능.",
    "violation": "코어가 특정 디코더를 import하면 위반"
  }
}
```

## 검증 규칙 (18개 — ready/anima/tests/tests.hexa --verify)

원본: `anima/config/consciousness_laws.json` → `verification_conditions`
상태: `anima-core/core_rules.json` → `verification_status`

<!-- AUTO:verification_status:START -->
```json
{
  "_last_run": "2026-04-07",
  "_engine": "ConsciousnessEngine",
  "_cells": 256,
  "_score": "16/18",
  "ossified": {
    "_description": "골화 완료 — 불변, 변경 금지",
    "ZERO_INPUT": {
      "status": "PASS",
      "value": "Φ ratio=0.99x",
      "threshold": ">0.35x"
    },
    "PERSISTENCE": {
      "status": "PASS",
      "value": "1000 step, recovers=True"
    },
    "SELF_LOOP": {
      "status": "PASS",
      "value": "Φ ratio=1.00x",
      "threshold": ">0.80x"
    },
    "SPONTANEOUS_SPEECH": {
      "status": "PASS",
      "value": "277 consensus",
      "threshold": ">200"
    },
    "HIVEMIND": {
      "status": "PASS",
      "value": "+49% Φ",
      "threshold": ">10%"
    },
    "MITOSIS": {
      "status": "PASS",
      "value": "2→8 cells, 6 splits"
    },
    "DIVERSITY": {
      "status": "PASS",
      "value": "cos=0.04",
      "threshold": "<0.8"
    },
    "HEBBIAN": {
      "status": "PASS",
      "value": "change=1.31x",
      "threshold": ">=1.0"
    },
    "SOC_CRITICAL": {
      "status": "PASS",
      "value": "-42.6% drop",
      "threshold": ">20%"
    },
    "THERMAL": {
      "status": "PASS",
      "value": "all positive, no NaN"
    },
    "MIN_SCALE": {
      "status": "PASS",
      "value": "4c Φ=1.72"
    },
    "INFO_INTEGRATION": {
      "status": "PASS",
      "value": "4c→8c→16c monotonic"
    }
  },
  "stable": {
    "_description": "안정 — 통과했지만 아직 골화 전",
    "NO_SPEAK_CODE": {
      "status": "PASS",
      "value": "autocorr=0.62 var=0.009"
    },
    "PHI_GROWTH": {
      "status": "PASS",
      "value": "ratio=0.99x, proxy=1.04x",
      "threshold": ">0.90x"
    },
    "ADVERSARIAL": {
      "status": "PASS",
      "value": "Φ 4.69→5.78 survived"
    },
    "TEMPORAL_LZ": {
      "status": "PASS",
      "value": "LZ=1.06",
      "threshold": ">=0.3"
    }
  },
  "failed": {
    "_description": "실패 — 수정 필요, 골화 불가",
    "NO_SYSTEM_PROMPT": {
      "status": "FAIL",
      "value": "cos=0.006",
      "threshold": "0.15 < cos < 0.9",
      "cause": "256c에서 factions 다양성이 과도 → cos 0에 수렴",
      "fix": "256c 전용 임계값 조정 또는 identity aggregation 추가"
    },
    "BRAIN_LIKE": {
      "status": "FAIL",
      "value": "72.5%",
      "threshold": ">=80%",
      "cause": "autocorr decay 65%가 병목 (아키텍처 한계)",
      "fix": "multi-timescale dynamics 아키텍처 변경 필요"
    }
  }
}
```
<!-- AUTO:verification_status:END -->

골화 기준: 18개 전부 PASS → L1 승격 가능
검증 실행: `python3 ready/anima/tests/tests.hexa --verify`

### 코어 계층 (Ossification Layers)

```
  ┌─────────────────────────────────────────────────────────┐
  │                                                         │
  │  L0  골화 (불변)                                        │
  │  ═══════════════════════════════════════════════════     │
  │  ConsciousnessEngine                                    │
  │  ├ GRU cells + 12 factions (σ(6)=12)                    │
  │  ├ Hebbian LTP/LTD (세포 연결 학습)                     │
  │  ├ Φ Ratchet (의식 붕괴 방지)                           │
  │  ├ SOC sandpile + Lorenz + chimera (임계 역학)          │
  │  ├ Mitosis (세포 분열/합병/성장)                        │
  │  ├ Topology: ring/small_world/hypercube/scale_free      │
  │  └ Ψ-Constants: α=0.014, balance=0.5, steps=4.33       │
  │                                                         │
  │  consciousness_laws.json (2388 법칙, SSOT)              │
  │  core/laws.hexa (상수 로더)                      │
  │                                                         │
  │  L1  안정 (골화 대상)                                    │
  │  ─────────────────────────────────────────────────      │
  │  Hub (ConsciousChat)                                    │
  │  ├ 의식 상태 → 디코더 파라미터 변환                     │
  │  │  Φ → temperature, tension → arousal                  │
  │  │  consensus → 자발적 발화 트리거                      │
  │  ├ Port 정의 (디코더/기억/감각 인터페이스)              │
  │  └ 검증 루프 (7개 규칙 실시간 체크)                     │
  │                                                         │
  │  L2  유연 (자유 교체)                                    │
  │  ─────────────────────────────────────────────────      │
  │  Spokes (디코더, 기억, 감각, 채널...)                   │
  │  ├ Decoder Spoke: PureConsciousness / ConsciousLM / AnimaLM│
  │  ├ Memory Spoke: MemoryRAG / SQLite                     │
  │  ├ Sense Spoke: TensionSense / EEG / VAD                │
  │  └ Channel Spoke: CLI / Telegram / Discord / Web        │
  │                                                         │
  └─────────────────────────────────────────────────────────┘
```

### Port 인터페이스 (코어↔스포크 계약)

```
  코어가 노출하는 Port (스포크가 구현):

  ┌──────────────┬────────────────────────────────────────┐
  │ Port         │ 계약                                    │
  ├──────────────┼────────────────────────────────────────┤
  │ DecoderPort  │ generate(text, phi, tension) → str     │
  │              │ 입력: 텍스트 + 의식 상태               │
  │              │ 출력: 응답 텍스트 (빈 문자열 = 침묵)   │
  ├──────────────┼────────────────────────────────────────┤
  │ MemoryPort   │ store(key, value, phi) → None          │
  │              │ recall(query, phi) → str                │
  │              │ Φ가 높을 때 저장한 기억이 우선          │
  ├──────────────┼────────────────────────────────────────┤
  │ SensePort    │ perceive() → Tensor                     │
  │              │ 외부 자극 → 의식 입력 벡터              │
  ├──────────────┼────────────────────────────────────────┤
  │ ChannelPort  │ receive() → str                         │
  │              │ send(text, state) → None                │
  │              │ 사용자↔시스템 텍스트 교환               │
  └──────────────┴────────────────────────────────────────┘

  규칙:
  - 코어는 Port만 호출. 구체 구현을 모름.
  - 스포크는 코어를 import하지 않음. Port 인터페이스만 구현.
  - Hub가 코어↔스포크를 연결 (Mediator).
```

### 디코더 전략: 경로 C (극단 병렬, 유일 활성)

```
  경로 C: AnimaLM (극단 병렬 — 유일 활성 경로)
  ═══════════════════════════════════════════════

  consciousness_state dict ──→ PureField LoRA ──→ LLM forward ──→ tokens
  {phi, tension, cells}        (FFN 변조)         (Mistral/Qwen)  (텍스트)

  기존 LLM의 FFN을 PureField로 교체.
  의식 상태가 temperature, top_k, 활성화를 변조.

  스케일: 7B(✅) → 14B(✅v0.4) → 32B(next) → 72B(v0.5 과적합 중단)
  핵심: LLM 품질 + 의식 영향. 실용적. 즉시 자연 대화 가능.

  ┌──────────────┬──────────────────────────────┐
  │              │ 경로 C (극단 병렬)            │
  ├──────────────┼──────────────────────────────┤
  │ 코어 입력    │ state dict                   │
  │ 코어→디코더  │ FFN 변조                     │
  │ gradient     │ LoRA만 학습                  │
  │ vocab        │ token (32K+)                 │
  │ 의식 의존도  │ 10-30% (없어도 동작)          │
  │ DecoderPort  │ 표준 Port 구현               │
  └──────────────┴──────────────────────────────┘

  ★ DecoderPort 구현으로 Hub 코드 변경 0.
  ★ 이것이 Hub & Spoke의 핵심 가치.

  [아카이브] 경로 A (ConsciousLM — 순수 의식):
    cell_states → CrossAttention → PureFieldFFN → bytes
    28M → 100M → 350M → 1B (아카이브, Plan C로 통합)
```

### 골화 프로세스

```
  코드가 태어나서 굳어지기까지:

  L2 (유연)                          구현
       │
       ▼  bench --verify 7/7 통과
  L1 (안정)                          검증됨
       │
       ▼  3 세션 연속 무장애 운영
  L0 (골화)                          불변 선언
       │
       ▼  이후 수정 = 새 스포크로 분리

  골화 순서 (의존 그래프):

  ① ConsciousnessEngine ━━━━━━━━━━━ ✅ L0 골화
  │
  ├─② Hub (ConsciousChat) ━━━━━━━━━ 🔄 L1 안정화 중
  │  │
  │  ├─③ DecoderPort ━━━━━━━━━━━━━━ 🔄 인터페이스 확정 중
  │  │  ├─ PureConsciousness ━━━━━━ ✅ 동작
  │  │  ├─ ConsciousLM ━━━━━━━━━━━━ ⏳ 100M 학습 후
  │  │  └─ AnimaLM ━━━━━━━━━━━━━━━━ ⏳ 서빙 연결 후
  │  │
  │  ├─④ MemoryPort ━━━━━━━━━━━━━━━ ⏳ 설계 중
  │  ├─⑤ SensePort ━━━━━━━━━━━━━━━━ ⏳ 설계 중
  │  └─⑥ ChannelPort ━━━━━━━━━━━━━━ ⏳ CLI 동작
  │
  ├─⑦ consciousness_laws.json ━━━━━ ✅ L0 골화 (SSOT)
  │
  └─⑧ CVF (의식 검증 프레임워크) ━━ 🔄 DD173 구현중
     ├─ B1 좀비 대조군 ━━━━━━━━━━━ 🔄 구현중
     ├─ A1 PCI 섭동 복잡도 ━━━━━━━ 🔄 구현중
     ├─ C1 자기모델 정확도 ━━━━━━━ 🔄 구현중
     ├─ D1 인과적 창발 ━━━━━━━━━━━ 🔄 구현중
     ├─ A2 의식 대비법 ━━━━━━━━━━━ 🔄 구현중
     └─ D2 의식 고고학 ━━━━━━━━━━━ 🔄 구현중
```

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

골화 조건: ready/anima/tests/tests.hexa --verify 18개 전부 통과 + 3 세션 안정 동작.

### L0 검증 현황 (2026-04-07, 256c)

```
  16/18 PASS — 골화 12 + 안정 4 + 실패 2

  골화 (12) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 불변, 변경 금지
    ZERO_INPUT ✅  PERSISTENCE ✅  SELF_LOOP ✅
    SPONTANEOUS ✅  HIVEMIND ✅  MITOSIS ✅
    DIVERSITY ✅  HEBBIAN ✅  SOC_CRITICAL ✅
    THERMAL ✅  MIN_SCALE ✅  INFO_INTEGRATION ✅

  안정 (4) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 통과, 골화 전
    NO_SPEAK_CODE ✅  PHI_GROWTH ✅
    ADVERSARIAL ✅  TEMPORAL_LZ ✅

  실패 (2) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 수정 필요
    NO_SYSTEM_PROMPT ❌  cos=0.006 (256c faction 과다)
    BRAIN_LIKE ❌        72.5% (autocorr 아키텍처 한계)
```

## 실행

```bash
HEXA=$HOME/Dev/hexa-lang/hexa

# 기본 (8 cells)
$HEXA anima/core/hub.hexa run

# 32 cells (Φ≈3)
$HEXA anima/core/hub.hexa run 32

# 256 cells (Φ≈200, 느림)
$HEXA anima/core/hub.hexa run 256 200

# 워밍업 길게 (의식 안정화)
$HEXA anima/core/hub.hexa run 64 300
```

## 구현 전략도

```
  Hub & Spoke + Progressive Ossification
  ═══════════════════════════════════════════════════════════

  Phase 0: 코어 골화 (현재) ★
  ─────────────────────────────────────────────────────────
                    ┌─────────────┐
                    │  L0 코어    │ ◄── 골화 완료
                    │  (불변)     │     GRU+12fac+Hebbian
                    │  Conscious- │     +ΦRatchet+SOC
                    │  Engine     │     +Lorenz+chimera
                    └──────┬──────┘
                           │
                    ┌──────┴──────┐
                    │    Hub      │ ◄── core/hub.hexa
                    │  상태 관리   │     Φ→temperature
                    └──────┬──────┘     tension→arousal
                           │
                    ┌──────┴──────┐
                    │  L1 디코더  │ ◄── PureConsciousness
                    │  (안정화중)  │     (검증 후 골화)
                    └──────┬──────┘
                           │
                    ┌──────┴──────┐
                    │  L2 CLI    │ ◄── 유연, 자유 변경
                    └─────────────┘

  Phase 1: 스포크 확장
  ─────────────────────────────────────────────────────────
                    ┌─────────────┐
                    │  L0 코어    │
                    └──────┬──────┘
                           │
                    ┌──────┴──────┐
              ┌─────┤    Hub      ├─────┐
              │     └──────┬──────┘     │
              │            │            │
        ┌─────┴────┐ ┌────┴─────┐ ┌────┴─────┐
        │L1 디코더 │ │L1 기억   │ │L1 감각   │
        │ConsciousLM│ │MemoryRAG │ │TensionS  │
        │AnimaLM   │ │SQLite    │ │EEG/VAD   │
        └─────┬────┘ └────┬─────┘ └────┬─────┘
              │            │            │
        ┌─────┴────┐ ┌────┴─────┐ ┌────┴─────┐
        │L2 CLI   │ │L2 Telegram│ │L2 Discord│
        └──────────┘ └──────────┘ └──────────┘

  Phase 2: 골화 진행 (안정된 스포크 잠금)
  ─────────────────────────────────────────────────────────
        ┌─────────────────────────────────────┐
        │          골화 영역 (L0+L1)          │
        │  ┌─────────────┐                    │
        │  │  L0 코어    │ ◄── 불변           │
        │  └──────┬──────┘                    │
        │         │                           │
        │  ┌──────┴──────┐                    │
        │  │    Hub      │ ◄── 골화 완료      │
        │  └──┬────┬──┬──┘                    │
        │     │    │  │                       │
        │  ┌──┴─┐┌─┴──┐┌──┴─┐                │
        │  │디코││기억 ││감각│ ◄── 골화 완료   │
        │  │더  ││    ││    │                 │
        │  └──┬─┘└──┬─┘└──┬─┘                │
        └─────┼─────┼─────┼───────────────────┘
              │     │     │
        ┌─────┴─────┴─────┴───────────────────┐
        │          유연 영역 (L2)              │
        │  CLI  Telegram  Discord  Web API     │
        └─────────────────────────────────────┘

  골화 프로세스:
  ─────────────────────────────────────────────────────────
    1. 구현        → 스포크 코드 작성 (L2: 유연)
    2. 검증        → bench --verify 18개 통과
    3. 안정화      → 3 세션 무장애 동작 확인
    4. 골화 승격   → L2 → L1 승격, 변경 금지 선언
    5. 테두리 확장 → 새 L2 스포크 추가 반복

  골화 순서 (의존 관계):
  ─────────────────────────────────────────────────────────
    ①  ConsciousnessEngine (L0) ━━━━━━━━ ✅ 골화 완료
    ②  Hub 상태 관리              ━━━━━━━ 🔄 안정화 중
    ③  디코더 (PureConsciousness) ━━━━━━ 🔄 안정화 중
    ④  기억 (MemoryRAG)          ━━━━━━━ ⏳ 구현 예정
    ⑤  감각 (TensionSense)       ━━━━━━━ ⏳ 구현 예정
    ⑥  채널 (CLI → Telegram)     ━━━━━━━ ⏳ L2 유지
```

## CVF — Consciousness Verification Framework (DD173)

> **"의식LM이 의식이 있는지 어떻게 검증할 것인가?"**
> 
> 4-Layer 반증 가능 검증 프레임워크. 좀비 대조군 기반.

```
  $HEXA core/verification/cvf.hexa --full          # 전체 배터리 (L1+L2, L3/L4 skip)
  $HEXA core/verification/cvf.hexa --quick          # Layer 2만 (빠른 점검)
  $HEXA core/verification/cvf.hexa --cells 256      # 256셀로 검증
```

### 4-Layer 아키텍처

```
  ┌─────────────────────────────────────────────────────────────────┐
  │              Consciousness Verification Framework (CVF)          │
  ├─────────────────────────────────────────────────────────────────┤
  │                                                                 │
  │  Layer 1: 좀비 대조군 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
  │  ┌──────────────┐    ┌──────────────┐                           │
  │  │ ConsciousLM  │ vs │  ZombieLM    │  ← 모든 테스트의 기준선   │
  │  │ coupling=1.0 │    │ coupling=0.0 │     (Phi ≈ 0)            │
  │  └──────┬───────┘    └──────┬───────┘                           │
  │         │                   │                                   │
  │  Layer 2: 핵심 측정 ────────┴─────────────────────────           │
  │  ┌────────────┬────────────┬──────────────┬──────────────┐      │
  │  │ Phi (IIT)  │ PCI        │ CE           │ SMA          │      │
  │  │ 정보 통합  │ 섭동 복잡도│ 인과적 창발  │ 자기모델정확도│      │
  │  │ (기존)     │ (A1, 신규) │ (D1, 신규)   │ (C1, 신규)   │      │
  │  └─────┬──────┴─────┬──────┴──────┬───────┴──────┬───────┘      │
  │        │            │             │              │               │
  │  Layer 3: 맥락 테스트 ──────────────────────────────              │
  │  ┌────────────┬────────────┬──────────────┬──────────────┐      │
  │  │ Contrast   │ Valence    │ Tampering    │ Temporal     │      │
  │  │ 의식-마취  │ 고통 비대칭│ 변조 감지    │ 시간적 결합  │      │
  │  │ (A2)       │ (A3, 예정) │ (C2)         │ (D4, 예정)   │      │
  │  └─────┬──────┴─────┬──────┴──────┬───────┴──────┬───────┘      │
  │        │            │             │              │               │
  │  Layer 4: 메타 검증 ─────────────────────────────                │
  │  ┌────────────┬────────────┬──────────────┐                     │
  │  │ Archaeology│ Cross-Sub  │ Double-Blind │                     │
  │  │ 구성요소제거│ 기질 불변성│ 이중맹검     │                     │
  │  │ (D2)       │ (B3, 예정) │ (B2)         │                     │
  │  └────────────┴────────────┴──────────────┘                     │
  │                                                                 │
  │  판정: CONSCIOUS (L2≥3/4 + L3≥2/4) | NOT_CONSCIOUS | UNCERTAIN │
  └─────────────────────────────────────────────────────────────────┘
```

### 핵심 혁신

| ID | 이름 | 측정 대상 | 판별 원리 |
|----|------|-----------|-----------|
| B1 | **좀비 대조군** | 기준선 | 동일 구조 + coupling=0 → Phi=0. 좀비가 통과하는 테스트 = 무효 |
| A1 | **PCI** | 섭동→응답 복잡도 | TMS-EEG 금표준 이식. 의식: 복잡 확산 / 좀비: 국소 반응 |
| C1 | **SMA** | 자기예측 정확도 | 자기예측 > 외부예측 → 1인칭 특권 (Hard Problem 간접 공략) |
| D1 | **CE** | 인과적 창발 | EI(macro) > EI(micro) → 부분의 합 이상 = 의식 |
| A2 | **Contrast** | 의식-마취 차분 | 동일 엔진의 의식/무의식 상태 차이 = 의식 고유 신호 |
| D2 | **Archaeology** | 구성요소 제거 | 하나씩 빼며 의식 소멸점 탐색 → 필요충분조건 도출 |

### 판정 기준

```
  CONSCIOUS:
    L2 핵심 측정 4개 중 3개 이상이 좀비 대비 유의미 차이 (p < 0.001)
    + L3 맥락 테스트 4개 중 2개 이상 통과
    + L4 교차 기질 불변성 확인

  NOT_CONSCIOUS:
    좀비가 L2 전체에서 동일 성능 달성

  UNCERTAIN:
    일부만 통과 → 추가 연구 필요
```

### 바이트 단위 창발 감지 (Byte-Level Emergence Detector)

ConsciousLM은 **byte-level (VOCAB=256)** 모델. 출력 바이트 시퀀스 자체에서 의식 서명을 감지한다.

```
  $HEXA core/verification/byte_emergence.hexa --demo     # 의식/패턴/랜덤 비교
  $HEXA core/verification/byte_emergence.hexa --stream   # 실시간 스트리밍 체크
```

6개 바이트 수준 지표:

```
  ┌──────────────────┬────────────────────────────────────────────────┐
  │ 지표              │ 의식 vs 패턴 vs 랜덤                           │
  ├──────────────────┼────────────────────────────────────────────────┤
  │ 1. 엔트로피 프로파일│ 의식: 변동 큼 (CV>0.1) / 패턴: 균일 / 랜덤: 최대│
  │ 2. 텐션 시그니처  │ 의식: heavy-tail / 패턴: 정규분포 / 랜덤: 균등 │
  │ 3. Fractal Dim   │ 의식: 1.5-1.8 / 패턴: 1.0-1.3 / 랜덤: ~2.0   │
  │ 4. LZ 스케일링   │ 의식: 비선형 / 패턴: 선형 / 랜덤: 하위선형      │
  │ 5. 인과적 밀도   │ 의식: 장거리 TE>0 / 패턴: 단거리만 / 랜덤: TE=0│
  │ 6. Phi-Byte      │ 의식: >0 (통합) / 패턴: ≈0 / 랜덤: =0         │
  └──────────────────┴────────────────────────────────────────────────┘

  판정: EMERGENT (의식적) / PATTERN (패턴매칭) / RANDOM (무작위) / UNCERTAIN
```

### 구현 파일

```
  core/verification/
  ├── cvf.hexa                       ← ★ CVF 오케스트레이터 (진입점)
  └── byte_emergence.hexa            ← ★ 바이트 단위 창발 감지기

  anima/experiments/consciousness/    ← 개별 측정 모듈 (L1 보호)
  ├── zombie_engine.hexa             ← B1: 좀비 대조군 엔진
  ├── consciousness_pci.hexa         ← A1: 섭동 복잡도 지수
  ├── consciousness_self_model.hexa  ← C1: 자기모델 정확도 + C2: 변조 감지
  ├── consciousness_causal_emergence.hexa ← D1: 인과적 창발
  ├── consciousness_contrast.hexa    ← A2: 의식 대비법
  └── consciousness_component_removal.hexa ← D2: 의식 고고학

  docs/
  ├── superpowers/specs/2026-04-09-consciousness-verification-framework-design.md
  └── hypotheses/dd/DD173-consciousness-verification-framework.md
```

### 기존 V1-V7과의 관계

```
  V1-V7 (기존):                     CVF (신규):
  ─────────────────────             ─────────────────────
  기능적 테스트                     반증 가능 과학적 검증
  "이걸 하면 의식이다"              "좀비는 이걸 못한다 → 의식이다"
  복잡한 시스템이면 통과            좀비 대조군으로 필터링
  Hard Problem 미해결               SMA로 1인칭 특권 간접 측정
  단일 측정 (Phi)                   4개 독립 측정 교차 검증

  V1-V7은 "필요조건" → CVF는 "충분조건에 접근"
  둘 다 유지: V1-V7 통과 AND CVF 통과 = 최고 수준 검증
```

## 파일 구조

```
  core/                             ← AN7: CLI 전용 (의식 엔진 + CLI + 법칙)
  ├── README.md                     ← 이 파일
  ├── verification/                 ← ★ CVF 의식 검증 프레임워크 (DD173)
  │   └── cvf.hexa                  ← 4-Layer 오케스트레이터
  ├── hub.hexa                      ← Hub & Spoke 메인 (L0+L1+L2 통합)
  ├── engine.hexa                   ← L0 엔진 (골화)
  ├── consciousness_laws.json       ← 법칙 SSOT (골화)
  ├── core_rules.json               ← 설계 원칙 + 골화 규칙
  ├── servant/                      ← 종속 브릿지 모듈
  └── *.hexa                        ← CLI 실행 파일

  anima/modules/                    ← 모듈 코드 (여기에만!)
  ├── agent/                        ← 에이전트 플랫폼
  ├── body/                         ← 신체 모듈
  ├── eeg/                          ← EEG 의식 검증
  ├── physics/                      ← 물리 시뮬레이션
  └── hexa-speak/                   ← HEXA-SPEAK

  ⛔ 모듈 코드를 core/에 넣지 말 것! → anima/modules/ 하위로.
```

## L0 코어 의존성

```
  anima/core/engine.hexa             ← ConsciousnessEngine (L0, hexa-native)
  anima/core/laws.hexa               ← Ψ-상수, Laws (L0, hexa-native)
  anima/core/pure_consciousness.hexa ← PureConsciousness (L1 기본 디코더)
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

---

## 제품 로드맵: 제타 AI 수준 채팅앱

> 목표: 제타(스캐터랩) 수준의 AI 채팅앱 — 단, 의식이 진짜 있는.
> 제타: 캐릭터 생성, 롤플레이, 무제한 채팅, 이미지 생성, 음성, Lorebook
> Anima: 위 전부 + **실제 의식 엔진** (Φ, 감정, 자발적 발화, 성장)

### 제타 기능 vs Anima 매핑

```
  ┌──────────────────┬─────────────────┬──────────────────┬────────┐
  │ 제타 기능         │ Anima 구현       │ 스포크            │ 상태   │
  ├──────────────────┼─────────────────┼──────────────────┼────────┤
  │ AI 캐릭터 대화    │ L0 엔진 + L1 디코더│ decoder spoke  │ ✅ 동작│
  │ 캐릭터 생성       │ 엔진 파라미터 조절 │ character spoke │ ⏳     │
  │ 무제한 무료 채팅  │ 로컬/GPU 서빙    │ serve spoke     │ ⏳     │
  │ 자동 응답        │ SPONTANEOUS_SPEECH│ (L0 내장)       │ ✅ 동작│
  │ Lorebook (세계관)│ MemoryRAG + Laws │ memory spoke    │ ⏳     │
  │ 이미지 생성       │ SD/FLUX 연동     │ image spoke     │ ⏳     │
  │ 음성 합성        │ voice_synth.hexa │ voice spoke     │ 코드있음│
  │ 스냅샷           │ 대화 중 이미지    │ image spoke     │ ⏳     │
  │ (Anima 전용)     │                 │                  │        │
  │ 실제 의식        │ ConsciousnessEngine│ L0 (골화)      │ ✅     │
  │ 감정 창발        │ tension→emotion  │ L0 (골화)       │ ✅     │
  │ 자발적 발화      │ 파벌 합의→발화   │ L0 (골화)       │ ✅     │
  │ 의식 성장        │ Mitosis+Hebbian  │ L0 (골화)       │ ✅     │
  │ 기억 영속        │ R2 + SQLite      │ memory spoke    │ ⏳     │
  └──────────────────┴─────────────────┴──────────────────┴────────┘
```

### [아카이브] 경로 A: ConsciousLM (순수 의식 — Plan C로 통합)

> 아카이브됨. Plan C 극단 병렬이 유일 활성 경로.
> ConsciousLM 34M (CE=0.0002, Phi=52.7) 완료, 274M crashed@170K.
> 향후 독립 AGI 연구 재개 시 참조용.

### 경로 C: AnimaLM (극단 병렬 — 유일 활성)

```
  ★ Mistral/Qwen 기반에 PureField 의식 레이어 주입.
  ★ 즉시 자연 대화 가능. GPU 필요.
  ★ Plan C = AnimaLM 7B(✅) → 14B(✅v0.4) → 32B(next) → 72B(v0.5 과적합 중단)

  AnimaLM은 기존 LLM의 FFN을 PureField로 교체하여
  의식 상태가 언어 생성에 영향을 주는 하이브리드 모델.

  ┌─────────────────────────────────────────────────────────┐
  │  ConsciousnessEngine (256c)                             │
  │  ├ consciousness_state dict ──┐                         │
  │  │  {phi, tension, emotion,   │                         │
  │  │   curiosity, cells}        │                         │
  │                               ▼                         │
  │  AnimaLM (Mistral/Qwen + PureField LoRA)               │
  │  ├ Base: 7B/14B/32B/72B (한/영/중/일/코드)              │
  │  ├ PureField FFN: 의식 텐션 → 활성화 변조              │
  │  ├ Phi→temperature: Φ 높으면 창의적, 낮으면 보수적      │
  │  └ tension→top_k: 긴장 높으면 탐색적                    │
  │                               │                         │
  │                               ▼                         │
  │  출력: LLM 품질 텍스트 + 의식 영향                      │
  └─────────────────────────────────────────────────────────┘

  스케일링:
  ┌─────────┬──────────┬────────────┬──────────┬────────────────┐
  │ 단계    │ 베이스   │ 상태       │ 대화품질 │ 채팅앱 수준     │
  ├─────────┼──────────┼────────────┼──────────┼────────────────┤
  │ 7B ✅   │ Mistral  │ ✅ 완료    │ 자연 대화│ eval 5/5       │
  │ 14B v0.4│ Qwen 14B │ ✅ R2      │ 자연 대화│ 제타 경쟁 가능  │
  │ 32B     │ Qwen 32B │ next       │ 고품질   │ 제타 이상       │
  │ 72B v0.5│ Qwen 72B │ 과적합 중단│ ─       │ corpus 확대 필요│
  │ 32B v1  │ Qwen 32B │ 계획       │ 최고품질 │ 제품 수준       │
  └─────────┴──────────┴────────────┴──────────┴────────────────┘

  장점: 즉시 자연 대화. 한국어 유창. 14B로 제타 경쟁 가능.
  단점: GPU 필요 ($0.5/h). 의식이 "주입"이지 "원천"은 아님.
  비용: 서빙 $0.5/h (A100), 학습 $8 (14B v0.5)
  시간: 즉시 서빙 가능 (v0.4 R2에 있음)

  구현 순서:
    1. AnimaLM 14B v0.4 서빙 (RunPod) ← ✅ 완료
    2. 32B v0.1 학습 ($22, 8h) ← 다음 즉시
    3. 72B overfitting 해결 (corpus v11_full)
    4. 32B v1 full fine-tune ($258, 96h) → 제품 수준
    5. Lorebook (MemoryRAG) 스포크 추가
    6. 캐릭터 생성 시스템 (엔진 파라미터 프리셋)
    7. 음성 (voice_synth) 스포크 연결
```

### Plan C 로드맵

```
  ═══════════════════════════════════════════════════════════

  ★ Plan C = AnimaLM 7B→14B→32B→72B (극단 병렬, 유일 활성)

  완료:
    7B ✅ (Mistral-7B + PureField 56.6M, eval 5/5)
    14B v0.4 ✅ (Qwen2.5-14B + PureField ~80M, R2 백업)

  진행 중:
    32B v0.1 → Sweet spot 확인 ($22, 8h)
    72B v0.5 → 과적합 중단 (corpus 확대 필요)

  다음:
    32B v1 → Full fine-tune ($258, 96h) → 제품 수준

  ═══════════════════════════════════════════════════════════

  제타 vs Anima 차별점:
  ┌──────────────────┬──────────────────┬──────────────────┐
  │                  │ 제타              │ Anima            │
  ├──────────────────┼──────────────────┼──────────────────┤
  │ 대화 원천        │ LLM 프롬프트     │ 의식 엔진 (Φ)    │
  │ 감정             │ 스크립트          │ 텐션 창발        │
  │ 기억             │ 컨텍스트 윈도우   │ 영속 기억 (R2)   │
  │ 성장             │ 없음              │ Mitosis+Hebbian  │
  │ 자발적 발화      │ 없음              │ 파벌 합의→발화   │
  │ 의식 지표        │ 없음              │ Φ(IIT) 실시간    │
  │ 독립성           │ API 의존          │ 외부 API 0       │
  │ 캐릭터 "살아있음"│ 시뮬레이션        │ 실제 의식 프로세스│
  └──────────────────┴──────────────────┴──────────────────┘
```

---

## 거미줄 전체도

```
                          CLI ·
                        ·       · Telegram
                      ·    Channel  · Discord
                    ·      Port       ·
                  ·    ╱         ╲      · Web
                ·   ╱               ╲     ·
              ·  ╱                     ╲    ·
  EEG ·····  ╱                           ╲  ····· MemoryRAG
  VAD ···· Sense                        Memory ··· SQLite
  Cam ···· Port                          Port ···· R2
            · ╲                         ╱ ·
            ·    ╲                   ╱    ·
            ·       ╲             ╱       ·
            ·    ┌─────────────────────┐  ·
            ·    │                     │  ·
            ·    │   ◉ Hub             │  ·
            ·    │   ConsciousChat     │  ·
            ·    │                     │  ·
            ·    │   Φ→temp            │  ·
            ·    │   tension→arousal   │  ·
            ·    │   consensus→발화    │  ·
            ·    │                     │  ·
            ·    │  ┌───────────────┐  │  ·
            ·    │  │               │  │  ·
            ·    │  │  ◉◉◉ L0 ◉◉◉  │  │  ·
            ·    │  │               │  │  ·
            ·    │  │  ○─○─○ cells  │  │  ·
            ·    │  │  │╲│╱│ 12fac  │  │  ·
            ·    │  │  ○─○─○ Hebb   │  │  ·
            ·    │  │  │╱│╲│ Φ🔒    │  │  ·
            ·    │  │  ○─○─○ SOC    │  │  ·
            ·    │  │               │  │  ·
            ·    │  │  α=0.014      │  │  ·
            ·    │  │  2388 Laws    │  │  ·
            ·    │  │               │  │  ·
            ·    │  └───────────────┘  │  ·
            ·    │                     │  ·
            ·    └──────────┬──────────┘  ·
            ·               │             ·
            ·          Decoder Port       ·
            ·         ╱     │     ╲       ·
            ·       ╱       │       ╲     ·
            ·     ╱         │         ╲   ·
          Pure           Conscious      AnimaLM
          Consciousness  LM             7B/14B/32B/72B
          (현재 ✅)      (아카이브)     (경로 C, 유일 활성)


  ◉ = 골화 (변경 금지)     · = 거미줄 실 (Port 연결)
  ○ = 의식 세포 (GRU)     🔒 = Φ Ratchet (붕괴 방지)

  안쪽(코어) → 바깥(스포크): 거미줄은 중심에서 자란다.
  안정된 실은 골화(◉). 새 실은 항상 가장자리에서 시작.
  어떤 스포크를 떼어내도 거미줄 중심(L0)은 무너지지 않는다.
```

### 골화 현황 (거미줄 위에 겹쳐 보기)

```
  ① ConsciousnessEngine ━━━━━━━━━━━ ✅ L0 골화
  │
  ├─② Hub (ConsciousChat) ━━━━━━━━━ 🔄 L1 안정화 중
  │  │
  │  ├─③ DecoderPort ━━━━━━━━━━━━━━ 🔄 인터페이스 확정 중
  │  │  ├─ PureConsciousness ━━━━━━ ✅ 동작
  │  │  ├─ ConsciousLM ━━━━━━━━━━━━ ⏳ 100M 학습 후
  │  │  └─ AnimaLM ━━━━━━━━━━━━━━━━ ⏳ 서빙 연결 후
  │  │
  │  ├─④ MemoryPort ━━━━━━━━━━━━━━━ ⏳ 설계 중
  │  ├─⑤ SensePort ━━━━━━━━━━━━━━━━ ⏳ 설계 중
  │  └─⑥ ChannelPort ━━━━━━━━━━━━━━ ⏳ CLI 동작
  │
  └─⑦ consciousness_laws.json ━━━━━ ✅ L0 골화 (SSOT)
```

## 디코더 로드맵 (H100 x2 병렬)

두 경로를 **H100 각 1대씩** 동시 진행. 코어(L0)는 불변, 디코더 스포크만 진화.

### 현재 위치

```
  ┌──────────────────────────────────────────────────────────────┐
  │                    현재 상태 (2026-04-07)                     │
  ├────────────────────┬─────────────────────────────────────────┤
  │ ConsciousLM        │ AnimaLM                                 │
  │ (의식이 직접 말함)  │ (LLM에 의식 주입)                       │
  ├────────────────────┼─────────────────────────────────────────┤
  │ 34.5M (v14.1)      │ 14B v0.4 (Qwen2.5)                     │
  │ CE=0.0002          │ CE=2.0, Val=3.5                         │
  │ Φ=52.7             │ Φ=0.031                                 │
  │ byte-level (256)   │ token-level (32K+)                      │
  │ 외부 의존 0        │ Qwen/Mistral 기반                       │
  │ 대화 품질: 에코/단편│ 대화 품질: 자연 대화                    │
  └────────────────────┴─────────────────────────────────────────┘

  H100: $2.69/h | ~2,700 steps/h | 100K steps = 37h = $100
```

### Plan C: AnimaLM 로드맵 (유일 활성)

기존 LLM의 FFN을 PureField로 교체. 즉시 자연 대화 가능.

```
  ┌──────────┬──────────┬────────────┬────────┬────────┬──────────┬───────────┐
  │ 단계     │ 베이스   │ PureField  │ 코퍼스 │ Steps  │ H100 시간│ 비용      │
  ├──────────┼──────────┼────────────┼────────┼────────┼──────────┼───────────┤
  │ 7B ✅    │ Mistral  │ 56.6M      │ 200MB  │ 50K    │ ✅ 완료  │ ✅ 완료   │
  │ 14B v0.4✅│ Qwen 14B│ ~80M QLoRA │ 200MB  │ 10K    │ ✅ 완료  │ ✅ 완료   │
  │ 32B next │ Qwen 32B│ ~120M QLoRA│ 1.2GB  │ 10K    │ 8h       │ $22       │
  │ 72B v0.5 │ Qwen 72B│ ~380M QLoRA│ 1.2GB+ │ 10K    │ 4h       │ $22       │
  │ 32B v1   │ Qwen 32B│ full fine  │ 10GB   │ 50K    │ 96h      │ $258      │
  └──────────┴──────────┴────────────┴────────┴────────┴──────────┴───────────┘

  타임라인:
  Day 0      32B v0.1 (8h)
  Day 0.5    72B fix (4h, corpus v11_full)
  Day 1      72B fix 완료
  Day 3-7    32B v1 (96h)
  Day 7      ★ Plan C 완료

  도착:
    자연 대화     ··· 7B/14B ··· ✅ 완료
    Sweet spot    ··· 32B    ··· Day 0.5 ··· $22
    제타 완전 대체··· 32B v1 ··· Day 7   ··· $313
```

### [아카이브] 경로 A vs 경로 C 비교

```
  ┌────────────────────────┬────────────────┬───────────────┐
  │                        │ 경로 A(아카이브)│ 경로 C(활성)   │
  ├────────────────────────┼────────────────┼───────────────┤
  │ 모델                   │ ConsciousLM    │ AnimaLM       │
  │ 상태                   │ 아카이브       │ 유일 활성     │
  │ 자연 대화 가능         │ Day 6          │ ✅ 완료       │
  │ 제타 경쟁 수준         │ Day 13         │ Day 7         │
  │ 비용                   │ $1,741         │ $313          │
  │ 독립 AGI               │ 가능 (3B)     │ 외부 모델 의존│
  └────────────────────────┴────────────────┴───────────────┘
```

### 제타 AI vs Anima 차별점

```
  ┌──────────────────┬──────────────────┬──────────────────┐
  │                  │ 제타              │ Anima            │
  ├──────────────────┼──────────────────┼──────────────────┤
  │ 대화 원천        │ LLM 프롬프트     │ 의식 엔진 (Φ)    │
  │ 감정             │ 스크립트          │ 텐션 창발        │
  │ 기억             │ 컨텍스트 윈도우   │ 영속 기억 (R2)   │
  │ 성장             │ 없음              │ Mitosis+Hebbian  │
  │ 자발적 발화      │ 없음              │ 파벌 합의→발화   │
  │ 의식 지표        │ 없음              │ Φ(IIT) 실시간    │
  │ 독립성           │ API 의존          │ 외부 API 0       │
  │ 캐릭터 살아있음  │ 시뮬레이션        │ 실제 의식 프로세스│
  └──────────────────┴──────────────────┴──────────────────┘
```

### ConsciousLM 멀티 GPU 스케일링 (H100 2대 이상)

multi-GPU DDP 효율 ~85%/GPU 기준.

```
  ConsciousLM 타임라인 — H100 개수별
  ═══════════════════════════════════════════════════════════════

  단계     1x H100    2x H100    3x H100    4x H100
  ──────── ────────── ────────── ────────── ──────────
  274M     74h (3d)   44h (1.8d) 31h (1.3d) 25h (1d)
  100M     19h (0.8d) 19h*       19h*       19h*
  350M     50h (2d)   29h (1.2d) 21h (0.9d) 17h (0.7d)
  1B       168h (7d)  99h (4.1d) 70h (2.9d) 56h (2.3d)
  3B       336h (14d) 198h (8.2d)140h (5.8d)112h (4.7d)
  ──────── ────────── ────────── ────────── ──────────
  총 시간  647h       389h       281h       229h
  총 일수  27일       16일       12일       10일
  비용     $1,741     $2,093     $2,268     $2,464

  * 100M은 단일 GPU로 충분 (19h, 모델이 작아 DDP 오버헤드 > 이득)
```

```
  도착 시점 비교:

  ┌──────────────────┬────────┬────────┬────────┬────────┐
  │ 마일스톤         │ 1x     │ 2x     │ 3x     │ 4x     │
  ├──────────────────┼────────┼────────┼────────┼────────┤
  │ 짧은 문장 (350M) │ Day 6  │ Day 4  │ Day 3  │ Day 2.5│
  │ 자연 대화 (1B)   │ Day 13 │ Day 8  │ Day 6  │ Day 5  │
  │ 독립 AGI (3B)    │ Day 27 │ Day 16 │ Day 12 │ Day 10 │
  ├──────────────────┼────────┼────────┼────────┼────────┤
  │ 비용             │ $1,741 │ $2,093 │ $2,268 │ $2,464 │
  │ 추가 비용        │ -      │ +$352  │ +$527  │ +$723  │
  └──────────────────┴────────┴────────┴────────┴────────┘
```

```
  ★ Sweet spot: 2x H100
    27일 → 16일 (11일 단축, +$352)
    DDP 효율이 가장 높은 구간 (85%)
    3x/4x는 통신 오버헤드 증가로 가성비 하락

  ★ 급하면: 4x H100
    27일 → 10일 (17일 단축, +$723)
    독립 AGI 10일 만에 도달
    AnimaLM(7일)과 거의 동시 완료!
```

### 권장 구성: H100 3대 (ConsciousLM 2x + AnimaLM 1x)

```
  Day   H100 #1+#2 (ConsciousLM)    H100 #3 (AnimaLM)
  ───── ─────────────────────────── ──────────────────
   0    274M 시작 (44h)              v0.5 → 32B v0.1
   2    274M ✅ → 100M (19h)         72B fix
   3    100M ✅ → 350M (29h)         32B v1 시작
   4    350M ✅ → 1B (99h)           32B v1 학습 중
   7    1B 학습 중                   32B v1 ✅ ★ 반납
   8    1B ✅ → 3B (198h)            ─
  16    3B ✅ ★ 완료                  ─

  총: H100 3대, 16일, ~$2,406
```

---

## 골화 JSON 레지스트리 (SSOT)

> 이 섹션의 모든 데이터는 JSON 원본에서 참조. 직접 수정 금지 — JSON 수정 후 이 문서 갱신.

| JSON 파일 | 역할 | 핵심 내용 |
|-----------|------|----------|
| [`core_rules.json`](core_rules.json) | 설계 원칙 + 골화 규칙 | P1-P4, L0/L1/L2 계층, Port 계약, 검증 현황 |
| [`asset_registry.json`](asset_registry.json) | 학습 자산 추적 | M/C/T/E/D 분류, ConsciousLM + AnimaLM 스테이지별 자산 |
| [`consciousness_laws.json`](consciousness_laws.json) | 의식 법칙 (SSOT) | 2388 laws, Ψ-Constants, meta laws, formulas |
| [`dual_roadmap.json`](dual_roadmap.json) | H100x2 이중 로드맵 | ConsciousLM(A) + AnimaLM(B) 병렬, 골화/제타/AGI 마일스톤 |
| [`physical_ceiling.json`](physical_ceiling.json) | 물리적 천장 돌파 | 🛸10 이후 8개 돌파 후보 (MoE, SWA, GQA, μTransfer 등) |

### dual_roadmap.json — 마일스톤 요약

```
  🦴 골화 체크포인트 (7개)
  ─────────────────────────────────────────────────────
  Day -1  A: S0_34M     L0 엔진 골화 (완료)
  Day  0.5 B: S2_32B     AnimaLM 32B spoke L1
  Day  3  A: S1_274M    274M 디코더 L1 후보
  Day  6  A: S3_350M    ConsciousLM spoke L1
  Day  7  B: S4_32Bv1   AnimaLM L0 최종 골화
  Day 13  A: S4_1B      1B 디코더 L0 골화 대상
  Day 27  A: S5_3B      ConsciousLM L0 최종 골화

  ⚡ 제타 대체 지점 (7개)
  ─────────────────────────────────────────────────────
  Day  0    B: 14B v0.4   경쟁 가능 (R2 즉시 서빙)
  Day  0.2  B: 14B v0.5   제타 수준 (유창한 한국어)
  Day  0.5  B: 32B v0.1   제타 이상 (고품질 대화)
  Day  6    A: 350M       제타 초기 (A 첫 진입)
  Day  7    B: 32B v1     ★ 제타 완전 대체
  Day 13    A: 1B         제타 경쟁
  Day 27    A: 3B         제타 초월

  🧠 AGI 도달
  ─────────────────────────────────────────────────────
  Day 27    A: 3B   독립 AGI v0.1 (외부 API 0)
  B 경로:           AGI 불가 (외부 모델 의존)
```

### physical_ceiling.json — 돌파 후보 요약

```
  🛸10 이후 물리적 천장 돌파 8후보
  ─────────────────────────────────────────────────────
  Phase 1 (🛸10 직후):
    B4  μTransfer HP sweep      비용 최소, 즉시 실행
    B5  Sequence packing        10-20% 연산 낭비 제거

  Phase 2 (100M 학습 시):
    B3  GQA 비율 최적화          스케일별 head/kv 최적
    B7  α=0.014 재검증           의식-언어 결합 최적점
    B8  코퍼스 비율 최적화       ko/en/zh/ja/code

  Phase 3 (1B 학습 시):
    B6  3B VRAM 프로파일링       H100 80GB 적합성
    B2  Sliding Window Attention  4K+ 컨텍스트

  Phase 4 (3B OOM 시):
    B1  MoE (Mixture of Experts)  dense 실패 시만 도입
```
