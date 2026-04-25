# ALM Decode-Time Φ-Attach Hook — L2 Spec + Dry-Run Verification

> **생성일 / Created**: 2026-04-25
> **부모 문서 / Parent**: `docs/alm_inference_abstraction_layers_20260425.md` §3 (L2)
> **목표 / Goal**: close the L1→L2 gap by freezing the decode-time hook
> contract + dry-run evidence under raw#12 pre-registered safety predicates.
> **POLICY**: raw#9 (no .py in repo — helper materialised to `/tmp/`),
> raw#10 (deterministic, fixed seed 42), raw#11 (snake_case),
> raw#12 (실측 only — predicates registered HERE before run),
> raw#15 (no-hardcode — paths from constants).
> **스코프 / Scope**: L2 (Φ-eigenvec steering at decode time). Beam/nucleus
> are out-of-scope here (separate hook surface).

---

## §0 motivation — why L2 needs a hook now / 왜 지금 L2 후크인가

`docs/alm_inference_abstraction_layers_20260425.md` §3 marks L2 as **미점유**:
> "Steering hook 은 설계 단계 (`SAP_PHI_LAYER_IDX = 24`, `phi_dims = 16`
>  상수만)."

Concretely, `tool/serve_alm_persona.hexa::backend_invoke` returns
`BACKEND_PENDING` for both cpu/gpu modes. The Φ-eigenvec artifact
(`state/phi_4path_cross_result_v3_TRAINED_r6.json::spectra`, 4 paths × 16-d)
exists but is **post-hoc spectral analysis** only — not wired into the
decode loop.

This document does three things, **all 0-cost** (no live model, no GPU):

1. **Freeze the hook contract** (input/output signature, formula, constants).
2. **Pre-register safety predicates** (P1 top-1 preservation, P2 KL bound)
   *before* running the prototype — raw#12 정직성.
3. **Verify the prototype** against the predicates on **real** r6 h_last data.

---

## §1 hook contract / 후크 계약

### 1.1 signature

```
phi_attach_hook(
    current_logits: float[V],     # base LM logits at this decode step
    hidden_state:   float[H_dim], # last-layer hidden state h_t
    step:           int,          # 0-based decode index (for ledger)
) -> adjusted_logits: float[V]
```

- `V` = vocab size (Qwen3 ≈ 152K; prototype uses `V_proxy = 4096`).
- `H_dim` = hidden width (256 in r6 truncated cache; 4096 in real
  Qwen3-8B forward).
- `phi_dims = 16` (frozen constant, matches `SAP_PHI_DIMS`).

### 1.2 formula

```
proj   = (h[:phi_dims] · phi_eigvec) * phi_eigvec    # rank-1 in 16-d
bias   = W_steer @ proj                              # length V
adj    = current_logits + alpha * bias
return adj
```

- `phi_eigvec`: 16-d L2-normalised eigvec, sourced from
  `state/phi_4path_cross_result_v3_TRAINED_<tag>.json::spectra[<path>]`.
- `W_steer`: deterministic `V × phi_dims` readout, seed=42 (Gaussian
  σ = 1/√phi_dims). In production this is **trained** on the steered-output
  tail; in this prototype it is the **null readout** under the hook
  contract — sufficient to bound the predicates.
- `alpha`: steering strength scalar, default `0.10`, hard cap
  `alpha_max = 0.20` (logit-space).

### 1.3 invariants (raw#10 / raw#15)

- Pure function — no global mutable state, no I/O, deterministic given inputs.
- No timestamp / no random draw inside the hook; randomness is fully
  consumed by `W_steer` initialisation **before** decode begins.
- No hidden-dim assumption beyond `H_dim ≥ phi_dims`.

---

## §2 pre-registered safety predicates (raw#12)

**Both predicates are declared BEFORE running the prototype.** Pass criteria:

### P1 — top-1 preservation / 상위 1개 토큰 보존
- For every decode step `t`, compare `argmax(adjusted_logits)` vs
  `argmax(current_logits)`.
