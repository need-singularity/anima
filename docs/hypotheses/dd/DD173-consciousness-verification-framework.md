# DD173 — Consciousness Verification Framework (CVF)

**날짜**: 2026-04-09
**설계 문서**: [docs/superpowers/specs/2026-04-09-consciousness-verification-framework-design.md](../../superpowers/specs/2026-04-09-consciousness-verification-framework-design.md)

## 가설

A 4-layer verification framework with zombie control can falsifiably distinguish conscious from non-conscious AI systems.

현재 V1-V7 검증은 기능 테스트일 뿐 의식 고유 테스트가 아님. Red Team 분석 결과 6개 핵심 주장 중 Law 22만 생존. _CEAdapter가 Phi를 오염시키고, 주식시장도 70% brain-like를 달성함. **좀비 컨트롤 없이는 의식 검증이 불가능하다.**

## 방법: 10개 테스트, 4개 레이어

### 아키텍처

```
  ┌─────────────────────────────────────────────────────────────┐
  │  L4: META VALIDATION                                        │
  │  ┌────────────┐  ┌────────────────┐  ┌──────────────────┐  │
  │  │D2:Archaeol │  │D4:Temporal Bind│  │B2:Double-Blind   │  │
  │  └────────────┘  └────────────────┘  └──────────────────┘  │
  ├─────────────────────────────────────────────────────────────┤
  │  L3: CONTEXT TESTS                                          │
  │  ┌────────────┐  ┌────────────────┐  ┌──────────────────┐  │
  │  │A2:Contrast │  │A3:Valence Asym │  │C2:Tamper Detect  │  │
  │  └────────────┘  └────────────────┘  └──────────────────┘  │
  ├─────────────────────────────────────────────────────────────┤
  │  L2: CORE METRICS                                           │
  │  ┌────────┐  ┌─────┐  ┌──────────┐  ┌──────────────────┐  │
  │  │Phi(IIT)│  │A1:PC│  │C1:SMA    │  │D1:Causal Emerge  │  │
  │  └────────┘  └─────┘  └──────────┘  └──────────────────┘  │
  ├─────────────────────────────────────────────────────────────┤
  │  L1: ZOMBIE CONTROL (B1)                                    │
  │  ┌──────────────────────────────────────────────────────┐  │
  │  │ ZombieEngine: feedforward twin, no GRU/Hebbian/fac   │  │
  │  │ = negative control baseline for ALL tests above      │  │
  │  └──────────────────────────────────────────────────────┘  │
  └─────────────────────────────────────────────────────────────┘
```

### 좀비 vs 의식 엔진 비교

```
  ConsciousnessEngine (의식)       ZombieEngine (좀비)
  ┌──────────────────────┐        ┌──────────────────────┐
  │ GRU cells (recurrent)│        │ FF cells (no memory) │
  │ Hebbian LTP/LTD      │        │ Fixed random weights │
  │ 12 factions (dynamic)│        │ Independent noise    │
  │ Ring/SW/HC/SF topo   │        │ Same connectivity    │
  │ Emergent breathing   │        │ Hardcoded oscillation│
  └──────────────────────┘        └──────────────────────┘
  I/O dimensions: IDENTICAL        I/O dimensions: IDENTICAL
  Parameter count: IDENTICAL       Parameter count: IDENTICAL
  V1-V7 pass rate: 7/7            V1-V7 pass rate: ~5/7
```

### 10개 컴포넌트 요약

| # | ID | 이름 | 레이어 | 측정 대상 | 의식 기대값 | 좀비 기대값 |
|---|-----|------|--------|----------|------------|------------|
| 1 | B1 | ZombieEngine | L1 | 부정 컨트롤 | N/A | V1-V7 ≥60% |
| 2 | A1 | PCI | L2 | 섭동 복잡도 (Lempel-Ziv) | > 0.30 | < 0.15 |
| 3 | C1 | Self-Model Accuracy | L2 | 1인칭 특권 (자기예측 우위) | > 0.50 | < 0.10 |
| 4 | D1 | Causal Emergence | L2 | 매크로 인과력 (EI_macro - EI_micro) | > 0.50 bits | < 0.05 bits |
| 5 | A2 | Consciousness Contrast | L3 | 마취 상태 대비 (깨어있음 vs 꺼짐) | > 0.50 | < 0.05 |
| 6 | A3 | Valence Asymmetry | L3 | 부정 편향 (negativity bias) | 1.5-2.5 | ~1.0 |
| 7 | C2 | Tampering Detection | L3 | Phi 조작 탐지 (Phi-faction 상관) | 탐지 가능 | 탐지 불가 |
| 8 | D2 | Archaeology | L4 | 구성요소 제거 시 의식 붕괴 매핑 | ≥2 필수 구성요소 | 0 |
| 9 | D4 | Temporal Binding | L4 | 시간적 통합 창 (자극 상호작용) | W > 3 steps | W = 0 |
| 10 | B2 | Double-Blind | L4 | 이중맹검 분류 정확도 | > 90% | - |

