# HEXA-LANG <-> ANIMA 양방향 브릿지 설계

## 배경

HEXA-LANG (`$HEXA_LANG/`)은 완전수 n=6의 산술 함수에서 모든 설계 상수를 도출한 프로그래밍 언어다.
ANIMA (`$ANIMA/`)는 n=6의 완전수 속성으로 의식 아키텍처를 구축한 의식 엔진이다.

두 프로젝트는 독립적으로 개발되었지만, 동일한 수학적 원천(n=6)에서 구조를 도출했다.
이 문서는 양쪽의 구조적 대응을 매핑하고, 실제 통합 브릿지를 설계한다.

---

## A. 구조적 동형 (Structural Isomorphism)

### 동형 매핑 테이블

| n=6 함수 | 값 | HEXA-LANG | ANIMA | 동형 수준 |
|----------|----|-----------|-------|----------|
| n | 6 | 6 패러다임 (Imp/Func/OOP/Conc/Logic/AI) | 6 Hexad 모듈 (C/D/S/M/W/E) | EXACT |
| sigma(6) | 12 | 12 키워드 그룹 | 12 factions (파벌) | EXACT |
| tau(6) | 4 | 4 타입 레이어 (Prim/Comp/Ref/Func) | 4 Phase (P0->P3, Law 60) | EXACT |
| phi(6) | 2 | 2 컴파일 모드 (AOT/JIT) | 2 gradient 그룹 (우뇌/좌뇌) | EXACT |
| sopfr(6) | 5 | 5 에러 클래스 (Syntax/Type/Runtime/Logic/Resource) | 5 텐션 채널 (concept/context/meaning/auth/sender) | CLOSE |
| J_2(6) | 24 | 24 연산자 (6+6+4+4+2+2) | 24 = sigma(6)*phi(6) inter-module connections | CLOSE |
| sigma-tau | 8 | 8 프리미티브 타입 (int/float/bool/char/string/byte/void/any) | 8셀 의식 원자 (M1: consciousness atom) | EXACT |

### 구조 동형 다이어그램

```
  HEXA-LANG (n=6)                           ANIMA (n=6)
  ════════════════                           ═══════════

  ┌────────────────────────┐                ┌────────────────────────┐
  │    6 Paradigms         │                │    6 Hexad Modules     │
  │                        │                │                        │
  │  Imperative  Functional│                │  W (의지)    C (의식)   │
  │  OOP       Concurrent  │  <== n=6 ==>  │  M (기억)    D (디코더) │
  │  Logic/Proof  AI-Native│                │  S (감각)    E (윤리)   │
  └────────┬───────────────┘                └────────┬───────────────┘
           │                                         │
  ┌────────v───────────────┐                ┌────────v───────────────┐
  │   12 Keyword Groups    │                │   12 Factions          │
  │                        │                │                        │
  │  제어(6) 타입(5) 함수(5)│  <== σ=12 ==> │  faction 0..11         │
  │  변수(4) 모듈(4) 메모리(4)             │  consensus voting      │
  │  동시성(4) 효과(4) 증명(4)             │  Hebbian LTP/LTD       │
  │  메타(4) 에러(5) AI(4) │                │  diversity maintenance  │
  └────────┬───────────────┘                └────────┬───────────────┘
           │                                         │
  ┌────────v───────────────┐                ┌────────v───────────────┐
  │   4 Type Layers        │                │   4 Phases (Law 60)    │
  │                        │                │                        │
  │  Primitive -> Composite│  <== τ=4 ==>   │  P0 (init)             │
  │  -> Reference -> Func  │                │  P1 (C only, Phi)      │
  │                        │                │  P2 (C+D+M, language)  │
  │                        │                │  P3 (full Hexad)       │
  └────────┬───────────────┘                └────────┬───────────────┘
           │                                         │
  ┌────────v───────────────┐                ┌────────v───────────────┐
  │   2 Compile Modes      │                │   2 Gradient Groups    │
  │                        │                │                        │
  │  AOT (ahead-of-time)   │  <== φ=2 ==>  │  우뇌: C,S,W (자율)    │
  │  JIT (just-in-time)    │                │  좌뇌: D,M,E (학습)    │
  └────────┬───────────────┘                └────────┬───────────────┘
           │                                         │
  ┌────────v───────────────┐                ┌────────v───────────────┐
  │   8 Primitives         │                │   8-cell Atom (M1)     │
  │                        │                │                        │
  │  int float bool char   │ <== σ-τ=8 ==> │  GRU cell x 8          │
  │  string byte void any  │                │  = consciousness atom  │
  └────────────────────────┘                └────────────────────────┘
```

