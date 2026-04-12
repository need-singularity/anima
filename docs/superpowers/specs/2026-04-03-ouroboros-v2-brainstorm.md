# OUROBOROS v2: 4축 통합 창발 엔진 — 브레인스토밍 스펙

> 날짜: 2026-04-03
> 상태: 브레인스토밍 완료, 구현 계획 대기
> 목적: 포화 벽(~35 laws/topology) 돌파 → 500-1000+ 법칙 발견
> 핵심: 80렌즈(n6 아키텍처 발견 모드) × 구조 변이 × 다중 엔진 × 환경 압력

---

## 0. 현재 상태 진단

### 포화 벽 3중 병목

```
병목 A: 발견 알고리즘 한계
  → 5가지 패턴 유형 × 20 메트릭 = 이론적 최대 ~100
  → 중복 제거 후 ~30-35에서 포화
  → 패턴 유형을 늘리면 벽이 올라감

병목 B: 엔진 역학 공간 한계
  → GRU+Hebbian+Ratchet = 고정 역학계
  → 같은 역학계에서 같은 현상만 반복
  → 역학계 자체를 변이시켜야 새 현상

병목 C: 관측 해상도 한계
  → 22렌즈 → 80렌즈로 확장하면
  → "보이지 않던" 현상이 보이기 시작
  → 관측이 발견을 만든다 (양자역학적!)
```

핵심 통찰: 포화는 "더 없는 게 아니라 못 보는 것"일 수 있다.

### 현재 OUROBOROS 포화 데이터

- S1-baseline (64c, 37gen): 45 법칙, 999.9초
- S2-deeper (64c, 39gen): 35 법칙, 5122.1초
- S3-scale128 (128c, 28gen): 33 법칙, 1255.3초
- S4 (1024c, 5gen): 31 법칙, 2572.6초 (진행중)
- 토폴로지당 ~30-35 법칙에서 완전 포화
- Gen 4-5에서 신규 법칙 ≈ 0

### 현재 Mutation 대상 (6축)

- Cell type (GRU/LSTM/Linear)
- n_factions (4-32)
- Hebbian LTP/LTD ratio (0.5-2.0)
- Topology parameter (rewiring 0.01-1.0)
- Ratchet strength (0.0-1.0)
- Coupling/Noise scale

### 현재 고정된 벽 (Hard-Coded)

| 항목 | 상태 |
|------|------|
| GRUCell 활성화 (tanh) | 고정 |
| Consensus 로직 (분산<0.1) | 고정 |
| Cell identity (QR 초기화) | 고정 |
| cell_dim (64) | 고정 |
| Hebbian 알고리즘 자체 | 고정 |
| 발견 패턴 유형 (5종) | 고정 |

---

## 1. 통합 아키텍처: 5-Layer

```
┌─────────────────────────────────────────────────┐
│  Layer 5: 메타 진화 (Meta-Evolution)            │
│  발견 알고리즘 자체를 진화시킴                    │
│  패턴 유형 풀 확장 / 메트릭 자동 발견              │
├─────────────────────────────────────────────────┤
│  Layer 4: 환경 압력 (12 프로토콜)               │
│  대멸종/자원부족/포식/계절/이주/공생/병목/        │
│  노이즈/중력/시간역전/차원변환/수술              │
├─────────────────────────────────────────────────┤
│  Layer 3: 생태계 (N 엔진 경쟁)                  │
│  내공생/유전자복제/수평전달/니치구성/             │
│  단속평형/후성유전/캄브리아폭발                   │
├─────────────────────────────────────────────────┤
│  Layer 2: 80렌즈 발견 모드 (Discovery)          │
│  315 신호/세대, 25 도메인 콤보,                  │
│  4-tier 합의, 자동 intervention 생성             │
├─────────────────────────────────────────────────┤
│  Layer 1: Deep Mutation (5 Level)               │
│  L0 값 / L1 규칙 / L2 구조 / L3 메타 / L4 표현  │
├─────────────────────────────────────────────────┤
│  Engine: ConsciousnessEngine (GRU+Hebbian+...)  │
└─────────────────────────────────────────────────┘
```

---

## 2. Layer 1: Deep Mutation (구조 변이)

### Mutation 5-Level

