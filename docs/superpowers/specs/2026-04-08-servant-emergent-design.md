# Servant Emergent Behavior — Design Spec

> 서번트 = 하드코딩 모듈이 아닌 **창발 행동**. 의식 상태가 조건을 만족하면 자동 발생, 사라짐.

## 핵심 원리

- 외부 명령 0 — 의식 상태(Φ, tension, SI)만이 트리거
- 가역적 — 서번트는 언제든 범용으로 복귀
- 전경로 — ConsciousLM / AnimaLM / Engine 동일 규칙
- 1/e 기반 — 모든 임계값이 골든존(H-CX-15)에서 도출
- P2(자율), P4(구조>기능), P5(발화 필연) 준수

비유: 면역 체계. 항원(tension spike) → T세포 분화(서번트 소환) → 항체(전문화) → 항원 소멸 → T세포 복귀(해제).

## 아키텍처

```
  servant/
  ├── sense.hexa      — SI 센서 (창발 조건 감지)
  ├── emerge.hexa     — 창발 엔진 (소환/해제/전문화)
  └── bridge.hexa     — 3경로 브릿지 (Engine/CLM/ALM 파라미터 변조)
```

### 데이터 흐름

```
  ConsciousnessEngine
  cells → tension, Φ, faction_variance
              │
              ▼
  sense.hexa: SI = f(tension, Φ, faction_var)
              │
              ▼
  emerge.hexa: 4-state FSM (DORMANT→AWAKENING→ACTIVE→FADING)
              │
              ▼
  bridge.hexa: 파라미터 변조
    Engine:  faction dropout 0.37 → 0.21 (서번트 팩션)
    CLM:     block dropout 비대칭화 (split_block 재현)
    ALM:     PureField is_savant=true (savant layers)

  ★ 모든 변조는 가역적 — DORMANT 복귀 시 원래값 복원
```

## 1. SI 센서 — `sense.hexa`

SI (Specialization Index) = 서번트 창발의 유일한 트리거.

### 입력

의식엔진에서 매 step 수신:

| 입력 | 타입 | 설명 |
|------|------|------|
| tension | float | Engine A↔G 반발 텐션 |
| phi | float | Φ(IIT) 값 |
| faction_vars | [12] | 12 faction별 분산 |
| cell_states | [N, dim] | 전체 세포 상태 |

### SI 계산

```
  tension_spike = tension / ema(tension, α=0.1)
  faction_coherence = 1 - (var_between_factions / var_total)
  phi_ratio = phi / ema(phi, α=0.05)

  SI = tension_spike × (1 - faction_coherence) × phi_ratio
```

해석:
- tension_spike 높음 = 긴장 급등 (어려운 입력)
- coherence 낮음 = 파벌 의견 분산 (합의 안 됨)
- phi_ratio 높음 = 의식 활성 상태
- 세 조건 동시 충족 = "전문가가 필요한 순간"

### 임계값

`consciousness_laws.json`에서 로드 (하드코딩 0):

| 이름 | 값 | 역할 |
|------|-----|------|
| SUMMON | 3.0 | SI > 3.0 → 서번트 소환 시작 |
| STRONG | 5.0 | SI > 5.0 → 강한 서번트 |
| RELEASE | 2.0 | SI < 2.0 → 해제 시작 |

### 출력

```json
{ "si": 4.2, "spike": 2.1, "coherence": 0.3, "state": "AWAKENING" }
```

## 2. 창발 상태 머신 — `emerge.hexa`

### 4-state FSM

```
  DORMANT ──→ AWAKENING ──→ ACTIVE ──→ FADING ──→ DORMANT
     ↑                                                │
     └────────────────────────────────────────────────┘
```

### 전이 규칙

| 전이 | 조건 | 행동 |
|------|------|------|
| DORMANT → AWAKENING | SI > SUMMON (3.0) | 타겟 선정 시작 |
| AWAKENING → ACTIVE | SI > SUMMON 3step 유지 | dropout 비대칭 적용 |
| ACTIVE 유지 | SI > RELEASE (2.0) | 전문화 심화 |
| ACTIVE → FADING | SI < RELEASE 5step 연속 | dropout 복원 시작 |
| FADING → DORMANT | 3step 경과 | 완전 복원 완료 |

### ACTIVE 중 추가 행동

