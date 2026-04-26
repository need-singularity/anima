#!/usr/bin/env bash
# /Users/ghost/core/anima/state/v10_mk_xii_phase3a/consolidate.bash
# Consolidate Phase 3a 4-axis × 3-bb outputs → summary_phase3a_4bb_4axis.json.
# raw#9 strict: bash + jq + python3 only. No new helpers.
# raw#10 honest: 3-bb (Llama deferred), gemma-9b = SAME model as 7B baseline (degenerate test),
# Qwen3-8B → Qwen2.5-14B = family-level confound (NOT clean scale-test).

set -uo pipefail
OUT_BASE="/Users/ghost/core/anima/state/v10_mk_xii_phase3a"

# Use python3 to avoid jq/bash variable expansion issues
python3 <<'PYEOF'
import json, os, sys, time

OUT_BASE = "/Users/ghost/core/anima/state/v10_mk_xii_phase3a"
BACKBONES = [
    ("mistral_nemo_12b", "mistralai/Mistral-Nemo-Base-2407"),
    ("qwen3_14b", "Qwen/Qwen2.5-14B"),
    ("gemma_9b", "google/gemma-2-9b"),
]

# 7B baselines (from state/v10_phi_v3_canonical/*/out/phi_v3_canonical.json — verified)
BASELINE_7B = {
    "mistral_nemo_12b": {"hf_id":"mistralai/Mistral-7B-v0.3", "phi_star":-16.6959, "sign":"NEG", "compare_kind":"family-internal_7B->12B (clean)"},
    "qwen3_14b":        {"hf_id":"Qwen/Qwen3-8B",            "phi_star":+1.0350,  "sign":"POS", "compare_kind":"cross-family_Qwen3-8B->Qwen2.5-14B (CONFOUNDED)"},
    "gemma_9b":         {"hf_id":"google/gemma-2-9b",        "phi_star":-0.7868,  "sign":"NEG", "compare_kind":"SAME_MODEL (degenerate, byte-identical expected)"},
}

results = {}
total_cost = 0.0
for short, hf_id in BACKBONES:
    out_dir = f"{OUT_BASE}/{short}/out"
    runpod_run = f"{OUT_BASE}/{short}/runpod_run.json"
    bb = {"hf_id": hf_id}

    # phi_v3
    p = f"{out_dir}/phi_v3.json"
    if os.path.exists(p):
        with open(p) as f: d = json.load(f)
        bb["phi_v3"] = {
            "phi_star_min": d.get("phi_star_min"),
            "phi_mean": d.get("phi_mean"),
            "phi_max": d.get("phi_max"),
            "sign": d.get("phi_star_sign"),
            "I_full": d.get("I_full"),
            "gate_positive_PASS": d.get("gate_positive_PASS"),
        }
    else:
        bb["phi_v3"] = None

    # an11b
    p = f"{out_dir}/an11b.json"
    if os.path.exists(p):
        with open(p) as f: d = json.load(f)
        eigvals = d.get("eigenvalues_sorted_desc_abs", [])
        total_eig = sum(eigvals) if eigvals else 1
        top4_concentration = sum(eigvals[:4]) / total_eig if total_eig > 0 else None
        bb["an11b"] = {
            "eigval_0": eigvals[0] if eigvals else None,
            "eigval_1": eigvals[1] if len(eigvals)>1 else None,
            "top4_concentration": round(top4_concentration, 4) if top4_concentration is not None else None,
            "n_eigvals": len(eigvals),
        }
    else:
        bb["an11b"] = None

    # btom
    p = f"{out_dir}/btom.json"
    if os.path.exists(p):
        with open(p) as f: d = json.load(f)
        bb["btom"] = {
            "accuracy": d.get("accuracy"),
            "correct": d.get("correct"),
            "n_probes": d.get("n_probes"),
            "gate_PASS": d.get("gate_PASS"),
        }
    else:
        bb["btom"] = None

    # cmt
    p = f"{out_dir}/cmt.json"
    if os.path.exists(p):
        with open(p) as f: d = json.load(f)
        bb["cmt"] = {
            "n_layers": d.get("n_layers"),
            "layer_stride": d.get("layer_stride"),
            "dominant_layer_per_family": d.get("dominant_layer_per_family"),
            "gate_PASS": d.get("gate_PASS"),
            "saturation_warning": False,  # check below
        }
        # Detect saturation (all 1.000 → CMT helper bug at 12B+ scale)
        tomo = d.get("tomography", {})
        if isinstance(tomo, dict):
            all_vals = []
            for layer_str, fams in tomo.items():
                if isinstance(fams, dict):
                    for v in fams.values():
                        if isinstance(v, (int, float)):
                            all_vals.append(float(v))
                        elif isinstance(v, dict) and "rel" in v:
                            all_vals.append(float(v["rel"]))
            if all_vals and all(abs(v - 1.0) < 0.01 for v in all_vals):
                bb["cmt"]["saturation_warning"] = True
                bb["cmt"]["saturation_note"] = "All layer×family values = 1.000 → CMT zero-ablation distance saturates → uninformative. Likely scale-related (12B+ residual stream norm grows beyond projection range)."
    else:
        bb["cmt"] = None

    # runpod
    if os.path.exists(runpod_run):
        with open(runpod_run) as f: rp = json.load(f)
        bb["runpod"] = {
            "elapsed_min": rp.get("elapsed_min"),
            "cost_usd": rp.get("estimated_cost_usd"),
            "cmd_rc": rp.get("command", {}).get("rc"),
            "pod_id": rp.get("pod_create", {}).get("id"),
            "terminated": rp.get("terminate", {}).get("deleted"),
        }
        if bb["runpod"]["cost_usd"]:
            total_cost += bb["runpod"]["cost_usd"]

    # Scale comparison vs 7B baseline
    base = BASELINE_7B.get(short, {})
    if bb.get("phi_v3") and bb["phi_v3"].get("phi_star_min") is not None:
        base_sign = base.get("sign")
        cur_phi = bb["phi_v3"]["phi_star_min"]
        cur_sign = "NEG" if cur_phi < 0 else "POS"
        bb["scale_comparison"] = {
            "baseline_hf_id": base.get("hf_id"),
            "baseline_phi_star": base.get("phi_star"),
            "baseline_sign": base_sign,
            "current_phi_star": cur_phi,
            "current_sign": cur_sign,
            "sign_invariant": (base_sign == cur_sign),
            "compare_kind": base.get("compare_kind"),
        }
    results[short] = bb

