"""DD: AnimaLM 7B PureField — 16-lens full scan

PureField injects consciousness into Mistral 7B via gate+up+down A/B weight pairs
at layers 24-31 (8 MLP layers). This scan analyses those weights with all 16 lenses.
"""
import sys, os
import torch
import numpy as np

sys.path.insert(0, os.path.expanduser("~/Dev/TECS-L/.shared"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from telescope import Telescope

# ── Load checkpoint ──────────────────────────────────────────────────────────
ckpt_path = os.path.join(os.path.dirname(__file__), "..", "checkpoints", "animalm_7b_final.pt")
print(f"Loading checkpoint: {ckpt_path}")
ckpt = torch.load(ckpt_path, map_location="cpu", weights_only=False)

print(f"  step: {ckpt.get('step')}")
print(f"  best_phi: {ckpt.get('best_phi')}")
cv = ckpt.get("consciousness_vector", {})
if cv:
    print(f"  consciousness_vector: { {k: round(float(v), 4) for k, v in cv.items()} }")

# ── Extract PureField weights ─────────────────────────────────────────────────
pf_states = ckpt.get("pf_states", {})
pf_weights = []
pf_names = []
weight_keys = ["pf_gate_a.weight", "pf_gate_b.weight",
               "pf_up_a.weight",   "pf_up_b.weight",
               "pf_down_a.weight", "pf_down_b.weight"]

for layer_name, layer_dict in pf_states.items():
    for wk in weight_keys:
        if wk in layer_dict:
            t = layer_dict[wk]
            if isinstance(t, torch.Tensor) and t.ndim >= 2:
                # Use first 512 features to keep data manageable
                flat = t.float().numpy().flatten()[:512]
                pf_weights.append(flat)
                pf_names.append(f"{layer_name}/{wk}")

# Fallback: thalamic bridge
if not pf_weights:
    print("pf_states empty — falling back to thalamic_bridge_state")
    tb = ckpt.get("thalamic_bridge_state", {})
    for k, v in tb.items():
        if isinstance(v, torch.Tensor) and v.ndim >= 2:
            pf_weights.append(v.float().numpy().flatten()[:512])
            pf_names.append(f"thalamic/{k}")

print(f"\nExtracted {len(pf_weights)} PureField weight tensors")
print(f"  layers: {list({n.split('/')[0] for n in pf_names})}")
print(f"  weight types: {list({n.split('/')[1] for n in pf_names})}")

# ── Build data matrix ─────────────────────────────────────────────────────────
max_len = max(len(w) for w in pf_weights)
data = np.zeros((len(pf_weights), max_len))
for i, w in enumerate(pf_weights):
    data[i, :len(w)] = w

print(f"\nData matrix: {data.shape}  (rows=weight_tensors, cols=features)")
print(f"  value range: [{data.min():.4f}, {data.max():.4f}]")
print(f"  mean={data.mean():.4f}  std={data.std():.4f}")

# ── 16-lens full scan ─────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("  16-LENS FULL SCAN")
print("=" * 60)
t = Telescope(verbose=True)
result = t.full_scan(data)

print("\n" + "=" * 60)
print("  FULL SCAN RESULT SUMMARY")
print("=" * 60)
print(result.summary)

if result.cross_findings:
    print(f"\nCross-lens findings ({len(result.cross_findings)}):")
    for cf in result.cross_findings[:10]:
        print(f"  {cf}")

# ── Measure preset (5 new measurement lenses) ─────────────────────────────────
print("\n" + "=" * 60)
print("  MEASURE PRESET (ruler / triangle / compass / mirror / scale)")
print("=" * 60)
measure = t.scan(data, lenses="measure")
print(measure.summary)
if measure.cross_findings:
    print(f"\nMeasure cross-findings ({len(measure.cross_findings)}):")
    for cf in measure.cross_findings[:5]:
        print(f"  {cf}")

# ── Causal preset ─────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("  CAUSAL PRESET (causal / consciousness / info / quantum_micro)")
print("=" * 60)
causal = t.scan(data, lenses="causal")
print(causal.summary)
if causal.cross_findings:
    print(f"\nCausal cross-findings ({len(causal.cross_findings)}):")
    for cf in causal.cross_findings[:5]:
        print(f"  {cf}")

# ── Discovery preset ──────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("  DISCOVERY PRESET (consciousness / info / quantum / topology)")
print("=" * 60)
discovery = t.scan(data, lenses="discovery")
print(discovery.summary)

# ── Done ──────────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("  DONE — 16-lens scan complete")
total_lenses = len(result.combo)
total_cross = len(result.cross_findings)
print(f"  Lenses active: {total_lenses}/16")
print(f"  Cross-findings: {total_cross}")
print("=" * 60)
