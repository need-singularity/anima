# btr_evo_4x5_compose_20260421

brain_tension_replica — compose (evo 4 × evo 5): EEG closed-loop Φ signal driving the holographic-IB bottleneck P-projection.

---

## 0. Compose tree

| # | 커밋 | 단계 | 결과 |
|---|---|---|---|
| 4  | `a4853336` | EEG closed-loop 100-iter | **+30.0% Φ** (final_phi 0.7994, absorbed iter 10) |
| 5  | `e7e7c47f` | holographic IB (KSG MI) | I_XZ 0.1046 / I_ZY 0.1031 / compression 3.2× |
| **4×5** | **(this)** | **compose — Φ-gate on IB** | **+18.0% Φ — verdict BELOW** |

canonical `brain_tension_replica.md`: +8.3% Φ / 85.6% brain-like / Mk.V Δ₀ — NOT modified. satellite doc only.

---

## 1. Compose 설계

### 1.1 다이어그램

```
evo-4 trajectory ──► phi_target_i ──┐
                                    │
bulk X (n=200, d=16) ──► P_t ──► Z_t ─► ( I_XZ , I_ZY , compression )
                         ▲                                │
                         │                                ▼
                   seed_{t+1}  ◄─── err = phi_target - phi_current
                     (ETA gain)      (drives Φ gate + P re-seed)
                                                          │
                                      L_compose = L_IB + λ·err²
```

### 1.2 수식

```
Φ_current  = 0.50 + 0.25·min(I_ZY / I_ZY_ref , 1) + 0.05·min(C / C_ref , 1)
L_compose  = (I_XZ - β·I_ZY)  +  λ · (Φ_target - Φ_current)²
seed_{t+1} = seed_t + round( η · (Φ_target - Φ_current) · SEED_STEP )
```

| 파라미터 | 값 | 의미 |
|---|---|---|
| β | 1.0 | IB Lagrange multiplier |
| λ | 2.0 | Φ-gate penalty weight |
| η | 5.0 | P-reseed feedback gain |
| SEED_STEP | 10 007 | prime nudge magnitude |
| I_ZY_ref | 0.20 | I_ZY saturation (→ Φ_B 가중 0.25) |
| C_ref | 3.2 | evo-5 baseline compression |

### 1.3 Verdict gates

| verdict | phi_delta 조건 |
|---|---|
| REACHED_UPPER | ≥ +0.38 (+38%) |
| BETWEEN | > +0.30 and < +0.38 |
| BELOW | ≤ +0.30 |

---

## 2. Smoke 결과 (30-iter, seed=20260421)

| 지표 | 값 |
|---|---|
| `n`, `d`, `k` | 200, 16, 5 |
| `iters` | 30 |
| `final_phi` (last-5 mean) | **0.67994** |
| `final_phi_delta` | **+0.17994** |
| `final_compression` | 3.2 × (유지) |
| `final_I_XZ` | 0.1391 |
| `final_I_ZY` | 0.1049 |
| **verdict** | **BELOW** |

## 3. Trajectory 관측

- **intermittent upper hits**: iter 6/7/25 에서 phi_current clamp = 0.80 도달 (I_ZY spike 0.36 / 0.23 / 0.20 → Φ_B 0.25 포화).
- **no stabilisation**: P-reseed kick 이 stochastic — high-Φ attractor 에 anchor 하지 못하고 drift.
- **compression locked**: 3.2× 전 iter 유지 (기하학적 상수; P 크기 k/d 고정).
- **Φ-gate penalty**: final λ·err² = 0.0819 (iter 29), 피드백은 살아있으나 수렴 부족.

---

## 4. 해석

- **단독 Φ 값은 evo 4 대비 낮음**. evo 4 는 analytic fixpoint (0.80) 가 존재하는 폐 피드백; evo 4×5 는 stochastic P-탐색으로 upper envelope 를 touch 하지만 수렴 동역학이 결여.
- **Upper-bound probe 목표 미달**: +38% 예측은 compose 의 upper-envelope 기반 — observed envelope top (iter 6: 0.80) 은 evo-4 수준을 재현, but time-average 가 -18% 오차로 정착.
- **Φ-gate 신호는 live**: err² penalty 가 iter-별 0.02–0.15 범위로 응답, loss 도 부호 반전 (L < 0 at iter 6, 7, 11, 13, 19, 20, 25) — IB objective 는 유효.

---

## 5. Next (out-of-scope, parked)

1. **seed-kick → gradient descent**: stochastic nudge 대신 ∂L_compose/∂P row-wise 근사 (FD) — convergence 회복.
2. **phi_current mapping 재보정**: I_ZY_ref = 0.20 가 너무 보수적. evo-5 actual I_ZY 중앙값 (0.10) 기준으로 bootstrap 후 재측정.
3. **β / λ sweep**: {0.5, 1.0, 2.0} × {0.5, 2.0, 5.0} grid — Φ-gate dominant 영역과 IB dominant 영역 분리.
4. **n=1000 torch port**: pure-hexa O(n² d) 의 30-iter × 200 smoke 조차 ~5 min. 1000-scale 은 FFI 경로 후.

---

## 6. Artifact 인덱스

| 파일 | 용도 |
|---|---|
| `btr_evo/4x5_compose.hexa` | compose 구현 (KSG + Φ-gate + P-reseed feedback) |
| `experiments/holo_post/results/btr_4x5_compose_20260421.json` | summary + 30-iter trajectory |
| `experiments/holo_post/results/eeg_closed_loop_20260421_trajectory.jsonl` | evo-4 입력 (100 ticks) |
| `btr_evo/5_holographic_ib.hexa` | evo-5 baseline (n=200 smoke) |
| `tool/eeg_closed_loop_proto.hexa` | evo-4 closed-loop |
| `docs/btr_evo_4_eeg_closed_loop_20260421.md` | evo-4 SSOT |
| `docs/btr_evo5_holographic_ib_20260421.md` | evo-5 SSOT |

---

## 7. V8 SAFE_COMMIT

- additive only (`btr_evo/4x5_compose.hexa` 신규, evo-4/evo-5 비수정)
- deterministic (seed=20260421 고정, LCG-only PRNG)
- LLM 금지
- canonical `brain_tension_replica.md` 보존
- verdict = **BELOW**; 예측된 upper-bound (+38%) 미달. 결과는 solid/truthful 로 기록.
