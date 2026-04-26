#!/usr/bin/env bash
# Consolidate Qwen family-internal scale test results.
# Inputs:
#   qwen25_7b/out/phi_v3_canonical.json (this cycle)
#   qwen3_14b/out/phi_v3_canonical.json (this cycle, Qwen3-14B-Base)
# Reused (disk):
#   Qwen2.5-14B  : state/v10_mk_xii_phase3a/qwen3_14b/out/phi_v3.json
#   Qwen3-8B     : state/v10_phi_v3_canonical/qwen3/out/phi_v3_canonical.json
set -uo pipefail

ANIMA="/Users/ghost/core/anima"
OUT="${ANIMA}/state/v10_mk_xii_qwen_family_internal"

Q25_7B="${OUT}/qwen25_7b/out/phi_v3_canonical.json"
Q3_14B="${OUT}/qwen3_14b/out/phi_v3_canonical.json"
Q25_14B="${ANIMA}/state/v10_mk_xii_phase3a/qwen3_14b/out/phi_v3.json"
Q3_8B="${ANIMA}/state/v10_phi_v3_canonical/qwen3/out/phi_v3_canonical.json"

for f in "$Q25_7B" "$Q3_14B" "$Q25_14B" "$Q3_8B"; do
  if [ ! -f "$f" ]; then
    echo "ERR: missing $f" >&2
    exit 1
  fi
done

# Use python3 for clean JSON aggregation
python3 - "$Q25_7B" "$Q3_14B" "$Q25_14B" "$Q3_8B" <<'PYEOF' > "${OUT}/summary_qwen_internal.json"
import json, sys, time
q25_7b_p, q3_14b_p, q25_14b_p, q3_8b_p = sys.argv[1:5]

def load(p):
    with open(p) as fh: return json.load(fh)

q25_7b  = load(q25_7b_p)
q3_14b  = load(q3_14b_p)
q25_14b = load(q25_14b_p)
q3_8b   = load(q3_8b_p)

def cell(d, hf_id):
    return {
      "hf_id": hf_id,
      "phi_star_min": d.get("phi_star_min"),
      "phi_mean": d.get("phi_mean"),
      "phi_max": d.get("phi_max"),
      "sign": "POS" if d.get("phi_star_min", 0) > 0 else "NEG",
      "I_full": d.get("I_full"),
    }

def sgn(x): return "POS" if x > 0 else "NEG"

m = {
  "qwen25_7b":  cell(q25_7b,  "Qwen/Qwen2.5-7B"),
  "qwen25_14b": cell(q25_14b, "Qwen/Qwen2.5-14B"),
  "qwen3_8b":   cell(q3_8b,   "Qwen/Qwen3-8B"),
  "qwen3_14b":  cell(q3_14b,  "Qwen/Qwen3-14B-Base"),
}

q25_inv = m["qwen25_7b"]["sign"] == m["qwen25_14b"]["sign"]
q3_inv  = m["qwen3_8b"]["sign"]  == m["qwen3_14b"]["sign"]

if q25_inv and q3_inv:
    verdict = "HQS-A_SCALE_INVARIANT_FAMILY_INTERNAL"
    detail  = "양 family scale 동일 sign — HMK-B sign FLIP 은 family-change artifact 확인"
elif (not q25_inv) and (not q3_inv):
    verdict = "HQS-B_SCALE_BREAK_REAL"
    detail  = "양 family 모두 scale break — HMK-B real, R46 BIMODAL 위협"
else:
    verdict = "HQS-C_MIXED_BACKBONE_CONDITIONAL"
    detail  = f"Qwen2.5 invariant={q25_inv} / Qwen3 invariant={q3_inv} — backbone-conditional fragility"

out = {
  "schema": "anima/mk_xii_qwen_family_internal_summary/1",
  "task": "Qwen family-internal scale test (axis 109, disentangle aa9a4de3 HMK-B)",
  "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
  "matrix": m,
  "qwen25_scale_invariant": q25_inv,
  "qwen3_scale_invariant":  q3_inv,
  "qwen25_delta_phi": round(m["qwen25_14b"]["phi_star_min"] - m["qwen25_7b"]["phi_star_min"], 4),
  "qwen3_delta_phi":  round(m["qwen3_14b"]["phi_star_min"]  - m["qwen3_8b"]["phi_star_min"],  4),
  "verdict": verdict,
  "detail":  detail,
  "raw10_honest": [
    "phi_v3_canonical ONLY — AN11(b)/B-ToM/CMT 미측정 (cost cap)",
    "Qwen3-14B-Base 는 Qwen3-14B family 의 base variant; instruct 와 다름",
    "Qwen2.5-14B BASE measurement reused from aa9a4de3 (state/v10_mk_xii_phase3a/qwen3_14b/out/phi_v3.json — 폴더명 'qwen3_14b' 는 misnomer, 실제 Qwen2.5-14B)",
    "BASE only; A3 perturbation / B1 corpus assignment 미적용",
    "Sign-only verdict; magnitude (Δphi) 는 descriptive — strict scale-invariance 는 magnitude 까지 보장 아님",
  ],
  "next_cycle_proposal": "Llama-3.1-8B → Llama-3.1-70B (axis 86 unblock 이후) + gemma-2-9b → gemma-2-27b 로 family-internal coverage 확장",
}
print(json.dumps(out, indent=2, ensure_ascii=False))
PYEOF

echo "[consolidate] DONE → ${OUT}/summary_qwen_internal.json"
cat "${OUT}/summary_qwen_internal.json" | python3 -m json.tool | head -80