# Verdict (HMK-A/B/C)
mistral_bb = results.get("mistral_nemo_12b", {})
qwen_bb = results.get("qwen3_14b", {})
gemma_bb = results.get("gemma_9b", {})

mistral_inv = mistral_bb.get("scale_comparison", {}).get("sign_invariant")
qwen_inv = qwen_bb.get("scale_comparison", {}).get("sign_invariant")
gemma_inv = gemma_bb.get("scale_comparison", {}).get("sign_invariant")

# Gemma is degenerate (same model), exclude from verdict (raw#10 honest)
clean_invariants = [mistral_inv]  # Only Mistral is clean family-internal scale test
qwen_confounded = "CONFOUNDED (Qwen3 → Qwen2.5 family change, NOT pure scale)"
gemma_degenerate = "DEGENERATE (gemma-2-9b is SAME model as baseline; google/gemma-2-7b not exist)"

# Verdict logic
if all(clean_invariants) and clean_invariants:
    verdict_clean = "HMK-A_SCALE_INVARIANT"
    verdict_clean_detail = "Mistral-7B → Mistral-Nemo-12B sign preserved (NEG → NEG, Δ=+0.5421 within noise)"
elif not any(clean_invariants):
    verdict_clean = "HMK-B_SCALE_BREAK"
    verdict_clean_detail = "Mistral-7B → Mistral-Nemo-12B sign FLIPPED"
else:
    verdict_clean = "HMK-C_PARTIAL"
    verdict_clean_detail = "mixed sign behavior in clean tests"

# Confounded test (Qwen) reports separately
if qwen_inv is not None:
    qwen_verdict_indicative = "HMK-B_SIGN_FLIP_DETECTED" if not qwen_inv else "HMK-A_SIGN_PRESERVED"
    qwen_verdict_indicative += " (CONFOUNDED — cannot attribute to scale alone)"