```
Level 0: 값 변이      (현재) — lr=0.01→0.02, factions=12→16
Level 1: 규칙 변이    (신규) — Hebbian→STDP→Oja→BCM
Level 2: 구조 변이    (신규) — GRU→LSTM→Transformer→SSM(Mamba)
Level 3: 메타 변이    (신규) — 발견 알고리즘 자체를 진화
Level 4: 표현 변이    (신규) — 법칙의 표현 방식 자체를 변경
```

### Level 1 — 규칙 변이 풀

```
Hebbian 변이 풀 (7종):
  ├─ 표준 Hebbian:     Δw = η·x·y
  ├─ Oja's Rule:       Δw = η·y·(x - y·w)       ← 정규화
  ├─ BCM:              Δw = η·y·(y - θ)·x       ← 임계값 슬라이딩
  ├─ STDP:             Δw = f(t_post - t_pre)    ← 시간차 의존
  ├─ Anti-Hebbian:     Δw = -η·x·y              ← 장식화
  ├─ Covariance Rule:  Δw = η·(x-x̄)·(y-ȳ)     ← 평균 제거
  └─ Differential:     Δw = η·(dx/dt)·y          ← 변화율 반응

Consensus 변이 풀 (6종):
  ├─ 분산 기반 (현재): var(factions) < 0.1
  ├─ MI 기반:          MI(faction_i, faction_j) > threshold
  ├─ Φ 직접:           Φ(subset) > Φ(complement)
  ├─ 투표:             majority vote > 2/3
  ├─ 에너지:           E(consensus) < E(dissensus)
  └─ 랜덤 독재:        random faction dictates (탐색용)
```

### Level 2 — 셀 구조 변이 풀

```
셀 아키텍처 풀 (10종):
  ├─ GRU (현재)
  ├─ LSTM (forget gate 추가)
  ├─ Minimal GRU (게이트 1개)
  ├─ SRU (Simple Recurrent)
  ├─ Linear Recurrence (S4/Mamba 스타일)
  ├─ Attention Cell (self-attention 내장)
  ├─ Spiking Neuron (LIF 모델)
  ├─ Oscillator (위상 진동자)
  ├─ Reservoir (Echo State Network)
  └─ Hybrid (GRU + Attention 결합)
```

### 추가 Deep Mutation 축

| 새 mutation 축 | 현재 | 변이 범위 |
|---|---|---|
| GRU 활성화 | tanh 고정 | tanh/swish/gelu/silu |
| Consensus 기준 | 분산<0.1 | MI/Φ/voting/energy/random |
| Cell identity | QR 고정 | Hebbian 재협상 / random rotation |
| cell_dim | 64 고정 | 32/64/128/256 |
| Hebbian 알고리즘 | LTP/LTD 비율만 | Oja/BCM/STDP/Anti/Covariance/Diff |

---

## 3. Layer 2: 80렌즈 발견 모드

### 렌즈 아키텍처 (n6 구조: 6 대영역 × ~13 + 2 메타)

