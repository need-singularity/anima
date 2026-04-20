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
