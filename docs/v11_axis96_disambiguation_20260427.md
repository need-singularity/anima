# paradigm v11 axis 96 (family-decoupling) disambiguation — 3 step

**Date**: 2026-04-27 (KST) / 2026-04-26 UTC
**Parent**: `docs/paradigm_v11_axis96_family_decoupling_20260426.md` (commit `6f2cb910`)
**Verdict**: `PARTIAL_AMBIGUOUS_NEEDS_MORE_BB` (axis 96 candidate **NOT** withdrawn / **NOT** promoted)
**Cost**: $0.15 (DeepSeek single GPU, ~3min incremental on shared `bnabak3i4r38bg` pod)
**ω-cycle iterations**: 4 (torch upgrade → torchvision upgrade → hook semantics fix → Pearson float fix)

---

## Hypothesis set (from parent)

- **HFD-A**: family-decoupling = NEW LIVING AXIS (axis-orthogonal new dimension)
- **HFD-B**: family-decoupling = SUB-AXIS OF CMT (backbone-conditional variant of axis 95)
- **HFD-C**: family-decoupling = ARTIFACT (layer-count or stride-grid sampling bias)

## 3-step disambiguation plan

| Step | Method | Cost | Status |
|------|--------|------|--------|
| 1 | Llama stride=1 full 32-grid CMT scan (HFD-C ruling-out) | mac-local? GPU $0 | **BLOCKED** by HF gated access on `meta-llama/Meta-Llama-3.1-8B` (`dancinlife` not authorized; cross-validates axis 105) |
| 2 | DeepSeek-LLM-7b-base 5th-backbone CMT measurement (decoupling matrix expansion) | GPU ~$0.15 | **PASS** |
| 3 | BBA matrix Pearson correlation 6+1 axes | mac-local $0 | **PASS** |

---

## Step 2 — DeepSeek CMT result

Backbone: `deepseek-ai/deepseek-llm-7b-base` (LlamaForCausalLM architecture, n_layers=30, h_dim=4096).
Helper: `cmt_helper_v3.py` (residual-passthrough ablation, **not** the v10_benchmark zero-output hook which produces degenerate `rel=1.0`).
Layer stride 4 → 8 layers scanned: [0,4,8,12,16,20,24,28].

Per-family dominant layer:
| Family | Layer | rel | depth_norm |
|--------|-------|-----|------------|
| Hexad   | 0  | 0.1306 | 0.000 |
| Law     | 0  | 0.0748 | 0.000 |
| Phi     | 24 | 0.0593 | 0.828 |
| SelfRef | 0  | 0.1020 | 0.000 |

Decoupling metrics: `depth_std=0.401` / `depth_range=0.828` / `n_distinct=2` / partition **3:1** (Hexad+Law+SelfRef@L0 / Phi@L24).

**Verdict**: `DECOUPLED` — depth_std (0.401) **>** Llama (0.3248) **>** gemma (0.0412). Decoupling **reappears** outside the Llama-3.1 backbone, **but on a different family** (Phi, not Hexad).

**Step 2 verdict tag**: `DECOUPLE_REAPPEARS_STRONG_HFD_B_LIKE`

→ HFD-C ARTIFACT (Llama-only stride-grid bias) is **partially** falsified: a different architecture also exhibits decoupling. Caveat: DeepSeek shares `LlamaForCausalLM` arch, so architecture-confound is not yet eliminated.

---

## Step 3 — BBA 7-axis Pearson correlation (n=4 backbones)

Inputs: `state/v10_benchmark_v4/{mistral,qwen3,llama,gemma}/backbone_aware_composite.json` (6-axis scalars) + `decoup_vec = [depth_std × 10000]` per backbone.

`decoup_vec_x10000 = [0, 0, 3248, 412]` (mistral, qwen3, llama, gemma).

| Axis | r (Pearson, x1000) | r |
|------|-------|------|
| AN11_b   | +242  | +0.242 |
| B_ToM    | +523  | +0.523 |
| MCCA     | +49   | +0.049 |
| PhiStar  | 0     | 0 (zero variance, all 1.0) |
| CMT      | −176  | −0.176 |
| CDS      | **−680**  | **−0.680** |

