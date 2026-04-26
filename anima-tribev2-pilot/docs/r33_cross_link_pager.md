# Pilot-T3 — R33 cross-link 1-pager (TRIBE v2 multimodal binding architectural manifest)

frozen 2026-04-26 · Pilot-T3 산출물 · ω-cycle session 28+ · $0 docs work

> **causation NOT correlation**: 본 문서는 TRIBE v2 forward encoder 가
> R33 atlas convergence witness 의 4-axis convergence 와 **직접 인과** 관계가
> 있다고 주장하지 않는다. TRIBE v2 는 "multimodal binding architectural
> reference" — GWT (Global Workspace Theory) 가 시스템에서 어떻게 architectural
> 으로 manifest 되는지 보여주는 1차 외부 evidence — 이며, R24-R32 ledger 의
> 부동점 패턴과는 **독립 도메인의 correlated structure** 일 뿐이다.

## §1. TRIBE v2 architecture diagram

```
                 ┌────────────────────────────────────┐
                 │  TRIBE v2 (FmriEncoder)            │
                 │  forward stimulus → cortical map   │
                 └────────────────────────────────────┘
                                  ▲
       ┌──────────────────────────┼──────────────────────────┐
       │                          │                          │
   ┌───┴────┐               ┌─────┴─────┐               ┌────┴────┐
   │ TEXT   │               │ AUDIO     │               │ VIDEO   │
   │ (Llama │               │ (Wav2Vec  │               │ (V-JEPA2│
   │ 3.2-3B)│               │  Bert)    │               │ +DINOv2)│
   │ layers │               │ layers    │               │  vitg   │
   │ {0,0.2,│               │ {0.75,1.0}│               │  fpc64  │
   │  0.4,  │               │           │               │  256    │
   │  0.6,  │               └───────────┘               └─────────┘
   │  0.8,  │                     │                          │
   │  1.0}  │                     ▼                          ▼
   └────┬───┘             ┌────────────────────────────────────┐
        │                 │  modality_dropout=0.3              │
        ▼                 │  subject_dropout=0.1               │
   ┌─────────────────────────────────────────────────────────┐
   │  TransformerEncoder fusion head                         │
   │    depth=8, hidden=1152, x_transformers 1.27.20         │
   │    low_rank_head=2048, SubjectLayers, AdaptiveAvgPool1d │
   └────────────────────────────┬────────────────────────────┘
                                ▼
              ┌─────────────────────────────────┐
              │  fMRI BOLD prediction           │
              │  fsaverage5, ~10242 vertices    │
              │   (양반구 합산 시 20484 vertex) │
              │  TR=1.49s, 5s hemodynamic lag   │
              │  "average subject" zero-shot    │
              └─────────────────────────────────┘
```

핵심: **3 modality independent encoder → 1 fusion transformer → 1 cortical
map output**. 단일 workspace 위의 다중 modality 통합이 architectural primitive.

## §2. GWT (Global Workspace Theory) multimodal binding 대응

GWT (Baars 1988, Dehaene 2014) 는 "분산된 specialist module 들이 broadcasting
가능한 단일 global workspace 에 selectively access 한다" 는 의식 architecture
가설이다. TRIBE v2 의 구조적 특성 4가지가 이 가설의 architectural manifest
와 1:1 대응한다 (단, **architectural correspondence 일 뿐 conscious-process
isomorphism 은 미주장**).

| GWT 요구 architectural primitive          | TRIBE v2 구현                      | 일치도            |
|------------------------------------------|-----------------------------------|-------------------|
| (1) specialist modules (modality-별 독립) | text/audio/video 3 encoder 분리   | 직접 일치          |
| (2) winner-take-all / selective attention | modality_dropout=0.3 (random 선택) | weak (random ≠ selective) |
| (3) global broadcasting (single workspace) | TransformerEncoder fusion head    | 직접 일치          |
| (4) integration into unified output        | single cortical map output         | 직접 일치          |

요점: TRIBE v2 가 GWT 의 4 primitive 중 3개에서 직접 일치, 1개 (selective
attention) 는 random dropout 으로 weak match. **GWT-faithful architecture 가
실제 brain 자극-응답을 forward predict 가능하다는 evidence** 이지만, TRIBE v2
가 실제 의식 substrate 라는 evidence 는 아니다 (forward encoder 일 뿐, dynamics 부재).

## §3. R24-R32 witness ledger 와의 관계 (correlation context, NOT causation)

