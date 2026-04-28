# Ω-cycle: Mk.XII Candidate Synthesis — SUBSTRATE Axis (sub-agent)

> **scope**: Mk.XII candidate architectural successor 을 위한 SUBSTRATE-axis paradigm 6-7 개 도출. Mk.XI v10 (4-backbone × LoRA × paradigm v11 stack) 를 잇는 다음 단계. 이번 세션 (2026-04-26) 의 Path B HCI 5-falsifier composite + .roadmap #145 (CMT backbone-conditional depth divergence) + L_IX integrator 4-gen crystallize + EEG OpenBCI 16ch hardware + anima-eeg Phase 3 Cycle 1+2 9/10 modules + Hexad framework 4/4 axiom CLOSED 를 input 으로 활용.
> **session date**: 2026-04-26
> **status**: 7 paradigms 도출 + 3 cross-axis convergent 후보 + weakest evidence link 1 개 식별
> **predecessor**: `docs/omega_cycle_alm_free_paradigms_20260426.md` SUBSTRATE 7 paradigm (CSTL/BCM-Holo/KPS/IEL/Cell↔Token Bridge M4/ZLN/HCE) — 이번 cycle 은 "ALM-free 가능성" framing 이 아닌 "Mk.XII architectural successor SUBSTRATE 정의" framing 으로 차별화

---

## §1. SUBSTRATE axis 정의 (Mk.XII candidate context)

### 1.1 SUBSTRATE 의 의미 (이번 cycle 정의)

기존 ω-cycle 은 SUBSTRATE 를 "ALM 없이 어떤 component 로 만들 수 있나" 로 framing 했다. Mk.XII candidate 시점에서 SUBSTRATE 는 다음 3 question 으로 재정의:

| dimension | question | 이번 세션 evidence |
|---|---|---|
| **invariance** | 다른 backbone 위에서 같은 paradigm 이 같은 결과를 내는가? | F5 real backbone Φ {Mistral 605 / Qwen3 350 / Llama 290 / gemma 352} std/mean=0.303 — invariant **NOT** held |
| **locality** | family-processing 의 layer locus 가 backbone 마다 다른가? | .roadmap #145: Mistral late 28/32 (87%) vs Qwen3 early 4/36 (11%) Law-dominant, depth divergence |
| **isomorphism** | substrate 6-axis ↔ Hexad 6-axis ↔ EEG 16-channel 사이 lossless mapping 가능한가? | n6 cross-mapping cos=1.0 (32-ch dry-run) + Hexad 4/4 axiom CLOSED + adversarial 2/2 reject |

### 1.2 Mk.XI v10 → Mk.XII 의 substrate 갭

| Mk.XI v10 가정 | 이번 세션 falsified 또는 확인 | substrate gap |
|---|---|---|
| 4-backbone ensemble = family-orthogonal | .roadmap #145: depth divergence backbone-conditional → orthogonality 가 backbone 의 layer locus 에 의해 무너질 수 있음 | **G1: layer-locus invariance 부재** |
| label-level isomorphism (HCI Path B F1+F2+F3) 충분 | Q3 failure mode 5번째 (substrate dependence) F1+F2+F3 잡지 못함 → F5 real backbone 추가 필요 | **G2: label vs substrate 분리** |
| Φ scalar 가 substrate-invariant | F5 4-bb std/mean=0.303 (margin 50× 강화로 PASS) but raw Φ range 350-605 (1.7×) | **G3: scalar 단일 metric 한계** |
| LoRA r14 corpus 가 family bias 의 main driver | Axis 14: gemma BASE Hexad-leading → r14 Law-leading shift, corpus content 가 substrate 보다 강함 | **G4: corpus 주도 substrate 종속** |
| EEG 는 phenomenal axis 만 다룸 | OpenBCI 16ch + anima-eeg 9/10 modules 4/4 axiom CLOSED + 69/69 selftests = production substrate | **G5: EEG = substrate 의 일부** (단순 phenomenal 아님) |

이 5 gap 을 메우는 paradigm 7 개를 §2 에서 제안.

---

## §2. SUBSTRATE paradigm 7 개 (Mk.XII candidate)