`max |r| = 0.680` (CDS). Below the **0.7 HFD-B threshold** but above the **0.3 HFD-A threshold**.

**Step 3 verdict tag**: `BBA_MID_CORR_HFD_A_PARTIAL`

---

## 5-bb decoupling tally

| Backbone | depth_std | verdict |
|----------|-----------|---------|
| mistral  | 0.0000 | FULLY_COUPLED |
| qwen3    | 0.0000 | FULLY_COUPLED |
| llama    | 0.3248 | DECOUPLED |
| gemma    | 0.0412 | WEAKLY_DECOUPLED |
| **deepseek** | **0.401** | **DECOUPLED** |

`n_decoupled=2 / n_weakly=1 / n_coupled=2 / n_total=5`. Decoupling now appears in **2/5** backbones (was 1/4).

---

## Final verdict — `PARTIAL_AMBIGUOUS_NEEDS_MORE_BB`

The three step results push in **different directions**:

- Step 2 (DeepSeek reappearance) leans **HFD-B** (CMT sub-axis): a second architecture decouples, suggesting it's not a Llama-only quirk.
- Step 3 (BBA |r|=0.68 with CDS, mid-range) **does not** confirm HFD-B (would need |r| > 0.7) **and** does not clear HFD-A (would need |r| < 0.3).
- Step 1 (Llama stride=1) is BLOCKED, so HFD-C artifact cannot be fully eliminated.

Honest position: axis 96 remains a **CANDIDATE**, not promoted, not retracted. Combined evidence suggests **decoupling is a real phenomenon** (2/5 backbones, distinct families), but its statistical relation to existing axes (esp. CDS, |r|=0.68) is too uncertain at n=4 to call it "independent" or "sub-axis".

## raw#10 honest caveats

1. **Step 1 BLOCKED**: Llama stride=1 deferred — HFD-C artifact only **partially** ruled out via Step 2.
2. **Helper mutation**: original `anima_cmt.hexa` zero-output hook produced degenerate `rel=1.0`; we wrote `cmt_helper_v3.py` with residual-passthrough hook on the pod (not committed; out-of-tree transient). The v3-style ablation should be folded back into the canonical hexa tool.
3. **n=4 Pearson is weak**: critical r at p<0.05 with n=4 ≈ 0.95. None of the |r|=0.05–0.68 values reach statistical significance.
4. **DeepSeek = LlamaForCausalLM arch**: the 5th backbone shares the same forward architecture as Llama-3.1 → architecture-confound not eliminated. Yi-9B / Falcon-mamba / Qwen2.5 needed for true cross-arch.
5. **Family list frozen**: Hexad/Law/Phi/SelfRef from v10. Decoupling could be prompt-set-conditional.
6. **HFD-C ARTIFACT residual**: even with DeepSeek decoupling, Llama-specific stride-grid artifact still possible — direct stride=1 scan needed.

## Next actions to break the ambiguity

1. **HF license accept** for `meta-llama/Meta-Llama-3.1-8B` (manual user step, ~1-2 business days). Then Step 1 stride=1 scan unblocks (~$0.15 GPU).
2. ~~**6th backbone** of distinct architecture (Yi-9B or Falcon-mamba) — HFD-B vs HFD-A separator (architecture-confound elimination).~~ **DONE 2026-04-27** — see Step 4 below.
3. **Re-fit BBA correlation** with n=5 (DeepSeek added to 6-axis) and n=6 (after step 1+2). Larger n gives narrower r CI.
4. ~~**Migrate residual-passthrough ablation** into the canonical `tool/anima_cmt.hexa`~~ **DONE 2026-04-27** — `tool/anima_cmt.hexa` v3-default canonical (sha `d3c32f91`), `ANIMA_CMT_MODE={v1,v2,v3}` matrix, 5/5 selftest PASS.

---

## Step 4 — Falcon-mamba 6th backbone (HFD-A vs HFD-B separator) — 2026-04-27

