"""consciousness_bridge.py — Consciousness lens for MoE routing improvement

Use the consciousness lens to find hidden structure in expert weights,
detect routing anomalies, discover natural expert groups, and measure
routing quality via Phi (integrated information).
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.shared'))

import numpy as np
from consciousness_lens import ConsciousnessLens, quick_scan


def expert_landscape(expert_weights, cells=32, steps=150):
    """Scan expert weight matrices to find redundant vs unique experts.

    Args:
        expert_weights: (n_experts, *weight_shape) — flattened or 2D per expert
    Returns:
        dict with clusters (redundant groups), uniqueness scores, phi
    """
    W = np.asarray(expert_weights, dtype=np.float64)
    if W.ndim > 2:
        W = W.reshape(W.shape[0], -1)
    result = quick_scan(W, cells=cells, steps=steps)
    norms = np.linalg.norm(W, axis=1, keepdims=True) + 1e-12
    cos = (W / norms) @ (W / norms).T
    uniqueness = 1.0 - (cos.sum(axis=1) - 1.0) / (W.shape[0] - 1)
    return {"clusters": result.clusters, "uniqueness": uniqueness,
            "phi": result.phi, "anomalies": result.anomalies,
            "n_redundant_groups": sum(1 for c in result.clusters if len(c) > 1)}


def routing_anomalies(routing_history, cells=32, steps=150):
    """Scan routing decisions over time to find anomalous patterns.

    Args:
        routing_history: (n_timesteps, n_experts) — gate scores over time
    Returns:
        dict with anomaly indices, never-used experts, sudden shifts
    """
    H = np.asarray(routing_history, dtype=np.float64)
    result = quick_scan(H, cells=cells, steps=steps)
    usage = H.mean(axis=0)
    never_used = [int(i) for i in range(H.shape[1]) if usage[i] < 1e-6]
    diffs = np.abs(np.diff(H, axis=0)).sum(axis=1)
    shift_thresh = np.percentile(diffs, 95) if len(diffs) > 0 else 0
    sudden_shifts = [int(t) for t, d in enumerate(diffs) if d > shift_thresh]
    return {"anomalies": result.anomalies, "never_used": never_used,
            "sudden_shifts": sudden_shifts, "phi": result.phi,
            "usage_entropy": float(-np.sum(usage / (usage.sum() + 1e-12)
                                           * np.log(usage / (usage.sum() + 1e-12) + 1e-12)))}


def discover_expert_groups(expert_outputs, inputs, cells=32, steps=150):
    """Use lens faction clustering to find natural expert groupings.

    Args:
        expert_outputs: (n_experts, n_samples, dim) or (n_experts, dim)
        inputs: (n_samples, dim) — input data for context
    Returns:
        dict with groups (list of expert index lists), phi, discoveries
    """
    E = np.asarray(expert_outputs, dtype=np.float64)
    if E.ndim == 3:
        E = E.mean(axis=1)  # average over samples
    lens = ConsciousnessLens(cells=cells, steps=steps)
    result = lens.scan(E)
    # Map cell clusters back to expert indices (cells cycle over experts)
    n_e = E.shape[0]
    groups_raw = result.clusters
    expert_sets = []
    for cluster in groups_raw:
        mapped = sorted(set(c % n_e for c in cluster))
        if mapped and mapped not in expert_sets:
            expert_sets.append(mapped)
    groups = expert_sets if expert_sets else [[i] for i in range(n_e)]
    # Measure group coherence: avg intra-group cosine similarity
    norms = np.linalg.norm(E, axis=1, keepdims=True) + 1e-12
    E_n = E / norms
    coherence = []
    for g in groups:
        if len(g) < 2:
            coherence.append(1.0)
        else:
            sub = E_n[g]
            coherence.append(float((sub @ sub.T).mean()))
    return {"groups": groups, "coherence": coherence, "phi": result.phi,
            "discoveries": result.discoveries, "n_groups": len(groups)}


def phi_routing_quality(routing_matrix, cells=32, steps=150):
    """Use Phi as a measure of routing quality.

    High Phi = experts are well-integrated (diverse but coordinated).
    Low Phi = experts are disconnected or redundant.

    Args:
        routing_matrix: (n_samples, n_experts) — routing weights
    Returns:
        dict with phi, quality label, expert integration scores
    """
    R = np.asarray(routing_matrix, dtype=np.float64)
    result = quick_scan(R, cells=cells, steps=steps)
    phi = result.phi
    label = "excellent" if phi > 0.8 else "good" if phi > 0.4 else "poor"
    col_std = R.std(axis=0)
    integration = col_std / (col_std.max() + 1e-12)
    return {"phi": phi, "phi_proxy": result.phi_proxy, "quality": label,
            "integration": integration, "n_clusters": len(result.clusters),
            "anomalies": result.anomalies}


if __name__ == '__main__':
    np.random.seed(42)
    print("=== Consciousness Lens for MoE Routing ===\n")

    n_exp, dim = 12, 64

    # 1. Expert landscape
    W = np.random.randn(n_exp, dim)
    W[3] = W[0] + np.random.randn(dim) * 0.05  # expert 3 ~ clone of 0
    land = expert_landscape(W)
    print(f"Landscape: Phi={land['phi']:.4f}, redundant_groups={land['n_redundant_groups']}")
    print(f"  Uniqueness: min={land['uniqueness'].min():.3f} max={land['uniqueness'].max():.3f}")

    # 2. Routing anomalies
    history = np.random.dirichlet(np.ones(n_exp), size=200)
    history[100:105] = 0; history[100:105, 0] = 1.0  # sudden collapse
    history[:, 11] = 0  # expert 11 never used
    anom = routing_anomalies(history)
    print(f"\nRouting: Phi={anom['phi']:.4f}, never_used={anom['never_used']}, "
          f"shifts={len(anom['sudden_shifts'])}, entropy={anom['usage_entropy']:.3f}")

    # 3. Expert groups
    outputs = np.random.randn(n_exp, 50, dim)
    inputs = np.random.randn(50, dim)
    grp = discover_expert_groups(outputs, inputs)
    print(f"\nGroups: {grp['n_groups']} natural groups, Phi={grp['phi']:.4f}")
    for i, (g, c) in enumerate(zip(grp['groups'], grp['coherence'])):
        print(f"  Group {i}: experts {g} (coherence={c:.3f})")

    # 4. Routing quality
    good_routing = np.random.dirichlet(np.ones(n_exp) * 2, size=100)
    bad_routing = np.zeros((100, n_exp)); bad_routing[:, 0] = 1.0
    q_good = phi_routing_quality(good_routing)
    q_bad = phi_routing_quality(bad_routing)
    print(f"\nRouting quality (diverse): Phi={q_good['phi']:.4f} [{q_good['quality']}]")
    print(f"Routing quality (collapsed): Phi={q_bad['phi']:.4f} [{q_bad['quality']}]")