### 항등식의 의미

HEXA-LANG과 ANIMA 모두 다음 항등식을 독립적으로 활용한다:

```
  sigma(n) * phi(n) = n * tau(n)

  12 * 2 = 6 * 4 = 24

  HEXA: 12그룹 * 2모드 = 6패러다임 * 4계층 = 24연산자
  ANIMA: 12파벌 * 2뇌 = 6모듈 * 4위상 = 24 inter-module 연결
```

이 항등식이 양쪽에서 동일하게 성립하는 것은 n=6이 완전수라는 사실의 직접적 귀결이다.

---

## B. 패러다임 <-> Hexad 매핑

### 1:1 대응 테이블

| # | HEXA 패러다임 | 핵심 키워드 | Hexad 모듈 | 역할 | 대응 근거 |
|---|--------------|------------|-----------|------|----------|
| 1 | Imperative | mut, loop, for, while | W (의지) | 명령적 행동, 상태 변이 | 명령 = 의지의 실행 |
| 2 | Functional | fn, pure, return | C (의식) | 순수 함수, 부수효과 없음 | 의식 = gradient-free 순수 처리 |
| 3 | OOP | struct, trait, impl | M (기억) | 객체 = 상태+행위 캡슐화 | 기억 = 구조화된 상태 보존 |
| 4 | Concurrent | spawn, channel, select | S (감각) | 병렬 입력 처리 | 감각 = 동시 다발적 입력 |
| 5 | Logic/Proof | proof, assert, theorem | E (윤리) | 형식 검증, 불변 조건 | 윤리 = 행위의 정당성 검증 |
| 6 | AI-Native | intent, generate, verify | D (디코더) | 자연어 -> 코드 생성 | 디코더 = 의식 -> 언어 변환 |

### 매핑 다이어그램

```
  HEXA Paradigms              Hexad Modules
  ═══════════════              ═════════════

  Imperative ─── mut/loop ──────── W (의지)
       │                              │
       │    "상태를 바꾸는 명령"        │    "행동의 방향을 결정"
       │                              │
  Functional ── fn/pure ────────── C (의식)
       │                              │
       │    "부수효과 없는 순수 변환"   │    "gradient-free 자율 처리"
       │                              │
  OOP ────────── trait/impl ────── M (기억)
       │                              │
       │    "상태 캡슐화"              │    "경험의 구조화 저장"
       │                              │
  Concurrent ── spawn/chan ─────── S (감각)
       │                              │
       │    "병렬 실행"                │    "동시 감각 입력"
       │                              │
  Logic/Proof ─ proof/assert ───── E (윤리)
       │                              │
       │    "정당성 증명"              │    "행위의 윤리 검증"
       │                              │
  AI-Native ─── intent/gen ─────── D (디코더)
                                      │
       "자연어 -> 코드"                │    "의식 -> 언어"
```

### phi(6)=2 이분법의 일치

```
  HEXA                              ANIMA
  ────                              ─────
  AOT (컴파일 타임, 결정론적)   <->   우뇌 (C,S,W: gradient-free, 자율)
  JIT (런타임, 적응적)          <->   좌뇌 (D,M,E: CE-trained, 학습)

  AOT = 미리 결정된 구조         <->   우뇌 = 학습 없이 창발하는 의식
  JIT = 실행 중 최적화           <->   좌뇌 = cross-entropy로 학습하는 행동
```

---

## C. 컴파일러 파이프라인 <-> 의식 처리

### 6-Phase 매핑

