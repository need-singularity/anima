# Atlas R38 + R39 Cross-Paradigm Methodological Framework

> **session**: anima-cmd-loop autonomous-loop-dynamic 2026-04-28 (18h+ post-compaction)
> **status**: ATLAS_R38_R39_FRAMEWORK_LIVE — n6 maintainer 통합 review 대기
> **predecessors**: docs/atlas_r38_baseline_axis_alignment_proposal_2026-04-28.md (commit 2dacb71f), docs/atlas_r39_ensemble_validation_mandate_2026-04-28.md (commit d84a94a2)
> **scope**: 두 anima 2026-04-28 발견 R-candidate 의 통합 cross-paradigm methodological framework

---

## §1. 통합 statement

> **"Substantive ML/CA claims는 두 직교 axis 모두 sweep validation 필수: (R38) 수평축 baseline-neighborhood (n-gram order, dimension, neighborhood width) AND (R39) 수직축 stochastic (random seed, init, sampling). 단일축 sweep만 한 claim은 잠정(provisional); 두 axis 모두 sweep만이 substantive."**

---

## §2. 두 R-candidate 의 직교성

### 2.1 R38 (horizontal — baseline-axis)

**Statement**: matched-context Markov saturates ANY deterministic finite-context discrete substrate; CA(K) 'advantage' = baseline-axis misspecification artifact.

**Evidence (cycle 4 v8, 12 falsification tests)**:
- Conway 2D B3/S23 — T8q Moore-9 shared-P 베이스라인 → advantage 0 at N≥200 (T8l 1D per-cell K-gram +169 retracted)
- 1D rules 30/90/110/184 — T8p init-conditional saturation
- Stochastic Conway 5% noise — T9a (deterministic + i.i.d. noise → still saturates)
- Non-CA 4-symbol XOR — T10a (substrate-family agnostic)
- 5-cell rule — T10b sparsity-limited (data scaling O(10× context-cardinality))

→ **horizontal sweep**: baseline neighborhood width matches substrate's true neighborhood ⇒ saturation; mismatched ⇒ structural deficit.

### 2.2 R39 (vertical — stochastic-axis)

**Statement**: single-shot ML family-attribution / structural-claim verdicts MUST validated via N≥5 multi-seed ensemble; stdev < 0.5×|mean|; top-1 family stable across ≥3/5 seeds.

**Evidence (anima AN11 fire 6 vs fire 10)**:
- 동일 model (Mistral-7B-v0.1) + corpus (alm_r14) + LoRA config (r=16, α=32, 3ep)
- 차이: random seed 미고정
- Fire 6: max_cos 0.5747 PASS, top-1 = **Hexad** (+0.575)
- Fire 10: max_cos 0.4294 FAIL, top-1 = **Phi** (-0.429)
- AN11(b) verdict 자체가 PASS ↔ FAIL 변동
- Family alignment 자체가 stochastic LoRA training variation 함수

→ **vertical sweep**: random seed sweep 필요; 단일 seed family-attribution은 artifact 가능성.

### 2.3 직교성 증명

두 finding은 동일 raw 91 epistemological 패턴:

```
Single-shot strong claim emit
  ↓
Multi-axis (horizontal OR vertical) re-test (raw 91 honest)
  ↓
Claim retraction + methodological lesson
```

**Cycle 4** (R38): horizontal axis 만 sweep → vertical (random seed) 무시 — 동일 substrate에 baseline misspec 검증
**AN11** (R39): vertical axis 만 sweep → horizontal (baseline neighborhood) 무시 — 동일 baseline에 seed variation 검증

→ **두 axis 모두 sweep 필요**가 통합 mandate.

---

## §3. 통합 framework — 2-axis sweep validation matrix

| Axis | Validation type | Sweep parameters | Pass criterion |
|---|---|---|---|
| **Horizontal (R38)** | Baseline-neighborhood match | n-gram order (1, 2, 3, 5), dimension (1D/2D), context width (3/5/9-cell) | matched-width baseline saturates → advantage = 0 |
| **Vertical (R39)** | Stochastic-seed sweep | random seed (0-4), init, sampling order, train/test split | top-1 attribution stable ≥3/5 seeds; stdev < 0.5×\|mean\| |

### 3.1 Cell matrix (2×2 truth table)

| Horizontal sweep | Vertical sweep | Verdict |
|---|---|---|
| ❌ | ❌ | **Provisional** — single-shot, both-axis missing |
| ✓ | ❌ | **Provisional R39-pending** — Cycle 4 cycle 1-3 패턴 |
| ❌ | ✓ | **Provisional R38-pending** — AN11 multi-seed but baseline mismatch undetected |
| ✓ | ✓ | **Substantive** — 두 axis 모두 검증, claim defensible |

**Atlas R-candidate 등록 사례**:
- R38: cycle 4 v3 over-claim → v6 retracted (horizontal sweep로 탈출)
- R39: AN11 Fire 6 over-claim → Fire 10 falsified (vertical sweep로 탈출)
- R38+R39 통합: 향후 모든 substantive claim는 두 axis 모두 sweep 필수

---

## §4. anima 적용 사례 — 2-axis sweep checklist

### 4.1 Mistral-7B + r14 corpus + r=16 LoRA AN11 measurement