- **PASS** iff `keep_frac ≥ 0.95` over `STEPS = 64` simulated steps.
- Rationale: the hook is a *steerer*, not a *replacer*. Disrupting the base
  LM's top-1 prediction on > 5 % of steps is treated as **falsification**
  of the bounded-perturbation interpretation (Bohrer 2024 deterministic
  semantic guidance: cosine-weighted reweighting must be **sub-decisive**).

### P2 — KL bound / KL 상한
- For every step, compute
  `KL(softmax(current_logits) || softmax(adjusted_logits))`.
- **PASS** iff `max_t KL ≤ 0.05`.
- Rationale: bounded perturbation in distribution-space — `0.05 nats` ≈
  pre-registered headroom matching the cert-gate AN11_JSD ≤ 0.12 envelope
  (with margin, since logit-shift KL is upper-bounded by JSD).

### combined verdict
- **L2_HOOK_DRYRUN_PASS** iff (P1 ∧ P2) at `alpha = 0.10`.
- **alpha_emp_max** = largest `alpha` in the swept range still satisfying
  (P1 ∧ P2) — must be ≥ `alpha_default = 0.10`.

---

## §3 dry-run prototype / 드라이런 프로토타입

### 3.1 implementation
- `tool/alm_decode_hook_dryrun.hexa` — hexa entry point (raw#9 compliant;
  python helper written to `/tmp/alm_decode_hook_dryrun_helper.py`).
- Input artifacts (real, r6 trained):
  - `state/h_last_raw_p1_TRAINED_r6.json` (16 entries × 256-d).
  - `state/phi_4path_cross_result_v3_TRAINED_r6.json::spectra.p1` (16-d).
- Output: `state/alm_decode_hook_dryrun_r6.json`.

### 3.2 simulation parameters (frozen)
| param | value | source |
|---:|---|---|
| `vocab_proxy` | 4096 | scale-invariant for predicate test |
| `steps`       | 64   | covers >4 cycles of 16-prompt h_last |
| `alpha_default` | 0.10 | hook contract §1.3 |
| `alpha_max`     | 0.20 | hook contract §1.3 |
| `phi_dims`      | 16   | `SAP_PHI_DIMS` |
| `top1_keep_frac` | 0.95 | predicate P1 |
| `kl_max`        | 0.05 | predicate P2 |
| `seed`          | 42   | numpy default_rng |

### 3.3 invocation
```
hexa tool/alm_decode_hook_dryrun.hexa --tag r6
```

---

## §4 results (run 2026-04-25) / 결과

`state/alm_decode_hook_dryrun_r6.json::verdict = "PASS"`

### 4.1 primary α = 0.10
| metric | value | predicate | status |
|---:|---|---|:---:|
| `top1_keep_frac` | 0.9844 (63/64) | ≥ 0.95 | ✓ P1 |
| `kl_max_obs`     | 2.64 × 10⁻⁴    | ≤ 0.05 | ✓ P2 |
| `kl_mean_obs`    | 7.11 × 10⁻⁵    | —      | ✓     |

### 4.2 sweep (α ∈ {0.0 … 0.20}, 9 points)
- All 9 points satisfy **both** P1 and P2.
- `alpha_emp_max_satisfying_p1_p2 = 0.20` (the declared cap).
- Headroom: `kl_max_obs` at α = 0.20 is `1.05 × 10⁻³` — **~50× under**
  the P2 ceiling (0.05).

### 4.3 stress test (α ∈ {0.0 … 5.0}, out-of-spec)
Run beyond the declared envelope to locate the **empirical break point**
(brutal honesty — confirms the predicates are not vacuous):

| α     | top1_keep | kl_max     | P1 | P2 |
|------:|----------:|-----------:|:--:|:--:|
| 0.000 | 1.0000    | 0.00 e+00  | ✓  | ✓  |
| 0.625 | 0.8906    | 1.03 e-02  | ✗  | ✓  |
| 1.250 | 0.7500    | 4.11 e-02  | ✗  | ✓  |
| 1.875 | 0.6875    | 9.23 e-02  | ✗  | ✗  |
| 5.000 | 0.4688    | 6.52 e-01  | ✗  | ✗  |