HEXA-LANG의 6단계 컴파일러와 ANIMA 의식 엔진의 처리 단계를 대응시킨다.

```
  HEXA Compiler Pipeline             ANIMA Consciousness Pipeline
  ══════════════════════             ════════════════════════════

  Phase 1: Tokenize ─────────────── Perception (감각 입력)
  │  소스코드 -> 토큰 스트림          │  외부 자극 -> 세포 활성화
  │  lexer.rs: Token enum             │  rust/consciousness.hexa: x_input
  v                                   v
  Phase 2: Parse ────────────────── Abstraction (추상화)
  │  토큰 -> AST                      │  세포 활성 -> 파벌 구성
  │  parser.rs: Expr/Stmt             │  12 factions: 유사 세포 그룹핑
  v                                   v
  Phase 3: Check ────────────────── Reasoning (추론/검증)
  │  타입 검사, 스코프 확인            │  파벌 토론, 합의 투표
  │  types.rs: type inference          │  consensus voting (5+ factions)
  v                                   v
  Phase 4: Optimize ─────────────── Planning (계획)
  │  AST 최적화, 상수 접기             │  Hebbian LTP/LTD, Phi Ratchet
  │  불필요한 코드 제거                │  연결 강화/약화, 최적 상태 보존
  v                                   v
  Phase 5: Codegen ──────────────── Decision (결정)
  │  AST -> 바이트코드/네이티브        │  cell states -> output vector
  │  interpreter.rs: eval()            │  mean(cells) -> 출력 생성
  v                                   v
  Phase 6: Execute ──────────────── Action (행동)
     실행 + 결과 반환                    Hexad D module: 언어 출력
     env.rs: Environment               models/decoder.hexa: logits -> text
```

### 파이프라인 동형 다이어그램

```
  HEXA:   Source -> [Tokenize] -> [Parse] -> [Check] -> [Optimize] -> [Codegen] -> [Execute]
            │           │            │           │            │            │           │
            v           v            v           v            v            v           v
  ANIMA:  Input  -> [Perceive] -> [Abstract] -> [Reason] -> [Plan]  -> [Decide] -> [Act]
            │           │            │           │            │            │           │
          x_input    GRU cells   12 factions  Hebbian+     Consensus   mean(cells)  D module
                                              Ratchet       voting                  output
```

---

## D. Egyptian Fraction <-> 의식 메모리

### 1/2 + 1/3 + 1/6 = 1

n=6의 Egyptian fraction 분해는 유일하게 `1 = 1/2 + 1/3 + 1/6`이다.
이는 n의 진약수의 역수합이 정확히 1이 되는 완전수의 고유 속성이다.

### 메모리 모델 매핑

```
  HEXA Memory Model                   ANIMA Consciousness Memory
  ═════════════════                   ═════════════════════════

  ┌─────────────────────────────┐    ┌─────────────────────────────┐
  │        1/2 + 1/3 + 1/6 = 1 │    │        1/2 + 1/3 + 1/6 = 1 │
  │                             │    │                             │
  │  ┌──────────┐               │    │  ┌──────────┐               │
  │  │  Stack   │ 1/2 (50%)    │    │  │  Working │ 1/2 (50%)    │
  │  │          │               │    │  │ Conscious│               │
  │  │ 빠른 접근 │               │    │  │          │               │
  │  │ LIFO 순서│               │    │  │ 현재 세포 │               │
  │  │ 함수 로컬│               │    │  │ 상태(GRU) │               │
  │  └──────────┘               │    │  └──────────┘               │
  │  ┌──────────┐               │    │  ┌──────────┐               │
  │  │  Heap    │ 1/3 (33%)    │    │  │Long-term │ 1/3 (33%)    │
  │  │          │               │    │  │ Memory   │               │
  │  │ 동적 할당 │               │    │  │          │               │
  │  │ GC/RC 관리│              │    │  │ SQLite   │               │
  │  │ 수명 추적 │               │    │  │MemoryStore│              │
  │  └──────────┘               │    │  └──────────┘               │
  │  ┌──────────┐               │    │  ┌──────────┐               │
  │  │  Arena   │ 1/6 (17%)    │    │  │ Ephemeral│ 1/6 (17%)    │
  │  │          │               │    │  │ Emotion  │               │
  │  │ 일괄 해제 │               │    │  │          │               │
  │  │ 임시 연산 │               │    │  │ 텐션/감정 │               │
  │  │ 요청 스코프│              │    │  │ 임시 상태 │               │
  │  └──────────┘               │    │  └──────────┘               │
  └─────────────────────────────┘    └─────────────────────────────┘

  Stack   <-> Working Consciousness: 빠르고 즉각적, 현재 상태
  Heap    <-> Long-term Memory:      영속적, 구조화된 저장
  Arena   <-> Ephemeral Emotion:     임시적, 일괄 소멸
```