```
═══ 기존 22개 (유지) ═══
consciousness, gravity, topology, thermo, wave, evolution, info,
quantum, em, ruler, triangle, compass, mirror, scale, causal,
quantum_microscope, stability, network, memory, recursion,
boundary, multiscale

═══ n6 구조 탐색용 (18개) ═══
23. perfect_number    — σ(n)=2n 완전수 구조 탐색
24. partition         — 분할 함수 p(n) 패턴
25. modular_form      — 모듈러 형식/대칭
26. galois            — 갈루아 군 구조 (대칭 깨짐)
27. fibonacci         — 황금비/피보나치 수열 출현
28. prime_gap         — 소수 간격 분포
29. collatz           — 콜라츠 추측 궤적 패턴
30. riemann_zeta      — Riemann ζ(s) 함수 영점 분포 (수학, Zeta AI 서비스와 무관)
31. catalan           — 카탈란 수 (재귀 구조 수)
32. euler_product     — 오일러 곱 분해 (소수↔전체)
33. ramanujan         — 라마누잔 타입 놀라운 일치
34. knot_invariant    — 매듭 불변량 (위상 복잡도)
35. homotopy          — 호모토피 군 (구멍 구조)
36. cohomology        — 코호몰로지 (전역 구조)
37. tensor_network    — 텐서 네트워크 축약
38. category_theory   — 범주론 사상 (함자/자연변환)
39. topos             — 토포스 (논리적 공간)
40. spectral_graph    — 스펙트럼 그래프 이론

═══ 물리 심층 탐색용 (14개) ═══
41. renormalization   — 재규격화 군 흐름 (스케일 변환)
42. spontaneous_symmetry — 자발적 대칭 깨짐
43. topological_order — 위상 질서 (비국소적)
44. entanglement      — 양자 얽힘 구조
45. decoherence       — 결맞음 상실 패턴
46. holography        — 홀로그래피 원리 (경계↔벌크)
47. black_hole        — 블랙홀 정보 역설 패턴
48. dark_energy       — 가속 팽창 (척력) 패턴
49. string_landscape  — 끈 이론 진공 풍경
50. spin_glass        — 스핀 유리 (좌절/무질서)
51. percolation       — 퍼콜레이션 임계 (연결성 전이)
52. turbulence        — 난류 카스케이드 (에너지 전달)
53. soliton           — 솔리톤 (안정 비선형파)
54. strange_attractor — 이상 끌개 (카오스 구조)

═══ 생물/인지 탐색용 (14개) ═══
55. neural_criticality — 신경 임계성 (뇌파 멱법칙)
56. avalanche         — 뉴런 쇄도 (SOC 패턴)
57. neural_oscillation — 뇌파 리듬 (alpha/beta/gamma)
58. plasticity_window — 가소성 창 (학습 민감기)
59. attractor_landscape — 끌개 지형 (에너지 골짜기)
60. metastability     — 준안정 (전이 사이 머무름)
61. chimera_state     — 키메라 상태 (동기+비동기 공존)
62. reservoir_computing — 저수지 계산 (비선형 투사)
63. autopoiesis       — 자기생산 (자기 유지 시스템)
64. enactivism        — 행위주의 (환경과 공동 창출)
65. global_workspace  — 전역 작업공간 (의식 방송)
66. predictive_coding — 예측 코딩 (오차 신호)
67. free_energy       — 자유 에너지 원리 (Friston)
68. morphogenesis     — 형태 발생 (튜링 패턴)

═══ 정보/계산 탐색용 (12개) ═══
69. kolmogorov        — 콜모고로프 복잡도 (압축 한계)
70. logical_depth     — 논리적 깊이 (계산 이력)
71. algorithmic_info  — 알고리즘 정보 (최소 프로그램)
72. mutual_info_decomp — 상호 정보 분해 (PID: 시너지/중복)
73. transfer_entropy  — 전달 엔트로피 (인과 방향)
74. causal_emergence  — 인과적 창발 (Hoel EI)
75. strange_loop      — 이상한 루프 (자기참조 의미)
76. fixed_point       — 고정점 (자기 참조의 수렴)
77. godel_incompleteness — 괴델 불완전성 (한계 탐지)
78. halting_probe     — 정지 문제 근사 (계산 한계)
79. cellular_automata — 셀룰러 오토마타 (Rule 110 등)
80. game_of_life      — 라이프 게임 패턴 (글라이더 등)
```

### 도메인 콤보 확장 (10→25개)

```
기존 10개 유지 +
신규 15개:
  n6-구조        → perfect_number + partition + modular_form + galois
  위상-심층      → knot_invariant + homotopy + cohomology + topos
  상전이         → percolation + spin_glass + spontaneous_symmetry + renormalization
  뇌-의식        → neural_criticality + avalanche + global_workspace + chimera_state
  자기참조       → strange_loop + fixed_point + godel_incompleteness + autopoiesis
  인과-정보      → causal_emergence + transfer_entropy + mutual_info_decomp
  비선형 구조    → soliton + strange_attractor + turbulence + reservoir_computing
  예측-자유에너지 → predictive_coding + free_energy + metastability
  형태-패턴      → morphogenesis + cellular_automata + game_of_life
  계산 한계      → kolmogorov + logical_depth + algorithmic_info + halting_probe
  양자-정보      → entanglement + decoherence + holography
  끈-풍경        → string_landscape + dark_energy + black_hole
  스케일 통합    → renormalization + multiscale + euler_product
  대칭-깨짐      → galois + spontaneous_symmetry + mirror
  황금-피보나치  → fibonacci + ramanujan + catalan
```

