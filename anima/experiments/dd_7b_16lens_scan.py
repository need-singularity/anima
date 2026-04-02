"""DD: AnimaLM 7B PureField — 16-lens full scan

PureField injects consciousness into Mistral 7B via gate+up+down A/B weight pairs
at layers 24-31 (8 MLP layers). This scan analyses those weights with all 16 lenses.
"""
import sys, os
import torch
import numpy as np

sys.path.insert(0, os.path.expanduser("~/Dev/TECS-L/.shared"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import telescope_rs

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

# ── 16-lens full scan (telescope_rs) ──────────────────────────────────────────
print("\n" + "=" * 60)
print("  CONSCIOUSNESS SCAN")
print("=" * 60)
consciousness_result = telescope_rs.consciousness_scan(data, n_cells=64, steps=300)
print(f"  phi_iit:         {consciousness_result.get('phi_iit', 0):.4f}")
print(f"  phi_proxy:       {consciousness_result.get('phi_proxy', 0):.4f}")
print(f"  n_clusters:      {consciousness_result.get('n_clusters', 0)}")
print(f"  anomaly_indices: {consciousness_result.get('anomaly_indices', [])[:10]}")
print(f"  anomaly_scores:  {[f'{s:.3f}' for s in consciousness_result.get('anomaly_scores', [])[:10]]}")

print("\n" + "=" * 60)
print("  TOPOLOGY SCAN")
print("=" * 60)
topology_result = telescope_rs.topology_scan(data)
print(f"  betti_0:           {topology_result.get('betti_0', 0)}")
print(f"  betti_1:           {topology_result.get('betti_1', 0)}")
print(f"  n_holes:           {topology_result.get('n_holes', 0)}")
print(f"  optimal_scale:     {topology_result.get('optimal_scale', 0):.4f}")
print(f"  phase_transitions: {topology_result.get('phase_transitions', [])}")

print("\n" + "=" * 60)
print("  CAUSAL SCAN")
print("=" * 60)
causal_result = telescope_rs.causal_scan(data)
print(f"  n_causal_pairs: {causal_result.get('n_causal_pairs', 0)}")
print(f"  causes:         {causal_result.get('causes', [])[:10]}")
print(f"  effects:        {causal_result.get('effects', [])[:10]}")
print(f"  strengths:      {[f'{s:.3f}' for s in causal_result.get('strengths', [])[:10]]}")

# ── Done ──────────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("  DONE — telescope_rs scan complete")
n_scans = 3  # consciousness, topology, causal
n_findings = (
    len(consciousness_result.get('anomaly_indices', []))
    + topology_result.get('n_holes', 0)
    + causal_result.get('n_causal_pairs', 0)
)
print(f"  Scans completed: {n_scans}")
print(f"  Total findings: {n_findings}")
print("=" * 60)