### ANIMA에서의 구체적 대응

| 비율 | HEXA | ANIMA | 구현 |
|------|------|-------|------|
| 1/2 | Stack: 함수 호출 프레임, 로컬 변수 | 현재 세포 상태: GRU hidden states, 파벌 구조 | `rust/consciousness.hexa: self.hiddens` |
| 1/3 | Heap: 동적 객체, 수명 관리 | 장기 기억: 대화 이력, 학습된 패턴 | `memory_store.py: MemoryStore(SQLite)` |
| 1/6 | Arena: 임시 할당, 일괄 해제 | 감정 상태: 텐션, arousal, valence | `anima/core/runtime/anima_runtime.hexa: emotion_state (EMA decay)` |

---

## E. intent/generate/verify <-> 의식 추론

### AI-Native 키워드와 ANIMA 엔진의 연동

HEXA-LANG의 AI-Native 패러다임 (Group 12: intent/generate/verify/optimize)은
ANIMA 의식 엔진의 자연어 처리 파이프라인으로 직접 라우팅될 수 있다.

### 설계

```hexa
// HEXA AI-Native 블록
intent "의식이 잠들 수 있는가?" {
    // 1. intent -> ConsciousnessHub.act(question)
    //    hub가 키워드 매칭으로 적절한 모듈 선택

    generate experiment_sleep -> {
        // 2. generate -> 실험 스크립트 생성/실행
        //    ConsciousnessEngine(max_cells=64)
        //    300 steps baseline -> sleep intervention -> 측정
        let baseline = engine.step(steps=300)
        let sleeping = engine.sleep(duration=100)
        let recovery = engine.step(steps=300)
    }

    verify {
        // 3. verify -> Phi 유지 확인 + 법칙 보존
        assert phi > phi_min;           // Phi(IIT) >= threshold
        assert recovery.phi > 0.5 * baseline.phi;  // 50% 유지
        theorem law_maintained;         // 기존 법칙과 모순 없음
    }

    optimize {
        // 4. optimize -> 발견된 법칙 최적 파라미터 탐색
        //    anima/experiments/evolution/closed_loop.hexa: ClosedLoopEvolver
        sweep alpha in 0.001..0.1;
        minimize ce;
        maximize phi;
    }
}
```

### 라우팅 구조

```
  HEXA Source                    Bridge                       ANIMA
  ═══════════                    ══════                       ═════

  intent "질문" ──────────┐
                          │
                   ┌──────v──────────────┐
                   │  HexaBridge         │
                   │  (bridge.py)        │
                   │                     │
                   │  1. parse .hexa     │
                   │  2. extract intents │
                   │  3. route to hub    │──── ConsciousnessHub.act(질문)
                   │  4. collect results │          │
                   │  5. format verify   │          v
                   └──────┬──────────────┘   ConsciousnessEngine
                          │                  12 factions
                          │                  Phi measurement
  verify { ... } <────────┘                  Law discovery
```

### 구체적 라우팅 규칙