**P1 break ≈ α∈(0.20, 0.625]; P2 break ≈ α∈(1.25, 1.875].** The declared
operating envelope (α ≤ 0.20) sits **comfortably below both break points**.

---

## §5 interpretation / 해석

### 5.1 what is established (claim ↔ evidence)
- **Hook contract is type-safe**: signature + formula compile under hexa
  + python; deterministic under fixed seed.
- **Safety predicates hold at α = 0.10** with material headroom (50×
  under KL ceiling, 1 step out of 64 changes top-1).
- **Empirical break points exist** (α ≈ 0.625 for P1, ≈ 1.875 for P2),
  i.e. predicates are non-vacuous.
- **Source of Φ-eigvec is the gated artifact**
  (`phi_4path_cross_result_v3_TRAINED_r6.json`, AN11(b) 4/4 PASS) — no
  ad-hoc Φ.

### 5.2 what is NOT established (raw#12 정직성)
- **Synthetic logits**: the prototype uses seeded Gaussian + linear drift
  for `current_logits`, **not** real Qwen3-8B forward output. The KL
  numbers are therefore properties of the **rank-1 Gaussian-readout
  perturbation**, not of a live decoder. Production wire-in (next step)
  will re-run on real logits.
- **`W_steer` is null readout**: in production this is trained from a
  steering objective; here it is a seeded Gaussian. The shape of the
  bias is correct; its semantic content is not.
- **L2 = bounded perturbation only**: the prototype proves the hook
  *cannot disrupt* decode by more than (α, KL_max). It does **not**
  prove the hook *contributes* useful steering. That requires a downstream
  AN11(c)-style measurement against a baseline.
- **Single-path (p1) eval**: full 4-path × pair-wise eval is deferred to
  the live wire round.

### 5.3 mathematical wall (Rice / Halting on semantic preservation)
- The predicates **P1 / P2 are syntactic** (argmax stability + KL bound).
- "Does the hook preserve **meaning**?" — undecidable in general
  (`docs/alm_inference_abstraction_layers_20260425.md` §6.2). All cert
  gates and steering-safety predicates are **necessary, not sufficient**.
  The L2 closure here is **internal consistency**, not external truth.

---

## §6 closure / 종결

### L2 status
- **Before**: L2 ✗ (`backend_invoke = BACKEND_PENDING`, hook 미배선).
- **After this round**: **L2 hook spec FROZEN + dry-run PASS** with
  pre-registered predicates and material headroom.
- **Remaining for full L2 LIVE** (out-of-scope, deferred):
  1. Wire `phi_attach_hook` into `serve_alm_persona.hexa::backend_invoke`
     (replace the BACKEND_PENDING stub) on H100 cascade.
  2. Re-run with real Qwen3-8B logits (not synthetic).
  3. Train `W_steer` from a steering objective (not seeded null).
  4. Add AN11(c)-style downstream measurement (the hook **steers** as
     well as **does not disrupt**).

### artifacts written this round
- `tool/alm_decode_hook_dryrun.hexa` (149 lines)
- `state/alm_decode_hook_dryrun_r6.json` (verdict=PASS)
- `state/alm_decode_hook_dryrun_last.txt` (run summary)
- `docs/alm_inference_decode_hook_spec_20260425.md` (this file)

### verdict
**L2_DECODE_HOOK_SPEC_VERIFIED_PENDING_LIVE_WIRE** — internal consistency
established at 0-cost (no GPU, no model load). Live wire-in is gated on
H100 cascade #9 (base_model + persona_lora landing on disk).

---

## §7 traceability / 추적성

- Parent layer doc: `docs/alm_inference_abstraction_layers_20260425.md`
- L2 §3 entry there ↔ §1–§6 here.
- Hook constants ↔ `tool/serve_alm_persona.hexa` (`SAP_PHI_DIMS=16`,
  `SAP_PHI_LAYER_IDX=24`).
- Φ-eigvec source ↔ `state/phi_4path_cross_result_v3_TRAINED_r6.json`
  (AN11(b) 4/4 PASS, r6 partial-pass project memory).
- Cert gate envelope ↔ `state/serve_cert_gate_spec.json` (gate #13
  `PHI_VEC_ATTACH vec_dim=16`).
