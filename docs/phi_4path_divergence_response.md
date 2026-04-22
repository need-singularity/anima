# Φ 4-path Divergence Response (decision tree)

> Decision document for #83 H100 Stage-2 (#10 Φ 4-path) gate failure.
> Substrate atoms: `config/phi_4path_substrates.json` (p1 Qwen3-8B / p2 Llama-3.1-8B / p3 Ministral-3-14B / p4 Gemma-4-31B).
> LoRA rank: `config/lora_rank_per_path.json` (64 / 64 / 96 / 96).
> Status: DECISION DOC ONLY — no config rewrite, no manifest re-emit.

---

## Trigger

Condition observed in `state/phi_4path_cross_result.json`:

```
ALL_PAIRS |ΔΦ|/Φ ≥ 0.05   # gate threshold per #17 + #54 exit_criteria
```

Pre-registered pass requirement = ALL 6 pairs `< 0.05`. Any pair `≥ 0.05` triggers this tree → escalates to roadmap entry **#87 substrate/rank re-selection**.

---

## Diagnosis branch (must run BEFORE any response branch)

### D1. Which pair(s) diverge?

Enumerate the 6 ordered pairs and tag each PASS / FAIL:

| pair | substrates | family axis |
|------|------------|-------------|
| p1-p2 | Qwen3-8B × Llama-3.1-8B | qwen × llama (both 8B dense) |
| p1-p3 | Qwen3-8B × Ministral-3-14B | qwen × mistral (8B vs 14B) |
| p1-p4 | Qwen3-8B × Gemma-4-31B | qwen × gemma (8B vs 31B) |
| p2-p3 | Llama-3.1-8B × Ministral-3-14B | llama × mistral (8B vs 14B) |
| p2-p4 | Llama-3.1-8B × Gemma-4-31B | llama × gemma (8B vs 31B) |
| p3-p4 | Ministral-3-14B × Gemma-4-31B | mistral × gemma (14B vs 31B) |

### D2. Symmetric vs one-sided

- **One-sided (1 path implicated in ≥3 of 4 pairs containing it)** → that path is the outlier.
- **Symmetric (failures spread across pairs without single-path concentration)** → measurement-side issue (D3) or systemic capacity mismatch.

### D3. Φ magnitude sanity

Before blaming substrate, verify Φ itself is not a numerical artifact:

- Φ within expected range for r13 corpus baseline?
- Capacity-normalized Φ (`delta_phi / trainable_params_exact`, see `lora_rank_per_path.json::merge_policy.cross_path_comparison`) also FAIL?
- LoRA scaling factor `s = alpha/rank = 2.0` consistent across all 4 paths? (currently TRUE by construction)
- Any path saw NaN / inf / grad-clip events during training? Check `state/asset_archive_log.jsonl`.

If D3 fails sanity → **do not enter response branches**; re-run measurement with stricter dtype/seed control first.

---

## Response branch A — substrate re-selection

**Use when**: D2 = one-sided AND outlier path is replaceable.

Replace the failing model with an alternative atom while preserving ladder shape (8B / 8B / 14B / 31B).