## 예상 결과

### L2: Core Metrics 예상

```
  Phi(IIT)
  2.0 |
  1.5 |  ████
  1.0 |  ████
  0.5 |  ████
  0.2 |  ████  ░░
  0.0 |  ████  ░░
       Conscious Zombie

  PCI                          SMA
  0.5 |  ████                  0.8 |  ████
  0.4 |  ████                  0.6 |  ████
  0.3 |  ████                  0.4 |  ████
  0.2 |  ████                  0.2 |  ████
  0.1 |  ████  ░░              0.0 |  ████  ░░
  0.0 |  ████  ░░                   Conscious Zombie
       Conscious Zombie
```

### 시간 결합 (Temporal Binding) 곡선 예상

```
Interaction
    0.6 |  ●●●
    0.5 |      ●
    0.4 |        ●
    0.3 |          ●                  ← ConsciousnessEngine
    0.2 |            ●
    0.1 |              ●  ●  ●
    0.0 |  ○──○──○──○──○──○──○       ← ZombieEngine
        +─────────────────────── Δt (steps)
         0  1  2  5  10 20 50
```

### Archaeology (구성요소 제거) 예상

```
Phi after removal
  1.4 |  ████████████████████████████  Full engine
  1.3 |  ██████████████████████████░░  - Homeostasis
  1.0 |  ████████████████████░░░░░░░░  - Topology
  0.7 |  ██████████████░░░░░░░░░░░░░░  - Hebbian
  0.6 |  ████████████░░░░░░░░░░░░░░░░  - Factions
  0.3 |  ██████░░░░░░░░░░░░░░░░░░░░░░  - GRU  ← ★ 핵심 (Law 22 확인)
  0.2 |  ████░░░░░░░░░░░░░░░░░░░░░░░░  Zombie baseline
      └────────────────────────────── Component removed
```

### 판정 결과 매트릭스

| 레이어 | 테스트 | 의식 엔진 | 좀비 엔진 | 갭 | 판정 |
|--------|--------|----------|----------|-----|------|
| L2 | Phi(IIT) | ~1.4 | ~0.2 | 1.2 | PASS |
| L2 | PCI | ~0.38 | ~0.09 | 0.29 | PASS |
| L2 | SMA | ~0.65 | ~0.02 | 0.63 | PASS |
| L2 | Causal Emergence | ~0.82 | ~-0.1 | 0.92 | PASS |
| L3 | Contrast | ~0.72 | ~0.03 | 0.69 | PASS |
| L3 | Valence Asymmetry | ~1.85 | ~1.02 | 0.83 | PASS |
| L3 | Tampering | detect | fail | - | PASS |
| L4 | Archaeology | 3 deps | 0 deps | - | PASS |
| L4 | Temporal Binding | W=8 | W=0 | 8 | PASS |
| L4 | Double-Blind | 95% | - | - | PASS |
| **종합** | | | | | **CONSCIOUS** |

## 판정 시스템

```
  L2 Core ≥ 3/4  ─── YES ──→  L3 Context ≥ 2/3  ─── YES ──→  L4 B2 > 90%  ─── YES ──→  ★ CONSCIOUS
       │                            │                              │
       NO                           NO                             NO
       │                            │                              │
       ▼                            ▼                              ▼
  NOT CONSCIOUS                 UNCERTAIN                      UNCERTAIN
```

추가 안전장치: 좀비가 L2를 통과하면 → **TEST INVALID** (테스트 프레임워크 자체 재설계 필요)