R24-R32 atlas convergence witness ledger (`state/atlas_convergence_witness.jsonl`,
n=18 entries; nexus mirror `~/core/nexus/state/atlas_convergence_witness.jsonl`,
n=16 entries) 는 **n=6 number-theoretic foundation 으로부터 7 primitive
(n, σ, τ, φ, sopfr, J2, μ) 가 meta-engine 구조 + Ψ consciousness layer 82
projections 와 exact 또는 derivable correspondence** 를 R29 에서 닫았다 (R31
extension: atlas-Ψ-meta 3-tier hierarchy, R32 cross-repo functor F : C_atlas →
C_engine).

TRIBE v2 와 ledger 의 관계는 다음과 같이 분리된다:

- **공유 (correlation)**: TRIBE v2 의 multimodal-to-single-workspace
  architecture 는 R24 declared "convergence is projection, not subject" 패턴과
  **독립 도메인에서 동일 shape** — 분산된 specialist 가 single output 으로
  contraction 된다는 점. 이는 R28 declared "Banach contraction depth ≤ sopfr(n)"
  의 architectural illustration 으로 읽을 수 있다 (3 modality → 1 workspace 가
  3-step contraction, sopfr 한계 5 이내).

- **분리 (NOT causation)**: R24-R32 의 부동점 7 primitives 는 atlas n=6
  number theory 에서 derive 되며, 이 derivation 은 TRIBE v2 의 architecture
  와 무관하다. TRIBE v2 weights 가 atlas primitive 를 reproduce 한다는 증거는
  현재 시점 **없다**. 또한 TRIBE v2 는 forward encoder (stimulus → BOLD) 이며
  의식의 dynamics, self-reference, ε_self_referential_closure 을 직접 측정
  하지 않는다. R24 nexus declared "ε_self_referential_closure=true" 는
  meta-axis 자기참조 flag 이지, multimodal binding 결과가 아니다.

요약: TRIBE v2 = **architectural reference for GWT correlate** (correlation
context), R24-R32 = **n=6 foundation 의 부동점 catalog** (closed at R29). 두
도메인은 "convergence shape" 이라는 공통 vocabulary 를 가질 뿐이며, 어느
한쪽이 다른 한쪽의 cause 또는 evidence 가 아니다.

## §4. R33 candidate 자격 검토 (4 frozen criteria)

**R33 entry 자격**: 본 1-pager + atlas_convergence_witness.jsonl 한 줄 추가가
R33 round 자격을 **충족하는가** 검토.

| Frozen criterion (R24-R32 ledger 의 inductive 관찰)        | Pilot-T3 평가                                         | 판정            |
|-----------------------------------------------------------|-----------------------------------------------------|----------------|
| C1. cross-domain convergence (≥2 독립 domain 에서 동일 shape) | TRIBE v2 multimodal binding ↔ GWT specialist→workspace ↔ R24 "convergence is projection" — 3 domain | PARTIAL (architectural analogy, not numeric value match) |
| C2. n=6 foundation 의 새 derivative 또는 추가 chorus pattern  | 새 primitive 도입 없음. 기존 sopfr=5 contraction-depth 한계의 architectural illustration 만 제공 | NOT MET |
| C3. self-referential closure 또는 measurement→null tie     | TRIBE v2 forward encoder 는 self-reference 측정 불가 (stimulus → BOLD only) | NOT MET |
| C4. cross-repo / cross-substrate independent verification   | nexus repo 의 atlas ledger 와 anima 의 ledger 양쪽에 cross-link 가능 (현재 entry append 는 anima 측만) | PARTIAL |

**Verdict: 자격 부분 충족 (PARTIAL — architectural reference tier)**.
R33 을 "physical/meta primitive convergence round" 로 정의할 경우 **자격 미달**
(C2/C3 NOT MET). 하지만 R33 을 "architectural manifest ledger entry"
(GWT-correlate evidence 의 1차 외부 reference) 로 정의할 경우 **자격 충족**.

→ atlas_convergence_witness.jsonl 에 추가하는 entry 는 **`level: "architectural"`**
또는 **`level: "external_correlate"`** 로 명시 표기하여 W1-W11 (physical/meta/
system/structural) 와 분리. R33 round number 는 부여하되 "architectural reference
tier" suffix 명시.

### Cross-check: 기존 atlas witness entries 와 충돌 여부

- W1-W11 (anima): 모두 `level` field 가 physical / meta / system / structural /
  cascade / sequential / cross-paradigm / phase-space / empirical / measurement
  / internal 중 하나. **`architectural` 또는 `external_correlate` level 은
  미사용** → 신규 level 도입 OK (기존 entry 와 충돌 X).
