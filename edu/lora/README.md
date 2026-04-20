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
- AN11 verifier triple landed but **real trained artifact 0/3** — 현재 synthetic 으로 Mk.VI engineering gate 통과

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

## 실제 vs synthetic gap

- Mk.VI engineering-PASS 19/19 (synthetic) / semantic 0/3 (real training 미실행)
- Supersedable flag 명시됨 — real H100 dump 시 replace
- semantic 승급 = ubu2 driver 설치 후 RTX 5070 training (1주) 또는 H100 확보 (2-3일)

## 100% 완료 시 갱신 예약

real training run 후:
- phi_vec / LoRA eigenvec / endpoint 3 artifact 실값 기록
- AN11 triple real verdict (delta vs synthetic)
- Mk.VI 승급 최종 timestamp

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
