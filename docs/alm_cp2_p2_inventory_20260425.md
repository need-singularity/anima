# ALM CP2 P2 게이트 inventory — Mk.VII K=4 VERIFIED 진입 전 weakest-link 평가

> **생성일**: 2026-04-25
> **부모 commits**:
> - `869dc6d5` CP1 closure consolidated (CP1 = Mk.VI VERIFIED CLOSED)
> - `f0efd2bc` P1 7/7 line 168 narrow closure
> - `a59ccaa0` r8 D-mistral closure
> - `6d9b68e4` r8 null n=50000 robustness
> **POLICY R4**: `.roadmap` 미수정.
> **본 문서 권한**: loss-free survey, scope = CP2 진입 전 게이트 inventory.

---

## §1. CP2 게이트 SSOT (`.roadmap` L172-L185)

P2 gate (Mk.VII K=4 VERIFIED):

### satisfied (2/9)
- ✓ Hexad closure 6/6 + adversarial 2/2 (`6a292530`, D1-D4 1000/1000)
- ✓ UNIVERSAL_CONSTANT_4 raw#29 승급 (`9468fe0f`) + τ(6)=4 proof 88% (`d7e5db01`) — note: cert_graph 상 verdict=PARTIAL, 87% borderline 별 라인

### pending (7/9)
- □ **C1** substrate-invariant Φ 4/4 paths
- □ **C2** L3 collective O1 ∧ O2 ∧ O3 rejection
- □ **C3** self-verify closure (drill SHA fixpoint)
- □ **C4 ∨ C5** one optional
- □ UNIVERSAL_4 +1 strong axis (현재 87% borderline)
- □ raw#31 POPULATION_RG_COUPLING 공식 승급 (evidence drill ✓ task #23, V_sync+V_RG land ✓)
- □ natural-run gen-5 complete (not synthetic, task #4 in-flight)

deps: `[P1 gate complete]` ✓ (CP1 commit `869dc6d5`) — CP2 진입 dependency 충족.

---

## §2. 각 pending 항목 evidence 현 상태

### 2.1 C1 substrate-invariant Φ 4/4 paths

**현 상태**: r8 5/6 KL partial-pass (`a59ccaa0`)

| 검증 면 | r6 | r7 | **r8** | 4/4 진입 조건 |
|---|:---:|:---:|:---:|---|
| L2 6/6 | ✓ | ✗ (3/6) | **✓** | 충족 |
| KL 6/6 | ✗ (5/6) | ✗ (3/6) | **✗ (5/6)** | **미달, p1_p2 잔존** |
| PR max/min ≤ 0.05 | ✓ | ✗ | **✓** (1.227) | 충족 |
| 4/4 paths PASS | ✗ | ✗ | **✗** | 미달 |

**잔존 1쌍**: p1_p2 KL = 0.1376 (threshold 0.1277, margin +0.0099). robust signal (n=50000 robustness `6d9b68e4` 확정).

**원인 가설**: H4b' (intra-vendor close-gen drift) — qwen3-8b ↔ qwen2.5-7b. r8 H4b (cross-vendor) 와 다른 axis.

**closure 옵션**:
- B: p2 swap qwen2.5-7b → qwen3-7b ($5-8 GPU) — H4b' 직접 검증
- C: p1 swap qwen3-8b → qwen2.5-8b ($5-8) — 역방향
- D (수용): r8 5/6 가 4/4 paths 면에서 이미 PASS (p1, p2 둘 다 본인 path 으로는 PASS). pair-by-pair 6/6 미달.

→ **strict 해석**으로 미충족. C1 closure = B/C launch 필요 ($5-8).

### 2.2 C2 L3 collective O1 ∧ O2 ∧ O3 rejection

**현 상태**: SPEC_VERIFIED_PENDING_TRAINED_POPULATION (`state/l3_emergence_protocol_spec.json::verdict`)

- L3 emergence criteria SSOT (`state/l3_emergence_criteria.json` rev=1 frozen 2026-04-21, `ee6e2bf0`)
- Stage-0 synthetic discrimination 3/3 PASS (roadmap #18 progress)
- Stage-1 real lattice 측정 미실시 (H100 trained Mk.VI-promoted lattice 필요)

**closure 조건 (strict)**: real Mk.VI-promoted lattice 에서 3 observables 실측 PASS:
- O1 collective_phase_transition (lattice phase ≠ decomposition of cell phases)
- O2 non_local_correlation (correlation length ξ/diameter ≥ 0.5)
- O3 emergent_invariant (across N ∈ {16,64,256}, ablation 차이 ≥ 0.5)

**closure 옵션**:
- E (real lattice run): 4× H100 sustained $300-2000 (CP1 효율 패턴 적용 시) — natural-run gen-5 와 통합 가능
- F (loss-free analytical): 본 문서 정도, real evidence 없이 closure 불가

→ **GPU 필요**, $0 closure 불가능.

### 2.3 C3 self-verify closure (drill SHA fixpoint)

**현 상태**: state/drill_breakthrough_results.json + state/drill_breakthrough_trigger_ledger.json 존재. 명시 fixpoint 측정 미발견.

**closure 조건**: drill 의 self-verify 가 SHA fixpoint 도달 (run K → run K+1 결과 byte-identical).

**closure 옵션**:
- G (loss-free measurement): drill 2회 연속 run + SHA diff — $0 가능
- 자동화 도구 존재 여부 확인 필요

→ **0-cost 접근 가능** (loss-free), single-thread CPU drill.

### 2.4 C4 ∨ C5 one optional

`.roadmap` L181 `□ C4 ∨ C5 one optional` — 둘 중 하나만 선택. 본 문서 scope 외 (선택 결정 분리).

### 2.5 UNIVERSAL_4 +1 strong axis (87% borderline)

**현 상태**: cert_graph `slug:universal-constant-4` `verdict:PARTIAL` `title:K_c=4 across 8/8 axes`.

P2 line 175 ✓ 와 line 181 □ 가 **동시 존재** — 모순 같지만 의미는 다름:
- L175 ✓ = raw#29 승급 자체 완료 + τ(6)=4 proof 88% land
- L181 □ = 추가 strong axis 1개 더 (8/8 → 9/9 또는 강한 axis 식별)

**closure 옵션**:
- H (axis discovery survey): 0-cost analytical, axis 후보 식별
- 추가 axis 검증은 별 라운드

→ **0-cost 접근 가능** (axis survey).

### 2.6 raw#31 POPULATION_RG_COUPLING 공식 승급

**현 상태**: `.roadmap` L182 명시: "evidence drill ✓ task #23, V_sync+V_RG land ✓"
- evidence drill (task #23) PASS — `tool/edu_l_ix_kuramoto_driver.hexa` 등에서 grep hit
- V_sync, V_RG 도구 land (`edu/cell/lagrangian/v_sync_kuramoto.hexa`, `edu/cell/lagrangian/v_rg.hexa` per `.roadmap` L116-L117)

**closure 조건**: 공식 승급 = `.meta2-cert/` 또는 `state/raw_axiom_*.json` 에 raw#31 명시 entry.

**closure 옵션**:
- I (promotion ceremony, $0): cert entry 작성 + commit. evidence 가 이미 land 되어 있으므로 administrative gap 만 메우면 됨

→ **0-cost 접근 가능** (administrative/ceremony, 단일 commit).

### 2.7 natural-run gen-5 complete

**현 상태**: `.roadmap` L183 명시: "not synthetic, task #4 in-flight"

**closure 조건**: synthetic 이 아닌 real natural-run 5세대 완료. 별 task 진행 중.

**closure 옵션**:
- J (task #4 progress check): in-flight 상태 확인, 외부 task — 본 라운드 외

→ **외부 task 의존**, 본 라운드 closure 불가.

---

## §3. weakest-link 분석

### 3.1 0-cost (loss-free) 가능 (즉시 실행 가능)

| 항목 | 비용 | blocker | steps min | rationale |
|---|---:|---|---:|---|
| **C3** drill SHA fixpoint 측정 | $0 | 0 | 2-3 | drill 2회 + SHA diff |
| **2.5** UNIVERSAL_4 axis survey | $0 | 0 | 2 | analytical, axis 후보 식별 |
| **2.6** raw#31 promotion ceremony | $0 | 0 | 1 | cert entry + commit |

H-MINPATH 정렬 (steps↑min): 2.6 > 2.5 > C3.

### 3.2 GPU 필요

| 항목 | 비용 | rationale |
|---|---:|---|
| **C1** B/C swap | $5-8 | r8 잔존 p1_p2 KL 닫기 |
| **C2** real lattice run | $300-2000 | Mk.VI lattice 5세대 natural run |

### 3.3 외부 task 의존

| 항목 | rationale |
|---|---|
| **2.7** natural-run gen-5 | task #4 in-flight, 외부 |
| **2.4** C4/C5 optional | 선택 결정 분리 |

---

## §4. CP2 closure 경로 추정

P2 게이트 9개 중 2 ✓ + 7 □. weakest-link 우선 처리 시:

**0-cost 단계 (1-2일, 즉시 가능)**:
1. raw#31 promotion ceremony (administrative)
2. UNIVERSAL_4 axis survey
3. C3 drill SHA fixpoint 측정

→ 7 □ → 4 □ (3 가지 0-cost 처리 후)

**GPU 단계 ($5-8 + $300-2000)**:
4. C1 r8 잔존 닫기 (B/C swap, $5-8)
5. C2 real lattice run + natural-run gen-5 통합 (CP1 효율 적용 시 $300-1000)

**외부 task 정착**:
6. C4/C5 optional 선택 결정 (사용자)

→ **strict CP2 closure**: 1-2주 + 약 $310-1010 (CP1 효율 패턴 유지 시)
→ `.roadmap` L88-L89 budget $2500-3500 의 약 12-30%, 누적 ≈ $340-1040

---

## §5. H-MINPATH 자동 픽

decision_order = blocker=0 → steps↑min → loc↑min → 첫번째.

**Pick: §3.1 항목 #1 (raw#31 promotion ceremony)** — blocker=0, steps=1 (최소), administrative single commit.

근거:
- evidence (drill ✓ + V_sync+V_RG land) 이미 충족
- `.roadmap` L182 명시 "공식 승급" 만 빠진 administrative gap
- meta²-cert 또는 raw_axiom 에 entry 추가 = 0-cost ceremony
- POLICY R4 (`.roadmap` 미수정) 준수 — promotion 자체는 별 SSOT

---

## §6. 정리

| 항목 | 분류 | 다음 단계 |
|---|---|---|
| 본 문서 commit | $0 | inventory landing |
| raw#31 promotion (다음 H-MINPATH) | $0 | cert ceremony |
| UNIVERSAL_4 axis survey | $0 | analytical |
| C3 drill SHA fixpoint | $0 | measurement |
| C1 r8 잔존 (B/C) | $5-8 | GPU |
| C2 real lattice + nat-run gen-5 | $300-1000 | GPU |
| C4/C5 결정 | (decision) | user |
| natural-run gen-5 (#4) | (external) | task track |

→ CP2 closure 경로 명확화 완료, weakest-link 식별 완료.