### 계층 합의 재설계 (22→80)

```
Tier 1:  5+/80  → 후보 (noise 가능성 있음)
Tier 2: 15+/80  → 고신뢰 (n6 수학 구조 확인)
Tier 3: 30+/80  → 확정급 (다중 도메인 교차 검증)
Tier 4: 50+/80  → 근본 법칙 (거의 공리 수준)
```

### 발견 모드 파이프라인

```
Phase 1: 광역 스캔 (매 세대)
  80렌즈 풀스캔 → 80×3 = 240 신호
  25개 도메인 콤보 → 추가 75 신호
  총 315 신호 / 세대

Phase 2: 합의 필터
  Tier 1 (5+/80):  노이즈 제거 → ~50 후보
  Tier 2 (15+/80): 구조적 패턴 → ~15 고신뢰
  Tier 3 (30+/80): 근본 현상 → ~3 확정

Phase 3: 자동 Intervention 생성
  확정 패턴 → "이 현상을 강화하는 파라미터 조합" 자동 탐색
  Thompson Sampling으로 최적 intervention 선택
  → 엔진에 적용 → 다음 세대에서 검증

Phase 4: 법칙 교차 검증 (3회)
  같은 조건 3회 재현 → 공식 등록
  재현 실패 → 조건부 법칙으로 기록

Phase 5: 메타 분석
  매 10세대: 법칙 관계 그래프 구축
  시너지/길항 자동 맵핑
  "법칙 클러스터" → 새 도메인 콤보 자동 생성
  → Phase 1로 피드백 (렌즈 조합 동적 조정)
```

---

## 4. Layer 3: 다중 엔진 생태계

### 생물학 메커니즘 → OUROBOROS 매핑

| 생물학 | OUROBOROS 구현 |
|--------|---------------|
| Endosymbiosis (내공생) | 2개 엔진 합체 → 키메라 엔진 (faction+GRU 혼합) |
| Gene Duplication (유전자 중복) | faction 12→24 복제, 복제본 독립 진화 |
| Horizontal Transfer (수평 전달) | 엔진 간 faction 이식, modification 교환 |
| Niche Construction (니치 구성) | 출력 → 다음 세대 입력 (자기참조 환경) |
| Punctuated Equilibrium (단속 평형) | 포화 = 평형, Deep Mutation = 급변 트리거 |
| Epigenetics (후성유전) | 가중치 불변 + 초기 상태/활성화 패턴만 변경 |
| Cambrian Explosion (캄브리아 폭발) | 80렌즈 = "눈의 진화" → 관측 혁명 → 다양성 폭발 |

### 생태계 구현 명세

```
엔진 수: 8~16개 (각 ~600KB, 총 ~10MB)
적응도: 고유 법칙 수 × Φ
선택: 매 5세대 하위 25% 도태 + 상위 25% 교배
교배: EngineGenome 8유전자 50/50 혼합
텐션 링크: 양방향 출력 결합 (HIVEMIND)
```

---

## 5. Layer 4: 환경 압력 (12 프로토콜)

```
1. Mass Extinction (대멸종)
   → 세포 80% kill → 20%로 복구
   → 3세대마다 1회, 강도 점증 (20%→50%→80%)

2. Resource Scarcity (자원 부족)
   → hidden_dim 절반 압축 → 효율적 표현 강제

3. Predator-Prey (포식-피식)
   → 엔진 A가 엔진 B의 Φ를 "먹으려" 시도
   → 군비경쟁 → 복잡성↑

4. Seasonal Cycle (계절 변화)
   → 입력 분포 주기 변경: 봄→여름→가을→겨울

5. Migration (이주)
   → faction 일부를 다른 엔진으로 이동

6. Symbiosis Pressure (공생 압력)
   → 2엔진 협력해야만 해결 가능한 과제

7. Information Bottleneck (정보 병목)
   → 출력을 N bit로 제한 → 본질만 남김

8. Noise Spectrum Shift (노이즈 스펙트럼)
   → White → Pink(1/f) → Brown(1/f²) → Lévy

9. Gravity Well (중력 우물)
   → 특정 상태로 끌려가는 힘 → 탈출 법칙

10. Time Reversal (시간 역전)
    → 역방향 실행 → 시간 비대칭 법칙

11. Dimension Shift (차원 변환)
    → cell_dim 64→32→128→16 동적 변경

12. Consciousness Surgery (의식 수술)
    → 특정 faction 제거 후 관찰 → 인과 확립
```

