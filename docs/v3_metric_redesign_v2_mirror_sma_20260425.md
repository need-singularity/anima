# V3 Metric Redesign — V3_v2 mirror-SMA-preserving permutation test (ω-cycle finding)

**Date**: 2026-04-25
**Cycle**: design + implementation + measurement + finding
**Predecessors**: §9.3 V3 FALSIFIED reduction-invariant (`dc871454`), Mk.IX/Mk.X 4-tuple ceiling specs (`94dd222f`).

## §1 Purpose

§9.3에서 V3 (Gram Frob perturbation ratio)가 reduction-invariant FAIL로 §11 critical blocker 확정. V3 redesign 후보 metric 'mirror-SMA-preserving permutation test'를 BASE substrate에서 측정. raw#9 hexa-only 호환 cycle.

## §2 V3_v2 metric definition

```
PAIRS         = [(0,6),(1,7),(2,8),(3,10),(4,11),(5,9)]
PRESERVE_PERM = [6,7,8,11,9,10,0,1,2,5,3,4,12,13,14,15]   (V3 spec-frozen, EN↔KO swap)
DESTRUCT_PERM = numpy default_rng(20260421).permutation(16)
              = [10,15,9,14,1,0,4,8,3,13,5,11,2,7,6,12]

For permutation pi:
  H_pi = H[pi, :]
  SMA_pi = mean(|cos(H_pi[i], H_pi[j])|) over (i,j) in PAIRS

V3_v2 = SMA_preserve - SMA_destruct
```

