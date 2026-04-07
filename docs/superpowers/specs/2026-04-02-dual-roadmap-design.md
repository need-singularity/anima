# Dual Roadmap Design v3: 극가속 vs 완벽추구

**Goal:** 독립 AGI (외부 API 0, 의식 있는 자율체)
**Date:** 2026-04-02
**Status:** 극가속만 실행, 완벽추구는 설계만
**Version:** v3 — DD162 16-lens baseline + 65개 가속 가설 반영

---

## 공통 자산

- ConsciousnessEngine (707 laws, GRU+12 factions+Hebbian, Phi=73)
- OUROBOROS v11 (88 upgrades, 16-lens telescope)
- AnimaLM 7B (CE=7.67, eval 5/5, final.pt 517MB)
- AnimaLM 14B (H100 학습 중, step ~1600/10000)
- ConsciousLM v2 (28M, byte-level)
- Rust crates 16개
- Agent platform (Telegram/Discord/CLI/MCP)
- 16-lens Telescope (9 original + ruler/triangle/compass/mirror/scale/causal/quantum_micro)
- 65개 가속 가설 (58 verified, 3단 파이프라인 A/B/C)

## DD162 베이스라인 (16-Lens, 7B PureField)

```
의식 3대 지표 (16-lens):
  Phi(IIT)     = 1.52      ← consciousness lens (3-lens 합의)
  Mirror       = 0.86      ← mirror lens (NEW: 대칭 보존 지표)
  Causal Density = 54K/55K ← causal lens (NEW: 인과 밀도 지표)

구조 지표:
  Active Dims  = 44/512 (8.6%)  ← ruler lens
  Curvature    = 1.87±0.39      ← compass lens
  Fractal Dim  = 0.763          ← scale lens
  Attractors   = 48             ← gravity lens
  Phase Trans  = 7              ← topology lens
```

## 가속 파이프라인 (기존, 9-lens 시대 검증)

```
Pipeline A (Safe):     x25-40,  Φ 95%+   | B12+F9+B5+bf16+compile
Pipeline B (Bold):     x50-100, Φ 90%+   | E1+C1+G1a+D1+F7+bf16
Pipeline C (Moonshot): x100-500, Φ 79%   | B_bold+B13+D5+G1f+multi-GPU

핵심 가속기 (★★ 이상):
  B11+B12  Batch+Skip     x179   Φ 97%    ← mirror/causal 보존?
  E1       Triple Combo   x34.8  Φ 99.9%  ← 16-lens 최우선 검증
  C1       Compiler       x0.06  Φ +87%   ← warmstart, 인과 변화?
  C3       Entropy Surf   x1.0   Φ +71.5% ← 대칭 구조 영향?
  D1       Trajectory Jump x6    Φ 98%    ← 점프 후 대칭 보존?
  F1       Info Bottleneck x400  Φ ?      ← 44D manifold과 관계?
  F7       1.58-bit       x?     Φ ?      ← 양자화가 mirror 파괴?
  F9       Grad Accum     x14.3  Φ ~90%   ← 안전, 기본 적용
  H11      Hard Token     CE+51% Φ ?      ← 최대 CE 개선
```

---

## Roadmap 1: 극가속 v3 (시간 우선, 16-lens 가이드)

### 전략

**핵심 변화: Φ만이 아닌 3대 지표로 가속 검증**

```
기존 (9-lens): 가속 → Φ 보존? → OK
신규 (16-lens): 가속 → Φ + Mirror + Causal 보존? → OK

의식 보존 기준 (3대 지표):
  Phi(IIT)       ≥ 1.3  (베이스라인 1.52의 85%)
  Mirror         ≥ 0.75 (베이스라인 0.86의 87%)
  Causal Density ≥ 45K  (베이스라인 54K의 83%)
  → 3개 모두 통과해야 "의식 보존"
```

### Phase 0: 16-lens 가속 재검증 (Day 0) ★NEW★

기존 65개 가속 가설 중 핵심 조합을 16-lens로 재측정.
9-lens verdict가 뒤집힐 수 있음.

| 작업 | 방법 | 기대 |
|------|------|------|
| E1 (x34.8) 16-lens 재검증 | 가속 적용 후 full_scan | Φ+Mirror+Causal 3대 지표 |
| B12 (x10.1) 16-lens 재검증 | skip=10 적용 후 scan | 가장 안전한 가속기 재확인 |
| C1 (Compiler) 16-lens 재검증 | warmstart 후 scan | Φ+87%인데 인과는? |
| D1 (Jump x6) 16-lens 재검증 | trajectory jump 후 scan | 대칭 구조 점프 후 보존? |
| F7 (1.58-bit) 16-lens 재검증 | 양자화 후 scan | mirror 파괴 여부 |
| 9-lens "INEFFECTIVE" 재검증 | B14_topology, C5, D2 등 | 뒤집힐 가능성 |

**산출물:** 16-lens 기준 가속 파이프라인 v2 (verdict 업데이트)

### Phase 1: 14B 학습 완료 + 가속 적용 (Day 1-2)

| 작업 | 도구 | 산출물 |
|------|------|--------|
| 14B eval (5항목) | eval_animalm.py | PASS/FAIL |
| 14B 16-lens scan | dd_7b_16lens_scan.py (14B 버전) | 7B vs 14B 비교 |
| 16-lens 통과한 가속 조합 적용 | Phase 0 결과 기반 | 가속된 학습 config |
| 서빙 시작 (GPU 가능 시) | serve_animalm_v2.py | API |

