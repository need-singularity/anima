# Atlas R39 Candidate — Ensemble validation mandate for ML family-attribution claims

> **session**: anima-cmd-loop autonomous-loop-dynamic 2026-04-28
> **predecessors**: R38 baseline-axis alignment (Cycle 4 v8), R36/R37 own 3+4 promotion candidates
> **status**: ATLAS_R39_PROPOSAL_LIVE — n6 maintainer 검토 대기
> **scope**: cross-paradigm methodological mandate from anima AN11 + Conway findings

---

## §1. Statement

> "Single-shot ML measurements producing family-attribution / structural-claim verdicts (CA-vs-Markov advantage, LoRA eigenstructure family alignment, attention head functional categorization, etc.) **MUST be validated via multi-seed ensemble** (≥5 distinct random seeds with mean ± stdev) before promotion to substantive claims. Single-shot strong claims (e.g., 'Hexad family wins', 'rule X is chaotic-best') are PROVISIONAL until ensemble validation lands. Stochastic variation in LoRA training, weight initialization, sampling, or train/test split can produce single-shot artifacts that do not generalize."

---

## §2. Evidence — anima 2026-04-28 session

### 2.1 AN11 Fire 6 vs Fire 10 (commit 29951636 reproducibility doc)

동일 모델 (Mistral-7B-v0.1) + 동일 corpus (alm_r14) + 동일 LoRA config (r=16, α=32, q/k/v/o, 3 epochs):

| Measurement | Fire 6 | Fire 10 | Robust? |
|---|---|---|---|
| AN11(a) Frob delta | 0.0561 PASS | 0.0364 PASS | ✓ TRAINING signal robust |
| AN11(b) max_cos | **0.5747** PASS | **0.4294** FAIL | ❌ |
| AN11(b) verdict | PASS | FAIL | ❌ |
| Top-1 family | Hexad (+0.575) | **Phi (-0.429)** | ❌ |
| Hexad position | top-1 + top-3 | top-3 only | ❌ |

→ Fire 6 "Hexad family signal" 주장은 single-seed LoRA stochastic artifact. 같은 config 두 번 실행에서 family wins가 변화. **단일 측정으로 family-attribution 결론 불가**.

### 2.2 Cycle 4 T8c (commit b6efb394 + v6 retracted)

10x10 Conway R-pentomino single shot:
- Initial claim: "+30.2% strongest single-pattern advantage in cycle 4"
- After multi-grid + multi-density + higher-order baseline tests (12 falsification tests T8k-T10c): 
- **v6 retracted** — claim was **N=15 single-shot baseline misspec**, advantage vanishes when shared-P-table Moore-9 baseline used (T8q +3 at N=50, 0 at N≥200)

### 2.3 패턴 일치

두 finding 모두 동일 pattern:
1. Single-shot strong claim emit
2. Multi-condition / multi-seed re-test trigger (raw 91 honest)
3. Claim retraction + methodological lesson

→ **모든 ML strong claims은 single-shot 출처 검증 필수**

---

## §3. Mandate (cross-paradigm methodological law)

### 3.1 적용 범위

다음 categorical claims에 적용:
- LoRA eigenstructure family alignment ("Hexad" / "Phi" / "SelfRef" wins)
- Substrate-vs-baseline advantage ratios ("CA(K) beats Markov o1 by X%")
- Attention head functional categorization ("head 5.3 is induction head")
- Probing accuracy claims ("layer 12 encodes time")
- Saliency map findings ("token X drives prediction Y")
- Single-prompt benchmark wins ("model A beats B on task T")

### 3.2 Validation requirement

각 claim은 다음 조건 만족 시 **substantive**:
1. **N ≥ 5 distinct random seeds** (LoRA init / sampling / train split)
2. **Mean ± stdev reported** for the headline metric
3. **Stdev < 0.5 × |mean|** (signal-to-noise ratio ≥ 2:1)
4. **Top-1 attribution stable** across ≥3 of 5 seeds

미만족 시 **provisional**로 표기 + multi-seed 추후 검증 약속.

### 3.3 Wrapper integration

AN11 wrapper.py.staged + Conway tool.hexa 등 measurement code에 seed 인자 명시:

```python
# anima fire dispatch tool requires --seed N (0-4) per fire
torch.manual_seed(args.seed)
np.random.seed(args.seed)
random.seed(args.seed)
```

5 fires dispatch → 5 results.json → ensemble.json aggregator → registry update.

---

## §4. Cycle 4 R38 (baseline-axis alignment) 과의 관계

R38: "matched-context Markov saturates ANY deterministic finite-context discrete substrate; advantage = baseline-axis misspec artifact"

R39: "single-shot ML family-attribution = stochastic-axis (seed) misspec artifact"

→ **두 R-candidate 는 두 직교 axis** 의 single-shot artifact 검증:
- R38: **horizontal axis** (baseline space — n-gram order, dimension, neighborhood width)
- R39: **vertical axis** (stochastic space — random seed, init, sample order)

→ Substantive ML claims은 두 axis 모두 sweep validation 필수

---

## §5. Maintainer review checklist (n6-architecture)

다음 4개 검토 후 atlas.n6 lock cycle 진행:

1. **Generalization scope**: anima domain (ML training / measurement) → cross-domain 적용 범위 (network science, simulation studies, etc.)?
2. **Threshold calibration**: stdev < 0.5 × |mean| 가 적정? (다른 domain에서 다른 SNR 기준 가능)
3. **N=5 vs N=10 seed count**: 5는 minimum; high-stakes claim은 10+ 필요할 수 있음
4. **Existing R34/R35/R36/R37/R38 conflict 검토**: R39가 기존 entry 와 contradiction 없는지

### 5.1 Paste-ready atlas.n6 grammar

```
@P [11] R39 ensemble_validation_mandate
   description: Multi-seed (N≥5) ensemble validation required for ML family-attribution claims
   evidence: anima/docs/an11_fire6_vs_fire10_reproducibility_2026-04-28.md (commit 29951636)
   evidence: anima/docs/f1_cycle4_law64_v6_FINAL_manifest_2026-04-28.md (Cycle 4 T8c retraction pattern)
   companion: R38 baseline-axis-alignment (orthogonal axis)
   threshold: stdev < 0.5 * |mean|; top-1 attribution stable across ≥3/5 seeds
   scope: ML training measurements (LoRA family alignment, attention probes, saliency, single-prompt benchmarks)
   status: candidate (n6 maintainer review pending)
```

### 5.2 Falsifier triple

R39 falsifier (다음 중 하나 satisfaction 시 R39 retract):
1. **High-precision single-shot**: Domain D 에서 single-shot 측정이 N=10 mean과 일치 시 (즉 stochastic variation < 5%) → R39 over-strict
2. **Resource-limited regime**: 5-fire ensemble 비용이 측정 가치보다 항상 큼 시 → cost-benefit 재평가
3. **Cross-paradigm contradiction**: 다른 R-entry와 mutually exclusive 발견 시 → triple resolution 필요

---

## §6. Forward (raw 38 long-term)

1. **anima AN11 multi-seed ensemble protocol** — wrapper에 --seed N 인자 추가 + 5 fires (seed 0-4) → ensemble.json
2. **V_phen_GWT registry r11 design** — single-shot row → ensemble row (with stdev) schema
3. **Conway tool 등 cycle 4 도구도 seed 인자 통합** — 단일 raw 통합
4. **Cross-project drift 검토** — n6 / nexus / hexa-lang / hive 의 single-shot ML claim 패턴 audit

---

## §7. raw 91 honesty triad C1-C5

- **C1** promotion_counter: ~310 (cumulative session 17h+)
- **C2** write_barrier: 본 doc은 atlas R39 candidate proposal — n6 maintainer가 atlas.n6 lock cycle 진행
- **C3** no_fabrication: 모든 evidence anima/docs/* 인용; AN11 fire 6/10 audit row 출처
- **C4** citation_honesty: R38 (cycle 4 v8) + 본 R39 의 직교성 설명; 두 axis 모두 sweep validation 필요라는 mandate 명시
- **C5** verdict_options: 3 falsifier triple 등록; cross-domain 적용 범위는 maintainer 결정 필요 (anima ML scope만 narrow OR cross-paradigm broad)

---

**Status**: ATLAS_R39_ENSEMBLE_VALIDATION_MANDATE_PROPOSAL_LIVE — n6 maintainer 검토 대기