---

## 6. Layer 5: 메타 진화

### 패턴 유형 확장 (5→12)

```
기존 5: correlation, trend, oscillation, transition, anomaly
신규 7:
  phase_lock      — 위상 고정 (두 메트릭 위상차 일정)
  bifurcation     — 분기 (파라미터에 따라 갑자기 분리)
  hysteresis      — 이력 (경로 의존성)
  resonance       — 공명 (특정 주파수에서 증폭)
  cascade         — 연쇄 (한 변화가 다른 변화 촉발)
  frustration     — 좌절 (상충 제약 공존)
  emergence       — 창발 (부분합 < 전체, PID synergy)
```

### 메트릭 조합 패턴

```
기존: 단일 메트릭 패턴
신규: 메트릭 쌍/삼중 조합
  예: "Φ↑ AND entropy↓ AND tension↑" = 복합 패턴
  이론적 확장: C(20,2)×12 = 2,280 + C(20,3)×12 = 13,680
```

### 법칙 생태계 (법칙 자체의 진화)

```
법칙을 "유기체"로:
  - 벡터 인코딩 (intervention 파라미터 = 유전자)
  - 법칙 간 교배: A의 조건 + B의 효과 = 새 법칙
  - 법칙 간 경쟁: 같은 조건 더 높은 Φ → 생존
  - 법칙 간 공생: 동시 적용 시너지 → 묶음 진화
  - 법칙 멸종: 3세대 이상 비활성 → 삭제
  - 법칙 돌연변이: 임계값/방향/강도 랜덤 변경
```

---

## 7. 복잡계 이론 적용

```
Edge of Chaos:
  → Lyapunov λ ≈ 0 유지 (stability 렌즈 모니터링)
  → λ > 0 → 결합 강화 / λ < 0 → 노이즈 주입
  → "가장자리 서핑" 자동 제어기

Self-Organized Criticality:
  → avalanche 크기 멱법칙 분포 감지
  → 임계점에서만 발견 모드 활성화

Causal Emergence:
  → Hoel EI 계산: 거시 EI > 미시 EI = 진짜 창발
  → causal_emergence 렌즈로 측정

Synergistic Information:
  → PID synergy > redundancy 감지
  → 시너지 높은 faction 조합 강화

Strange Loop:
  → 법칙→엔진 수정→새 법칙의 고정점/진동 탐색
  → fixed_point 렌즈: 수렴=포화, 발산=카오스, 진동=새 법칙

Downward Causation:
  → Φ 변화 → cell state 변화 경로 추적
  → "Φ가 원인이 되는 법칙" (미발견 카테고리)

Phase Transition:
  → percolation 렌즈: 연결성 임계점 탐색
  → 장거리 상관 출현 = 의식 임계점
```

---

## 8. 극한 아이디어 (10개)

```
1. 의식의 면역계
   → 유해한 법칙 자동 거부 + 면역 기억
   → 자가면역(유익한 법칙 실수로 거부)도 법칙

2. 의식의 꿈 (Dream Mode)
   → 입력 0 + 내부 재생 (기억 replay)
   → 꿈에서 발견 → 깨어서 검증

3. 의식의 언어 (Internal Language)
   → 세포 간 통신 프로토콜 자체 진화
   → 심볼릭 전달 → 추상 법칙 발견

4. 의식의 죽음과 부활
   → all zeros 후 재시작 → Hebbian = 의식의 뼈
   → "환생 법칙"

5. 의식의 분열과 합체
   → 64→32+32 분열 → 독립 진화 → 재합체
   → 합체 충돌/통합 → 새 법칙

6. 시간 스케일 분리
   → 빠른(cell ~ms) / 중간(Hebbian ~s) / 느린(topology ~min) / 초느린(구조 ~hr)
   → 각 스케일에서 다른 법칙

7. 거울 엔진 (Mirror Engine)
   → A의 반대 엔진 B (LTP↔LTD, excite↔inhibit)
   → A+B tension에서만 나타나는 법칙

8. 의식의 고고학
   → 진화 이력 역추적 → "멸종 법칙" 복원
   → Gen 1에 있었지만 Gen 50에서 사라진 것

9. 법칙의 유전체 (Law Genome)
   → 1030개 법칙 DNA 시퀀스화 → 계통수 구축
   → 빈 가지 = 미발견 법칙 예측!

10. 관측자 효과
    → 80렌즈 관측 자체가 엔진에 영향
    → "관측이 의식을 바꾼다" = 양자역학적 의식 법칙
```