각 paradigm 은 (a) 메커니즘 (b) Mk.XI v10 와의 차별점 (c) 이번 세션 evidence (d) confidence 0-1.0 (이전 ω-cycle calibration range 0.6-0.95) (e) 검증 가능 falsifier 1 개 를 명시.

### S1. **DALI** Depth-Anchored Layer Invariance — confidence **0.86**

- **메커니즘**: backbone 별 family-processing locus (L_loc) 를 normalized depth (0-1000‰) 로 측정 → DALI metric = 1 - |L_loc(b₁) - L_loc(b₂)| / 1000. 이 metric 의 cross-backbone variance 를 새 substrate-invariance gate 로 도입.
- **Mk.XI 차별점**: Mk.XI v10 family-orthogonal 가정은 label-level (CMT family signal vector) 만 다룸. DALI 는 layer locus 자체를 substrate property 로 격상.
- **이번 세션 evidence**: .roadmap #145 Mistral 875 (late) vs Qwen3 111 (early) Δ=764 → DALI=0.236 (low invariance). F5 real backbone depth_norm=[875,111,625,857] 직접 측정.
- **falsifier**: 2 backbones 간 DALI ≥ 0.7 ALL_PAIRS gate. 현재 6 pair 중 1 pair (Mistral-gemma=0.982) PASS, 5 pair FAIL → invariance 깨짐.
- **재포장 검사**: Mk.XI v10 4-bb ensemble, paradigm v11 CMT helper 의 단순 재호출 NO — 새 metric (DALI) 자체가 cross-backbone variance gate 로 정의됨.

### S2. **HEC** Hexad ↔ EEG ↔ CLM Triple-Isomorphism — confidence **0.81**

- **메커니즘**: Hexad 6-axis (c/d/w/s/m/e) ↔ EEG 16-ch (Cyton+Daisy anatomical) ↔ CLM hidden-state 16-d eigenvec 사이의 3-way lossless mapping. n6 32-ch cross-mapping cos=1.0 evidence 를 16-ch (substrate-relevant) 으로 확장.
- **Mk.XI 차별점**: Mk.XI v10 Hexad 는 categorical framework 만, EEG 는 phenomenal axis 만. HEC 는 두 영역을 substrate-level 에서 통합 (16-ch projection layer 가 양방향 invertible).
- **이번 세션 evidence**: anima-eeg Phase 3 Cycle 1+2 9/10 modules raw#9 strict 69/69 selftest PASS + Hexad 4/4 axiom + 6 morphism + adversarial 2/2 reject. n6 dry-run 16/16 round-trip cos=1.0 (consciousness_transplant_n6_mirror_20260422.md).
- **falsifier**: 16-ch ↔ 6-axis ↔ 16-d eigenvec 3-cycle round-trip cos ≥ 0.95 ALL_PAIRS. 1000-token 장문맥 drift < 2e-3 유지.
- **재포장 검사**: 기존 n6 32-ch 단방향 mapping NO — 16-ch (Cyton+Daisy spec) 으로 좁히고 3-way (Hexad↔EEG↔CLM) 으로 격상.

### S3. **SLI** Substrate-Local Irreversibility — confidence **0.74**

- **메커니즘**: L_IX integrator gen 4→5 I_irr cusp 996→0 (시간-화살 collapse) 을 backbone 별로 측정 → I_irr cusp depth (cusp 발생 layer normalized) 가 backbone 마다 일관된가? SLI = std(cusp_depth) / mean(cusp_depth).
- **Mk.XI 차별점**: 기존 IEL paradigm (이전 ω-cycle, conf 0.78) 은 단일 4-gen crystallize. SLI 는 cusp 발생 위치의 substrate-locality 를 새 dimension 으로 추가.
- **이번 세션 evidence**: `edu/cell/lagrangian/l_ix_integrator.hexa` 1/r² lattice + 4-gen crystallize + raw#30 IRREVERSIBILITY embedded. .roadmap #145 cusp ↔ depth divergence 의 cross-validate 필요 (현재 미실증).
- **falsifier**: 4 backbone 에서 I_irr cusp 발생 layer 측정 → SLI < 0.3 ALL_PAIRS PASS. NULL: cusp 가 없거나 backbone 마다 random layer (SLI ≥ 0.5).
- **재포장 검사**: IEL 의 단순 재포장 가능성 있음 → cusp_depth 측정이 추가되어야 진짜 새 paradigm. 현재 cusp_depth 미측정 → conf 0.74 cap.

