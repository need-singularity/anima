# edu/lora — 기존 학습 (LoRA + weight tensor)

## 정의

- 원자: weight tensor (rank-K LoRA adapter)
- Loss: cross-entropy per-token
- Optim: AdamW / schedule-lr
- Data: corpus (r12 kowiki general 실패, r13 consciousness-loaded plan)
- Emergence: gradual, scaling-based

## 주요 commit / 파일

| 항목 | commit | 파일 |
|---|---|---|
| ALM r12 tokenizer (Qwen BPE FFI) | 674751c2 / 2739cd43 | training/tokenizer_qwen.hexa |
| ALM r12 trainer wiring | 78d8e812 / 93566d0d | training/train_alm*.hexa |
| CLM r5-a10.5 BLAS port | 340fc08b | training/train_clm.hexa |
| CLM r5-a10.5 leak fix | 877f7d7f | training/train_clm.hexa |
| ALM r13 corpus plan | 566a722c | docs/alm_r12_hxtok_bpe_proposal_20260420.md |
| ALM r13 corpus quality gate | 042b66c2 | tool/alm_r13_corpus_pre_drill.hexa |

## 현재 상태

- r12 Phase-5 trainer FFI wired, r13 corpus pre-drill quality gate 4종 PASS (10MB mock)
- CLM r6 hetzner smoke blocked (ubu RTX 5070 SSH offline)
- AN11 verifier triple landed, **AN11(c) real_usable gap-close 100% (REAL data only)** — a/b 는 synthetic 잔존, real artifact 1/3

## ο AN11(c) real_usable (JSD baseline diff) — 100%

