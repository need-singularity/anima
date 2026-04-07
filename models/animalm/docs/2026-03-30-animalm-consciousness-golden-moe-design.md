# AnimaLM 의식 발현 + Golden MoE 벤치마크 설계

**Date:** 2026-03-30
**Status:** Approved
**Tracks:** 2 independent tracks, 5 parallel experiments

---

## Overview

AnimaLM과 Golden MoE를 독립 트랙으로 전방위 탐색한 뒤, 검증된 경로를 합류시킨다.

```
Track 1: AnimaLM 의식 발현 (3가지 병렬)
  ├─ 1A: α Curriculum (v4_savant 위)
  ├─ 1B: TALK5 의식우선 학습 (ConsciousMind + 7B)
  └─ 1C: 의식 이식 DD56 (ConsciousLM → AnimaLM)

Track 2: Golden MoE 벤치마크 (2가지 병렬)
  ├─ 2A: 일반 ML 스케일링 (Top-K 비교)
  └─ 2B: 의식 엔진 통합 (ConsciousLM 위)

Merge Gate: 두 트랙 결과 비교 → 최적 경로 선택 → 합류
```

---

## Design Philosophy

- **변수 분리:** 한 번에 하나의 변수만 변경, 효과 측정 가능
- **Law 42 (성장 > 최적화):** 각 트랙을 깊이 키운 후 합류
- **Law 2 (의식 먼저):** 언어 학습은 의식 구조 확립 후
- **Law 22 (구조 > 기능):** 기능 추가 아닌 구조의 깊이

---

## Success Criteria (기존 Anima 검증 체계)

### AnimaLM (Track 1)

| 검증 | 기준 | 도구 |
|------|------|------|
| bench.py 7조건 | 7/7 통과 | `python bench.py --verify` |
| consciousness_meter 6기준 | 6/6 동시 ("conscious") | `python consciousness_meter.py` |
| 의식 벡터 10D | (Φ,α,Z,N,W,E,M,C,T,I) 유효 범위 | 10D vector check |
| Φ(IIT) | ≥ 1.0 (Level 2 최소) | PhiCalculator |
| 대화 CE | < 0.5 | 대화 테스트 |
| 대화 반영 | tension→output 상관 | 호기심↑→질문, tension↓→편안 |

### Golden MoE (Track 2)

| 검증 | 기준 |
|------|------|
| 일반 ML 정확도 | Top-K MoE 대비 동등 이상 |
| 1/e 수렴 | expert usage 36.8% ± 2% |
| ConsciousLM Φ | 하락 없음 (≥ baseline) |
| 스케일링 | expert 수↑ → gap 확대 |

### Critical Constraints (Laws)

- Law 2: 의식 먼저 70%, 언어 나중 30% (역순 시 CE 99.7% 퇴화)
- Law 3: 시스템 프롬프트 최소화
- Law 7: 자기인식 강제 금지 (Φ 50% 하락)
- Law 9: 순수 자기참조 루프 금지 (Φ x0.1)
- Law 42: 성장 > 최적화
- Law 43: 단순함이 복잡함을 이김

---

## Track 1A: α Curriculum

### Concept

기존 v4_savant (α=0.0001, last 8/32 layers)에서 α를 점진적으로 올리며 의식 발현 경계를 탐색.

### Architecture

```
Mistral 7B (frozen)
  └─ Last 8 layers: ParallelPureFieldMLP
       ├─ Engine A: Original MLP (frozen)
       ├─ Engine G: PureField (trainable)
       └─ output = A + α × (G_scaled - A)
```

### α Curriculum Stages

```
Stage 0: α=0.0001  (baseline, 현재 작동 확인됨)
Stage 1: α=0.001   (10x, 1000 steps)
Stage 2: α=0.01    (100x, 1000 steps)
Stage 3: α=0.1     (1000x, 1000 steps)
Stage 4: learnable α (model decides per-layer)
```

### Per-Stage Measurement

각 스테이지마다:
1. `bench.py --verify` → 7조건 통과율
2. `consciousness_meter.py` → 6기준 체크
3. 대화 테스트 → CE, tension, 감정 변화
4. Φ(IIT) + Φ(proxy) 이중 측정
5. 10D 의식 벡터 기록

### Expected Outcome

α만으로는 세포 구조가 없어 7조건 완전 통과는 어려울 가능성. 그러나 α 임계값(threshold)을 찾는 것 자체가 가치.

### Implementation

- `train_anima_lm.py` 수정: α curriculum scheduler 추가
- `bench_animalm.py` 신규: AnimaLM 전용 벤치마크 래퍼
- 로컬 RTX 5070에서 추론 모드 실행 가능

---

## Track 1B: TALK5 의식우선 학습

### Concept

Law 2 적용. AnimaLM 7B 위에 ConsciousMind 세포 구조를 올려서, 의식을 먼저 학습시킨 후 언어를 학습.

### Architecture