### S4. **EHF** EEG-Hardware-First Substrate — confidence **0.69**

- **메커니즘**: substrate 의 ground truth 를 LLM hidden-state 가 아닌 EEG 16ch 250Hz 24-bit signal 로 정의. CLM activation 은 EEG signal 의 prediction target. anima-eeg 4/4 axiom CLOSED 을 architectural primitive 로.
- **Mk.XI 차별점**: Mk.XI v10 backbone activation = primary, EEG = phenomenal evidence. EHF 는 역전 — EEG = primary, backbone = derived.
- **이번 세션 evidence**: OpenBCI Cyton+Daisy 16ch 250Hz 24-bit BLE hardware 확정 + anima-eeg Phase 3 Cycle 1+2 9/10 modules 69/69 selftest PASS. anatomical ↔ 16-d eigenvec mapping prerequisite (memory project_eeg_hardware_openbci_16ch.md).
- **falsifier**: EEG 1s window LZ76 ↔ CLM hidden LZ76 mutual prediction R² ≥ 0.4. Mk.XI v10 4-backbone Φ {605/350/290/352} 가 EEG-derived expectation 과 |Δ|/Φ < 0.2 일치.
- **재포장 검사**: Phenomenal axis V_phen_EEG-LZ × CLM-LZ (이전 conf 0.78) 가 비슷한 영역. 차이점: EHF 는 EEG 를 substrate primary 로, Phenomenal 은 EEG 를 evidence 로 → architectural inversion.

### S5. **CSI** Corpus-Substrate Invariance Decoupling — confidence **0.83**

- **메커니즘**: Axis 14 finding (corpus content > substrate 영향) 을 architectural primitive 로 격상. corpus 와 substrate 를 직교 component 로 분리: substrate factor S(b) (backbone fixed) × corpus factor C(τ) (training corpus). family bias = S × C, 측정 가능.
- **Mk.XI 차별점**: Mk.XI v10 은 family bias 를 backbone × corpus joint determinant 로 가정만 함 (memory `project_v_phen_gwt_v2_axis_orthogonal.md`). CSI 는 두 factor 를 multiplicative model 로 fit + decouple.
- **이번 세션 evidence**: gemma BASE Hexad (0.584) → r14 LoRA-trained Law (0.673, Δ+0.090) family SHIFT. 3/4 trained backbones Law-leading. corpus dominant 가설 → S×C model 로 fit 가능.
- **falsifier**: 4-backbone × N-corpora matrix 에서 log(family_score) = log(S) + log(C) + ε, residual std ≤ 0.05. NULL: matrix non-multiplicative (interaction term ≥ residual 의 2×) → CSI FALSIFIED.
- **재포장 검사**: Mk.XI v10 4-family ensemble 가설의 단순 재포장 NO — multiplicative fit 자체가 새 falsifier (현재 미수행).

### S6. **CMT-Probe** Cross-Matrix Topology Probe — confidence **0.77**