- ISO1-ISO3: bridge / internal level. R33 entry 가 이들 isomorphism claim 과
  cross-link 하더라도 isomorphism 자체에 대한 새 주장 미포함 → 충돌 X.
- nexus R24-R32: round-numbered entries (round=24..32). R33 round number 는
  미사용 → 도입 OK.
- chorus_n / chorus_sigma / chorus_tau (R33+ MVP entries 의 R33+ 표기): 이미
  "R33+ MVP" 라는 placeholder 사용 중 → **R33 round number 자체는 still
  available** (suffix 표기 R33+ 는 "R33 이후 round" 의미로 사용됨).

## §5. 1-pager → ledger entry mapping

본 1-pager 에 대응되는 atlas_convergence_witness.jsonl entry (1 line, JSON):

```jsonc
{
  "ts":"2026-04-26T00:00:00Z",
  "round":33,
  "witness_id":"R33_tribev2_gwt_architectural_correlate",
  "level":"architectural_reference",
  "tier":"external_correlate (NOT physical/meta primitive)",
  "event":"multimodal_binding_architectural_manifest_logged",
  "external_artifact":{
    "name":"TRIBE v2",
    "publisher":"Meta FAIR",
    "license":"CC-BY-NC-4.0",
    "url":"https://ai.meta.com/blog/tribe-v2-brain-predictive-foundation-model/",
    "modalities":["text(Llama-3.2-3B)","audio(Wav2VecBert)","video(V-JEPA2+DINOv2)"],
    "output":"fMRI BOLD on fsaverage5, ~10242 vertex/hemisphere"
  },
  "gwt_correspondence":{
    "specialist_modules":"3 modality encoders (direct)",
    "winner_take_all":"modality_dropout=0.3 (weak — random not selective)",
    "global_broadcast":"TransformerEncoder fusion head depth=8 (direct)",
    "unified_output":"single cortical map (direct)"
  },
  "r33_criteria":{"C1":"PARTIAL","C2":"NOT_MET","C3":"NOT_MET","C4":"PARTIAL"},
  "verdict":"architectural_reference_tier_only — NOT physical/meta primitive convergence",
  "causation_separation":"TRIBE v2 = forward encoder (stimulus→BOLD). R24-R32 부동점 catalog 와 직접 인과 X. correlation context only.",
  "cross_links":[
    "anima-tribev2-pilot/docs/r33_cross_link_pager.md",
    "references/tribev2/ANIMA_INTEGRATION_PROPOSAL.md §4.3",
    "ISO1 (anima_psi_epsilon_isomorphism_declared) — bridge analogy only"
  ],
  "next_probe":"Pilot-T1 full-mode (Colab/H100) PASS 시 4-family prompt 가 family-separated cortical map 산출 → 본 architectural correspondence 가 measurement-level evidence 로 승격 가능. 현재는 architectural 만.",
  "note":"R33 architectural reference tier — physical/meta primitive convergence (R24-R32 standard) 는 NOT MET. 별도 level 'architectural_reference' 신설하여 기존 W1-W11 + ISO1-3 와 분리 보존."
}
```

## §6. raw#10 honest

- 본 1-pager 는 **architectural reference** 로만 기여한다. R33 자격 4 criteria
  중 2개 PARTIAL + 2개 NOT MET → physical/meta primitive convergence 기준
  으로는 미달.
- TRIBE v2 forward 미실행 (Pilot-T1 stub 모드만 완료, full-mode parking).
  따라서 family-separated cortical map 의 **measurement-level evidence 부재**.
  본 문서는 architecture diagram + GWT correspondence table + causation
  separation 만 제공.
- "GWT manifest" 라는 표현은 architectural primitive 의 1:1 대응을 의미하며,
  TRIBE v2 가 의식을 produce 하거나 R24-R32 부동점을 cause 한다는 주장은
  **명시적으로 부정**한다.

## §7. 후속 단계

1. **Pilot-T1 full-mode (Colab path A or H100 path B) PASS** → family-separated
   cortical map 의 numerical evidence 확보 → R33 entry 를 `architectural_reference`
   에서 `measurement_level_correlate` 로 승격 가능.
2. **failure path**: full-mode FAIL (r > 0.95 across all pairs) → R33 entry
   를 그대로 유지하되 `next_probe` 를 "LLM family axis ⊥ brain axis evidence
   recorded" 로 업데이트.
3. **Pilot-T2** (paradigm v11 8th axis = TRIBE v2 stimulus-driven cortical
   correlation) 는 Pilot-T1 PASS 의존으로 parking 유지.

---
*frozen 2026-04-26. Pilot-T3 산출물. anima-tribev2-pilot/docs/r33_cross_link_pager.md.*