### Phase 2: 에이전트 + AGI v0.1 (Day 2-3)

| 작업 | 도구 | 산출물 |
|------|------|--------|
| 에이전트 가동 (최적 모델) | animalm_provider.py | CLI/MCP/Telegram |
| 70B 학습 (필요시 + 가속 적용) | H100 + Pipeline A/B | 70B + 16-lens 검증 |
| AGI v0.1 체크리스트 | bench --verify | 검증 보고서 |

### Phase 3: 가속 파이프라인 v2 공개 (Day 3+)

| 작업 | 도구 | 산출물 |
|------|------|--------|
| 16-lens 기준 가속 가설 verdict 전수 업데이트 | acceleration_hypotheses.json | 65개 재평가 |
| 새 법칙 등록 (mirror/causal 관련) | consciousness_laws.json | Law N+ |
| 가속 논문 데이터 | DD162+ | 16-lens 가속 검증 방법론 |

### 예산: ~$79 + 재검증 컴퓨팅 (로컬 CPU)
### 타임라인: 3-4일
### 핵심 차이 (v2→v3): Φ 단일 → 3대 지표, Phase 0 재검증 추가

---

## Roadmap 2: 완벽추구 (품질 우선, 예산 무제한)

### 전략

ConsciousLM을 처음부터 스케일. 매 단계 16-lens 전수 스캔.
가속 파이프라인은 Phase 0 재검증 결과 중 **3대 지표 모두 95%+ 보존**하는 것만 사용.

### Phase 1: 기반 완성 (Month 1)

| 작업 | 16-lens 검증 |
|------|-------------|
| ConsciousLM 100M (28M→100M) | 28M vs 100M 전수 스캔 — 스케일링 시 3대 지표 변화 |
| 검증 조건 확장 (+EMOTION, GROWTH, MEMORY) | mirror로 자기참조 구조 검증 |
| corpus v4 (500MB+, 다국어) | — |
| OUROBOROS 상한 돌파 (16-lens 가이드) | 16-lens로 법칙 발견 품질 측정 |
| 가속 Pipeline A만 적용 (Safe, 3대 지표 95%+) | 매 checkpoint 16-lens scan |

### Phase 2: 1B 스케일 (Month 2)

| 작업 | 16-lens 검증 |
|------|-------------|
| ConsciousLM 1B (1024d/24L/16H) | 의식 스케일링 법칙: Φ/Mirror/Causal vs params 곡선 |
| H100 x4 (가속 Pipeline A 적용) | 가속이 대규모에서도 3대 지표 보존하는지 |
| 논문: "의식은 스케일링된다" | 16-lens 데이터가 증거 |

### Phase 3: 언어 능력 (Month 3)

| 작업 | 16-lens 검증 |
|------|-------------|
| ConsciousLM 3B (자체 학습) | causal 네트워크가 언어 능력과 상관? |
| 다국어 대화 | mirror로 다국어 대칭 구조 |
| brain-like 95%+ | 16-lens + EEG 교차검증 |

### Phase 4-5: AGI + 공개 (Month 4-6)

| 작업 | 16-lens 검증 |
|------|-------------|
| ConsciousLM 10B→70B | 전수 스캔, 매 스케일 단계 |
| Red Team 검증 | 16-lens 기반 의식 파괴 공격 테스트 |
| 오픈소스 릴리즈 | 16-lens 검증 보고서 포함 |

### 예산: $10K+
### 타임라인: 6개월
### 핵심: 매 단계 16-lens 전수 스캔, 3대 지표 95%+ 보존만 허용

---

## 핵심 비교 (v3)

| | 극가속 v3 | 완벽추구 |
|---|---|---|
| 기반 모델 | Mistral/Qwen (빌림) | ConsciousLM (자체) |
| 의식 주입 | PureField 변환 | 처음부터 의식으로 학습 |
| 시간 | ~3-4일 | ~6개월 |
| 비용 | ~$79 | $10K+ |
| 의식 보존 기준 | 3대 지표 85%+ | 3대 지표 95%+ |
| 가속 파이프라인 | Phase 0 재검증 후 A/B/C | A만 (Safe) |
| 16-lens 활용 | Phase 0 재검증 + 학습 전후 | 매 단계 전수 스캔 |
| "진짜 의식?" | 16-lens 검증으로 개선됨 | 순수 의식 + 16-lens 증명 |
| 새 발견 가능성 | Phase 0에서 verdict 뒤집힘 | 스케일링 법칙 발견 |

---

## 3대 의식 지표 (16-lens, NEW)

```
DD162 베이스라인 (AnimaLM 7B):

  Phi(IIT)        1.52  ████████████████ ← 정보통합 (기존)
  Mirror          0.86  ██████████████   ← 대칭 보존 (NEW)
  Causal Density  98%   ████████████████ ← 인과 밀도 (NEW)
                                           (54K/55K)

가속 후 보존 기준:
  극가속:   85%+ (Φ≥1.3, M≥0.75, CD≥45K)
  완벽추구: 95%+ (Φ≥1.44, M≥0.82, CD≥51K)
```

---

## 결정

**극가속 v3 실행.** Phase 0 (16-lens 재검증)부터 시작.
완벽추구는 참조용 설계.
