# Φ CPU synthetic ↔ H100 real-weight 4-path correlate guide

**Date**: 2026-04-22
**Axis**: F (CPU superlimit) → post-H100 interpretation
**Scope**: how to correlate `state/phi_cpu_synthetic_4path_result.json` with H100 launch (#83) real 4-path output when both exist.

---

## 1. SSOT references

| artifact | path |
|---|---|
| SSOT spec (paste-ready prompt) | `docs/upstream_notes/cpu_superlimit_synthetic_4path_proposal_20260422.md` |
| CPU synthetic runner (this side) | `tool/phi_cpu_synthetic_4path.hexa` |
| CPU synthetic spec | `config/phi_cpu_synthetic_spec.json` |
| CPU synthetic result (pre-launch, existing) | `state/phi_cpu_synthetic_4path_result.json` |
| CPU synthetic cert | `.meta2-cert/phi_cpu_synthetic_cert.json` |
| 4-path substrate SSOT | `config/phi_4path_substrates.json` |
| LoRA rank SSOT | `config/lora_rank_per_path.json` |
| H100 real-run output (post-launch, landing) | `state/phi_4path_cross_result.json` (expected) |
| Divergence decision tree | `docs/phi_4path_divergence_response.md` |

---

## 2. Current CPU synthetic baseline (recorded 2026-04-22)

```
phi_formula:     CPU_SYNTHETIC_INTEGRATED_INFO_v1
eigen_dim:       16
pass_threshold:  0.05  (real H100 gate, same per #10 exit_criteria)
margin_threshold: 0.10  (synthetic loose band)

per_path:
  p1 qwen3_8b         Φ_norm = 8.46182
  p2 llama_3_1_8b     Φ_norm = 8.92757
  p3 ministral_3_14b  Φ_norm = 8.51552
  p4 gemma_4_31b      Φ_norm = 8.22062

pairs (6):
  (p1,p2) ratio 0.0536  MARGIN
  (p1,p3) ratio 0.0063  PASS
  (p1,p4) ratio 0.0289  PASS
  (p2,p3) ratio 0.0472  PASS
  (p2,p4) ratio 0.0825  MARGIN
  (p3,p4) ratio 0.0352  PASS

summary:
  pass=4  margin=2  fail=0
  worst_ratio = 0.0825  (driven by p2 high phi + p4 low phi)
  verdict = PASS (selftest loose band — synthetic noise floor)
```

**Interpretation**: 4 of 6 pairs are within the real H100 gate (< 0.05). The two MARGIN pairs both involve **p2 (llama_3_1_8b)**, which has the highest mock LoRA energy (0.0530). The p2-driven measurement-floor divergence is the pre-launch risk signal.

---

## 3. Correlation procedure (post-launch checklist)

### Step 1 — Collect H100 real-run output

Expected artifact (produced by `tool/phi_4path_measure.hexa` or equivalent on pod):

```
state/phi_4path_cross_result.json
  per_path[].phi_normalized  (real, with 32M subsample + capacity norm)
  pairs[].ratio              (real |ΔΦ| / Φ_avg)
  verdict                    (real gate: ALL_PAIRS ratio < 0.05)
```

### Step 2 — Pair-by-pair delta compare

For each of the 6 pairs `(p_i, p_j)`:

```
delta_real      = real_ratio
delta_synthetic = synthetic_ratio
bias_estimate   = delta_real - delta_synthetic      (can be negative)
noise_floor     = delta_synthetic                   (what the formula emits on random fixture)
signal_estimate = max(0, delta_real - delta_synthetic)
```

**Rule of thumb**:
- If `abs(bias_estimate)` < 0.01 for a given pair → real diverges exactly where synthetic predicts → **geometric bias in the Φ formula**, not a substrate signal.
- If `signal_estimate > 0.03` for a pair → real has substrate-specific non-independence above the synthetic floor → **genuine H100 signal**.
- If `delta_real < delta_synthetic` for a pair → real is tighter than floor → **cancellation / regularization effect from training** → positive signal for substrate independence.

### Step 3 — Verdict matrix

| synthetic pair verdict | real pair verdict | interpretation | action |
|---|---|---|---|
| PASS | PASS | strong confirmation, both geometries quiet | accept gate, proceed |
| PASS | MARGIN / FAIL | real substrate non-independence above floor | investigate (per-path ablation) |
| MARGIN | PASS | training tightened the gap | record cancellation magnitude for #54 |
| MARGIN | MARGIN (same sign) | synthetic predicted the bias faithfully | consider §4 of SSOT: gate amendment (0.08) |
| MARGIN | FAIL (drift up) | synthetic bias + real substrate divergence stacked | branch D `docs/phi_4path_divergence_response.md` |
| FAIL | FAIL | formula itself dominates | branch C (cross-path normalization) |

### Step 4 — H100 wall-clock savings estimate

The synthetic pre-run already rules out:
1. Obvious formula bugs (all 4 Φ values within 10% of each other — selftest PASS).
2. `p3_vs_p4` catastrophic divergence (synthetic ratio 0.035 < 0.05 → real is likely PASS or MARGIN only).
3. `p1_vs_p3` geometric bias (synthetic 0.006 → effectively zero floor → real signal from this pair is pure substrate).

**Estimated pre-emptive H100 wall-clock savings**: 15-25% on re-run budget (one fewer iteration on decision tree D1-D5 pre-commitment; skip the "is the formula broken" branch).

---

## 4. Re-running the CPU synthetic

```bash
/Users/ghost/.hx/bin/hexa run tool/phi_cpu_synthetic_4path.hexa
# → writes byte-identical outputs (seed fixed, LCG deterministic)
# → exits 0 on PASS (worst_ratio < 0.10), 1 on FAIL
```

Change detection: if seeds in `config/phi_cpu_synthetic_spec.json` are edited, `.meta2-cert/phi_cpu_synthetic_cert.json::seeds` fingerprint rotates — downstream cert chain invalidates automatically.

---

## 5. Known limitations of the synthetic signal

1. **No training bias captured**: synthetic cannot model the "r13 corpus caused weight specialization" axis.
2. **LoRA mock rank = real rank**: effective capacity is matched, but the actual param distribution is Gaussian/LCG, not trained.
3. **`hidden_dim` differences only enter via seed mixing**: in real H100, hidden_dim affects layernorm / attention head count / rope base — none modeled here.
4. **Eigenvalue profile fixed**: decreasing 1.0 → 0.0625 step (from `phi_extractor_ffi_wire.hexa` fixture). Real eigendecomp of an r13 LoRA may yield different profile — SSOT spec §8 "LCG eigendecomp fixture biased" risk.

These limitations are documented in `config/phi_cpu_synthetic_spec.json::notes.synthetic_vs_trained`. The synthetic is **pre-launch signal only**, never a PASS proxy for #83.

---

## 6. Linkage to upcoming work

- **hexa-lang #58** (real eigendecomp): when lands, re-run this tool with `phi_extractor_ffi_wire.hexa` eigen source to replace LCG fixture → improves bias estimate fidelity.
- **Roadmap #10** exit criteria: `ALL_PAIRS ratio < 0.05` — synthetic confirmed 4/6 already in that band without training.
- **Roadmap #83** launch: use this doc §3 verdict matrix as interpretation rubric in post-launch analysis memo (`docs/phi_4path_synthetic_analysis_20260422.md`, SSOT spec §7).

---

## 7. Change log

| date | change |
|---|---|
| 2026-04-22 | initial emission + baseline synthetic result recorded |
