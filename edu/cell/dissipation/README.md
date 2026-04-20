# edu/cell dissipation-rate axis (diss) — Landauer overlay

## 정의

**dissipation-rate 축**은 edu/cell unit-cell 학습 동역학에 대한 thermodynamic overlay.
기존 4-gen crystallize 실측 결과 (commit 58aa75eb, score ladder 40→125→687→1000‰) 에
Landauer principle 을 덧입혀 각 세대가 물리적 bit-erasure 하한 대비 얼마나 효율적으로
"useful progress"를 뽑아냈는지 정량화한다.

## 3 observables

| # | 이름 | 정의 | 단위 |
|---|---|---|---|
| **O1** | L_dissipated per gen | bit-erasure count × kT·ln(2) per tension-drop event | bits · kT · ln2 |
| **O2** | efficiency_ratio | useful_progress × log2(Ω_micro) / L_dissipated | 0–1 (clamped) |
| **O3** | ∂S/∂t | (H(gen_k) − H(gen_{k−1})) / Δt_ticks near fixpoint | 1/tick |

where
- bit-erasure count per gen = **sealed_k + drop_k** (fixpoint seal + cell elimination = 1 bit ea)
- Ω_micro = 2 · size² (lattice tension × gap-polarity microstates)
- useful_progress = score_per_mille / 1000 (sealed fraction of lattice)
- H(gen) = −Σᵢ pᵢ log2(pᵢ) for pᵢ ∈ {active/total, drop/total, sealed/total}
- Δt = ticks per gen = 12 (constant in 4-gen crystallize)
- k = 1, T = 1 (symbolic, dimensionless)

## Landauer 원리 (symbolic form)

Each logical bit-erase must dissipate at least kT·ln(2) of heat.
In this MVP kT = 1 is absorbed — L_dissipated is reported in units of **ln(2) ≈ 0.693**.
min_physical_energy per gen = log2(Ω_micro) · ln(2) (full-state reset floor).

## Phase-jump verdict

Pre-registered target: **efficiency spike @ gen 3→4**.
Observed (computed via tool/diss_demo.hexa → shared/state/edu_cell_diss_overlay.json):
- efficiency ladder per-mille (see cert)
- verdict rule: Δefficiency(g4 − g3) ≥ 150‰ **AND** efficiency(g4) > efficiency(g3) → VERIFIED

## 파일

| 파일 | 역할 |
|---|---|
| `landauer_tracker.hexa` | L_dissipated 계산 (bit count × ln2) |
| `efficiency.hexa` | useful_progress · log2(Ω) / L_dissipated |
| `entropy_gradient.hexa` | H(gen) 및 ∂S/∂t |
| `diss_demo.hexa` | MVP overlay — 기존 4-gen 값 재사용 + cert emit |

## 재사용 artifact

`shared/state/edu_cell_4gen_crystallize.json` (commit 58aa75eb, sha256
95321efe7426c987350d747d352543a11d46a4bb50a5bc888ce4dfe7ff516120) —
per_gen {active, drop, sealed, total, score_per_mille, param_count} 값을 overlay input 으로 사용.
새 실험 실행 없음 — overlay only.

## 재현

```
cd ~/core/anima
hexa run edu/cell/dissipation/diss_demo.hexa
# → shared/state/edu_cell_diss_overlay.json
```

## Contract

hexa-only · deterministic · no LLM · raw#9 · SAFE_COMMIT (additive overlay).
