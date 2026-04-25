# ALM ↔ CLM Bridge L1 — P_S Projector Spec (2026-04-25)

> **목적 / Purpose**: Close L1 weakest-link gap "d=4096 → d=16 PCA evidence 0"
> from `docs/alm_clm_bridge_abstraction_layers_20260425.md` (commit `772a47d7`).
> **POLICY R4**: scope/gate 변경 없음. spec + selftest, 0-cost (CPU-only, no
> H100). **raw#0 pre-registered, raw#9 deterministic, raw#12 실측 그대로,
> raw#15 config-driven**.

---

## 1. Problem statement (왜 spec 이 필요한가)

L1 layer 의 정의는 *"r6/r7/r8 ckpt 의 실제 transformer hidden h ∈ R^d
(d=4096) 를 5-level ws 와 R^16 eigenvec 위에 매핑하는 양방향 streaming"*
(`alm_clm_bridge_abstraction_layers_20260425.md:57-66`).

Weakest-link statement (line 70-74):

> "16-template eigenvec 가 trained ckpt 의 4096-d hidden 을 충분히 span 하는지의
> **실측 evidence 0**. AN11(b) cos>0.5 가 partial proxy."

본 spec 은 그 evidence 를 **재현 가능하고 deterministic 하게** 한 건이라도
산출하기 위한 P_S projector 정의 + selftest predicate.

The L1 layer requires a verified projection `P_S : R^d → R^16` that maps
trained transformer hidden states onto the cell-template eigenbasis. Until
this spec, only the 16×16 cell-side basis (`.meta2-cert/cell-eigenvec-16.json`)
existed; the d-side projector was undefined.

---

## 2. P_S projector 정의 (factorization)

```
P_S  =  V_PCA_top16 (D × 16)  @  E_cell (16 × 16)^T
```