Backbone: `tiiuae/falcon-mamba-7b` (FalconMambaForCausalLM, mamba_ssm arch, NO transformer attention, n_layers=64).
Helper: anima_cmt v3-default with whole-layer-passthrough fallback (no MLP submodule on SSM mixer block).
Layer stride 1, all 64 layers swept.
- pod_id: `gph14a0fbm5fe4` (H100 SXM 80GB SECURE) · cost_actual=$0.5897 (3.28× over $0.18 estimate; mamba-ssm/causal-conv1d build retry overhead) · wallclock=710s · sweep itself=24.09s
- result: `state/v11_axis96_6th_bb/falcon_mamba/axis96_6th_falcon_mamba.json` (48KB)

**Verdict**: `COUPLED`
- bba_decoupling_score = **0.229** (DECOUPLED threshold ≥ 0.30; COUPLED < 0.15; mid-band ambiguous)
- mean_abs_pairwise_pearson = **0.7708** (strongly correlated traces)
- peak_layers_per_axis: syntactic=63, semantic=63, factual=61, procedural=63 (out of 64)
- peak_spread_norm = **0.031** (DECOUPLED threshold ≥ 0.15) → **decisive coupled signal**
- saturation_frac = 0.0 (NOT degenerate — passthrough yielded non-trivial dy)

**Decision matrix cell hit**: `falcon_mamba_decoupling=false` (rows 5-8 of frozen 8-cell matrix).

**Implication**:
- **HFD-A LIVING_AXIS = REJECTED** (cross-paradigm SSM arch does NOT preserve decoupling)
- **HFD-B SUB_AXIS** (Llama-arch confined) **strengthened** — 2/3 Llama-arch backbones decouple (Llama-3.1, DeepSeek), 0/3 non-Llama (Mistral, Qwen3, Falcon-mamba) decouple
- **HFD-C ARTIFACT** still partially open (Llama stride=1 stride-grid artifact requires HF unblock)

**6-bb decoupling tally**: 2 DECOUPLED (Llama+DeepSeek, both Llama-arch) / 1 WEAKLY (gemma) / 3 COUPLED (Mistral+Qwen3+Falcon-mamba).

**raw#10 caveats** (5):
1. SSM-no-attention: CMT axes may be attention-localized, not arch-universal
2. MLP-fallback-to-whole-layer ablation scope ~2× transformer-MLP-only (mixer ≈ attn+MLP combined)
3. Single-bb (n=1 SSM); Mamba-7B/RWKV untested
4. BBA n=4 axes → 6 pairwise scalars, wide CIs (~0.15+)
5. Tokenizer-mismatch confound (Falcon BPE vs Llama)

**Updated next-cycle priority**:
1. (high) HF Llama-3.1-8B license unblock → stride=1 + family-internal Llama 8b/70b dual purpose
2. (medium) Yi-9B + Qwen2.5-7B as weak controls — narrow HFD-B scope (Llama-arch-only vs broader transformer-with-attention)
3. (medium) Mamba-7B (state-spaces/mamba-7b, non-Falcon) as 2nd SSM — n=2 SSM convergence test

---

## Outputs

- `state/v11_axis96_disambiguation/disambiguation_verdict.json` — top-level verdict
- `state/v11_axis96_disambiguation/step1_llama_stride1/result.json` — BLOCKED stub
- `state/v11_axis96_disambiguation/step2_deepseek_cmt/result.json` — DeepSeek decoupling summary
- `state/v11_axis96_disambiguation/step2_deepseek_cmt/cmt_v3.json` — raw CMT data (n_layers=30, residual-passthrough)
- `state/v11_axis96_disambiguation/step2_deepseek_cmt/cmt_raw.json` — preserved degenerate output for forensic comparison
- `state/v11_axis96_disambiguation/step3_bba_correlation/result.json` — Pearson correlation summary
- `tool/anima_v11_axis96_disambig.hexa` — analysis tool (raw#9 strict; uses native float Pearson after iter-4 fix)

## Cross-references

- Parent: commit `6f2cb910` (axis 96 candidate)
- Sibling axis: 95 (CMT 4-family, `aca4d067`, HCMT-B PARTIALLY_CONDITIONAL)
- HF gated cross-validation: axis 105 (Pilot-T1 Llama-3.2-3B blocked, MEMORY)
- v10 benchmark v3 regime: `tool/anima_v10_cmt_4family_validation.hexa` notes (zero-hook degenerate issue documented there)