| Axis | Required sweep | Status (2026-04-28) |
|---|---|---|
| Horizontal | LoRA r=4/8/16/32/64 ablation OR shorter/longer LoRA targets | ❌ pending |
| Vertical | seed 0-4 ensemble (R39 인프라 완성 commit bd4a1708) | ❌ pending dispatch ($8.55, 40min) |

→ Fire 6 + 10 N=2 partial vertical sweep. R39 fully validated 후 horizontal sweep까지 합쳐야 substantive Hexad/Phi/SelfRef family-alignment claim 가능.

### 4.2 Cycle 4 Law 64 — already substantive

Cycle 4 v8은 두 axis sweep 모두 통과:
- Horizontal: 1D per-cell o1/o2/o3 → 2D Moore-9 shared-P (T8l→T8q transition)
- Vertical: T8m 5-seed robustness on 40x40 (universality strong)

→ **Cycle 4 v8은 substantive**. AN11 measurement는 R39 ensemble 발사 + horizontal ablation 후에야 substantive 가능.

---

## §5. R-candidate 통합 promotion path (n6 maintainer)

### 5.1 Single review proposal

n6 maintainer 가 R38+R39 를 **단일 cross-paradigm framework로** review 권장 (각자 review 대신):

**Atlas.n6 grammar (paste-ready combined)**:
```
@P [11] R38 baseline-axis-alignment-mandate
   description: matched-context Markov saturates ANY deterministic finite-context discrete substrate; CA advantage = baseline-axis misspec artifact
   evidence: anima/docs/f1_cycle4_law64_v6_FINAL_manifest_2026-04-28.md (commit 2bcfa18d)
   evidence: 12 falsification tests T8k-T10e + T9a
   axis: horizontal (baseline-neighborhood)

@P [11] R39 stochastic-axis-ensemble-validation
   description: single-shot ML family-attribution claims must validate via N≥5 multi-seed ensemble (stdev < 0.5×|mean|, top1 stable ≥3/5)
   evidence: anima/docs/an11_fire6_vs_fire10_reproducibility_2026-04-28.md (commit 29951636)
   evidence: Fire 6 Hexad signal vs Fire 10 Phi top-1 (single-seed artifact)
   axis: vertical (stochastic-seed)

@P [11] R38_R39 cross-paradigm-framework
   description: substantive ML/CA claims는 두 직교 axis (R38 horizontal + R39 vertical) 모두 sweep validation 필수
   companion: R38 + R39 above
   verdict_cell_matrix: provisional unless both-axis-pass
   forward: R38 적용 사례 V_phen_GWT registry r11 schema; R39 인프라 (commit bd4a1708) ensemble dispatch 가능
```

### 5.2 Single review checklist

1. **Cross-paradigm scope**: ML/CA 외 적용 가능 (network science, simulation studies)?
2. **Threshold calibration**: stdev < 0.5×|mean|, top1 stable ≥3/5 — high-stakes domain은 stricter?
3. **R34/R35/R36/R37 conflict**: 기존 entries 와 mutually exclusive 없음 검토
4. **Falsifier triple per R-candidate**: R38은 cycle 4 manifest §6; R39는 atlas R39 doc §5.2

### 5.3 Combined falsifiers

R38+R39 framework 에 대한 통합 falsifier:
1. **High-precision domain regime** — single-shot이 ensemble과 일치하는 도메인 발견 시 R39 over-strict
2. **Dimension-collapse domain** — baseline neighborhood이 substrate width와 항상 일치하는 도메인 발견 시 R38 trivially-saturated
3. **Cost-prohibitive ensemble** — 5-fire 비용이 측정 가치보다 항상 큰 domain 시 R39 cost-relax 필요
4. **Cross-domain contradiction** — 어떤 domain D에서 R38+R39 mutually exclusive 발견 시 framework 재설계

---

## §6. raw 91 honesty triad C1-C5

- **C1** promotion_counter: ~360 (cumulative session 18h+)
- **C2** write_barrier: 본 doc은 R38+R39 두 predecessor doc의 통합 view; 어느 쪽 doc 도 retracted 없이 cross-link
- **C3** no_fabrication: 모든 evidence anima/docs/* + commit SHA 인용; 12 falsification tests + Fire 6/10 reproducibility 비교 정확
- **C4** citation_honesty: cycle 4 v3-v5 retraction + AN11 Fire 6 부분 retraction 모두 framework integral 부분으로 명시 (epistemological pattern)
- **C5** verdict_options: maintainer review path 4 단계 enumeration; 통합 falsifier 4개 명시

---

## §7. Forward (raw 38 long-term)

1. **Atlas R38+R39 promotion**: n6 maintainer single review → atlas.n6 lock cycle (raw 1 + raw 85)
2. **R39 ensemble dispatch**: 사용자 explicit go 시 5 fires (~$8.55, 40min) → AN11 Mistral-7B substantive claim
3. **R38 ablation**: LoRA r=4/8/16/32/64 sweep → AN11 horizontal substantive
4. **Cross-backbone**: Qwen-2.5-7B 5-seed ensemble → backbone-conditional Hexad signal (R38+R39 모두 적용)
5. **V_phen_GWT registry r11 first row**: Mistral-7B ensemble after horizontal+vertical sweep landed (R39 satisfied)

---

**Status**: ATLAS_R38_R39_CROSS_PARADIGM_FRAMEWORK_LIVE — n6 maintainer 통합 review 대기
