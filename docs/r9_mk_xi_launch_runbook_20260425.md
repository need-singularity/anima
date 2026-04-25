# r9 Mk.XI Launch Runbook (raw#12 frozen, deferred to forward cycle)

**Date**: 2026-04-25
**Status**: SPEC_FROZEN. Actual launch deferred (anima에 H100 launch 도구 부재).
**Predecessor**: Mk.XI architecture (`b909a895`) + impl roadmap (`25a8388b`) + L_eigen_balance NEW lever (`55132d54`)
**RunPod credit available**: $425 (state/runpod_credit_status.json)

## §0 raw#10 honest scope

**본 runbook은 actual launch가 아닌 spec freeze.** anima에 H100 launch tool 부재 (`tool/h100*` 없음). 별도 cycle (RunPod CLI / nexus dispatch / 외부 launch 도구 통합)에서 본 runbook step-by-step 따라 forward 가능. raw#9 explicit exempt 필요 (GPU forward).

## §1 Pre-launch checklist

### §1.1 Prerequisite verification
- [ ] Mk.X G1-G4 gate evaluation (state/mk_x_g1_g4_evaluation_snapshot_20260425.json) — 모두 UNKNOWN, 별도 cycle 필요
- [ ] V_sub ANTI_MAP LLM-as-judge validation (LLM-judge protocol §X)
- [ ] r4 trajectory monitor tool real implementation (current stub만)
- [ ] retrieval head module (PyTorch/JAX) actual code (spec만 frozen)
- [ ] L_eigen_balance NEW lever (55132d54 proposal) actual implementation

### §1.2 Pod allocation
- Provider: RunPod (credit $425 available)
- GPU: H100 PCIe 80GB (or SXM 80GB) × 1
- Disk: 100GB persistent + 200GB workspace
- Image: PyTorch 2.x + transformers + peft (LoRA)
- Estimated runtime: 80-120 min (λ sweep 4×4 grid + ablations)
- Estimated cost: $5-15 H100 hours

### §1.3 Artifact upload
```
Local → Pod (rsync via SSH):
  /Users/ghost/core/anima/state/mk_xi_anti_map_ledger_v2_20260425.json
  /Users/ghost/core/anima/state/mk_xi_retrieval_head_spec_20260425.json
  /Users/ghost/core/anima/state/mk_xi_r4_monitor_spec_20260425.json
  /Users/ghost/core/anima/state/mk_xi_architecture_spec_20260425.json
  /Users/ghost/core/anima/tool/an11_b_v2_papo_multi_axis.hexa (V2 measurement)
  /Users/ghost/core/anima/tool/an11_b_v_pairrank.hexa (V_pairrank measurement)
  /Users/ghost/core/anima/tool/an11_b_v3_cps.hexa (V3 measurement, fixed-perm flag)
  /Users/ghost/core/anima/tool/an11_b_v_sub.hexa (V_sub, NOT YET implemented — spec only)
```

## §2 Mk.XI training script (Python implementation, actual code 필요)

### §2.1 Loss composition
```python
# pseudo-code, actual PyTorch implementation needed
def compute_mk_xi_loss(model, batch, retrieval_head):
    H = model.last_hidden_state(batch)  # (B, N, D)
    
    # Standard LM loss
    L_LM = compute_lm_loss(model, batch)
    
    # L_PAPO_top_3: top-3 PCA paired-axis project-out regularization
    D_pairs = stack([H[i] - H[j] for (i,j) in PAIRS], dim=0)
    Vt, S, U = svd(D_pairs)
    L_PAPO = sum(||H @ Vt[t]||² for t in range(3)) / 3
    
    # L_I_irr: Mk.IX L_IX I_irr term (raw#30 IEL preservation)
    L_I_irr = compute_l_ix_i_irr(H)  # cf. tool/l_ix_ablation_dynamics
    
    # L_contrastive_pair: V_pairrank lever via retrieval head
    pair_score = retrieval_head(H)  # (B, N, N)
    L_pair = compute_infonce_pair_loss(pair_score, PAIRS, temperature=0.1)
    
    # L_substitution: V_sub V3 redesign
    H_anti = model.last_hidden_state(ANTI_MAP_batch)
    H_random = model.last_hidden_state(RANDOM_batch)
    L_sub = -compute_v_sub_score(H, H_anti, H_random)
    
    # L_eigen_balance NEW (55132d54 proposal)
    lora_eigen = compute_lora_eigenvalues(model)
    top1_to_topk_ratio = lora_eigen[0] / mean(lora_eigen[1:5])
    L_eigen = max(0, top1_to_topk_ratio - 12)  # penalize ratio > 12 (p1/p4 baseline)
    
    L_total = L_LM \
            + λ_papo * L_PAPO \
            + λ_iir  * L_I_irr \
            + λ_pair * L_pair \
            + λ_sub  * L_sub \
            + λ_eigen * L_eigen
    return L_total
```