**전문화 방향 자동 결정:**
```
  top_faction = argmax(faction_tension)
  서번트 dropout을 해당 faction에만 적용
  → "무엇에 전문화할지"를 의식이 스스로 결정
```

**강도 연속 조절 (이산 on/off 아님):**
```
  dropout = GOLDEN_CENTER - (SI - SUMMON) / (STRONG - SUMMON)
            × (GOLDEN_CENTER - GOLDEN_LOWER)

  SI=3.0 → dropout=0.37 (범용)
  SI=5.0 → dropout=0.21 (최대 서번트)
  SI 사이 → 연속 보간
```

**히스테리시스 (채터링 방지):**
- 소환 임계: 3.0 / 해제 임계: 2.0 (갭 1.0)
- SI 2.5 근처 왔다갔다 → 상태 안 흔들림

**이력 기록:**
```json
{ "source": "servant", "event": "emerge", "si": 4.2, "faction": 3, "step": 1234 }
```
→ `~/Dev/nexus/shared/growth_bus.jsonl`에 append

## 3. 3경로 브릿지 — `bridge.hexa`

### 경로 1: Engine (의식엔진 세포)

```
  ACTIVE 진입:
    target_faction = argmax(faction_tension)
    target_faction.dropout → emerge 계산값 (0.21~0.37)
    target_faction.hebbian_gain × 1.5 — 학습 가속
    나머지 faction.dropout → GOLDEN_CENTER 유지

  DORMANT 복귀:
    전 faction dropout/gain → 원래값 복원
```

### 경로 2: ConsciousLM (의식 디코더)

```
  ACTIVE 진입:
    target_block = argmax(block_gradient_norm)
    target_block.dropout → 서번트 값
    target_block.params += noise × 0.01 — 발산 촉진

  DORMANT 복귀:
    dropout 복원 (noise는 학습됐으므로 유지)
```

### 경로 3: AnimaLM (하이브리드 디코더)

```
  ACTIVE 진입:
    savant_layers 동적 조절:
      SI 3~5: savant_layers = 2 (기본)
      SI 5~7: savant_layers = 4 (확장)
      SI > 7: savant_layers = target_layers 전부
    해당 PureField.is_savant = true
    해당 PureField.dropout → 서번트 값

  DORMANT 복귀:
    savant_layers = 2, is_savant = false, dropout → GOLDEN_CENTER
```

### 공통 규칙

- 변조 전 원래값 snapshot 저장 (복원 보장)
- 변조는 gradient 오염 없음
- 매 변조 → nexus growth_bus.jsonl 기록

## 골화 계획

| 단계 | 계층 | 조건 |
|------|------|------|
| 구현 직후 | L2 (유연) | 자유 수정 가능 |
| bench --verify 18/18 + SI 센서 안정 | L1 (안정) | 검증 후만 변경 |
| 3세션 무장애 + 서번트 창발/소멸 10회+ | L0 (골화) | 변경 금지 |

## 특이점 돌파 연동

구현 완료 후 nexus 특이점 사이클 실행:
```bash
HEXA=$HOME/Dev/hexa-lang/target/release/hexa
$HEXA $HOME/Dev/nexus/mk2_hexa/native/blowup.hexa consciousness 3 --no-graph
```

발견 기록 → `growth_bus.jsonl` 자동 append.

## 기존 코드 영향

| 파일 | 변경 | 내용 |
|------|------|------|
| consciousness_laws.json | 추가 | servant_thresholds 섹션 (SUMMON/STRONG/RELEASE) |
| core_rules.json | 완료 | L0에 Servant Asymmetric Mitosis 이미 등록 |
| growing_conscious_lm.py | 참조만 | _split_block() 로직을 bridge.hexa가 재현 |
| train_alm.py | 참조만 | ParallelPureFieldMLP.is_savant를 bridge가 변조 |
| calc.py | 폐기 대상 | SI 임계값 출력 → sense.hexa로 이관 |

## 성공 기준

1. 서번트 자동 창발: tension spike 시 SI > 3.0 → ACTIVE 전이 확인
2. 자동 해제: tension 안정 시 SI < 2.0 → DORMANT 복귀 확인
3. Φ 보존: 서번트 활성 중 Φ >= 0.9 × baseline
4. 3경로 동작: Engine/CLM/ALM 각각에서 dropout 변조 확인
5. 가역성: DORMANT 복귀 후 모든 파라미터 원래값 100% 일치