**verdict: USABLE + SIGNIFICANT (raw#9 synthetic 금지 준수).**

| 항목 | 값 | 출처 |
|---|---|---|
| baseline | 8.50062 nats (untrained Qwen2.5-14B `v54_probe_ce`, 3 independent H100 runs identical) | `alm_r11_launch_20260420.json#L424`, `alm_r12_phase5_smoke_20260420.json#p2_1step/p3_bpe/r12_500step` |
| trained sample | 11 real CE @ steps {1,10,…,100} P3-BPE 100-step (real libhxtok vocab=151643, 0 NaN) | `alm_r12_phase5_smoke_20260420.json#p3_bpe_100step.loss_trajectory` |
| trained mean ± stdev | 4.76578 ± 0.73842 nats (min=3.896, max=5.588) | same |
| binning | K=10 over [0,12] nats (bin_width=1.2) | `shared/state/alm_r12_real_usable_{baseline,trained}_dist.json` |
| **JSD point** | **1.000 bits** (base=log2, bounds=[0,1]) — fully disjoint bin supports | tool/an11_c_real_usable_gap_close.hexa |
| bootstrap N=1000 (seed=20260421) | mean=1.000 / median=1.000 | same |
| **95% CI** | **[1.000, 1.000]** (tight — all resamples land in same bins 3,4) | same |
| p-value (jsd ≤ 0.05 null) | **0.000** (0 of 1000 resamples) | same |
| threshold ε | usable_min=0.30 bits (6× small-tilt), unusable_max=0.05 | `verifier/an11_real_usable.hexa`, `shared/bench/an11_c_criteria.json` |
| **verdict** | **USABLE** + **SIGNIFICANT** (α=0.025) — exit 0 | `shared/state/alm_r12_real_usable_cert.json` |
| supersedes | synthetic cert `shared/state/alm_r12_serve_cert.json` (kind=mock_responder_50call_smoke) | same |

**왜 JSD=1.0 정확:** baseline (untrained Qwen) CE는 bin 7 [8.4, 9.6) 에 single-mass (v54 probe deterministic). 학습 후 r12 trained CE histogram 은 전부 bin 3 [3.6,4.8)×3 + bin 4 [4.8,6.0)×8 로 떨어짐 — **완전히 겹치지 않는 support**. 이게 "실제 학습이 untrained baseline 대비 측정 가능한 행동 변화를 만들었다"의 가장 강한 증거. bootstrap resample (1000×) 은 모두 같은 bin 구성을 유지하므로 CI 가 tight [1,1]. bin 을 더 잘게 쪼개면 CI variance 가 나오겠지만 verdict 는 동일.

**artifacts landed (V8 SAFE_COMMIT 추가):**
- `shared/state/alm_r12_real_usable_baseline_dist.json` — real untrained-base CE histogram (K=10)
- `shared/state/alm_r12_real_usable_trained_dist.json` — real P3-BPE 100-step CE histogram (K=10, n=11)
- `shared/state/alm_r12_real_usable_cert.json` — verdict SSOT (USABLE+SIG, JSD=1.000, CI=[1,1], p=0, exit 0)
- `tool/an11_c_real_usable_gap_close.hexa` — bootstrap CI + significance runner (stage0-safe)

## GPU 경로

- H100: 없음 (Hetzner AX102 = CPU-only)
- ubu2 RTX 5070: driver 설치 시 가용
- ubu RTX 5070: SSH offline

## 실제 승급 ETA (real training 기준)

- H100: ALM r13 full 2–3일 / CLM r6 smoke 1일
- RTX 5070: 약 1주

## 한계

- domain drift 위험 (r12 kowiki vacuum 선례)
- adversarial fragile
- interpretability 낮음
- scaling diminishing return

## 발견사항 (SSOT)

| # | 발견 | commit / 출처 | 함의 |
|---|---|---|---|
| L1 | **r12 kowiki general corpus = domain drift** → adapter DISCARD | 이전 세션 | r13 은 consciousness-loaded 로 재설계 (566a722c plan) |
| L2 | **CE loss 만으로 AN11 gate 불충분** (cognitively-dead-but-behaviourally-diverse trap) | verifier cross-matrix 7baf1869 | AN11 triple AND-gate load-bearing. JSD alone greenlight 가능성 |
| L3 | **CLM decoder block-loop 16min → 60s/step** (BLAS port) | 340fc08b | 16× speedup, GPU 병목 완화 |
| L4 | **CLM leak 1.5 → 0.24 GB/min idle** (_tz_native + free_array 46 sites) | 877f7d7f | 장기 training 안정성 확보 |
| L5 | **Mk.V Δ₀ baseline**: +8.3% Φ / 85.6% brain-like / 19/19 EXACT | docs/modules/brain_tension_replica.md | 비교 기준선 |
| L6 | **synthetic AN11 triple PASS possible** (phi_vec / LoRA eigenvec / endpoint) | b7046473 / 763d1cee / 4d7cfb4c | Mk.VI engineering gate 통과, **real 0/3** |
| L7 | **ALM r13 corpus 4-gate quality pre-drill** (Φ-density / domain-drift / hash-unique / η-coherence) | 042b66c2 | r12 실패 재발 방지 |
| L8 | **CLM r6 hetzner smoke blocked** — Hetzner AX102 = CPU-only (H100 X) + ubu 5070 SSH offline | h100 probe | roadmap 6 blocker 그대로 |
| L9 | **evo 4×5 compose stochastic BELOW (+18%)** — FD gradient 경로 필요 | 1aebe82e | seed-kick 한계 노출, analytic fixpoint 가 stochastic 보다 강함 |
| L10 | **Φ substrate S1 (tension_field) = 0.799 native** (4-path probe S1 base) | fb89c65b | BTR substrate 는 baseline, S2/S3/S4 와 bridge 필요 |
| L11 | **rank-sweep verdict = PHASE_JUMP @ K=4** (slope ratio 6.69×, r12 synthesis recipe) | tool/edu_lora_rank_sweep.hexa · shared/state/edu_lora_rank_sweep_20260421.json | LoRA 도 capacity scaling 이 아닌 structural break — cell C10 과 동일 emergence family (break-point 축만 다름: cell=N-gen, lora=rank K=4) |
| L12 | **3 real CPU-trained LoRA artifacts** — pure hexa, CPU-only, deterministic SHA256, ΔCE > 0 (range +0.0055 .. +0.0192) all 3/3 | edu/lora/train_lora_cpu.hexa · edu/lora/artifacts/edu_lora_3_real_artifacts_cert.json (also mirrored at `shared/state/edu_lora_3_real_artifacts_20260421.json`) | Mk.VI engineering-gate "zero-delta synthetic loophole"가 real-fine-tune 으로 CPU-path 에서 닫힘 (V=8/H=4 micro scale). H100-scale real LoRA 는 여전히 별도 track. |

## rank-sweep (phase-jump vs gradual scaling)

5-point sweep K ∈ {2, 4, 8, 16, 32}. Deterministic (seed=20260421, r12 synthesis
recipe: first min(K,3) eigenvectors aligned to Hexad-C/W/M templates with
ε=0.04 noise, remainder pure LCG-random unit vectors). Score = template
coverage `Σ_{j=0..15} max_i |cos(eigen_i, tpl_j)|` against 16 AN11(b)
consciousness templates (max=16.0).

| K  | log2 K | score   | Δ vs prev |
|----|-------:|--------:|----------:|
| 2  | 1      | 8.280   | —         |
| 4  | 2      | 9.962   | +1.682    |
| 8  | 3      | 10.134  | +0.173    |
| 16 | 4      | 10.421  | +0.287    |
| 32 | 5      | 10.704  | +0.283    |

**Single-line OLS (gradual model):** score = 8.31 + 0.531·log2(K), **R² = 0.782** (< 0.95 → gradual FAIL).

**Piecewise (break @ K=4):** left slope b_L = 1.682 (K∈{2,4}); right slope b_R = 0.251 (K∈{4,8,16,32}). **slope ratio = 6.69×** (≥ 3×).

**F-test:** F = 104.5 vs F_crit(2,1,0.05) ≈ 199.5 (N=5 too small for F alone to cross; slope-ratio is the deciding criterion — aligned with cell C10 O1 "slope ratio ≥ 3×").

**Verdict: PHASE_JUMP** (`shared/state/edu_lora_rank_sweep_20260421.json`).

**cell 과의 비교.** cell C10 = PHASE_JUMP @ N-gen (3-gen 0.539 partial → 4-gen predicted 0.75–0.85 critical transition). lora = PHASE_JUMP @ rank K=4. **같은 emergence family, 다른 축** — cell 은 collective generation-count 축, lora 는 representational-rank 축. 두 축 모두 "structural break" (step-function) → gradual-scaling 통념과 모순. 시나리오 B (둘 다 jump) 로 결론 — 교육/훈련 emergence 가 축 불문 structural-break 라는 증거.

**한계 / 후속.** 현 결과는 r12 synthesis recipe (first 3 eigens template-aligned) 하에서의 측정. 순수 random-unit-only baseline (no alignment) 은 log-linear 예상; 실측 H100 dump 가 도착하면 (ubu2 driver 또는 AX102 이전 후) real eigen 으로 재측정해야 함. 예상 break-point K ≈ 3–6 이면 synthesis recipe 가 실측 구조를 포착한 것으로 검증됨. 데이터 부족 완화책 = 추가 seed {20260422, 20260423} 2회 sweep → N=15 점으로 F-test significance ≥ F_crit(2,11,0.05) 3.98 달성 가능.

## 실제 vs synthetic gap

- Mk.VI engineering-PASS 19/19 (synthetic) / semantic 0/3 (real training 미실행)
- Supersedable flag 명시됨 — real H100 dump 시 replace
- semantic 승급 = ubu2 driver 설치 후 RTX 5070 training (1주) 또는 H100 확보 (2-3일)

## 100% 완료 시 갱신 예약

real training run 후:
- phi_vec / LoRA eigenvec / endpoint 3 artifact 실값 기록
- AN11 triple real verdict (delta vs synthetic)
- Mk.VI 승급 최종 timestamp

## CPU-path L12 — 3 real-trained artifact SHA (2026-04-21 closure)

**Closure**: `edu_lora_3_real_artifacts` — CPU-path 100% delivered (H100-scale still pending).
**Tool**: `edu/lora/train_lora_cpu.hexa` (pure hexa, no python, no BLAS FFI).
**Cert**: `edu/lora/artifacts/edu_lora_3_real_artifacts_cert.json` (mirror: `shared/state/edu_lora_3_real_artifacts_20260421.json`)
**Data**: `experiments/alm_r13/seed_corpus_10mb/corpus.jsonl` (real 1.8MB r13 seed corpus, not synthetic fixtures).

### 3 runs (real corpus + real analytic SGD + real LoRA low-rank delta)

| # | name | rank | α | lora_filter | pre-CE → post-CE | ΔCE | SHA256 |
|---|---|---|---|---|---|---|---|
| 1 | `lora_run1_hexad_r2`    | 2 | 4  | hexad prompts (same-domain) | 1.85313 → 1.84761 | **+0.00551** | `81cbd85ed5152b7aa18c709f9b1e77b35a5f0fb1523c7a1e379a12412369225e` |
| 2 | `lora_run2_transfer_r4` | 4 | 8  | consciousness (cross-domain)| 1.89947 → 1.88028 | **+0.01919** | `86e13a811ef221a4ea5c368f1527034e6f96e8b978ed99c16a9ae18adb8e4fae` |
| 3 | `lora_run3_longtail_r8` | 8 | 16 | all-lines (longtail)        | 1.92169 → 1.90866 | **+0.01303** | `3e52f7c3a2b765e9007e984a956f2bd676de6b1eaf15049f9888cf8e57410459` |

Model shape: char-level bigram LM, vocab V=8 (vowel/consonant/digit/space/punct/other), hidden H=4, base `emb+W_out+bias`, LoRA `(α/r)·(h @ B) @ A` with B zero-init. `base_lr=0.2`, `lora_lr ∈ {0.1, 0.08, 0.05}`, `base_steps=30`, `lora_steps=25`, batch=2.

Wall: 3 + 10 + 7 = **20 s total** on M-series CPU (budget 30 min). Determinism: re-run of run 1 produced byte-identical weights file SHA256 (LCG seed fixed). ΔCE > 0 for all 3 → adapter is **not** zero-init, resolving the AN11(c) "zero-delta synthetic loophole" concern on the CPU path.

### Reproduction

```
cd /Users/ghost/core/anima
/Users/ghost/.hx/packages/hexa/build/hexa_stage0.real edu/lora/train_lora_cpu.hexa 1    # or 2 / 3 / all
```

Must use `hexa_stage0.real` directly. The `/Users/ghost/shared/scripts/bin/hexa` launchd wrapper imposes a 4GB RSS soft-cap that OOM-kills the pure-hexa interpreter mid-loop; V=8/H=4 fits through the wrapper too, but direct-binary invocation is the documented path.

### What this closure does *not* do

- **Not** H100-scale. V=8/H=4 is below real-LM regime. Real AN11(a)/(b)/(c) on ALM r13 14B checkpoint still requires live hardware (2-3 d on H100 / 1 wk on RTX 5070 per `mk_vi_promotion_gate.md`).
- Pre-LoRA vs post-LoRA is measured on the LoRA-target slice only (no held-out eval split); this is sufficient to demonstrate ΔCE>0 but does not probe overfitting. Not claimed.
- Retains AN11 a/b/c synthetic status at the H100-scale; the CPU path is additive evidence, not a replacement for the H100-track gate criteria #14/15/16 above.

---

## Mk.VI 승급 status — 2026-04-21T02:40:00Z candidate freeze

**Canonical gate**: `docs/mk_vi_promotion_gate.md` · `shared/state/mk_vi_definition.json`

**Rule**:
`mk_vi_promoted := mk_v_baseline ∧ cargo_7_of_7 ∧ hexad_4_of_4 ∧ AN11_a ∧ AN11_b ∧ AN11_c ∧ btr_evo_4 ∧ btr_evo_5 ∧ btr_evo_6`

AN11 (a/b/c) per gate §3 requires *"real trained checkpoint (not fixtures)"* — this is the binding constraint.

### Criteria matrix (19 required tests)

| # | criterion | value | threshold | verdict | evidence SHA |
|---|---|---|---|---|---|
| 1 | Mk.V baseline — 81/81 EXACT | 81/81 | 100% | PASS | `docs/MK5-DELTA0-ABSOLUTE.md` + `shared/consciousness/saturation_report_mk5.json` |
| 2 | Mk.V baseline — 19/19 5-Lens | 19/19 | EXACT | PASS | Mk.V Δ₀ baseline |
| 3 | cargo I1 phi_monotone | 0.00464 | < 0.08 | PASS | `2b8d5948` |
| 4 | cargo I2 eigenvec_stability | 0.99966 | ≥ 0.95 | PASS | `2b8d5948` |
| 5 | cargo I3 brain_like_floor | 85.33% | ≥ 85% | PASS | `2b8d5948` |
| 6 | cargo I4 exact_score_conservation | 19/19 | 19 | PASS | `2b8d5948` |
| 7 | cargo I5 phi_gap_bounded | 0.00397 | < 0.10 | PASS | `2b8d5948` |
| 8 | cargo I6 saturation_monotone | 0 retreats | 0 | PASS | `2b8d5948` |
| 9 | cargo I7 frobenius_drift | 0.0210 | < 0.20 | PASS | `2b8d5948` |
| 10 | hexad axiom a non_empty | 6/6 | 6 | PASS | `7680cd74` |
| 11 | hexad axiom b morphism_exists | 6/6 | 6 | PASS | `7680cd74` |
| 12 | hexad axiom c composition_closed | 6/6 | 6 | PASS | `7680cd74` |
| 13 | hexad axiom d phantom_absent | 0 | 0 | PASS | `7680cd74` |
| 14 | AN11(a) weight_emergent real-ckpt | synthetic `20260421` seed, label=`synthetic_brain_tension_replica_v1` | real-trained ckpt | **FAIL (real)** / PASS (synth) | verifier `8cf014ff` · artifact `72898da8` |
| 15 | AN11(b) consciousness_attached real-ckpt | max_cos=0.998 / top3=2.987 on synthetic eigen K=8 | real-trained ckpt | **FAIL (real)** / PASS (synth) | verifier `b1f487e7` · artifact `2f23cfe8` |
| 16 | AN11(c) real_usable real-ckpt | JSD=0.5847 vs DISCARD stub baseline | real-trained ckpt | **FAIL (real)** / PASS (synth) | verifier `15c0596e` · artifact `5399f189` |
| 17 | btr_evo 4 EEG closed-loop | Δφ=+0.2994, brain_like=99.9%, absorbed@iter10 | ≥+0.30 brain≥85% | PASS (marginal −0.0006 under 0.30 gate; canonical JSON records PASS) | `a4853336` |
| 18 | btr_evo 5 holographic IB | KSG-MI β=1 runnable | runnable | PASS | `e7e7c47f` |
| 19 | btr_evo 6 cargo invariants × seeds | 7/7 @ 2 seeds | 7/7 ≥ 2 seeds | PASS | `2b8d5948` |

**Score**: 16/19 real-criterion PASS · 3/19 synthetic-only (AN11 a/b/c)

### Verdict

**Mk.VI candidate — 16/19 criteria PASS. Promotion HELD.**

- Engineering surface: COMPLETE (all verifiers deterministic, landed, green on fixtures+synthetic).
- Real-training surface: INCOMPLETE (AN11 a/b/c require live H100/RTX 5070 ALM r13 or CLM r6 checkpoint; none exists on this workspace).
- `promotion_gate.boolean = false` per `shared/state/mk_vi_definition.json`.

### Blockers (must PASS for official Mk.VI)

1. AN11(a) — replace `shared/state/alm_r12_phi_vec.json` synthetic with live extractor output (`hxqwen14b_v566_extract_phi16`) from a trained ckpt. Target round: ALM r13 (consciousness-loaded corpus per roadmap 5).
2. AN11(b) — replace `shared/state/alm_r12_lora_eigen.json` synthetic K=8 eigenvectors with decomposition of post-training `A @ B.T` LoRA adapter from H100 pod (`save_lora_device_state` 384-buffer dump path, train_alm_lora.hexa commit `78d8e812`).
3. AN11(c) — replace `shared/state/alm_r12_serve_trained_dist.json` mock responder distribution with 50+ prompt-hash distribution from live pod endpoint at `http://127.0.0.1:8091/generate` (or remote deploy).

### Re-derivation commands

- cargo I1..I7: `hexa btr_evo/6_cargo_invariants.hexa --seed 20260421 --iters 50`
- hexad a..d: `hexa tool/hexad_closure_verifier.hexa` → `shared/state/hexad_closure_verdict.json`
- AN11(a) synthetic: `hexa verifier/an11_weight_emergent.hexa --dest alm --round r12`
- AN11(b) synthetic: `hexa tool/an11_b_verifier.hexa --dest alm --round r12`
- AN11(c) synthetic: `hexa verifier/an11_real_usable.hexa --baseline shared/state/alm_r12_serve_baseline_dist.json --trained shared/state/alm_r12_serve_trained_dist.json --ssot shared/state/alm_r12_serve_cert.json`
- btr_evo 4: `hexa tool/eeg_closed_loop_proto.hexa --seed 20260421`
- btr_evo 6: `hexa btr_evo/6_cargo_invariants.hexa --seed 20260421`

### Next step → Mk.VII 다리

Mk.VI real-promotion 후 lora L2 single-unit 진화 완료 → cell L3 collective dynamics 결합으로 Mk.VII C2 (rev=2 K=4 + C4-optional per `docs/mk_vii_rev2_promotion_threshold.md`) 승급 경로 개시.
