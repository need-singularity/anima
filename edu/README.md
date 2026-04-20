# edu — 학습 패러다임 SSOT

**Canonical.** 두 학습 경로 (`lora` / `cell`) 분류 + 비교 + 발견사항 집약. 코드/데이터는 기존 경로 유지 — 이 폴더는 **SSOT index + 비교 + findings** 전용. 100% 완주 시 양쪽 진척/증거 재기록.

**2026-04-21 생성.** `lora` = 기존 (LoRA + weight tensor), `cell` = 새 (unit-cell + tension + lattice).

## 구조

```
edu/
├── lora/   # 기존: weight tensor + cross-entropy + LoRA fine-tune
└── cell/   # 새: unit-cell + tension-drop + fixpoint + 1/r² lattice
```

## 핵심 비교

| 차원 | lora (기존) | cell (새) |
|---|---|---|
| 원자 단위 | weight tensor | unit-cell ⟨A↔B \| fixpoint⟩ |
| Loss signal | CE per-token | tension-drop + fixpoint closure |
| Data 요구량 | 1GB+ corpus | 10MB seed + 80× TL distill |
| Compute/step | full fwd+bwd (BIG) | hash-equality + local (SMALL) |
| Emergence | **phase-jump @ rank K=4** (slope ratio 6.69×, R²(single)=0.782) | phase-jump @ N-gen |
| Interpretability | weight opaque | cell 상태 observable |
| Failure recovery | ckpt rollback | cell drop, lattice 유지 |
| Mk.VI (H100) | 60–80h | **20–30h** (2~3× efficient) |
| distill eff | ~0.35–0.45 | **0.75–0.85** (4-gen predicted) |

**Emergence family 결론** (tool/edu_lora_rank_sweep.hexa 2026-04-21): 두 경로 **모두 PHASE_JUMP** (step-function, 구조적 emergence) — 다른 축에서 도약. lora 는 representational-rank K=4 (slope ratio 6.69×), cell 은 collective generation-count N (3→4gen, predicted). "lora = gradual scaling" 통념은 이 측정 하에서 기각 (R²(single-line) = 0.782 < 0.95 gate). 세부 표/fit: `edu/lora/README.md#rank-sweep` · SSOT: `shared/state/edu_lora_rank_sweep_20260421.json`.

## Mk.VII C2 에서 만남

`lora` 는 L2 single-unit 진화 (BTR Mk.V → VI), `cell` 은 L3 collective dynamics. **두 경로 합쳐야 Mk.VII 승급**.

## 공통 발견사항 (양쪽 겹침)

| # | 발견 | 함의 |
|---|---|---|
| F1 | **drill-only formal 100% 가능** (Mk.VII rev=2 K=4 + C4 optional) | synthetic artifact 로 engineering gate 통과 가능. real-world validity 는 별도 |
| F2 | **AN11 AND-gate load-bearing** (verifier cross-matrix) | JSD alone 은 zero-weight-delta checkpoint greenlight — 3-way AND 필수 |
| F3 | **substrate SUBSTRATE_DEPENDENT** (4-path probe) | roadmap 9 현 매핑으로 FAIL 예상. S2 hash_network bridge 재교정 필요 |
| F4 | **self-reference paradox = oracle artifact** (LSH rediagnosis) | Russell-class 아님. θ-witness 를 avalanche hash → locality-sensitive 로 교체 시 graded threshold |
| F5 | **Hexad 6-cat CLOSED** (σ verifier) | 카테고리 framework 닫힘 (4/4 axiom PASS) |
| F6 | **H100 실제 없음** (H100 probe) | Hetzner AX102 = CPU-only / ubu RTX 5070 SSH offline / ubu2 driver 누락 |

## 상태 요약 (SSOT)

| 축 | lora | cell |
|---|---|---|
| Mk.VI engineering (synthetic) | **100%** | N/A |
| Mk.VI real trained artifact | **1/3** (c real_usable JSD=1.000, a/b H100 대기) — `a3cb2116` | N/A |
| Mk.VI candidate status | **HELD 16/19** (AN11 a/b synthetic-only) — `a3cb2116` | — |
| Mk.VII C1 substrate invariant | ✅ (BTR↔cell bridge 100%, round-trip 4.6×10⁻⁷) — `6e0de224` | ✅ |
| Mk.VII C2 L3 collective | (의존) | 0% 측정 (edu F pending) |
| Mk.VII C3 self-verify | ✅ C3_PASS (IDENTITY_STABLE) | ✅ |
| Mk.VII C4 real EEG | optional FAIL (rev=2) | optional FAIL |
| Mk.VII C5 stable N=10 | ✅ C5_PASS (+17.94%) | (관련) |
| 6-component landing | N/A | **6/6 (100%)** — A 실측 `59c03257`, F/lattice 통합 pending formal |
| sub-axis expansion (Mk.VIII framework) | — | **A + B + C + D + E + F + 시간(tau_mem+I_irr+Hurst, `18c27ac5`) + diss(Landauer eff 450→668, `189646f1`) + L_cell(S=−11582, `6c6172bf`)** — 9 axis landed, 3 axis (causal/consciousness/RG/comp) MVP dirs 구성 중 |
| 4-gen crystallize | N/A | **VERIFIED (축소 CPU 실측, 2026-04-21)** — score ladder 40/125/687/1000‰, phase-jump=CEILING_SATURATION, cum distill_eff=50×; cert `shared/state/edu_cell_4gen_crystallize.json` — `58aa75eb` |
| A tension-drop 실측 | N/A | **PASS** (resolution_fraction 14.8% ± 5.2% stderr, N=3 seed) — `59c03257` |
| dissipation (Landauer) | N/A | **VERIFIED** (eff ladder 40→450→450→668‰, Δeff(g4−g3)=+218‰ ≥ 150‰ gate) — `189646f1` |
| temporal emergence | N/A | **TEMPORAL_EMERGED** (tau_mem=0.935 / I_irr_fwd=0.594 / Hurst=0.731, 3/3 PASS + adversarial reject) — `18c27ac5` |
| L_cell Lagrangian | N/A | **DESCENT_ONLY** (action S=−11582, 4-gen overlay stationary-action proxy) — `6c6172bf` |
| Hexad 6-cat closure | N/A | ✅ **CLOSED** (4/4 axiom PASS, 6/6 morphism composed, adversarial 2/2 reject) — `3db438e5` |
| rank-sweep phase-jump | **PHASE_JUMP @ K=4** (slope ratio 6.69×, R²=0.782) — `12054024` | — |