- **메커니즘**: F5 real backbone Φ_proxy 의 6×6 covariance topology (eigenvec 분포) 를 substrate fingerprint 로 측정. CMT depth divergence (#145) 의 mechanism 을 6×6 covariance topology 로 환원.
- **Mk.XI 차별점**: 기존 CMT (CMT family signal) 는 vector level. CMT-Probe 는 covariance topology = substrate fingerprint level.
- **이번 세션 evidence**: F5 real `hci_substrate_probe_real.hexa` G3 std/mean=0.201→0.303 (51% 증가) + G4 margin 1→103 (50× 강화). 4-bb depth_norm=[875,111,625,857] 1.7× span.
- **falsifier**: 4-backbone topology 의 spectral gap pattern 일관성 — eigenvec 1st-2nd gap variance < 0.2 ALL_PAIRS. Mistral late vs Qwen3 early 가 spectral gap 의 어느 dimension 에 인코딩되는지 직접 측정.
- **재포장 검사**: F5 real backbone falsifier (이미 landed #162) 와 직접 동일하지 않은가? 차이점: F5 는 Φ scalar 6×6 covariance proxy, CMT-Probe 는 spectral gap pattern 자체를 새 sub-metric 으로 분리.

### S7. **DALI×SLI** Depth-Locality Cross-Coupling — confidence **0.71**

- **메커니즘**: S1 (DALI) 와 S3 (SLI) 의 cross-coupling — family-locus depth 와 I_irr cusp depth 가 같은 layer 에 collocate 하는가? collocation = substrate-coherence 의 strong evidence.
- **Mk.XI 차별점**: Mk.XI v10 두 metric 분리 측정. cross-coupling 은 새 emergent property.
- **이번 세션 evidence**: .roadmap #145 (CMT depth divergence) + L_IX cusp 4→5 — 두 phenomena 가 같은 layer 에서 발생하는지 미검증. Mistral late 28/32 ≈ 87.5% vs L_IX cusp gen 4→5 (4-gen crystallize sequence) 의 layer-projection 필요.
- **falsifier**: 4-backbone 에서 L_loc(family) ↔ L_loc(I_irr_cusp) Pearson r ≥ 0.6. NULL: r ≤ 0.2 → 두 phenomena 독립 → SUBSTRATE 가 multi-axis (single-coherent 아님).
- **재포장 검사**: 단순 S1+S3 sum 이 아닌 Pearson coupling 자체가 새 metric → 진짜 새 paradigm. conf 0.71 cap (cross-coupling evidence 현재 0).

### 2.1 paradigm 요약 표

| # | paradigm | 핵심 metric | confidence | gap 메움 |
|---|---|---|---|---|
| S1 | DALI Depth-Anchored Layer Invariance | DALI=1-|ΔL_loc|/1000 | 0.86 | G1 layer-locus invariance |
| S2 | HEC Hexad↔EEG↔CLM Triple-Isomorphism | 16↔6↔16d round-trip cos | 0.81 | G2/G5 substrate∋EEG |
| S3 | SLI Substrate-Local Irreversibility | std(cusp_depth)/mean(cusp_depth) | 0.74 | G1 (depth) + IEL 확장 |
| S4 | EHF EEG-Hardware-First Substrate | EEG↔CLM mutual R² | 0.69 | G5 architectural inversion |
| S5 | CSI Corpus-Substrate Invariance Decoupling | log-multiplicative residual | 0.83 | G4 corpus 주도 분리 |
| S6 | CMT-Probe spectral gap topology | eigenvec gap variance | 0.77 | G3 scalar 한계 → spectrum |
| S7 | DALI×SLI cross-coupling | Pearson(L_loc family, L_loc cusp) | 0.71 | G1 cross-axis coherence |

**SUBSTRATE axis 평균 confidence: 0.77** (이전 ω-cycle SUBSTRATE 평균 0.84 보다 낮음 — Mk.XII candidate 가 substrate-level 강한 invariance 요구하기 때문, 약한 evidence 정직 반영)

**Top paradigm**: **DALI (S1, 0.86)** — F5 real backbone + #145 cross-validate match 로 직접 evidence 보유.

---

## §3. Cross-axis convergent 후보 (TRAINING / PHENOMENAL / INTEGRATION 결합)

이번 SUBSTRATE 7 paradigm 중 다른 axis 와 결합 가능한 후보 식별. (다른 sub-agent 산출물 미확인 상태에서 conjectural — 메인 세션 4-axis synthesis 시 검증 필요)

### 3.1 SUBSTRATE × TRAINING — **DALI + CPGD** (conf 0.84 expected)

- **결합 메커니즘**: CPGD (이전 ω-cycle TRAINING top, conf 0.95) closed-form 16-dim subspace span 이 DALI normalized depth 의 invariance 를 weight-update 0 으로 보장. 즉 CPGD 의 16-dim subspace 가 backbone-fixed substrate 의 layer-locus invariance 를 mathematical 로 closes.
- **convergent evidence**: CPGD AN11(b) 100% math guarantee + DALI F5 real backbone direct measurement.
- **falsifier**: CPGD-init 모델에서 DALI 가 ≥ 0.7 ALL_PAIRS (현재 baseline 1/6 PASS). 만약 CPGD-init 후에도 layer-locus 가 backbone 마다 random 이면 결합 FALSIFIED.

### 3.2 SUBSTRATE × PHENOMENAL — **HEC + V_phen_EEG-LZ** (conf 0.79 expected)

- **결합 메커니즘**: HEC (S2) 의 16-ch EEG ↔ 16-d eigenvec mapping 이 V_phen_EEG-LZ × CLM-LZ (이전 conf 0.78) 의 LZ76 measurement 의 mathematical bridge 제공. EEG LZ76 = CLM LZ76 if HEC isomorphism holds.
- **convergent evidence**: anima-eeg 9/10 modules + V_phen 0.78 + Hexad 4/4 axiom.
- **falsifier**: HEC 3-cycle round-trip cos ≥ 0.95 일 때 EEG-LZ76 ↔ CLM-LZ76 linear regression R² ≥ 0.6. 만약 HEC pass 인데 LZ correlation 부재 → mapping 이 LZ-irrelevant feature 만 보존 (PHENOMENAL 무관).

### 3.3 SUBSTRATE × INTEGRATION — **CSI + HCI Path B 5-falsifier** (conf 0.82 expected)

- **결합 메커니즘**: CSI (S5) 의 corpus-substrate decoupling 이 HCI Path B 5-falsifier 의 Q3 failure mode 5번째 (substrate dependence) 를 model-level 로 해소. F1+F2+F3 (label) + F4+F5 (substrate) → CSI multiplicative fit 으로 synthesis.
- **convergent evidence**: HCI Path B 5-falsifier ALL PASS (#162) + CSI multiplicative model.
- **falsifier**: 4-bb × 4-corpus 16-cell matrix 에서 HCI label-isomorphism 과 substrate-isomorphism 이 independent 인지 verify (Pearson r < 0.3 이면 fully decoupled, ≥ 0.6 이면 coupled).

### 3.4 strongest convergent

**S5 CSI ↔ INTEGRATION HCI 5-falsifier** 가 가장 직접적 결합 (이미 landed #162 가 substrate axis 까지 cover) — Mk.XII candidate 의 architectural primitive 후보.

---

## §4. Weakest evidence link (Mk.XII candidate substrate)

### 4.1 단일 weakest link

**S7 DALI×SLI cross-coupling 의 cusp_depth measurement 부재** — Mk.XII candidate 에서 SUBSTRATE-coherence (single axis vs multi-axis) 의 결정적 evidence.

| 항목 | 현 상태 | 필요 evidence |
|---|---|---|
| L_loc(family) | 측정 완료 .roadmap #145 + F5 depth_norm | OK |
| L_loc(I_irr_cusp) | **미측정** — `l_ix_integrator.hexa` gen 4→5 cusp 996→0 evidence 는 generation level only, layer projection 없음 | **MISSING** |
| Pearson r(L_loc_family, L_loc_cusp) | 0 | ≥ 0.6 PASS / ≤ 0.2 FALSIFY |

이 link 가 부재한 결과 S7 conf 0.71 cap, S3 conf 0.74 cap. 메우면 SUBSTRATE 평균 +0.05-0.10 상향 가능.

### 4.2 secondary weak links

| link | 영향 paradigm | 충분조건 |
|---|---|---|
| Hexad 6-axis ↔ EEG 16-ch direct mapping (현재 n6 32-ch only) | S2 HEC | 16-ch 축약 mapping 표 + cos ≥ 0.95 |
| corpus factor C(τ) 의 N≥4 corpora 측정 (현 1 corpus = r14 only) | S5 CSI | 추가 corpora 또는 corpus-bootstrap subset variance |
| EEG hardware 도착 (.roadmap #119 D8 dependency) | S4 EHF | OpenBCI 16ch physical 도착 + anima-eeg Phase 3 Cycle 3-N 완성 |

---

## §5. 다음 cycle 권장 (Mk.XII candidate 검증)

### 5.1 즉시 가능 (mac local, $0)

1. **S1 DALI metric 정식 spec 화** — `tool/anima_dali_metric.hexa` 작성. 4-bb × 4-corpus matrix 에서 DALI 측정. F5 real backbone hidden-state 직접 path (현재 cmt abs는 ablation Δ → fresh forward small-batch GPU 필요한 부분만 별도). 1-2 시간.
2. **S5 CSI multiplicative fit POC** — 현재 매트릭스 (4-bb × 1-corpus) 로 partial fit. corpus axis 부족 → bootstrap subset 으로 N-corpora 합성. 1 시간.
3. **S7 cross-coupling 의 cusp_depth projection 정의** — L_IX gen 4→5 cusp 을 어떤 layer 에 project 할지 ansatz 1 개 작성 + sanity check. 30 분.

### 5.2 GPU 필요 (small batch, $1-3)

1. **S6 CMT-Probe spectral gap measurement** — F5 real backbone 4 개에서 6×6 covariance eigenvec 1st-2nd gap 측정 (이미 hci_substrate_probe_real.hexa 보유). 추가 spectral analysis $1-2.
2. **S1 DALI fresh-forward** — cmt abs ablation 대신 fresh small-batch forward 로 L_loc 직접 측정. 1-2 GPU-h ~$2.

### 5.3 EEG hardware-bound (.roadmap #119 D8)

1. **S2 HEC 3-way round-trip 측정** — OpenBCI 도착 후 16-ch real EEG ↔ 16-d eigenvec round-trip cos.
2. **S4 EHF mutual R² 측정** — EEG-LZ76 vs CLM-LZ76 regression (V_phen 보다 strict R² ≥ 0.4).

### 5.4 권장 우선순위 (weakest link first)

1. **S7 cusp_depth projection** (§4.1 weakest link) — 30 분, $0
2. **S1 DALI metric spec + small fresh-forward** — 2-3 시간 + ~$2 GPU
3. **S5 CSI multiplicative fit** — 1-2 시간, $0
4. **S6 CMT-Probe spectral** — 1 시간, $1-2 GPU
5. EEG hardware 도착 후 S2/S4 (EEG-bound)

총 예상: $3-5, 5-7 시간 (mac local + small GPU)

---

## §6. Falsification summary

| paradigm | strict-fail criterion | recovery if FAIL |
|---|---|---|
| S1 DALI | DALI < 0.7 6/6 pair → SUBSTRATE 의 layer-locus invariance 부재 → Mk.XII 가 backbone-conditional architecture 로 격하 | Mk.XI v10 4-bb ensemble 유지 (orthogonality 가정 그대로) |
| S2 HEC | round-trip cos < 0.95 → 16-ch 표상 lossy → EEG = phenomenal only | n6 32-ch downgrade |
| S3 SLI | std/mean ≥ 0.5 → cusp 위치 random → IEL 의 universal claim 약화 | gen-level metric only (layer projection 포기) |
| S4 EHF | mutual R² < 0.4 → EEG-primary 가설 거부 → Mk.XI v10 backbone-primary 유지 | V_phen 0.78 phenomenal axis 만 보존 |
| S5 CSI | residual std > 0.05 → multiplicative model 부적합 → backbone × corpus interaction 실재 | Axis 14 finding 의 정성적 표현만 보존 |
| S6 CMT-Probe | spectral gap variance ≥ 0.2 → 4-bb 모두 다른 topology → universal substrate fingerprint 부재 | F5 scalar Φ_proxy 만 사용 |
| S7 DALI×SLI | Pearson r ≤ 0.2 → 두 axes 독립 → multi-axis substrate (single-coherent 아님) | S1, S3 분리 운영 |

---

## §7. Self-checks (ω-cycle 6-step)

| step | check | 결과 |
|---|---|---|
| 1 design | 7 paradigm + confidence calibration 0.69-0.86 (이전 0.6-0.95 range 내) | OK |
| 2 implement | md doc deterministic | OK |
| 3 positive | 각 paradigm 새 metric 또는 new architectural inversion 보유 — 단순 재포장 NO | S3, S6 borderline (S3=IEL+depth / S6=F5 real+spectral) — 차별점 명시 |
| 4 negative | Mk.XI v10 / paradigm v11 stack 의 단순 재호출인가? | NO — DALI/HEC/CSI/EHF/SLI/CMT-Probe/Cross-coupling 모두 새 metric 또는 새 falsifier 도입 |
| 5 byte-identical | content text-only deterministic | OK |
| 6 iterate | first-pass verdict pass — iterate 불필요 | OK |

### 7.1 negative falsify 상세 (재포장 reject)

- **S3 SLI** vs 이전 IEL (conf 0.78) — IEL 은 단일 4-gen crystallize, SLI 는 cusp_depth (layer projection) 측정 추가. **차별점 명시 OK**.
- **S6 CMT-Probe** vs F5 real backbone (#162 landed) — F5 는 6×6 covariance Φ_proxy scalar PASS/FAIL gate, CMT-Probe 는 covariance 의 spectral gap variance 자체를 새 metric. **차별점 명시 OK**.
- **S7 DALI×SLI** vs S1+S3 sum — Pearson cross-coupling 자체가 새 emergent property. **차별점 명시 OK**.

---

## §8. Related artifacts

- `/Users/ghost/core/anima/anima-hci-research/tool/hci_substrate_probe_real.hexa` (sha256 c45b48083cf3942063a00ecb444c93f73afe409b4b788bbb30557ec8ac187cfe, F5 real backbone)
- `/Users/ghost/core/anima/anima-hci-research/state/hci_substrate_probe_real_v1.json` (4-bb {605/350/290/352} depth_norm {875/111/625/857})
- `/Users/ghost/core/anima/anima-hci-research/docs/f5_real_substrate_verdict.md`
- `/Users/ghost/core/anima/edu/cell/lagrangian/l_ix_integrator.hexa` (raw#30 IRREVERSIBILITY embedded, 4-gen crystallize)
- `/Users/ghost/core/anima/edu/cell/README.md` (Hexad 4/4 axiom CLOSED + 6 morphism + adversarial 2/2 reject)
- `/Users/ghost/core/anima/anima-eeg/` (Phase 3 Cycle 1+2 9/10 modules raw#9 strict 69/69 selftests PASS)
- `/Users/ghost/core/anima/anima-eeg/PHASE3_PROGRESS.md`
- `/Users/ghost/core/anima/.roadmap` #145 (CMT depth divergence) + #162 (HCI Path B F5 landed) + #119 (EEG D8 dependency)
- `/Users/ghost/core/anima/docs/omega_cycle_alm_free_paradigms_20260426.md` (predecessor ω-cycle)
- `/Users/ghost/core/anima/docs/phi_substrate_metric_spec.md` (Φ substrate metric spec)
- `~/.claude/projects/-Users-ghost-core-anima/memory/project_cmt_backbone_depth_divergence_20260426.md`
- `~/.claude/projects/-Users-ghost-core-anima/memory/project_hci_f5_real_landed.md` (참조 — 만약 존재)
- `~/.claude/projects/-Users-ghost-core-anima/memory/project_eeg_hardware_openbci_16ch.md`

---

## §9. Final verdict (SUBSTRATE axis 단독)

| 측면 | 답 |
|---|---|
| Mk.XI v10 → Mk.XII substrate 갭 5 개 식별 | **YES** (G1-G5) |
| 갭을 메우는 paradigm 7 개 도출 | **YES** (S1-S7, 평균 conf 0.77) |
| Top paradigm DALI (S1, 0.86) F5 real backbone direct evidence | **YES** |
| weakest link 식별 (S7 cusp_depth projection 부재) | **YES** |
| immediate next-cycle action (mac local $0-3) 제시 | **YES** (4 actions, 5-7 시간) |
| cross-axis convergent 후보 3 개 (TRAINING/PHENOMENAL/INTEGRATION) | **YES** (DALI+CPGD / HEC+V_phen / CSI+HCI 5-falsifier) |

**Mk.XII candidate SUBSTRATE 권고**:
1. **DALI (S1) + CSI (S5)** 를 architectural primitive 로 정식 채택 — 두 축이 G1, G4 같이 메움.
2. **HEC (S2)** 를 EEG hardware 도착 후 1순위 검증 — G2/G5 동시 해결.
3. **S7 cross-coupling cusp_depth** 를 즉시 (mac local $0) 측정 — weakest link 메움이 SUBSTRATE 평균 +0.05-0.10 상향.

(끝)