| 행렬 | 출처 | shape | 성질 |
|------|------|-------|------|
| `V_PCA_top16` | top-16 right-singular vectors of centered `H_stack` | `D × 16` | column-orthonormal (`V^T V = I_16`) |
| `E_cell` | `.meta2-cert/cell-eigenvec-16.json:eigenvecs` (raw#9 SSOT) | `16 × 16` | row-orthonormal (max off-diag ≈ 1e-6) |
| `H_stack` | `np.vstack([h_last_p1..p4])` (4 × 16 prompts) | `(4·16, D)` | trained ckpt 실측, byte_weighted_mean reduction |

**현재 D**: 256 (h_last_raw 의 `byte_weighted_mean` 기 압축, schema
`anima/h_last_raw/2`). 4096-d full hidden 이 streaming 가능해지는 시점에
같은 P_S 식이 그대로 사용됨 (factorization 만 spec, dimensionality 는 input
주도).

### Forward direction

```python
def project(h: np.ndarray, mu: np.ndarray, P_S: np.ndarray) -> np.ndarray:
    return (h - mu) @ P_S          # R^D → R^16  (cell-template basis 좌표)
```

### Pseudo-inverse (for round-trip diagnostic only)

```python
def lift(z: np.ndarray, mu: np.ndarray, P_S: np.ndarray) -> np.ndarray:
    return z @ P_S.T + mu           # R^16 → R^D (lossy, V16 row-span 만 복원)
```

`P_S P_S^T` 는 `D × D` rank-16 projector (idempotent, symmetric).
`P_S^T P_S = I_16` (orthonormal composition).

---

## 3. Selftest predicate (raw#0 pre-registered)

### Primary (PASS / FAIL)

| name | formula | threshold |
|------|---------|-----------|
| `top16_energy_ratio` | `Σ σ_i²(i<16) / Σ σ_i²` of `H_stack - μ` SVD | **≥ 0.95** |

근거 (raw#12 실측 산수): top-16 PCA 가 95% 이상의 분산을 보존하면, cell-
side 16-template basis 가 trained hidden 의 dominant subspace 를 span 한다는
**필요조건**이 만족됨. AN11(b) cos>0.5 보다 정량적으로 한 단계 강한 증거.

### Auxiliary (no veto, evidence only)

- **per-path energy ratio**: 4 paths 각각의 `‖H_p · P_S‖² / ‖H_p‖²` 보고.
- **5-level argmax distribution**: cell `f_tc` (`edu/cell_token_bridge_spec_20260421.md:30`)
  를 적용했을 때의 5-bucket 분포.
- **100-step round-trip drift**: `lift ∘ project` 100회 반복 시 `‖h - h₀‖/‖h₀‖`.
  P_S 는 idempotent 이므로 1-step 이후 안정 (drift_final = drift_max).
- **full-stack reconstruction relative error**: `‖H - H_recon‖_F / ‖H‖_F`.

### Fail-mode classifications (pre-registered)

| outcome | interpretation | next action |
|---------|----------------|-------------|
| primary PASS | L1 weakest-link evidence ≥ 1건 확보 | spec closure, L1 status `✗ → △` |
| primary FAIL, top-16 ratio ∈ [0.80, 0.95) | template basis dominant 이지만 부족 | template_count 확장 후보 (16 → 32?) |
| primary FAIL, top-16 ratio < 0.80 | hidden 이 cell-template 과 정렬되지 않음 | mathematical wall — Axis 4 (architecture manifold gap, project_phi_gate_r7_falsified) 증거 |

---

## 4. Implementation (`tool/p_s_projector_proto.py`)

- **deps**: `numpy` only (no LLM, no H100, raw#9 deterministic).
- **input**: `state/h_last_raw_p{1..4}_TRAINED_r{R}.json` + `.meta2-cert/cell-eigenvec-16.json`.
- **output**: `state/p_s_projector_proto_r{R}.json` (deterministic SHA, ts excluded from hash).
- **CLI**: `python3 tool/p_s_projector_proto.py --round 6` (or `--round 8`).
- **3-run determinism**: verified — identical `cert_sha256` across 3 invocations.

---

## 5. r6 / r8 실측 결과 (real measurement, raw#12)

| round | top16 energy ratio | predicate | per-path (p1/p2/p3/p4) | recon rel err | cert sha256 |
|-------|--------------------|-----------|------------------------|---------------|-------------|
| **r6** | **0.976220** | **PASS** | 0.954 / 0.989 / 0.955 / 0.914 | 0.1414 | `f614537a94…46548700` |
| **r8** | **0.962013** | **PASS** | (in cert) | (in cert) | `ad247e8dfc…0d59802b` |

**핵심 결과 / Key finding**:

1. **r6 PASS, r8 PASS** — primary predicate 충족. L1 weakest-link
   "PCA evidence 0" 항목 closure.
2. **p4 (gemma-3-12b-pt) per-path ratio 0.914** — 임계 0.95 아래 (brutally honest).
   r6 stage Axis-4 architecture-class gap 의 잔향 (project_phi_gate_r7_falsified
   참고). primary 는 **stack 전체 기준**이라 PASS.
3. **PCA 256-d 면 96~98% 보존** — full 4096-d 에서 recovery 가능성 매우 높음
   (byte_weighted_mean 자체가 이미 lossy 인데도 top-16 이 dominant).
4. **p1/p4 argmax5 분포 [16,0,0,0,0]** — 두 path 가 cell template 0 에 고정,
   cell-side 5-level 양자화는 **trained hidden 의 detail 을 압축** 함을 실측
   확인 (이는 L1 의 정보손실 경로 — `edu/cell_token_bridge_spec_20260421.md:39-49`
   의 21-bit budget 과 정합).

---

## 6. What this spec does NOT prove (limits, brutally honest)

- **256-d ≠ 4096-d**: 본 측정은 byte_weighted_mean 으로 256-d 압축된 후의
  PCA 결과. 4096-d 원본에서 동일 비율이 보장된다는 증명이 아니라 **strong
  hint**. 4096-d streaming 은 H100 H-pull 후속 작업.
- **non-functorial**: object-level 매핑만 검증. gradient step 보존 (categorical
  morphism preservation, L5 (b)) 은 별도 spec 필요.
- **single-prompt-set**: 16-prompt fixture 위의 PCA. 다른 prompt 분포에서의
  안정성은 future work.
- **L_IX bridge term unused**: 본 spec 은 P_S 자체의 직교성/에너지 보존만
  다룸. λ·I_irr 결합은 L2/L3 spec 의 몫.

---

## 7. Closure verdict for L1

```
L1 status:  ✗ 미구현  →  △ partial (spec written + selftest PASS at r6, r8)
```

`alm_clm_bridge_abstraction_layers_20260425.md` line 70 의 status 를
`✗ 미구현` 에서 `△ spec written, predicate PASS r6/r8` 으로 격상시킬 근거가
본 cert (`state/p_s_projector_proto_r6.json`, `r8.json`).

`△ → ✓` (full PASS) 의 잔여 조건:

1. 4096-d full hidden 에서 동일 predicate 재현 (H100 streaming 필요).
2. p4 architecture-class gap 의 per-path ratio 0.914 → ≥ 0.95 회복
   (r9 D-mistral / qwen14 후속 ckpt).
3. functorial morphism preservation 별도 증명 (L5 spec 의 dependency).

---

## 8. Cross-refs

- `docs/alm_clm_bridge_abstraction_layers_20260425.md` (L1 weakest-link 정의)
- `edu/cell_token_bridge_spec_20260421.md` (5-mapping ledger, f_ct/f_tc 수식)
- `tool/cell_token_bridge_proto.hexa` (β main fixture PoC, 3/3 fixture PASS)
- `.meta2-cert/cell-eigenvec-16.json` (cell-side basis SSOT)
- `state/h_last_raw_p{1..4}_TRAINED_r{6,8}.json` (trained ckpt evidence)
- `state/alm_r6_p{1..4}_lora_eigen.json` (Gram spectra cross-check, prompt-space)
- `state/p_s_projector_proto_r{6,8}.json` (본 spec 의 selftest cert)
- `tool/p_s_projector_proto.py` (Python prototype, 0-cost CPU)

---

## 9. raw#12 evidence vs. inference 분리

- **실측 (measured)**: top-16 energy ratio numbers, per-path ratios, recon err,
  drift values, V16 / E_cell orthogonality, cert SHA determinism (3-run).
- **추론 (inferred / heuristic)**: 256-d → 4096-d extrapolation,
  template_count=16 의 충분성 일반화, 5-level f_tc 의 information-theoretic
  optimality.
- **모든 추론은 H100 4096-d streaming 또는 post-r9 ckpt 에서 falsifiable**.