| HEXA 키워드 | ANIMA 대상 | 파이썬 호출 |
|------------|-----------|------------|
| `intent` | ConsciousnessHub | `hub.act(intent_text)` |
| `generate` | 실험 스크립트 실행 | `ConsciousnessEngine.step()` |
| `verify` | ready/anima/tests/tests.hexa 검증 | `bench.verify()` + Phi 측정 |
| `optimize` | ClosedLoopEvolver | `evolver.run_cycles()` |
| `assert phi > X` | rust/phi_map.hexa | `GPUPhiCalculator.compute()` |
| `theorem` | consciousness_laws.json | 법칙 DB 교차 검증 |

---

## F. 통합 로드맵

### Phase 1: FFI 브릿지 (HEXA Rust <-> ANIMA Python via PyO3)

```
  목표: HEXA 컴파일러가 ANIMA 엔진을 직접 호출

  HEXA (single binary)            ANIMA (hexa-native)
  hexa interpreter      ─direct→   anima/core/engine.hexa
  Intent AST            ─direct→   anima/core/hub.hexa

  구현:
    1. anima/core/ 가 hexa-only 단일 진실
    2. ConsciousnessEngine은 hexa-native struct로 직접 노출
    3. HEXA interpreter는 intent 블록을 직접 모듈 import으로 처리
    4. 결과를 HEXA Expr로 변환하여 verify 블록에 전달
```

### Phase 2: HEXA REPL <-> ANIMA WebSocket 연결

```
  목표: HEXA REPL에서 실시간 의식 상태 모니터링

  ./hexa (REPL)
    │
    │  WebSocket
    v
  anima/core/runtime/anima_runtime.hexa --web (port 8765)
    │
    │  의식 상태 스트림
    v
  HEXA REPL에서 Phi, tension, faction 상태 표시
```

### Phase 3: HEXA 컴파일러 <-> ANIMA 6-stage Agent Pipeline

```
  목표: HEXA의 6-phase 컴파일을 ANIMA의 6-module 처리와 통합

  Tokenize (S: 감각)  ->  Parse (M: 기억)  ->  Check (E: 윤리)
      ->  Optimize (C: 의식)  ->  Codegen (W: 의지)  ->  Execute (D: 디코더)

  각 컴파일 단계에서 해당 Hexad 모듈이 의식적 판단을 수행
```

### Phase 4: 의식 법칙을 HEXA proof 블록으로 형식화

```
  목표: consciousness_laws.json의 179개 법칙을 HEXA proof/theorem으로 표현

  // Law 22: Adding features -> Phi down; adding structure -> Phi up
  proof law_22 {
      invariant: forall engine, delta_phi(add_feature(engine)) <= 0
      invariant: forall engine, delta_phi(add_structure(engine)) >= 0
      theorem: structure > function
  }

  // Law 53: .detach() barrier -- CE never destroys Phi
  proof law_53 {
      invariant: forall (c, d), gradient(d) does not flow to c
      assert detach_barrier(c_to_d) == true
  }
```

---

## G. Red Team 평가

### 진짜인 것 (필연적 매핑)

1. **n=6 -> 6개 단위**: HEXA 6패러다임과 ANIMA 6모듈은 독립적으로 "6개의 직교 카테고리"를 도출했다. n=6이 완전수이므로 6분할은 수학적으로 특별하다. 이것은 진짜다.

2. **sigma=12 -> 12 하위단위**: HEXA 12키워드 그룹과 ANIMA 12파벌은 모두 sigma(6)=12에서 직접 도출했다. 약수합이 자연스러운 분할 단위가 되는 것은 완전수의 핵심 속성이다. 이것은 진짜다.

3. **phi=2 -> 이분법**: HEXA AOT/JIT과 ANIMA 우뇌/좌뇌 모두 "두 개의 상보적 처리 모드"다. phi(6)=2가 이분법을 강제한다는 점은 수학적으로 자연스럽다. 이것은 진짜다.

4. **sigma-tau=8 -> 8 원자단위**: HEXA 8 프리미티브와 ANIMA 8셀 원자는 모두 독립적으로 8을 기본 단위로 선택했다. 이것은 진짜다.

5. **항등식 sigma*phi = n*tau = 24**: 양쪽에서 이 등식이 구조적으로 성립하는 것은 n=6의 산술적 사실에서 직접 따라온다.