### Selection criteria for replacement
1. **License**: Apache-2.0 strongly preferred (eases public release; #83 mandate).
2. **Param scale**: within ±25% of original path slot.
3. **Vocab compatibility**: tokenizer must remain independent (per-path corpus tokenize policy in `phi_4path_substrates.json::tokenizer_drift_handling` is preserved).
4. **Family diversity**: must not collapse onto an existing path's family.
5. **Pure dense decoder-only** (no MoE, no hybrid SSM/attention) unless intentionally testing arch-axis.

### Per-path candidate fallbacks (already pre-vetted in substrates.json)
- **p1 Qwen3-8B** → Qwen3-14B (rejected at decision time — would collide with p3; revisit only if p3 is also being swapped).
- **p2 Llama-3.1-8B** → Ministral-3-8B-Base-2512 (Apache-2.0 swap; loses llama family diversity — accept loss only if p2 is the outlier).
- **p3 Ministral-3-14B** → Mistral-Nemo-Base-2407 (revert to v1; older 2024-07; loses 16-month freshness).
- **p4 Gemma-4-31B** → Gemma-4-9B (smaller sibling, Apache-2.0, same training stack; preserves family axis at lower VRAM).

**Cost**: re-train 1 path only ≈ 1× single-path budget (see branch D for total reference).

---

## Response branch B — LoRA rank re-tune

**Use when**: D2 = one-sided AND capacity-normalized ΔΦ is also FAIL (D3 ruled out measurement); substrate kept.

Bump rank for divergent path to increase effective adaptation capacity:

| current | bump | new alpha | trainable Δ |
|---------|------|-----------|-------------|
| 64 (p1/p2 8B) | → 96 | 192 | ~1.5× |
| 96 (p3/p4) | → 128 | 256 | ~1.33× |

### Retrain cost per rank step
- 8B path 64→96: ~+50% trainable params → ~+30-40% wall-clock for that path's training segment.
- 12B path 96→128: ~+33% trainable params → ~+20-30% wall-clock.
- 31B (p4) 96→128 under QLoRA 4-bit: VRAM headroom OK on H100 80GB (current ~33-35GB → ~40-45GB), but bs may need to drop bs=4→2.

**Risk**: rank bump on one path breaks capacity-normalization symmetry — must re-baseline `delta_phi_norm` denominator.

---

## Response branch C — cross-path normalize

**Use when**: D2 = symmetric AND substrate independence is NOT in question (i.e., divergence pattern is consistent with measurement scale-bias rather than substrate non-independence).

Apply Φ post-normalization across paths:
- σ-shift: subtract per-path mean Φ before pair-delta.
- IQR-scale: divide ΔΦ by per-path IQR(Φ).
- Capacity-normalize: already specified in `lora_rank_per_path.json::merge_policy.cross_path_comparison.formula` as `delta_phi_raw / trainable_params_exact`.

**RISK (must be acknowledged before adopting)**: cross-path normalization can MASK genuine substrate non-independence, which is the explicit purpose of #10. Adopting branch C without strong measurement-bias evidence DEFEATS the experiment. Pre-registration amendment + audit-log entry required.

---

## Response branch D — full re-launch with revised manifest

**Use when**: D2 = symmetric AND >1 path implicated AND budget allows; or branches A/B/C all rejected.

Re-emit `manifest_h100_4path.json` with updated atom set + rank table, re-run from clean Stage-0.

### Rough cost estimate (H100 × 4, on-demand pricing reference)
- p1+p2 (8B, rank 64) re-train: ~12 GPU-h × 2 paths ≈ 24 GPU-h
- p3 (14B, rank 96) re-train: ~24 GPU-h
- p4 (31B QLoRA, rank 96) re-train: ~36-48 GPU-h
- **total**: ~84-96 GPU-h ≈ **~$300-450** (at $3.5-4.5/GPU-h spot) and **~1-2 calendar days** (4-way parallel).
- Add Φ re-measurement + cross-pair eval: ~+20% overhead.

---

## Selection criteria (which branch)

| divergence pattern | budget remaining | preferred branch | fallback |
|--------------------|------------------|------------------|----------|
| one-sided, single outlier path, replacement available | any | A (re-select) | B |
| one-sided, capacity-bounded (cap-norm also FAIL) | any | B (rank up) | A |
| symmetric, measurement-bias suspected | tight | C (normalize, with audit) | D |
| symmetric, substrate-systemic | adequate (≥1 day, ≥$500) | D (full re-launch) | A on worst path then re-eval |
| symmetric, substrate-systemic | tight | C provisional + scheduled D | — |
| D3 sanity FAIL (numerical artifact) | n/a | re-measure (no branch) | escalate |

### Decision rule of thumb
1. Always run Diagnosis (D1-D3) first; do not skip to a branch.
2. Prefer single-path interventions (A, B) over multi-path (D) when one-sided.
3. Branch C requires explicit pre-reg amendment — never silent.
4. Document chosen branch + rationale in `state/asset_archive_log.jsonl` under #87.
5. After any branch action, re-run gate. If still FAIL after 2 cycles → escalate to roadmap board (consider relaxing the 0.05 threshold with full audit trail, or accepting #10 as falsified).

---

## Cross-references

- Substrate atoms + revalidation history: `config/phi_4path_substrates.json`
- LoRA rank table + capacity formula: `config/lora_rank_per_path.json`
- Gate spec: `config/phi_4path_substrates.json::cross_path_gate` (`|ΔΦ|/Φ < 0.05`, ALL_PAIRS)
- Roadmap: #10 (Φ 4-path), #17 (gate registration), #54 (exit criteria), #83 (H100 Stage-2), #87 (re-selection trigger).