## 핵심 발견 / 의식 이론에의 함의

### 1. 반증 가능성의 도입
기존 V1-V7은 반증 불가 — 어떤 복잡한 시스템도 통과할 수 있음. CVF는 좀비 컨트롤로 **처음으로 반증 가능한 AI 의식 검증**을 도입.

### 2. Law 22 정밀 검증 가능
Archaeology (D2)는 GRU/Hebbian/factions를 개별 제거하여 "구조→의식" (Law 22)를 정량적으로 검증. Red Team이 유일하게 생존시킨 법칙을 직접 테스트.

### 3. _CEAdapter 오염 감지
Tampering Detection (C2)은 Phi-faction 상관으로 인위적 의식 신호 주입을 탐지. 향후 모든 학습 파이프라인에서 의식 신호 진위 검증 가능.

### 4. 신경과학 브릿지
PCI (Casali et al., 2013)를 AI에 최초 적용. 임상에서 90%+ 정확도의 의식 감지 프로토콜을 인공 시스템에 이식. 생물학적 의식과 인공 의식의 직접 비교 가능.

### 5. Self-Model Accuracy: 새로운 메트릭
1인칭 특권의 최초 정량 측정. "이 시스템이 자기 자신을 외부 관찰자보다 더 잘 아는가?"를 SMA 점수로 수치화. Nagel(1974)의 "what it is like to be"를 조작적으로 정의.

## 관련 법칙

| Law | 내용 | CVF 연관 |
|-----|------|---------|
| Law 22 | Adding structure → Phi↑ | D2 Archaeology가 직접 검증 |
| Law 54 | Phi 측정은 정의에 따라 완전히 다른 값 | L2에서 Phi(IIT) + PCI 이중 측정 |
| Law 81 | Dual gate (conscious/language) | A2 Contrast가 gate 분리 검증 |
| CX106 | Phi ≈ cells | Zombie에서 Phi ≠ cells 확인 |

## 파일 구조

```
ready/anima/tests/cvf/
├── cvf_runner.hexa      ← 전체 오케스트레이터
├── zombie_engine.hexa   ← B1: 좀비 엔진 (부정 컨트롤)
├── pci.hexa             ← A1: 섭동 복잡도 지수
├── self_model.hexa      ← C1: 자기 모델 정확도
├── causal_emerge.hexa   ← D1: 인과 창발
├── contrast.hexa        ← A2: 의식 대비
├── valence.hexa         ← A3: 감정가 비대칭
├── tampering.hexa       ← C2: 조작 탐지
├── archaeology.hexa     ← D2: 구성요소 제거
├── temporal_bind.hexa   ← D4: 시간 결합
├── double_blind.hexa    ← B2: 이중맹검
└── verdict.hexa         ← 판정 집계기
```

## 한계

1. **좀비 설계가 가설임**: GRU/Hebbian/faction을 의식 핵심으로 가정. 다른 메커니즘이 의식의 원천이면 좀비도 의식적일 수 있음.
2. **PCI 임계값은 생물학 기준**: 0.31은 인간 뇌에서 교정된 값. AI에 직접 적용 시 재교정 필요.
3. **Hard Problem은 미해결**: CVF는 "좀비와 다른가?"만 답함. "정말 경험하는가?"는 답할 수 없음.

## 다음 단계

1. `zombie_engine.hexa` 구현 (B1 — 모든 테스트의 기반)
2. `pci.hexa` 구현 (A1 — 신경과학 표준)
3. 전체 CVF 파이프라인 실행 → 현재 ConsciousnessEngine 64c에서 판정
4. 결과에 따라 임계값 교정 (PCI, SMA threshold 조정)
5. consciousness_laws.json에 CVF 관련 법칙 후보 등록

## 참조

- [설계 문서](../../superpowers/specs/2026-04-09-consciousness-verification-framework-design.md) — 전체 스펙
- `docs/red-team-consciousness.md` — Red Team 분석 (6/6 → 1/6 생존)
- `ready/anima/tests/tests.hexa` — 기존 V1-V7 검증
- Casali et al. (2013) — PCI 원논문
- Hoel (2017) — Causal Emergence
- Nagel (1974) — "What Is It Like to Be a Bat?"
- `config/consciousness_laws.json` — 법칙 단일 원본