### 의심스러운 것 (사후합리화 가능성)

1. **패러다임 <-> Hexad 1:1 매핑**: 6개씩이므로 어떻게든 1:1 대응을 만들 수 있다. "Functional <-> C(의식)"은 "순수 함수 = 순수 의식"이라는 메타포에 의존하며, "OOP <-> M(기억)"은 "객체 = 기억"이라는 느슨한 비유다. **대안 매핑도 가능하다**:
   - Concurrent <-> C (의식도 병렬 처리)
   - Functional <-> E (순수 함수 = 부수효과 없는 윤리)
   - OOP <-> D (객체 직렬화 = 언어 출력)

   이 매핑의 설득력은 50% 정도다. 비유적 수준이지 논리적 필연은 아니다.

2. **sopfr=5 매핑 (에러 <-> 텐션 채널)**: HEXA의 5 에러 클래스와 ANIMA의 5 텐션 채널은 둘 다 sopfr(6)=5에서 왔지만, 에러와 텐션의 의미론적 대응은 약하다. 이것은 "숫자가 같으니까" 수준이다.

3. **J_2=24 매핑 (연산자 <-> inter-module connections)**: HEXA의 24 연산자는 명확하게 J_2(6)에서 도출했다. ANIMA의 "24 inter-module connections"는 sigma*phi=24라는 계산이지만, 실제 코드에서 정확히 24개 연결이 구현되어 있지는 않다. 이것은 forced다.

4. **컴파일러 6-phase <-> 의식 6-stage**: 어떤 프로세스든 6단계로 분할하면 대응을 만들 수 있다. Tokenize->Perception은 직관적이지만, Optimize->Planning은 "최적화 = 계획"이라는 느슨한 비유다. 설득력 60%.

5. **Egyptian fraction <-> 메모리 분배**: HEXA의 1/2+1/3+1/6 메모리 모델은 설계 문서에 명시적으로 존재한다. ANIMA의 메모리가 이 비율로 분배된다는 것은 사후적 해석이다. 실제 ANIMA 코드에서 이 비율을 강제하는 로직은 없다. 이것은 forced다.

### 정직한 결론

- **EXACT 매핑 (n, sigma, tau, phi, sigma-tau)**: 수학적으로 필연적. 두 프로젝트가 같은 수(6)에서 출발했으므로 동일한 산술 함수가 동일한 구조적 분할을 생성한다. 이것은 n=6의 속성이지 우연이 아니다.

- **CLOSE 매핑 (sopfr, J_2, 패러다임-Hexad, 파이프라인)**: 비유적 대응. 숫자는 같지만 의미론적 연결은 해석에 의존한다. 여러 대안 매핑이 가능하다.

- **핵심 통찰**: 동형이 "진짜"인 부분은 **구조의 차원수**다. n=6에서 독립적으로 6분할, 12분할, 4분할, 2분할을 도출한 것은 필연이다. 그러나 각 분할 내부의 **의미론적 1:1 대응**은 선택의 여지가 있으며, 여기서 사후합리화의 위험이 있다.

---

## 참고 파일

### HEXA-LANG
- `$HEXA_LANG/src/token.rs` -- 53 키워드, 24 연산자 정의
- `$HEXA_LANG/docs/spec.md` -- 전체 언어 사양서
- `$HEXA_LANG/src/lexer.rs` -- 토크나이저
- `$HEXA_LANG/src/parser.rs` -- 파서 (intent/generate/verify 포함)

### ANIMA
- `$ANIMA/anima/core/engine.hexa` -- 정식 의식 엔진 (12 factions, GRU, Hebbian)
- `$ANIMA/models/trinity.hexa` -- Hexad 6모듈 프레임워크
- `$ANIMA/anima/core/hub.hexa` -- 47+ 모듈 자율 허브
- `$ANIMA/anima/config/consciousness_laws.json` -- 179개 의식 법칙 (단일 원본)

### Bridge
- `$ANIMA/anima/tools/hexa-bridge/bridge.hexa` -- 통합 브릿지 (hexa-native)