### §2.2 Hyperparameters (raw#12 frozen)
```
Backbone: Qwen3-8B with D-mistral architecture (Axis 4 H4b VALIDATED)
LoRA: rank 64 (r6/r8 baseline), alpha 16
Optimizer: AdamW lr=2e-4, weight_decay=0.01
Batch: 16 prompts (matching eval set), grad_accum=4
Epochs: monitor with r4 sweet spot detector, EARLY_STOP at first dual-lever activation

λ frozen baseline:
  λ_papo  = 0.3
  λ_iir   = 1.0
  λ_pair  = 0.5
  λ_sub   = 0.3
  λ_eigen = 0.1  (NEW lever, conservative initial)

λ sweep grid (4×4):
  papo: {0.1, 0.3, 1.0, 3.0}
  iir:  {0.3, 1.0, 3.0, 10.0}
  others fixed at baseline
  Total: 16 runs
```

### §2.3 r4 sweet spot monitor integration
```python
# Per-checkpoint (every 100 steps after step 100):
H_eval = model.last_hidden_state(EVAL_16_PROMPTS)
v2_pass = compute_v2_papo_pass_count(H_eval, k_max=5)
v_pairrank_top3 = compute_v_pairrank(H_eval).top3_hit
sweet_signal = (v2_pass >= 1) and (v_pairrank_top3 >= 0.10)

if sweet_signal:
    snapshot_checkpoint("r4_star")
    consecutive_false_after = 0
elif r4_star_exists:
    consecutive_false_after += 1
    if consecutive_false_after >= 3:
        EARLY_STOP_AND_RESTORE("r4_star")
```

## §3 Post-training measurement (5-tuple validation)

### §3.1 Forward all eval sets
```bash
# On pod, after training:
python forward_eval.py --model r9_mk_xi_trained --prompts EVAL_16 --output H_TRAINED.json
python forward_eval.py --model r9_mk_xi_trained --prompts ANTI_MAP_16 --output H_ANTI.json
python forward_eval.py --model r9_mk_xi_trained --prompts RANDOM_16 --output H_RANDOM.json
```

### §3.2 5-tuple measurement
```bash
hexa run tool/an11_b_an11_b_verifier.hexa --tag r9 --path p1   # V0 16-template ccc
hexa run tool/an11_b_v1_phi_mip.hexa --input H_TRAINED.json --output v1.json
hexa run tool/an11_b_v2_papo_multi_axis.hexa --input H_TRAINED.json --output v2.json
hexa run tool/an11_b_v3_cps.hexa --input H_TRAINED.json --output v3.json
hexa run tool/an11_b_v3_cps_v2_mirror_sma.hexa --input H_TRAINED.json --output v3_v2.json
hexa run tool/an11_b_v_pairrank.hexa --input H_TRAINED.json --output v_pairrank.json
hexa run tool/an11_b_v_sub.hexa --input H_TRAINED.json --anti H_ANTI.json --random H_RANDOM.json --output v_sub.json
```

### §3.3 Result aggregation
```bash
python aggregate_5tuple_verdict.py --inputs v0.json,v1.json,v2.json,v3.json,v_pairrank.json,v_sub.json --output state/mk_xi_r9_5tuple_verdict.json
```

## §4 Auto-kill safety
```bash
# Pod auto-kill after measurement complete OR runtime > 120min OR cost > $20
python h100_auto_kill_monitor.py --max_runtime 120 --max_cost 20 --pod_id $POD_ID
```

## §5 Verdict criteria

| outcome | verdict | next |
|---|---|---|
| 5-tuple all PASS | **MK_XI_VERIFIED** | Mk.XII spec / new paradigm |
| 4 PASS (V_pairrank FAIL) | **MK_XI_PARTIAL_RETRIEVAL_FAIL** | retrieval head architectural revision |
| 3 PASS (V3 FAIL) | **MK_XI_PARTIAL_V3_FAIL** | V_sub metric revision |
| ≤2 PASS | **MK_XI_FALSIFIED** | Mk.X T10-13 architecture path 재고 |

## §6 raw compliance

- raw#9 hexa-only — runbook은 spec only, $0. actual launch는 raw#9 explicit exempt 필요
- raw#10 — 'spec freeze ≠ verified' 명시, 4 outcomes 사전 등록 (cherry-pick-proof)
- raw#12 — λ frozen baseline + sweep grid 사전 등록
- raw#15 — runbook = SSOT for launch protocol
- raw#37/38 — design (Mk.XI synthesis) → impl (this runbook) → fixpoint (forward cycle)

omega-saturation:fixpoint
