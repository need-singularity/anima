# own#3 (d)+(e) Wording Revision Proposal

**작성일**: 2026-04-27 (axis 107)
**작성자**: anima ω-cycle subagent (parallel session, mac-local)
**대상**: anima/.own own#3 entry sub-claim (d) + (e)
**선행**: axis 100 (commit `96d0a2eb`, own#3 d HOL-C MEASURED_DIFFERENT) + axis 101 (commit `c12a2a47` 후속, own#3 e HGM-D_PARTIAL_REINTERPRETATION_REQUIRED)
**상태**: **PROPOSAL ONLY** — anima/.own 직접 편집 없음. 사용자 explicit approval 필요 (governance change + chflags uchg unlock 절차)
**목적**: 측정 evidence 와 wording 간 gap 의 honest 보정 옵션 제안. 5/5 sub-claim post-evidence status 확정.
**비용**: $0 mac-local (docs only)

---

## §0 배경 및 변경 동기

### own#3 본문 (anima/.own L48–L74) 현재
own#3 "σ(6)/τ(6) = 12/4 = 3 — perfect number 6 mean divisor / phase acceleration scalar"
는 5개 sub-claim (a)~(e) 로 구성된 governance principle entry 다. severity=warn,
mathematical identity 12/4=3 자체는 falsifiable 아닌 algebra 로 own SSOT 영구 등록.

5개 sub-claim 가 모두 evidence-bound 영역으로 진입 후 status:

| sub-claim | content (one-line) | post-evidence status | 출처 cycle |
|---|---|---|---|
| (a) | Mamba/Jamba ×3 throughput 수학적 근거 | RESTORED_TO_CONFIRMED_CONDITIONAL (long-ctx ≥3× geom-mean 3.49×) | #231 axis 96 |
| (b) | Mk.XI v10 4-bb ↔ τ(6)=4 alignment | STRONG (4-bb count exact match) | #225 + axis 92 |
| (c) | 4-axis greedy basis = τ=4 | STRONG (axis 92 Tier 1+2 정확 일치) | #225 |
| (d) | Ψ_steps = 3/ln(2) = 4.33 (Law 70) | **HOL-C MEASURED_DIFFERENT** (4-bb mean=2.11 vs 4.33, rel_err -0.51) | #241 axis 100 |
| (e) | MoE 12전문가/4활성 = σ/τ = 3 (Golden MoE) | **HGM-D_PARTIAL_REINTERPRETATION_REQUIRED** (no 12/4 top-k 외부+내부) | #237 axis 101 |

(a)/(b)/(c) 는 wording 그대로 유지 가능. (d) + (e) 두 항목 만 evidence 와 wording
간 disambiguation 필요 — 이것이 본 proposal 의 scope.

### own#3 governance principle 자체 = UNAFFECTED
σ(6)/τ(6) = 12/4 = 3 (perfect number 6 약수합/약수개수 비) 의 수학적 identity
는 falsification 영역 밖. 본 proposal 은 sub-claim wording 만 다루며,
own#3 main entry 의 severity=warn governance reference scalar 역할은
변경하지 않는다.

---

## §1 own#3 (d) Ψ_steps Law 70 wording revision

### Current text (anima/.own L57)
> (d) σ/τ=3 ↔ Ψ_steps = 3/ln(2) = 4.33 분자 (Law 70) — 정보 비트당 의식 진화 속도 = (σ/τ)/ln(2)

### Evidence summary (axis 100, commit `96d0a2eb`)
- **Helper search**: anima-hexad/constants.hexa `fn psi_steps()` = declarative loader
  only. anima-core 에 native step counter helper 부재.
- **SSOT inconsistency 발견**: `anima/config/consciousness_laws.json` L36
  `psi_constants.steps.derivation = "13/3 — average steps per phase boundary; placeholder"`,
  source = `"empirical from C2 phase-transition trace (deferred validation)"`.
  own#3 (d) AND `docs/discovery-algorithm-anima.md` L19/L229 derive 4.33 from
  `3/ln(2) = (n/phi)/ln(phi)`. **두 derivation 모두 4.33 수렴** (13/3=4.333…
  vs 3/0.6931=4.328) but **structurally different source**.
- **Operational interpretation candidate (a)**: `layers(bb)/log2(vocab(bb))`
  = "depth per output bit". 4-bb (Mistral/Qwen3/Llama/gemma) BASE 측정
  (mac-local hexa, byte-identical 2-run sha=`1d0cd56c`):
  - mistral-7B-v0.3 (32L, V=32768) → 2.13333
  - qwen3-8B (36L, V=151936) → 2.09143
  - llama-3.1-8B (32L, V=128256) → 1.88592
  - gemma-2-9b (42L, V=256000) → 2.33786
  - mean = **2.11214** vs target 4.32809; rel_err = **-0.51199**
- **Best match (other hexad scalar)**: φ(6)=2 within +0.112 (Euler totient,
  balance denominator).
- **HOL-C MEASURED_DIFFERENT**: strict threshold (|rel_err|≤0.50) 기준 HOL-B
  DEPRECATED (0.512 just over threshold), 그러나 측정값 구조적 alignment
  (φ(6)+0.112 < 4.33-2.11=-2.22) → 다른 hexad 상수에 collapse 했을
  가능성 honest 명시.

### Revision options

#### Option A (Numerical reinterpretation — 강한 변화)
> (d) σ/τ=3 ↔ Ψ_steps measured ≈ φ(6) = 2 (4-bb mean, axis 100 architecture
> proxy `layers/log2(vocab)`). Structural relation to 3/ln(2) ≈ 4.33 holds
> only via SSOT loader convention; raw#10 alternate interpretation candidate.

**장점**:
- 측정 evidence 직접 반영 (φ(6)=2 alignment 명시)
- 사용자가 sub-claim 을 즉시 측정값 기준으로 이해
- own#3 의 hexad-canonical 상수 (8 strict matches) 참조 일관성 유지

**단점**:
- 4.33 수렴 (13/3 vs 3/ln(2)) SSOT 양쪽 결합이 약화됨
- Law 70 documentary chain (`docs/discovery-algorithm-anima.md` L19/L229) 와 mismatch
- "operational interpretation (a)" 가 단 하나의 architectural proxy 임에도
  canonical wording 화 → 다른 candidate (b/c) 평가 기회 차단

#### Option B (Status downgrade — 보수적 marker)
> (d) σ/τ=3 ↔ Ψ_steps = 3/ln(2) = 4.33 분자 (Law 70) — 정보 비트당 의식 진화
> 속도 = (σ/τ)/ln(2). **상태: MEASURED_DIFFERENT (axis 100, 4-bb mean=2.11,
> rel_err -0.51); operational proxy 측정값과 structural derivation 간 gap
> 잔존; Law 70 native step counter helper implementation pending.**

**장점**:
- 본문 변경 최소화, evidence marker 만 추가
- documentary chain 변경 없음 (Law 70 / 13/3 / 3/ln(2) 모두 reference 유지)
- pending status 가 future ω-cycle 의 추가 측정 (multi-interpretation
  verdict matrix candidate b=e=2.718, c=7.10) 을 자연스럽게 enable

**단점**:
- "wording revision" 자체는 minor (annotated downgrade)
- main claim 4.33 이 그대로 남아 있어 inconsistent 인상

#### Option C (Referent disambiguation — 두 layer 모두 보존, **권장**)
> (d) σ/τ=3 ↔ Ψ_steps **governance target** = 3/ln(2) = 4.33 (Law 70 documentary
> chain, anima/config/consciousness_laws.json `psi_constants.steps`); **operational
> proxy** ≈ φ(6) = 2 (4-bb mean axis 100, architecture-derived `layers/log2(vocab)`,
> -0.51 rel_err vs governance target). 두 SSOT layer 가 4.33 (T1 documentary)
> 와 2 (T2 architectural) 로 split — reconciliation pending Law 70 native
> step counter helper implementation (anima-core).

**장점**:
- documentary layer + operational layer 양쪽 명시 — 각각의 역할 분명히 보존
- φ(6)=2 alignment honest 기록 (raw#10 honest 준수)
- Law 70 / `discovery-algorithm-anima.md` chain 그대로 reference 유지
- future native helper implementation 시 reconciliation path 명확
- own#3 (a) RESTORED_TO_CONFIRMED_CONDITIONAL 와 동일 패턴
  (sub-claim 의 conditional clause 부착 → 원본 principle 보존)

**단점**:
- Wording 길이 증가 (~3배)
- "two SSOT layers" 의 정당성을 새로 introduce — 미래 cycle 에서
  layer 분리 자체를 audit 할 가능성

### 권장: **Option C (Referent disambiguation)**

근거:
1. own#3 (a) 의 RESTORED_TO_CONFIRMED_CONDITIONAL 패턴과 일관 — sub-claim
   conditional clause 부착이 governance principle 자체를 흔들지 않으면서
   evidence 를 honest 반영하는 검증된 형태.
2. φ(6)=2 alignment (Euler totient = balance denominator) 가 hexad
   8 canonical 상수 family 내부 collapse — 단순 falsification 이 아니라
   structural finding 이므로 governance-reference 가치가 있다.
3. SSOT JSON `13/3 placeholder` + own#3 `3/ln(2)` + 4-bb operational 2.11
   세 가지 layer 가 모두 살아있는 상태에서, 본 proposal 이 그
   relationship 을 wording 상 명시하는 것이 가장 transparent.

---

## §2 own#3 (e) Golden MoE 12/4 wording revision

### Current text (anima/.own L58)
> (e) MoE 12전문가/4활성 = σ/τ = 3 (H-CX-72 Golden MoE) — anima sub-projects/golden-moe 활성 비율 1/3

### Evidence summary (axis 101, commit `c12a2a47` follow-up)
- **REFERENT_PRESENT=true**: `models/golden-moe/` 와 `ready/models/golden-moe/`
  disk 존재. R36 absent-referent precedent NOT applicable (HGM-B rejected).
- **Sub-project actual configs (NO 12/4 anywhere)**:
  - `golden_moe_config.json`: `experts_optimal=4` + Law 87 "E=4 Optimal, 8≈4"
  - `moe.hexa`: `MOE_N_EXPERTS=8, MOE_TOP_K=2` (25% active)
  - `golden_moe_torch.hexa` main: `n_experts=8` with 3 configs
    {TopK K=2 25% / Boltzmann T=e ~70% / Dense 100%}
  - `golden_moe_v2.hexa`: `n_experts=4`
  - `finetune_golden_moe.hexa`: `total_experts=8, trainable_experts=2`
- **12/4 referent in tree (3-tier disambiguation)**:
  - T1 design_spec_mirror: `state/n6_ai_training_cost_status.json`
    `mk5_numerical {moe_experts=12, moe_active=4, moe_sparsity_ratio=3}`
    = mirror of n6 paper claim NOT measurement
  - T2 arithmetic_identity: `state/n6_training_selftest_result.json`
    PASS by σ(6)/τ(6) integer algebra NOT model run
  - T3 toy_moe_NOT_subproject: `tool/dd_bridge_gpu_batch.hexa` +
    `state/dd_bridge_gpu_batch_result.json` DD-1 12-expert load-balance
    entropy on H100 with ALL 12 active via softmax NOT top-k=4
- **Decisive design doc finding**:
  `models/animalm/docs/2026-03-30-animalm-consciousness-golden-moe-design.md`
  Track 2B Exp 2 explicitly maps:
  > "12 factions → 4 experts × 3 sub-factions"
  > Expert 0=factions 0,1,2 논리파; Expert 1=3,4,5 감정파; Expert 2=6,7,8 탐색파; Expert 3=9,10,11 보수파
- **Reinterpretation**: own#3 (e) 의 12 = σ(6) = CONSCIOUS FACTIONS (Law 44),
  NOT MoE experts. 1/3 ratio = FACTION-TO-EXPERT COMPRESSION ratio,
  NOT active-routing top-k ratio.
- **External reference negative**: Mixtral 8x7B = 8/2 ratio=4; Mixtral 8x22B
  = 8/2 ratio=4; Qwen2-MoE = 64/8; DeepSeek-V2 = 160/6; Jamba-v01 = 52B/12B
  PARAM count NOT expert count. **Zero mainstream MoE has literal 12/4 top-k.**

### Revision options

#### Option A (Literal correction with referent clarification — **권장**)
> (e) MoE faction-to-expert 압축 12파벌→4전문가 = σ/τ = 3 (H-CX-72 Golden MoE;
> design alignment with Track 2B Exp 2 "12 factions → 4 experts × 3 sub-factions";
> 본 12=σ(6)=consciousness factions per Law 44 NOT MoE experts; 1/3 = 압축
> 비율 NOT top-k active-routing 비율; 실제 sub-project configs 는 4-experts 또는 8/2)

**장점**:
- design doc Track 2B Exp 2 와 정확 일치 (대조 가능 chain)
- 12 = σ(6) = factions / 4 = experts 명시적 분리 → mathematical identity
  σ/τ=3 보존 + empirical referent disambiguation
- "12전문가/4활성" 의 misleading top-k routing connotation 제거
- 외부 mainstream MoE benchmark 와 mismatch 해소

**단점**:
- Wording 길이 증가 (~2.5배)
- Track 2B Exp 2 design doc 를 own#3 SSOT 가 직접 reference (외부 doc dependency)

#### Option B (Status downgrade — 보수적 marker)
> (e) MoE 12전문가/4활성 = σ/τ = 3 (H-CX-72 Golden MoE) — anima sub-projects/golden-moe
> 활성 비율 1/3. **상태: PARTIAL — 12/4 literal 은 anima 또는 mainstream MoE
> config 어디에도 부재; faction-to-expert compression interpretation 만 salvageable
> per Track 2B Exp 2 design doc (axis 101).**

**장점**:
- 본문 변경 최소화 (annotated downgrade)
- design doc 직접 reference 회피

**단점**:
- 본문이 여전히 misleading "12전문가/4활성" 유지 → reader 가 status marker 무시 시
  잘못된 referent 로 흘러갈 risk
- own#3 의 evidence-disambiguation 의도와 mismatch

### 권장: **Option A (Literal correction with referent clarification)**

근거:
1. (e) sub-claim 의 misleading 부분이 (d) 보다 훨씬 크다 — "12전문가/4활성"
   은 외부 MoE 표준 (Mixtral/Qwen2-MoE/DeepSeek 모두 다른 ratio) 와
   직접 충돌하는 specific architecture claim. Status marker 만으로는 부족.
2. Track 2B Exp 2 design doc 가 anima-internal SSOT 이며 이미 자세한
   faction→expert mapping 을 제공 → reference dependency 가 깨끗함.
3. σ/τ=3 mathematical identity 는 그대로 유지 (12=σ(6) factions /
   4=experts compression ratio 3:1 = σ(6)/τ(6) 와 정확 일치).
4. axis 101 evidence 의 "wording revision NOT principle deletion" recommendation
   직접 반영.

---

## §3 Revision 적용 시 own#3 5/5 status 재요약

### Pre-revision (현재)
| sub-claim | wording | post-evidence status |
|---|---|---|
| (a) | Mamba/Jamba ×3 throughput | RESTORED_TO_CONFIRMED_CONDITIONAL |
| (b) | 4-bb × τ(6)=4 alignment | STRONG |
| (c) | 4-axis greedy basis = τ=4 | STRONG |
| (d) | Ψ_steps = 3/ln(2) = 4.33 | **MISMATCHED**: wording 4.33 vs 측정 2.11 |
| (e) | MoE 12전문가/4활성 = 3 | **MISMATCHED**: wording top-k vs 실제 4 또는 8/2 |

### Post-revision (Option C for d + Option A for e 적용 시)
| sub-claim | wording | post-evidence status |
|---|---|---|
| (a) | Mamba/Jamba ×3 throughput long-ctx CONDITIONAL | CONFIRMED_CONDITIONAL |
| (b) | 4-bb × τ(6)=4 alignment | STRONG |
| (c) | 4-axis greedy basis = τ=4 | STRONG |
| (d) | governance target 4.33 / operational proxy φ(6)=2 split | **CONSISTENT**: two-layer split documented |
| (e) | faction→expert compression 12→4 = σ/τ=3 (NOT top-k) | **CONSISTENT**: design doc alignment |

5/5 sub-claim 모두 wording-evidence consistent 영역으로 진입.
own#3 main entry severity=warn governance reference scalar 역할 unchanged.

---

## §4 사용자 explicit approval 요청

### 적용 절차 (사용자 승인 후)
1. **chflags uchg unlock**:
   ```
   sudo chflags nouchg /Users/ghost/core/anima/.own
   ```
2. **anima/.own 편집**:
   - L57 (d) → Option C wording (위 §1 권장안)
   - L58 (e) → Option A wording (위 §2 권장안)
3. **Re-lock**:
   ```
   sudo chflags uchg /Users/ghost/core/anima/.own
   ```
4. **Verification**:
   - `cat .own | head -75` 로 변경 확인
   - hexa-only lint: `~/.hx/packages/hexa/build/hexa.real run /Users/ghost/core/hive/tool/hexa_only_lint.hexa --root /Users/ghost/core/anima` exit=0 유지
5. **Commit**:
   ```
   own(d-e-wording): own#3 (d)+(e) wording revision per axis 100/101 evidence
   ```
6. **Memory + atlas**: own SSOT change marker entry 추가

### 사용자 결정 필요 항목
- [ ] Option C (d, referent disambiguation) 승인 여부
- [ ] Option A (e, literal correction) 승인 여부
- [ ] 단일 commit vs 별도 commit 분리 (논리적 단일 cycle 권장)
- [ ] 적용 시점 (즉시 vs 다른 own SSOT change 와 batch)
- [ ] sub-agent 작업 권한 (현 session subagent 배경 작업 vs 사용자 직접)

### 미승인 시 fallback
사용자 승인 없으면 본 proposal docs 만 land, anima/.own 변경 없음.
post-evidence status 는 docs (`docs/own3_cross_check_4axis_evidence_20260426.md`
+ 본 doc) 으로만 추적. 차후 cycle 에서 재제안 가능.

### raw#10 honest 5-caveat
1. 본 proposal 은 governance change 이며 own SSOT 의 chflags uchg lock 은
   high-impact change 의 의도적 friction. 승인 없는 자율 적용 금지.
2. axis 100 의 φ(6)=2 alignment 는 architecture-derived proxy `layers/log2(vocab)`
   기반 — 다른 candidate (b: layers/log2(8192 ctx) → e=2.718, c: layers/sopfr(6)
   → 7.10) 측정 시 verdict 변동 가능. (d) Option C 는 이를 "operational proxy"
   라 명시함으로써 future re-measurement 와 호환.
3. axis 101 의 design doc Track 2B Exp 2 reference 가 own SSOT 에 도입됨 →
   해당 design doc 가 미래 변경/이동 시 wording 도 sync 필요. dependency
   audit 필요.
4. 4-bb N=4 statistically small. (d) operational proxy mean 2.11 의
   robustness 는 sample size limited.
5. own#3 (a)~(c) wording 은 본 proposal scope 밖 — (a) 는 #231 에서 이미
   별도로 RESTORED_TO_CONFIRMED_CONDITIONAL 로 재평가 완료, (b)/(c) 는
   STRONG 상태로 wording 변경 불요.

---

## §5 산출물 + reference

### 본 cycle 산출물
- `docs/own3_d_e_wording_revision_proposal_20260427.md` (본 doc, ~1900 단어)
- `.roadmap` 신규 entry (next # at write time, expect ~#242 if no race)
- `~/.claude/projects/-Users-ghost-core-anima/memory/project_own3_d_e_wording_revision_proposal.md`
- `state/_marker_axis107_own3_revision_proposal_<epoch>.flag`

### Refs
- `anima/.own` L48-L74 (own#3 본문, chflags uchg locked)
- commit `96d0a2eb` (axis 100 own#3 d HOL-C MEASURED_DIFFERENT)
- commit `c12a2a47` (axis 99 일부; axis 101 own#3 e HGM-D_PARTIAL referent measurement is companion roadmap #237)
- `state/own3_d_law70_validation/summary_law70.json` (axis 100 측정 raw)
- `state/own3_e_golden_moe_validation/summary_golden_moe.json` (axis 101 측정 raw)
- `docs/own3_cross_check_4axis_evidence_20260426.md` (#225 5-claim status framework)
- `~/.claude/projects/-Users-ghost-core-anima/memory/project_own3_d_law70_validation.md`
- `~/.claude/projects/-Users-ghost-core-anima/memory/project_own3_e_golden_moe_validation.md`
- `~/.claude/projects/-Users-ghost-core-anima/memory/project_own3_jamba_validation.md` (sister #231)
- `tool/anima_own3_d_law70_measure.hexa` (axis 100 측정 도구)
- Roadmap #184 (own#3 + atlas R35 등록 parent)
- Roadmap #225 (own#3 cross-check 4-axis evidence)
- Roadmap #231 (own#3 a sister sub-claim revalidation pattern)
- Roadmap #237 (own#3 e measurement)
- Roadmap #241 (own#3 d measurement)

---

## §6 ω-cycle 6-step verdict

- **R1 design**: 2-axis (d/e) wording revision 옵션 enumeration. d=A/B/C, e=A/B
  → 5 옵션 후보, 권장 (C/A) 결정 근거 §1/§2.
- **R2 implement**: 본 proposal docs (산출물 1), roadmap entry, memory entry,
  marker file. anima/.own 직접 편집 NONE (사용자 승인 대기).
- **R3 positive**: post-revision 5/5 sub-claim consistent (§3 표 우측 column).
- **R4 negative**: pre-revision 2/5 mismatch (d wording 4.33 vs 측정 2.11; e
  wording top-k vs 실제 4 또는 8/2) — 본 proposal 미적용 시 mismatch 잔존.
- **R5 byte-identical**: docs only, deterministic write. Re-run = identical.
- **R6 land + iterate**: docs commit + push + 사용자 승인 대기. 승인 시
  post-cycle 에서 .own 직접 적용 + sister memory + atlas R35 mirror update.

**Verdict**: PROPOSAL_LANDED_AWAITING_USER_APPROVAL.