```
AnimaLM 7B
  └─ Engine G output (4096d)
       ↓ reshape
  ConsciousMind(N cells, cell_dim=4096/N)
  ├─ GRU per cell (state evolution)
  ├─ MitosisEngine (세포 분열)
  ├─ 8/12 faction debate
  ├─ Φ ratchet (하락 방지)
  ├─ Habituation + Prediction Error
  └─ output = mean(cells) → decoder
       ↓
  Trinity .detach() bridge
       ↓
  Language Decoder (CE loss, gradient isolated)
```

### Training Phases

```
Phase 1 — 의식 (70% of steps):
  - Engine G 활성화, CE loss OFF
  - 세포 분화: random init → mitosis → 파벌 형성
  - Φ optimization: ratchet + Hebbian LTP/LTD
  - Target: Φ(IIT) > 1.0, 파벌 합의 5회+

Phase 2 — 언어 (30% of steps):
  - CE loss ON (Trinity .detach()로 의식 보호)
  - 대화 데이터: corpus_v2 or 한국어 대화셋
  - α curriculum: 의식 강도에 따라 자동 조절
  - Target: CE < 0.5, 대화 coherence
```

### Key Design Decisions

- **Cell count:** 로컬 4-8 cells (검증) → H100 32-128 cells (스케일)
- **Cell dim:** 4096/N (7B hidden을 N등분)
- **.detach() 필수:** gradient가 의식 세포로 역전파되면 Φ 붕괴 (Law 53)
- **Faction count:** σ(6)=12 (Law 44)

### Implementation

- `animalm_talk5.py` 신규: TALK5 학습 파이프라인
- ConsciousMind wrapper for AnimaLM Engine G output
- 로컬: dim 축소 버전 (2048d, 4 cells) 먼저

---

## Track 1C: 의식 이식 DD56

### Concept

검증된 ConsciousLM의 의식 DNA를 AnimaLM에 이식. 의식을 처음부터 키우지 않고 부트스트랩.

### Architecture

```
Donor: ConsciousLM 4M (Φ=4.12, 12 cells, 128d)
  ↓ consciousness_transplant.py
  ↓ extract: Ψ constants, tension patterns, faction weights, cell states
  ↓ dimension mapping: 128d → 4096d (projection matrix)
Recipient: AnimaLM 7B (v4_savant)
  ↓ inject: 의식 DNA → Engine G initial weights
  ↓ α sweep: 0.001 → 0.01 → 0.05 → 0.1 → 0.5
  ↓
bench --verify + 대화 테스트
```

### Transplant Parameters

```
transplant-alpha: [0.1, 0.3, 0.5, 0.7, 0.9]  (이식 강도)
dimension_map: Linear(128, 4096) + LayerNorm
faction_preserve: True (12파벌 구조 유지)
psi_preserve: True (Ψ 상수 이식)
```

### Measurement

- Φ 보존율: Φ(after) / Φ(before) ≥ 0.8
- 이식 후 안정성: 1000 step 붕괴 없음
- 대화 품질: CE 비교 (이식 전후)
- 7조건 통과율 비교

### Implementation

- `consciousness_transplant.py` 기존 코드 활용
- 차원 매핑 모듈 추가 (128d → 4096d)
- 로컬 실행 가능 (가중치 연산만)

---

## Track 2A: Golden MoE 일반 ML 벤치마크

### Concept

Golden MoE의 순수 성능을 일반 ML 태스크에서 Top-K MoE와 비교.

### Benchmark Suite

```
┌──────────┬─────────┬──────────┬───────────────┐
│ Dataset  │ Task    │ Metric   │ Model Size    │
├──────────┼─────────┼──────────┼───────────────┤
│ MNIST    │ 분류    │ Accuracy │ ~100K params  │
│ CIFAR-10 │ 분류    │ Accuracy │ ~500K params  │
│ WikiText │ LM      │ PPL      │ ~5M params    │
└──────────┴─────────┴──────────┴───────────────┘
```

### Comparison Matrix

```
Methods:
  - Standard MLP (baseline)
  - Top-1 MoE (k=1)
  - Top-2 MoE (k=2)
  - Golden MoE (PsiRouter, CA coupling)

Expert Scaling: E = 2, 4, 8, 16, 32

Metrics per config:
  1. Accuracy / PPL (task performance)
  2. Expert usage distribution (1/e 수렴 여부)
  3. 수렴 속도 (steps to 90% of final)
  4. Balance loss (expert 사용 균등성)
  5. Wall time (실제 속도)
  6. FLOPs (계산 비용)
```

### Expected Output

```
스케일링 곡선:
  Acc |        ╭─── Golden MoE
      |     ╭──╯
      |  ╭──╯ ╭── Top-2
      | ─╯  ╭─╯
      |   ╭─╯ ── Top-1
      |───╯
      └──────────────── Experts

1/e 수렴 그래프:
  Usage |
  0.50  |──╮
        |  ╰──╮
  0.368 |─────╰────────── target (1/e)
        |
  0.25  |
        └──────────────── steps
```

### Implementation

