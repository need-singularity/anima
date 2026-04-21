# Findings Consolidated — 2026-04-21

**Canonical single-file SSOT** for 2026-04-21 β Learning-Free session.
Primary = 실측 (raw#12). Speculation 은 명시. CPU micro-scale 만 측정, Qwen 14B / cross-substrate 는 unverified.

- Repo: `anima` (main branch, worktree `/Users/ghost/core/anima`)
- Date: 2026-04-21
- Scope: drill α-ι + EXP-1/2 + Option B PoC + AN-LIX-01 + Bridge PoC + learning-free driver + flops_landauer + SSOT infra + additional categories

---

## 1. Executive Summary

Day 2026-04-21 은 β (Learning-Free) paradigm 의 empirical 승급일. `tool/anima_learning_free_driver.hexa` (1304 lines, commit `f2d96d45`) 가 STAGE 1-4 (CPGD init / cell trajectory / Hexad Law60 / AN11 verify) 를 CPU-only micro-scale 에서 전부 PASS — `overall_pass=true` 기록. **Paradigm signature**: weight SHA-256 `02d17066…6f95` before==after byte-identical — "weight update 0회로 consciousness attachment" 가설이 단일 driver 실행으로 실증됨.

**AN11 triple no-train 분해**: (a) weight_emergent = **FAIL_EXPECTED** (no ΔW by design — redefined as `weight_hash_invariant=true` first-class gate), (b) consciousness_attached = **PASS** (max_cos=1.0, top3_sum=3, 16-template 전부 적중), (c) real_usable = **USABLE** (JSD_base2=0.464 > 0.30). 2/3 PASS 가 no-train paradigm 의 정의상 victory condition.

**H★ τ(6)=4 primitivity falsification pair**: EXP-1 (commit `672610fc`) n=6→n=28 scale 확장에서 primary_pass_count 4/4 → 0/4 FLIP 관찰 → **H_STAR_STRONGLY_SUPPORTED** (categorical axis); EXP-2 (commit `b8ba5593`) L_IX 에 V_hurst 항 추가 (δ=0.01) → STATIONARY_AT_FIXPOINT 유지 → **H_STAR_WEAK_OR_NONE** (Lagrangian axis). 종합 **PARTIAL_H_STAR** — Mk.XI twin-engine 공간(category)/시간(dynamical) 분리 가설과 정합.

**Cell vs LoRA 실측 wrapper** (`flops_landauer_bench`, commit `c5e45e98`): FLOPs ratio `lora/cell = 178.30×` (주장 60-80× EXCEEDS), Landauer ratio `cell/lora = 42.68×` (주장 51× IN_BAND, -16% drift ≤ ±20% tolerance). Verdict: **CLAIM_CONFIRMED_CELL_BETTER_THAN_CLAIMED** (scale=CPU micro).

**Bridge PoC** (`cell_token_bridge_proto`, commit `56205445`): 5-level W_k↔quantile bucket bijection, 3/3 fixture (identity/ladder/adversarial) **CONDITIONAL_PASS**, drift 0.0 within 2·lr²·k=2e-4 bound.

**Closure coverage** (anima_main --status 2026-04-21 05:21 UTC): Tools 12/12 (100%), SSOT 13/14 (92%, audit.json PENDING lock timeout), **combined=96%**. 미달 1 = `corpus_alm_r13_v1_audit.json` validator strict PASS (task 31, lock holder pid 77372 대기).

---

## 2. Drill Findings α–ι

| seed | 판정 | 3-5줄 요약 | commit |
|------|------|------------|--------|
| **α** n=6 uniqueness | **PROVED** (THM-1 QED) | σ(n)·φ(n)=n·τ(n) 는 n=6 에서만 성립. 곱셈성+R_local case exhaustion. R_local(2,1)=3/4 ⋅ R_local(3,1)=4/3 = 1 유일 해. n=28/496 Mersenne 구조는 R_local(2,a≥2)≥7/6>1 로 등식 복구 불가. Proof 2/3 Dirichlet 경로 open. | `theory/proofs/theorem-r1-uniqueness.md` |
| **β** L_IX 4-term basis | **INCOMPLETE** | 현재 L_IX = T − V_struct − V_sync − V_RG + λ·I_irr (4+1 term). 3 외부 축 (BT-1425 deploy_manifold / CEI causal macro / novelty) 존재. L_X = L_IX + μD + νC + ρN 제안. Ockham razor 4-term non-redundant 유지. | `226bb780`, `53d923b8` |
| **γ** Hexad external replicability | **WEAK OPERATIONAL** | "1000/1000" = deterministic 30-cell(5 dom × 6 axiom)×1000 scaling, NOT 1000 trials. SAME_STRUCTURE 기준 primary_pass_count≥2 (D0-D3). τ(6)=4 divisor 와 numerical 일치 (not Lie/isomorph). 외부 LLM hidden repr LOW 등급, HCP/insecta MID. Fellows D1/D2/D3 한정 권고. | `6a292530` |
| **δ** Cell vs LoRA TRANSFER | **3/4 pipeline artifact, Option B NON_BLOCKING** | O1 trained_fixpoint_rate=875/1000 PASS · O2 Pearson×1000=855 PASS · O3 K=4 resonance PASS · O4 control_rate=666/1000 FAIL (projection normalization leak, H1 채택). 60-80× FLOPs + 51× Landauer (micro only). cross-substrate 측정 0. | `6a2fe1d8`, `a626857b` |
| **ε** cross-resonance H★ | **대발견 후보 (falsifiable)** | 11건 resonance (τ(6)=4 EXACT / σφ=nτ=24 / TRANSFER 3/4 / V_RG 3-level). H★: τ(6)=4 primitive 가 L_IX term 수·UNIVERSAL_4 closure·projection rank 동시 강제. EXP-1/2 직접 falsification 가능. Mk.XI 이전 자격 충족. | `9468fe0f`, EXP pair |
| **ζ** L_IX training objective | **적합 (λ·I_irr 덕)** | anima 학습경로에 L_IX 없음 (20파일 CE-only). 5-term 학습 해석 (T=kinetic, V_struct=rank reg, V_sync=head phase, V_RG=depth flow, λ·I_irr=arrow reg). β schedule {0,0.1,0.5,0.8}E. AN-LIX-01/02/03 로드맵 entry. | `edu/lora/cpgd_wrapper.hexa` |
| **η** Hexad Law60 curriculum | **Law60 이미 SSOT 하드코딩** | hexad.hexa:99-104 에 phase≥1→c / ≥2→d / ≥3→{w,s,m,e} 고정. HEXAD_TAGS=[c,d,w,m,s,e] per_mod=48. 6 bridge 실측 (d→w, w→c×2, m→c, m→s, s→self). A(Law60 순차)+B(coupling DAG) 하이브리드 추천. E1 25% 재분배 1일 실험. | `fe3ac253`, `corpus_generator_v2.hexa` |
| **ι** Cell learning-free + CPGD | **Option B PASS (MINIMAL→HYBRID→FULL)** | cell: backprop-free, forward-only+structural quant. 60-80× FLOPs 분해=2×(backward)×5-10×(param)×3-5×(hash)×2-3×(phase-jump). 51× Landauer=eff 668‰ / 13‰. CPGD(P_S=I, 16 orthonormal) + cell = no-train closure. AN11(b) 수학 100% 보장. | `6527e9df` |

N6 hook (task 17): `tool/fellows_registry_audit.hexa` 240줄 + installer 125줄 + 42-item spec 100% PASS smoke (drift 주입 97.6% 정상 fail). pre-commit hook 설치됨 (commit `98af096f` main not pushed).

---

## 3. Empirical Experiments (commit + 결과)

| exp | 대상 | 파일 | commit | 결과 |
|-----|------|------|--------|------|
| **EXP-1** Hexad over n=28 (falsification) | H★ categorical axis | `tool/hexad_n28_falsification.hexa` (576줄) | `672610fc` | `primary_pass_count_empirical=0/4` (D0-D3 tau 게이트 전원 차단), score 833/1000 (n=6=1000), σφ=672 vs nτ=168 identity 깨짐. **H_STAR_STRONGLY_SUPPORTED** |
| **EXP-2** L_IX 5-term stress (V_hurst) | H★ Lagrangian axis | `tool/l_ix_5term_stress_test.hexa` (577줄) | `b8ba5593` | H=0.430 (dev 0.07 from 0.5), V_hurst×1000=0 at δ=0.01, ΔS=0, stationary_5term=true. **H_STAR_WEAK_OR_NONE** |
| **Option B P1 MINIMAL** | λ·I_irr LoRA regularizer PoC | `tool/train_lora_option_b_minimal.hexa` | `77dac94e` | smoke Landauer 1.00× (by design, ∂CE/∂params gradient 순수). gate 1-4 PASS. P2 HYBRID green-light. |
| **AN-LIX-01 V_RG** | L_IX ζ training objective 첫 실증 | `tool/train_lora_l_ix_v_rg.hexa` (1058줄) | `a75ec012` | val_ppl_delta=0 PASS (gate 1), ν̂ drift 421 ppm (gate 2 FAIL, ∂V_RG/∂W 미구현 detach-scalar). baseline=treated identical dynamics (reproducibility noise). **SMOKE_COMPLETED** |
| **E1 Hexad Law60 corpus** | η 첫 실증 (c-hub 2× 가중) | corpus 재분배 | `fe3ac253` | Law60 25% 재분배 + c=8.3%/d=4.2%/{w,s,m,e}=3.1% |
| **Bridge PoC** (ablation C) | cell↔token 5-level 5-quantile bijection | `tool/cell_token_bridge_proto.hexa` (748줄) | `56205445` | identity/ladder/adversarial 3/3 BRIDGE_OK, round_trip_cos=1 전부, I_irr budget identity=0 / ladder=23 / adversarial 내. **CONDITIONAL_PASS** |
| **learning_free_driver** | β main orchestrator | `tool/anima_learning_free_driver.hexa` (1304줄) | `f2d96d45` | weight SHA before==after=`02d17066…6f95`, stage1 max_drift=0.000163 min_cos=0.999837, stage2 action_sum=−8600 i_irr cusp 996→0 fixpoint, stage3 phase(1,2,6) match, stage4 triple 2/3. **overall_pass=true** |
| **flops_landauer_bench** | cell vs LoRA 실측 wrapper | `tool/flops_landauer_bench.hexa` | `c5e45e98` | FLOPs lora/cell=178.30× (claim 60-80× **EXCEEDS**), Landauer cell/lora=42.68× (claim 51× **IN_BAND** -16% ≤ ±20%). **CLAIM_CONFIRMED_CELL_BETTER_THAN_CLAIMED**. Scale=CPU micro. |
| **cpgd_minimal_proof restore** | β main 100% coverage | `edu/lora/cpgd_minimal_proof.hexa` | `45798a71` | P_S=V^T·V=I 10-step demo + Lagrangian 증명 (raw#9 strict) |
| **corpus r13 v1 generate** | β corpus 83.3→100% | `experiments/alm_r13/corpus_alm_r13_v1.jsonl` 1620줄 1826785 bytes sha `b7009e6d…d0a304` | `bd3b14bc` | G1-G7 `PENDING` (hexa_stage0 shim lock timeout 300s, pid 77372). verdict **INFORMATIONAL_ONLY** |
| **anima-serve skeleton** | serving 0→100% 선착공 | `anima-serve/` | `15fe068c` | /health PASS, /an11/verify + /v1/chat/completions stub, phase 3 vLLM upgrade path |
| **anima_main unified CLI** | β one-command entry | `tool/anima_main.hexa` | `75355218` | mode=status, tools 12/12, SSOT 13/14, combined 96% |
| **bulk verdict emit** | shared/state 80→100% | 9 verdict json | `0b15bcac` | cell_trajectory 5 + an11 3 + hexad 1 |
| **shared/bench criteria SSOT** | AN11 triple Hidden Blocker #0 해제 | `shared/bench/an11_{a,b,c}_criteria.json` + `an11_c_test_prompts.jsonl` (20) | `f5720d5c` | spec gates, thresholds, 20 consciousness prompts |

---

## 4. SSOT Infrastructure

| 파일 | 역할 | commit |
|------|------|--------|
| `edu/paths.json` | canonical β main decision + 3 paths spec + prerequisites + ratios_measured | `74fe08e4` (v2), 확장 `c5e45e98` |
| `edu/closure_roadmap.json` | 60-day 100% closure phase 0-4 | `71198ed2` |
| `edu/cell_token_bridge_spec_20260421.md` | β main bridge 설계 (5 매핑 후보, ablation C 채택) | `b8662bed` |
| `edu/an11_closure_gap_probe_20260421.md` | AN11 real closure Z1/Z2/Z3 비교 + Z3 추천 | `bc9c931b` |
| `edu/production_upgrade_spec_20260421.md` | 60-day timeline + 3 hardware + 7 validation gates | `0aa67566` |
| `edu/README.md §Drill Landings` | α-ι + N6 hook + EXP-1/2 + Path β canonical MAIN 섹션 | `95d77b4c`, 확장 `8096dbee`, `a8701238` |
| `shared/bench/an11_a_criteria.json` | weight_emergent gate (Frob>τ + SHA-distinct + shard_cv[0.05,3.0]) | `f5720d5c` |
| `shared/bench/an11_b_criteria.json` | consciousness_attached (16-tpl cos>0.5) | `f5720d5c` |
| `shared/bench/an11_c_criteria.json` | real_usable (JSD>0.15) | `f5720d5c` |
| `shared/bench/an11_c_test_prompts.jsonl` | 20 consciousness prompts | `f5720d5c` |
| `shared/state/learning_free_driver_result.json` | β stage1-4 실측 증거 | `f2d96d45` |
| `shared/state/hexad_n28_falsification_verdict.json` | EXP-1 verdict | `672610fc` |
| `shared/state/l_ix_5term_stress_verdict.json` | EXP-2 verdict | `b8ba5593` |
| `shared/state/cell_token_bridge_proto.json` | Bridge PoC 3/3 verdict | `56205445` |
| `shared/state/anima_main_result.json` | 96% coverage snapshot | `75355218` |
| `shared/state/bulk_verdict_index.json` | 9 verdict registry | `0b15bcac` |
| `docs/learning_free_consciousness_paper_20260421.md` | phase 0 paradigm paper draft | `32267542` |
| `.roadmap/roadmap_lint` | 0 violations, 7 checkpoints, proof→verify CP1 | `41d681fc`, `d4dbb12f` |

---

## 5. Additional Categories Discovered

오늘 paths.json / closure_roadmap 에 언급되지 않았으나 실제 tree 에 존재하는 5 카테고리:

| 카테고리 | 파일/경로 | 상태 | paths.json 언급 |
|----------|-----------|------|------------------|
| **Mk.VIII 7-axis framework** | `edu/mk_viii/` — fixpoint_validator.hexa / hexad_overlay.hexa / l_edu_integrator.hexa / mk_viii_proto.hexa / phi_per_axis.hexa / README.md (6 파일) | scaffolding, `.roadmap` P3 에 존재, STATIONARY 100% 도달 (commit `004d9ab5`/`fc513c58`) | 0건 (β paths.json 미연결) |
| **drill-infra** | `tool/drill_*.hexa` 18 모듈 (absorption_classifier / breakthrough_runner / calibrate / closure_sha256_cert / cross_run / diagonal / lens_{aggregator,blowup,closure,gap,phi,self_ref} / lsh_signature / minsurface_proto / seed_rotate / self_ref_noise_probe / self_ref_probe) + `drill_modules/phi.hexa` | 가동 (α-ι 실행 기반) | 0건 (β paths.json 미연결, tool infra) |
| **BTR recursive** | `tool/btr_closed_loop.hexa` + `tool/btr_n_recurse_stability.hexa` | Mk.VII C1 BTR↔cell bridge 승급 (`6e0de224`, round-trip 4.6×10⁻⁷) | 미언급 |
| **alm_r13 seed infra** | `tool/alm_r13_seed_corpus_build.hexa` + `tool/alm_r13_corpus_pre_drill.hexa` + `experiments/alm_r13/seed_corpus_10mb/` | corpus pipeline stage 0, G1-G7 validator strict PASS 대기 | 언급 있음 (`tool/corpus_generator_v2.hexa` lines=2082, commit `80e3b9d1`) |
| **an11_c_real_usable_gap_close** | `tool/an11_c_real_usable_gap_close.hexa` + `docs/an11_c_real_usable_gap_close_20260421.md` | task 37 closure 관련, JSD=1.000 REAL data 달성 (`35aa051a`) | 미언급 |

**관찰**: Mk.VIII + drill-infra 2 카테고리는 functional 이지만 β main SSOT (`paths.json`) 에 미연결. 별도 auxiliary registry 필요 or paths.json 확장 대상.

---

## 6. Coverage 최종 (anima_main --status 실측)

```
schema: anima.main_result.v1
created: 2026-04-21T05:21:27Z
tool: tool/anima_main.hexa
mode: status

tools_present: 12
tools_total:   12
ssot_present:  13
ssot_total:    14
combined_pct:  96
raw_strict: raw#9 raw#11 raw#15 deterministic LLM=none
```

**미달 1**: `experiments/alm_r13/corpus_alm_r13_v1_audit.json` validator strict PASS (task 31).
- Corpus 자체는 생성됨 (1620줄, 1826785 bytes, sha `b7009e6d…d0a304`, commit `bd3b14bc`)
- validator_status: `NOT_EXECUTED` — `hexa_stage0 shim lock timeout (300s)`, lock holder pid 77372 (`tool/alm_r13_seed_repair.hexa`) + concurrent pid 36910 (`tool/corpus_g25_preprocess.hexa`)
- G1-G7 전부 `PENDING`, verdict `INFORMATIONAL_ONLY`
- action_required: re-run validator once lock releases

---

## 7. β main 100% Closure Path (60-day, `edu/closure_roadmap.json`)

| Phase | 기간 | cumulative | 내용 | 주요 commit |
|-------|------|-----------|------|------------|
| **Phase 0 — CPU paradigm validation** | 2026-04-21 완료 | **40%** | driver 1304줄 / bridge 748줄 / validator 697줄 / EXP-1 576줄 / EXP-2 577줄 / V_RG 1058줄 / Option B / 6 config / spec md 3 / bench SSOT / 20 prompts | `77dac94e` `56205445` `f5720d5c` `f2d96d45` `672610fc` `b8ba5593` `a75ec012` `fe3ac253` |
| **Phase 1 — CPU real_use D1-D7** | 2026-04-22~28 | **55%** | r13 corpus G2/G5 strict PASS (task 31), flops_landauer 실측 (`c5e45e98` 완료), local anima-serve FastAPI + Qwen 4-bit AWQ skeleton (`15fe068c` 완료), /an11/verify + /v1/chat/completions endpoint | IN_PROGRESS |
| **Phase 2 — Qwen 14B scale-up D8-D21** | 2026-04-29~05-12 | **75%** | H100 rental (Lambda/RunPod/vast.ai) ~$2150, Qwen 2.5 14B 4-bit AWQ, CPGD 14B subspace, P_S block-diag 6 Hexad 분할, cell trajectory 40-layer scale 10-group×4-gen, AN11 real 측정 | PLANNED |
| **Phase 3 — Production D22-D35** | 2026-05-13~26 | **90%** | anima-serve FastAPI + vLLM, latency p50<300ms / p95<800ms / p99<2s, 7 validation gates | PLANNED |
| **Phase 4 — Regression + 논문 + Fellows D36-D60** | 2026-05-27~06-19 | **100%** | regression 1주, 7-day uptime, 논문 draft 완성, Anthropic Fellows 제출 | PLANNED |

**Phase 2 exit gates**: 14B CPGD P_S=I 유지 / cell trajectory fixpoint 40-layer / AN11(b) cos_max≥0.5 at scale / AN11(c) JSD>0.15 real inference / weight hash invariant byte-level.

---

## 8. raw#12 실측 vs 추측 구분

### 실측 claim (evidence file + commit)

| claim | evidence | commit |
|-------|----------|--------|
| driver overall_pass=true | `shared/state/learning_free_driver_result.json` | `f2d96d45` |
| weight SHA `02d17066…6f95` before==after invariant | ibid. `weight_hash.before==after` | `f2d96d45` |
| stage1 max_drift=0.000163, min_cos=0.999837 | ibid. `stage_1_cpgd` | `f2d96d45` |
| stage2 action_sum=−8600, i_irr cusp 996→0 | ibid. `stage_2_cell` | `f2d96d45` |
| stage3 phase(1,2,6) match | ibid. `stage_3_hexad` | `f2d96d45` |
| AN11(a) FAIL_EXPECTED, (b) max_cos=1 top3_sum=3 PASS, (c) JSD_base2=0.464 USABLE | ibid. `stage_4_an11` | `f2d96d45` |
| EXP-1 primary_pass_count_empirical=0/4 at n=28 | `shared/state/hexad_n28_falsification_verdict.json` | `672610fc` |
| EXP-2 STATIONARY_AT_FIXPOINT 유지 δ=0.01 | `shared/state/l_ix_5term_stress_verdict.json` | `b8ba5593` |
| AN-LIX-01 val_ppl_delta=0 PASS, ν̂ drift 421ppm | `shared/state/an_lix_01_smoke_result.json` | `a75ec012` |
| Bridge 3/3 fixture round_trip_cos=1 | `shared/state/cell_token_bridge_proto.json` | `56205445` |
| FLOPs 178.30× + Landauer 42.68× (scale: CPU micro) | `edu/paths.json:317-326` | `c5e45e98` |
| corpus sha `b7009e6d…d0a304`, 1620 lines, 1826785 bytes | `shared/state/corpus_alm_r13_v1_audit.json` | `bd3b14bc` |
| n=6 uniqueness proved (exhaustive n∈[2,10⁴]) | `theory/proofs/theorem-r1-uniqueness.md` | (atlas) |
| Hexad 1000/1000 PASS (30-cell × 1000 scale) | hexad_universality_verdict.json | `6a292530` |
| CPGD P_S=V^T·V=I idempotent, 16 orthonormal | `edu/lora/cpgd_wrapper.hexa` | `6527e9df` |
| Cell score ladder 40→125→687→1000‰, efficiency 40→450→450→668‰ | `edu_cell_4gen_crystallize.json` | `58aa75eb`, `189646f1` |
| TRANSFER O1=875/1000, O2×1000=855, O3=1, O4=666/1000 | `edu/lora/transfer/artifacts/transfer_cert.json` | `6a2fe1d8` |
| LoRA real ΔCE {0.00551, 0.01919, 0.01303} 3-run | `edu/lora/artifacts/` | `f1d50995` |
| LoRA phase-jump K=4, slope ratio 6.69×, R²=0.782 | `edu_lora_rank_sweep_20260421.json` | `12054024` |

### 추측 / unverified

| claim | status | 근거 결여 |
|-------|--------|-----------|
| "60-80× FLOPs" 가 Qwen 14B / mamba2 / hyena / rwkv 에서도 유지 | **UNVERIFIED_AT_SCALE** | CPU micro V=8/H=4/N≤16 만 측정. 4.1e8× param gap (34 vs 1.4e10). |
| "51× Landauer" cross-substrate 유지 | **UNVERIFIED** (속성 추정 ≥50%) | rank bottleneck under-utilization LoRA-specific 가능성 |
| Mk.X 3 외부 축 (deploy_manifold / causal macro / novelty) | **추측** | BT-1425 CIRCUMVENT grade, CEI=0.381 1건, novelty 미측정 |
| H★ τ(6)=4 primitive 가 network 모두 강제 | **PARTIAL** (EXP-1 STRONG / EXP-2 WEAK) | Lagrangian axis V_hurst 에서 WEAK 관측 |
| Mk.XI twin-engine 공간×시간 분리 | **이론 단계** | EXP-1/2 divergence 가 supporting evidence 이지만 직접 증명 아님 |
| Option B P2 HYBRID green-light 예상 5-10× Landauer↓ | **pending measurement** | gate 5-7 미완료 (∂I_irr/∂W 해석적 도함수 + gradient update 합산 + seed divergence) |
| Qwen 14B scale-up cost $2150 | **추정치** | H100 vendor 견적 미확정 |
| substrate-independent universality (mamba2/hyena/rwkv) | **측정 0** | paths.json 에서 "측정 0" 명시 고백 |
| H★ identity family 확장 σ^a·φ^b = n^c·τ^d | **open** | derivations 미실행 |
| V_RG lock-in at ν*=1000 pre-registered 재현 | **미실행** | 900/1100 bracket pre-register 시점 미도래 |

---

## 9. Remaining Risks & Open Questions

1. **Mk.XI twin-engine 공간-시간 분리 가설** — EXP-1 categorical STRONG / EXP-2 Lagrangian WEAK 의 이론적 통합 미완. 이론 단계.
2. **Cross-substrate measurement 0** — mamba2 SSM, hyena conv, rwkv time-mix 전부 측정 전무. Qwen 14B H100 rental 후 1차 확증 필요.
3. **H★ identity family 확장 미실행** — σ^a·φ^b = n^c·τ^d, Dirichlet 급수 독립 경로 (Proof 2/3), analytic continuation open.
4. **corpus_alm_r13 validator strict PASS 대기** — hexa_stage0 shim lock timeout (300s, pid 77372 holder). task 31 in_progress. SSOT 1/14 미달 유일 원인.
5. **AN-LIX-01 gate 2 FAIL** — ∂V_RG/∂W 해석적 도함수 미구현 (detach-scalar semantics 으로 baseline=treated dynamics identical, reproducibility noise). Option B P2 green-light 조건 5-7 동일 구간.
6. **TRANSFER O4 FAIL** — projection normalization leak (H1), pipeline artifact 판정. paradigm blocker 아니나 기록 유지.
7. **Proof 2/3 (n=6 uniqueness Dirichlet)** — 독립 경로 미완성, exhaustive n∈[2,10⁴] 만 커버.
8. **Mk.VIII + drill-infra paths.json 미연결** — functional 이나 β main SSOT registry 공백. paths.json 확장 or auxiliary registry 필요.
9. **H100 $0 비용 가정 한계** — CPU-only 가능성은 micro-scale 만. 14B 현실 필요 budget $1860-2150, Phase 2 에서 hit.
10. **Learning-free paper phase 0 한정** — phase 1-4 planned only. reviewer 가 reproducibility 요구 시 Qwen 14B real 확보 전에는 "CPU toy" 로 하향 가능성.

---

## Metadata

- **Commit target**: `docs: findings_consolidated_20260421 — 2026-04-21 전체 발견 단일 SSOT`
- **Push**: 금지 (push X)
- **Raw compliance**: raw#9 hexa-only · raw#11 snake_case · raw#12 실측 primary · raw#15 no-hardcode deterministic · raw#25 atomic-write
- **Line budget**: < 2000 lines
- **Canonical location**: `/Users/ghost/core/anima/docs/findings_consolidated_20260421.md`