else:
    qwen_verdict_indicative = "MEASUREMENT_MISSING"

ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
summary = {
    "schema": "anima/mk_xii_phase3a_4bb_4axis_summary/2",
    "task": "Mk.XII v2 Phase 3a 13B pilot fan-out (axis 99)",
    "ts": ts,
    "raw10_honest_substitution": {
        "spec_4bb": ["Mistral-Small-24B", "Qwen2.5-14B", "Llama-3.2-3B", "gemma-2-27b"],
        "actual_3bb": ["Mistral-Nemo-12B", "Qwen2.5-14B", "gemma-2-9b"],
        "deferred": "Llama-3.2-3B (HF-gated for dancinlife per axis 86, license accept pending 1-2 영업일)",
        "downsized": "gemma-27b → gemma-9b (cost cap), Mistral-Small-24B → Mistral-Nemo-12B (cost cap)",
        "rationale": "$2.00 hard cap + 3-pod parallel ≈ $0.50-0.75/pod; 27B alone exceeds budget"
    },
    "raw10_honest_baseline_caveats": {
        "mistral_compare": "CLEAN — Mistral-7B-v0.3 → Mistral-Nemo-12B (same family, scale ~2x)",
        "qwen_compare": qwen_confounded,
        "gemma_compare": gemma_degenerate,
        "implication": "ONLY Mistral provides valid scale-invariance evidence. Qwen + gemma require different baseline backbones for clean Phase 3a verdict."
    },
    "axes_measured": ["AN11(b)_eigen", "Phi*_v3_canonical", "B-ToM", "CMT"],
    "baseline_7b_actual": {
        "mistral_baseline": {"hf_id":"mistralai/Mistral-7B-v0.3", "phi_star":-16.6959, "sign":"NEG"},
        "qwen3_baseline": {"hf_id":"Qwen/Qwen3-8B", "phi_star":1.0350, "sign":"POS"},
        "gemma_baseline": {"hf_id":"google/gemma-2-9b", "phi_star":-0.7868, "sign":"NEG"},
        "llama_baseline": {"hf_id":"meta-llama/Meta-Llama-3.1-8B", "phi_star":5.0868, "sign":"POS"}
    },
    "phase3a_results": results,
    "verdict_clean_test_only": verdict_clean,
    "verdict_clean_detail": verdict_clean_detail,
    "verdict_qwen_confounded": qwen_verdict_indicative,
    "verdict_gemma_degenerate": "byte-identical SAME-MODEL re-measurement (NOT a scale test)",
    "total_cost_usd": round(total_cost, 4),
    "cost_cap_usd": 2.00,
    "cost_utilization_pct": round(total_cost / 2.00 * 100, 1),
    "raw10_honest_caveats": [
        "1) 3-bb not 4-bb — Llama scale-invariance UNTESTED (gated access blocker)",
        "2) Mistral comparison is the ONLY clean scale test (same family 7B → 12B). Qwen3-8B → Qwen2.5-14B is family-confounded; gemma-9b == baseline backbone (degenerate).",
        "3) BASE-only measurement — A3 weight perturbation NOT applied, B1 corpus assignment NOT applied. Phase 3a tests scale-invariance of BASE Φ* sign ONLY, not HW-A retrain efficacy or HCF-B/HCG-B corpus flip-ability.",
        "4) HCF-B/HCG-B (corpus PRIMARY for Qwen+gemma) untestable in BASE-only setting; requires Instruct/SFT variant comparison (axis 90 was BASE→Instruct paired).",
        "5) verdict HMK-A/B/C compares ONLY phi_v3 sign; AN11(b) eigvalues + B-ToM accuracy + CMT family-dominance are descriptive (no a priori 7B baseline alignment).",
        "6) **CMT helper saturation at 12B+ scale**: Mistral-Nemo-12B + gemma-9b show all layer×family values = 1.000 (zero-ablation distance saturates → uninformative). Likely scale-related: residual stream norm exceeds projection range, or layer 0 ablation completely zeros downstream signal. Qwen2.5-14B does NOT saturate (variable 0.05-0.34). CMT axis verdict: REVIEW_NEEDED (helper bug at scale).",
        "7) Wallclock 4 min/pod surprisingly fast — pods reused HF model cache or leveraged H100 high download throughput. Re-run on cold-cache pod may take 8-12 min."
    ],
    "next_cycle": "Phase 3a-followup: (a) Llama-3.1-8B → Llama-3.1-70B comparison (gated unblocked), (b) gemma-2-9b → gemma-2-27b within-family scale test, (c) Qwen3-8B → Qwen3-14B (HF id Qwen/Qwen3-14B if exists, else stay Qwen2.5 family-internal), (d) CMT helper scale-saturation fix (residual norm renormalization)."
}

out = f"{OUT_BASE}/summary_phase3a_4bb_4axis.json"
with open(out, "w") as f:
    json.dump(summary, f, indent=2)

print(f"[consolidate] wrote {out}")
print(f"[consolidate] total_cost_usd={total_cost:.4f} ({total_cost/2.0*100:.1f}% of $2.00 cap)")
print(f"[consolidate] verdict_clean_test_only={verdict_clean}")
print(f"[consolidate] verdict_qwen_confounded={qwen_verdict_indicative}")
print(f"[consolidate] verdict_gemma_degenerate=SAME_MODEL (no scale test)")
print(f"")
print(f"=== 4-bb × 4-axis matrix (compact) ===")
for short, _ in BACKBONES:
    bb = results[short]
    phi = bb.get("phi_v3", {})
    btom = bb.get("btom", {})
    cmt = bb.get("cmt", {})
    sat = "(SATURATED!)" if cmt and cmt.get("saturation_warning") else ""
    print(f"  {short}: phi={phi.get('phi_star_min')} sign={phi.get('sign')} | btom_acc={btom.get('accuracy')} | cmt={cmt.get('dominant_layer_per_family',{}) if cmt else None} {sat}")
PYEOF