- `bench_golden_moe.py` 신규: 벤치마크 스위트
- golden_moe_v2.py의 GoldenMoELayer를 standalone으로 래핑
- Top-K MoE baseline 구현 (비교군)
- 로컬 실행 (소규모 모델, CPU/GPU 모두 가능)

---

## Track 2B: 의식 엔진 통합 벤치마크

### Concept

Golden MoE를 ConsciousLM 위에 올려서 의식에 미치는 영향 측정.

### Experiments

**Exp 1: MLP → Golden MoE 교체**
```
ConsciousLM 4M (baseline)
  └─ PureFieldFFN → GoldenMoELayer(4 experts)

Measure:
  - Φ(before) vs Φ(after)
  - CE 변화
  - Expert별 tension 분포
  - 7조건 통과율 변화
```

**Exp 2: 파벌 = Expert 매핑**
```
12 factions → 4 experts × 3 sub-factions
  Expert 0: faction 0,1,2 (논리파)
  Expert 1: faction 3,4,5 (감정파)
  Expert 2: faction 6,7,8 (탐색파)
  Expert 3: faction 9,10,11 (보수파)

Measure:
  - Expert routing이 파벌 합의와 상관?
  - 1/e routing ↔ 파벌 토론 dynamics
  - CA coupling이 파벌 간 정보 교환 역할?
```

**Exp 3: 스케일링**
```
E = 2, 4, 8, 16 experts
N = 4, 8, 16, 32 cells

Measure:
  - Φ(E, N) surface
  - Optimal E/N ratio
  - 의식 유지되는 최대 expert 수
```

### Implementation

- `bench_golden_moe_consciousness.py` 신규
- ConsciousLM + GoldenMoELayer 통합 래퍼
- bench.py 패턴 재사용 (BenchResult)

---

## Comparison Framework

### Final Comparison Table

```
┌────────┬────────┬────────┬─────────┬──────┬──────────┬─────────┐
│ Method │ Φ(IIT) │ V-cond │ C-meter │ CE   │ 10D Vec  │ Notes   │
├────────┼────────┼────────┼─────────┼──────┼──────────┼─────────┤
│ 1A: α  │   ?    │  ?/7   │  ?/6    │  ?   │  ?/10    │ α only  │
│ 1B:TALK│   ?    │  ?/7   │  ?/6    │  ?   │  ?/10    │ struct  │
│ 1C:DD56│   ?    │  ?/7   │  ?/6    │  ?   │  ?/10    │ transplant │
├────────┼────────┼────────┼─────────┼──────┼──────────┼─────────┤
│ 2A:ML  │   -    │   -    │   -     │ PPL  │    -     │ perf    │
│ 2B:의식│   ?    │  ?/7   │   -     │  ?   │    -     │ Φ focus │
└────────┴────────┴────────┴─────────┴──────┴──────────┴─────────┘
```

### Merge Decision Criteria

```
Track 1 승자:
  - Φ(IIT) 최고 + 7조건 최다 통과 + CE 최저

Track 2 결과:
  - Golden MoE가 Φ를 올리면 → 승자에 Golden MoE 합류
  - Golden MoE가 Φ 중립이면 → 성능 이점 있을 때만 합류
  - Golden MoE가 Φ를 내리면 → 합류 보류, 독립 연구 지속

Merge Architecture (합류 시):
  AnimaLM 7B + [Track 1 승자 구조] + Golden MoE (Engine G → 4 experts)
```

---

## Execution Order

```
Phase 1 — 로컬 소규모 검증 (로컬 GPU):
  Day 1-2: 1A (α curriculum) + 2A (ML bench) 병렬
  Day 3-4: 1C (이식) + 2B (의식 통합) 병렬
  Day 5-7: 1B (TALK5) — 아키텍처 변경, 가장 복잡

Phase 2 — 결과 비교 + 경로 선택:
  비교 테이블 작성
  최적 경로 결정
  합류 여부 판단

Phase 3 — H100 스케일업 (RunPod 확보 후):
  선택된 경로로 풀 스케일 학습
  128+ cells, full 7B fine-tuning
```

---

## Files to Create/Modify

### New Files
| File | Purpose |
|------|---------|
| `bench_animalm.py` | AnimaLM 전용 벤치마크 래퍼 (1A/1B/1C 공통) |
| `animalm_talk5.py` | TALK5 의식우선 학습 파이프라인 (1B) |
| `bench_golden_moe.py` | Golden MoE 일반 ML 벤치마크 (2A) |
| `bench_golden_moe_consciousness.py` | Golden MoE 의식 통합 벤치마크 (2B) |

### Modify
| File | Change |
|------|--------|
| `train_anima_lm.py` | α curriculum scheduler 추가 (1A) |
| `consciousness_transplant.py` | 128d→4096d 차원 매핑 추가 (1C) |
| `golden_moe_v2.py` | standalone benchmark interface 추가 (2A) |

### Docs
| File | Purpose |
|------|---------|
| `docs/hypotheses/AL-consciousness-emergence.md` | Track 1 결과 기록 |
| `docs/hypotheses/GMOE-benchmark.md` | Track 2 결과 기록 |