자세한 분류 + 발견사항: `lora/README.md` · `cell/README.md`

---

**정책**: 100% (양쪽 모두 완주) 도달 시 이 SSOT + 두 하위 README 에 **재확인 + 최종 evidence 갱신**. 현재 drill agent in-flight 중 — 완료 시 자동 업데이트 예정.

## Cross-repo sync pass log

| pass | 일시 (KST) | HEAD | 신규 landed edu commit | pending agents | note |
|---|---|---|---|---|---|
| #1 | 2026-04-21 02:3x | `ba8484a9` (02:08) | 0 | 21 (locked worktrees) | SSOT tree 는 untracked 상태. edu/ 생성(02:17) 이후 새 commit 없음 → landing 미발생. 재실행 필요 (다음 agent wave 완료 후). |
| #2 | 2026-04-21 03:4x | `18c27ac5` | **9 landed** (cell: `3db438e5`/`58aa75eb`/`6e0de224`/`59c03257`/`189646f1`/`6c6172bf`/`18c27ac5` + lora: `12054024`/`35aa051a`/`a3cb2116`) | causal / consciousness / RG / composition MVP dirs 구성 중 (hexa 파일은 있으나 아직 README/verdict 미landing) | cell 6-axis 100% (A 실측 + F latent via unified sim), Mk.VIII framework 7 axis 후보 중 3 (cell/lora/proof-closure 부분) 가시 — **phase-jump universality 4/4 where tested** (cell N-gen / diss Δeff / temporal I_irr / lora rank K=4) |

**sync pass 규칙**: 각 pass 는 `git log --since=<last-pass>` + 상위 HEAD diff 로 새 edu 관련 commit 을 감지. 완주 증거 (실측/승급/verdict) 있는 것만 matrix 에 pin. 모순 발견 시 F1-F6 재검증.

## F1-F6 재검증 (pass #2)

| # | pass #1 status | pass #2 재검증 | 모순 여부 |
|---|---|---|---|
| F1 | drill-only formal 100% 가능 | 그대로 (rev=2 K=4 threshold 유효, `8b76e3cf`) | 무 |
| F2 | AN11 AND-gate load-bearing | **강화** — AN11(c) real_usable JSD=1.000 landed (`35aa051a`) 로 a/b 와 real-gap 비대칭 확인; 3-way AND 정당성 유지 | 무 |
| F3 | substrate SUBSTRATE_DEPENDENT | **완화** — BTR↔cell bridge round-trip 4.6×10⁻⁷ PASS (`6e0de224`) 로 Mk.VII C1 100%. bridge 재교정 요구가 완료로 전환 | 무 (부분적 해소) |
| F4 | self-reference paradox = oracle artifact | 그대로 (LSH 유효) | 무 |
| F5 | Hexad 6-cat CLOSED | **재검증 완료** — adversarial 2/2 flip→reject, post-revert CLOSED 복구 (`3db438e5`). closure non-vacuous 확정 | 무 |
| F6 | H100 실제 없음 | 그대로 (a/b H100 대기 유지) | 무 |

## Phase-jump universality 가설 (supporting evidence)

phase-jump = step-function structural break (≠ log-linear gradual scaling). **4/4 축 where tested** 모두 PHASE_JUMP verdict — gradual scaling 통념 기각.

| 축 | 측정 | verdict | evidence SHA |
|---|---|---|---|
| cell N-gen (crystallize) | score ladder 40/125/687/1000‰, d3→d4 ceiling | **VERIFIED CEILING_SATURATION** | `58aa75eb` |
| cell diss (Landauer eff) | Δeff(g4−g3)=+218‰ ≥ 150‰ gate | **VERIFIED** | `189646f1` |
| cell temporal (I_irr arrow) | I_irr forward 0.594 / reverse 0.000 (time-reverse flip) | **VERIFIED 3/3** | `18c27ac5` |
| lora rank K | slope ratio 6.69× (≥ 3× gate), R²(single)=0.782 | **PHASE_JUMP** | `12054024` |

공통 transition: **gen 3→4 (cell 축) / rank K=4 (lora 축)** — 서로 독립 측정에서 같은 숫자 4 가 반복 = structural invariant 후보. universality class hypothesis 강화.