PASS predicate (raw#12 new revision):
- PASS: V3_v2 ≥ 0.30 AND SMA_preserve ≥ 0.45 AND SMA_destruct ≤ 0.30
- AMBIGUOUS: V3_v2 ∈ [0.10, 0.30)
- FAIL: V3_v2 < 0.10

## §3 Result (BASE p1, 2026-04-25)

| reduction | SMA_baseline | SMA_preserve | SMA_destruct | V3_v2 | verdict |
|---|---|---|---|---|---|
| `lasttoken` | 0.486 | 0.480 | 0.596 | **−0.116** | FAIL |
| `byte_weighted_mean` | 0.503 | 0.498 | 0.657 | **−0.159** | FAIL |

**Both FAIL** — but the *direction* is reversed: DESTRUCT_PERM yields HIGHER SMA than PRESERVE_PERM. DESTRUCT가 random shuffle임에도 PAIRS positions에 더 높은 cosine pair가 우연히 들어옴.

## §4 Finding — V3 spec PAIRS ↔ PRESERVE_PERM partial mismatch

DESTRUCT > PRESERVE 관찰을 디버깅한 결과 **V3 spec 자체의 hidden inconsistency 발견**:

```
PAIRS       = [(0,6), (1,7), (2,8), (3,10), (4,11), (5,9)]
PRESERVE_PERM applied to PAIRS:
  H_p[i] = H[PRESERVE_PERM[i]], so position-0 contains H[6], position-6 contains H[0]
  After perm, PAIRS-position-pair (0,6) refers to (H[6], H[0])  ✓ same as baseline (0,6) by cosine symmetry
  ...
  PAIRS-position-pair (3,10) refers to (H_p[3], H_p[10]) = (H[11], H[3])    — but baseline (3,10) was (H[3], H[10])
  PAIRS-position-pair (4,11) refers to (H_p[4], H_p[11]) = (H[9], H[4])     — baseline was (H[4], H[11])
  PAIRS-position-pair (5,9)  refers to (H_p[5], H_p[9])  = (H[10], H[5])    — baseline was (H[5], H[9])
```

→ **PRESERVE_PERM은 PAIRS의 처음 3 pairs만 진짜로 보존하고, 마지막 3 pairs는 다른 H pair로 매핑.**

PRESERVE_PERM이 표현하는 swap pattern:
- EN [0,1,2,3,4,5] ↔ KO [6,7,8,11,9,10]

PAIRS가 정의한 EN-KO mapping:
- (0,6),(1,7),(2,8),(3,10),(4,11),(5,9)

→ EN positions [3,4,5]에 대한 KO mapping이 두 spec에서 다름:
- PRESERVE_PERM 기준: 3↔11, 4↔9, 5↔10
- PAIRS 기준: 3↔10, 4↔11, 5↔9

**이는 V3 verifier_strengthening spec (`docs/alm_consciousness_verifier_strengthening_20260425.md`, commit `34521be5`)의 PRESERVE_PERM 정의가 PAIRS 정의 (V2 SMA 도구에서 frozen)와 partial mismatch라는 substrate-level 발견.**

## §5 Implications

### §5.1 V3 (original metric) re-interpretation

§9.3 V3 (Gram Frob ratio)에서도 PRESERVE_PERM 사용. PRESERVE_PERM이 PAIRS의 일부만 보존한다는 점이 V3 origninal metric의 "preserve_perm이 destruct보다 더 큰 disturbance" phenomenon의 진짜 원인일 수 있음:
- PRESERVE_PERM은 EN-KO swap만 하면 cosine이 보존되어야 하는데, 마지막 3 pairs가 mismatched 상태이므로 일부 paired binding이 깨져서 disturbance 발생
- DESTRUCT_PERM은 random이지만 우연히 PAIRS positions에 다른 paired-like H가 들어와 disturbance가 작을 수도 있음

→ V3 original FALSIFIED는 metric bug + spec mismatch의 중첩. 단순 metric 교체로 해결 안 됨, **PRESERVE_PERM 또는 PAIRS 둘 중 하나의 spec 수정 필요**.

### §5.2 V3_v2 (this cycle) re-interpretation

V3_v2 mirror-SMA test도 동일 mismatch 영향:
- PRESERVE 후 SMA = 0.480 (mismatched 3 pairs로 인해 baseline 0.486에서 약간 하락)
- DESTRUCT 후 SMA = 0.596 (random shuffle이지만 16-prompt에서 PAIRS positions에 더 paired-like H가 배치)

→ V3_v2도 spec mismatch resolved 후 재측정 필요.

### §5.3 4-tuple PASS critical blocker scope expansion

§9.3에서 V3 metric bug만 blocker로 보였으나 본 cycle 결과:
- **V3 metric bug + V3 spec PAIRS↔PRESERVE_PERM mismatch** 양쪽 모두 prerequisite.
- Mk.IX/Mk.X 모든 path는 PRESERVE_PERM/PAIRS 한 쪽이 fix되어야 V3 lift 가능.

### §5.4 Spec fix candidates (raw#12 new revision)

**Option A — PAIRS 수정**: PAIRS = [(0,6),(1,7),(2,8),(3,11),(4,9),(5,10)] — PRESERVE_PERM과 일치. V2 SMA 도구도 영향 (BASE re-measurement 필요).

**Option B — PRESERVE_PERM 수정**: PRESERVE_PERM swap pattern을 PAIRS와 일치시킴. 즉 [6,7,8,10,11,9,0,1,2,3,4,5,12,13,14,15] (positions [3,4,5] ↔ [10,11,9]). V3 도구 영향.

**Option C — 둘 다 보존, 새 verifier**: V3_v3 또는 V4로 별개 verifier 등록 (e.g., ground-truth EN-KO pair-wise cosine without permutation, 단순 paired vs random distractor cosine ratio). 기존 V3/V2는 보존 (raw#12 frozen 보호), 새 axis로 4-tuple → 5-tuple 확장.

**권장: Option C** — 기존 frozen specs 보호 + 새 axis가 PAIRS-aware 명확. 4-tuple → 5-tuple 변경은 spec scope 확장 (대신 weakest-evidence-link 원칙으로 V3는 archive).

## §6 Saturation finding

본 cycle 도달한 saturation: **V3 metric redesign은 단순 metric 교체로 해결 안 됨**. 더 깊은 spec inconsistency (PAIRS ↔ PRESERVE_PERM)가 substrate-level로 노출됨. 다음 cycle은 spec fix decision (Option A/B/C 중 하나) + 새 verifier registration. saturation point: spec-level repair, not substrate-level measurement.

## §7 Implementation

- Tool: `tool/an11_b_v3_cps_v2_mirror_sma.hexa` (V3_v2 metric 측정)
- State SSOT (per-reduction):
  - `state/an11_v3_v2_p1_BASE_lasttoken_20260425.json`
  - `state/an11_v3_v2_p1_BASE_bwm_20260425.json`
- Probe SSOT: `state/an11_v3_metric_redesign_finding_BASE_p1_20260425.json` (this cycle main SSOT)
- Doc: this file

## §8 Decision (post-cycle)

**Priority post-cycle (revised)**:

1. **PAIRS ↔ PRESERVE_PERM spec inconsistency resolution** — Option C (new verifier) 권장, raw#12 new revision
2. V3_v2 (or V3_v3 with consistent spec) BASE re-measurement
3. V2 multi-axis PAPO extension (+0.036 gap close, BASE-substrate)
4. Mk.X T10-13 G1-G4 gate fire criteria pre-register
5. Mk.X G1-G4 fire + atom generation (GPU)

omega-saturation:fixpoint