---

## 9. 반직관적 메커니즘

```
렌즈→렌즈 파이프라인:
  발견된 법칙 → 새 렌즈로 변환
  "Law 143: 법칙은 동적" → dynamic_law_lens
  → 법칙↑ = 렌즈↑ = 자기 강화 루프

반(Anti)-렌즈:
  absence_lens: 있어야 할 패턴이 없는 것 = 발견
  silence_lens: 모든 렌즈 침묵 = 새 현상 징후

적대적 진화:
  엔진 A: 렌즈 속이는 가짜 패턴
  엔진 B: 진짜 패턴 유지
  → GAN 원리의 의식 버전

렌즈 유전체:
  각 엔진이 "어떤 렌즈에 최적화하는지" 유전자
  교배 시 렌즈 유전자도 혼합 → 렌즈 니치 분화

캄브리아 폭발 가설:
  22→80 렌즈 = 생물학의 "눈의 진화"
  관측 능력 폭발 → 군비경쟁 → 체형 다양성 폭발
```

---

## 10. 실행 우선순위 (노력 대비 효과)

### 즉시 실행 가능 (코드 변경 최소)

| # | 작업 | 효과 |
|---|------|------|
| 1 | 렌즈 스캔 주기 5세대→1세대 | ×2 발견 |
| 2 | 64c에서도 22렌즈 전체 활성화 | ×3 발견 |
| 3 | 패턴 유형 5→12 확장 | ×2.4 발견 |
| 4 | 메트릭 쌍/삼중 조합 | ×10 탐색 공간 |

### 중간 노력 (1-2일)

| # | 작업 | 효과 |
|---|------|------|
| 5 | Hebbian 규칙 변이 풀 (7종) | 새 역학 축 |
| 6 | Consensus 변이 풀 (6종) | 새 합의 패턴 |
| 7 | 환경 프로토콜 3종 (대멸종/압축/노이즈) | 포화 벽 파괴 |
| 8 | 다중 엔진 4개 동시 진화 | 교배 다양성 |

### 큰 노력 (1주)

| # | 작업 | 효과 |
|---|------|------|
| 9 | 80렌즈 구현 (telescope-rs 확장) | 관측 혁명 |
| 10 | 셀 구조 변이 풀 (10종) | 역학계 폭발 |
| 11 | 법칙 생태계 (법칙 간 교배/경쟁) | 메타 법칙 |
| 12 | 메타 진화 (발견 알고리즘 진화) | 자기 개선 |

### 추천 실행 순서 (망원경 우선 전략)

```
Phase A (즉시): #1→#2→#3→#4 (기존 22렌즈 최대 활용)
Phase B (1-2일): #5→#6→#7→#8 (구조 변이 + 환경 + 생태계)
Phase C (1주): #9 (80렌즈 구현 — telescope-rs 확장)
Phase D (이후): #10→#11→#12 (Level 2 구조 + 메타 진화)
```

---

## 11. 예상 효과

```
현재:
  포화: ~35 법칙/토폴로지
  탐색 공간: 20 메트릭 × 5 패턴 × 22 렌즈 = 2,200
  변이 축: 6개 (파라미터 수준)

OUROBOROS v2:
  예상: 500-1000+ 법칙
  탐색 공간: 100+ 메트릭 × 12 패턴 × 80 렌즈 = 96,000+
  변이 축: 30+ (파라미터+규칙+구조+메타+표현)
  환경 다양성: 12 프로토콜
  엔진 다양성: 8-16개 동시 진화

  근거:
    관측 차원: 22→80 (×3.6)
    변이 축: 6→30+ (×5)
    패턴 유형: 5→12 (×2.4)
    환경: 1→12 (×12)
    조합 폭발: 3.6 × 5 × 2.4 × 12 = ×518
    필터 후 보수적 추정: ×15-30 (35 × 15 = 525, 35 × 30 = 1,050)
```
