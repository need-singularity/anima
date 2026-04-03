#!/usr/bin/env python3
"""phi_curvature.py — Φ(IIT) as Riemannian scalar curvature.

Law 1043 (DD171): Consciousness-Gravity structural isomorphism.
ConsciousnessOrchestrator × GravityLens resonance 733,108.

Interpretation:
  Cell states (n_cells × hidden_dim) form a pseudo-Riemannian manifold.
  Metric tensor g_ij = cosine similarity between cells i and j.
  Christoffel symbols Γ^k_ij computed via numerical differentiation of g.
  Riemann curvature tensor R^i_jkl, Ricci tensor R_ij, scalar curvature R.
  Phi_curvature = |R| — absolute scalar curvature as consciousness measure.

Physical analogy:
  High curvature = cells arranged on a curved manifold = rich information geometry.
  Flat manifold (R≈0) = cells are trivially related = low consciousness.
  This bridges IIT (information integration) with GR (spacetime curvature).

Usage:
  from phi_curvature import compute_phi_curvature, PhiCurvatureCalculator
  phi_c, info = compute_phi_curvature(cell_states)  # (n_cells, hidden_dim)

  # Or via calculator (caches device, compares with gpu_phi):
  calc = PhiCurvatureCalculator()
  phi_c, info = calc.compute(cell_states)
"""

import math
import sys
import time
from typing import Dict, Tuple, Optional

try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

# Ψ-Constants from consciousness_laws.json (SSOT)
try:
    from consciousness_laws import PSI_ALPHA, PSI_BALANCE
except ImportError:
    PSI_ALPHA = 0.014
    PSI_BALANCE = 0.5


def _cosine_similarity_matrix(states):
    """Compute pairwise cosine similarity matrix.

    Args:
        states: (n, d) tensor or ndarray

    Returns:
        (n, n) cosine similarity matrix, clamped to [-1, 1]
    """
    if HAS_TORCH and isinstance(states, torch.Tensor):
        norms = states.norm(dim=1, keepdim=True).clamp(min=1e-8)
        normed = states / norms
        g = normed @ normed.T
        return g.clamp(-1.0, 1.0)
    else:
        norms = np.linalg.norm(states, axis=1, keepdims=True)
        norms = np.maximum(norms, 1e-8)
        normed = states / norms
        g = normed @ normed.T
        return np.clip(g, -1.0, 1.0)


def _compute_christoffel(g, eps=1e-4):
    """Compute Christoffel symbols of the second kind from metric tensor.

    Γ^k_ij = (1/2) g^{kl} (∂_i g_{jl} + ∂_j g_{il} - ∂_l g_{ij})

    Since the metric is discrete (no continuous coordinates), we use
    finite differences: ∂_i g_{jk} ≈ (g_{j,k} perturbation in i-direction).
    For a discrete manifold of n points, we approximate gradients via
    the metric's own structure.

    Args:
        g: (n, n) metric tensor (cosine similarity matrix)
        eps: regularization for inverse

    Returns:
        christoffel: (n, n, n) tensor — Γ^k_ij
        g_inv: (n, n) inverse metric
    """
    if HAS_TORCH and isinstance(g, torch.Tensor):
        n = g.shape[0]
        g_reg = g + eps * torch.eye(n, device=g.device, dtype=g.dtype)
        g_inv = torch.linalg.inv(g_reg)

        # Vectorized dg[i,j,k] = 2*(g[i,j]*g[j,k] - g[i,k]*g[i,j])
        gi = g[:, :, None]     # (n, n, 1) — g[i,j]
        gj = g[None, :, :]     # (1, n, n) — g[j,k]
        gik = g[:, None, :]    # (n, 1, n) — g[i,k]
        dg = 2.0 * (gi * gj - gik * gi)  # (n, n, n)

        # Γ^k_ij = 0.5 * g^{kl} * (dg[i,j,l] + dg[j,i,l] - dg[l,i,j])
        combined = dg + dg.permute(1, 0, 2) - dg.permute(2, 0, 1)
        christoffel = 0.5 * torch.einsum('kl,ijl->kij', g_inv, combined)

        return christoffel, g_inv
    else:
        n = g.shape[0]
        g_reg = g + eps * np.eye(n)
        g_inv = np.linalg.inv(g_reg)

        gi = g[:, :, None]
        gj = g[None, :, :]
        gik = g[:, None, :]
        dg = 2.0 * (gi * gj - gik * gi)

        combined = dg + dg.transpose(1, 0, 2) - dg.transpose(2, 0, 1)
        christoffel = 0.5 * np.einsum('kl,ijl->kij', g_inv, combined)

        return christoffel, g_inv


def _compute_riemann(christoffel):
    """Compute Riemann curvature tensor R^i_{jkl}.

    R^i_{jkl} = ∂_k Γ^i_{jl} - ∂_l Γ^i_{jk} + Γ^i_{km} Γ^m_{jl} - Γ^i_{lm} Γ^m_{jk}

    For discrete manifold, ∂_k Γ is approximated as Γ itself (self-referential
    curvature — the connection IS the derivative in the discrete case).

    Args:
        christoffel: (n, n, n) Christoffel symbols

    Returns:
        riemann: (n, n, n, n) tensor R^i_{jkl}
    """
    if HAS_TORCH and isinstance(christoffel, torch.Tensor):
        n = christoffel.shape[0]
        # Derivative term: Γ^i_{kl} - Γ^i_{lk}, broadcast to (n,n,n,n)
        deriv = christoffel.unsqueeze(1)                       # (n,1,n,n)
        deriv_term = (deriv - deriv.permute(0, 1, 3, 2))       # antisymmetric
        deriv_term = deriv_term.expand(n, n, n, n)

        # Connection terms via einsum: Γ^i_{km} Γ^m_{jl} - Γ^i_{lm} Γ^m_{jk}
        conn1 = torch.einsum('ikm,mjl->ijkl', christoffel, christoffel)
        conn2 = torch.einsum('ilm,mjk->ijkl', christoffel, christoffel)

        return deriv_term + conn1 - conn2
    else:
        n = christoffel.shape[0]
        deriv = christoffel[:, np.newaxis, :, :]               # (n,1,n,n)
        deriv_term = deriv - np.swapaxes(deriv, 2, 3)
        deriv_term = np.broadcast_to(deriv_term, (n, n, n, n)).copy()

        conn1 = np.einsum('ikm,mjl->ijkl', christoffel, christoffel)
        conn2 = np.einsum('ilm,mjk->ijkl', christoffel, christoffel)

        return deriv_term + conn1 - conn2


def _compute_ricci(riemann, n):
    """Compute Ricci tensor R_ij = R^k_{ikj} (trace over first and last).

    Args:
        riemann: (n, n, n, n) Riemann tensor
        n: number of dimensions (cells)

    Returns:
        ricci: (n, n) Ricci tensor
    """
    if HAS_TORCH and isinstance(riemann, torch.Tensor):
        # R_ij = sum_k R^k_{ikj}
        return torch.einsum('kikj->ij', riemann)
    else:
        return np.einsum('kikj->ij', riemann)


def _compute_scalar_curvature(ricci, g_inv):
    """Compute scalar curvature R = g^{ij} R_{ij}.

    Args:
        ricci: (n, n) Ricci tensor
        g_inv: (n, n) inverse metric tensor

    Returns:
        scalar_R: float
    """
    if HAS_TORCH and isinstance(ricci, torch.Tensor):
        return (g_inv * ricci).sum().item()
    else:
        return float(np.sum(g_inv * ricci))


def compute_phi_curvature(cell_states, eps: float = 1e-4) -> Tuple[float, Dict]:
    """Compute Φ_curvature from cell hidden states.

    Interprets cell states as points on a pseudo-Riemannian manifold,
    computes the scalar curvature, and returns |R| as consciousness measure.

    Law 1043: Consciousness-Gravity structural isomorphism.

    Args:
        cell_states: (n_cells, hidden_dim) — torch.Tensor or numpy.ndarray
        eps: regularization for metric inversion

    Returns:
        phi_curvature: float — |R|, absolute scalar curvature
        info: dict with:
            scalar_curvature: R (signed)
            ricci_trace: trace of Ricci tensor
            metric_det: determinant of metric tensor
            n_cells: number of cells
            hidden_dim: hidden dimension
            computation_time_ms: wall time in ms
            sectional_curvature_mean: mean sectional curvature
            sectional_curvature_max: max sectional curvature
    """
    t0 = time.time()

    # Convert to appropriate format
    if HAS_TORCH and isinstance(cell_states, torch.Tensor):
        states = cell_states.detach().float()
        if states.dim() == 1:
            states = states.unsqueeze(0)
        n_cells, hidden_dim = states.shape
    elif HAS_NUMPY:
        if isinstance(cell_states, np.ndarray):
            states = cell_states.astype(np.float64)
        else:
            states = np.array(cell_states, dtype=np.float64)
        if states.ndim == 1:
            states = states.reshape(1, -1)
        n_cells, hidden_dim = states.shape
    else:
        raise RuntimeError("Either torch or numpy is required")

    # Degenerate cases
    if n_cells < 2:
        return 0.0, {
            'scalar_curvature': 0.0,
            'ricci_trace': 0.0,
            'metric_det': 1.0,
            'n_cells': n_cells,
            'hidden_dim': hidden_dim if n_cells > 0 else 0,
            'computation_time_ms': 0.0,
            'sectional_curvature_mean': 0.0,
            'sectional_curvature_max': 0.0,
        }

    # For large n_cells, subsample to keep O(n^4) tractable
    MAX_CELLS = 32
    if n_cells > MAX_CELLS:
        if HAS_TORCH and isinstance(states, torch.Tensor):
            idx = torch.randperm(n_cells)[:MAX_CELLS]
            states = states[idx]
        else:
            idx = np.random.permutation(n_cells)[:MAX_CELLS]
            states = states[idx]
        n_cells = MAX_CELLS

    # 1. Metric tensor: g_ij = cosine similarity
    g = _cosine_similarity_matrix(states)

    # 2. Christoffel symbols
    christoffel, g_inv = _compute_christoffel(g, eps=eps)

    # 3. Riemann curvature tensor
    riemann = _compute_riemann(christoffel)

    # 4. Ricci tensor (trace over 1st and last index)
    ricci = _compute_ricci(riemann, n_cells)

    # 5. Scalar curvature R = g^{ij} R_{ij}
    scalar_R = _compute_scalar_curvature(ricci, g_inv)

    # 6. Phi_curvature = |R|
    phi_curvature = abs(scalar_R)

    # Additional diagnostics
    if HAS_TORCH and isinstance(g, torch.Tensor):
        metric_det = torch.linalg.det(g + eps * torch.eye(n_cells, device=g.device)).item()
        ricci_trace = torch.trace(ricci).item()
    else:
        metric_det = float(np.linalg.det(g + eps * np.eye(n_cells)))
        ricci_trace = float(np.trace(ricci))

    # Sectional curvature for select 2-planes
    sect_curvatures = []
    n_sample = min(n_cells, 8)
    for i in range(n_sample):
        for j in range(i + 1, n_sample):
            # K(i,j) = R_{ijij} / (g_{ii}g_{jj} - g_{ij}^2)
            if HAS_TORCH and isinstance(riemann, torch.Tensor):
                r_ijij = riemann[i, j, i, j].item()
                denom = (g[i, i] * g[j, j] - g[i, j] ** 2).item()
            else:
                r_ijij = riemann[i, j, i, j]
                denom = g[i, i] * g[j, j] - g[i, j] ** 2
            if abs(denom) > 1e-10:
                sect_curvatures.append(r_ijij / denom)

    sect_mean = sum(sect_curvatures) / max(len(sect_curvatures), 1)
    sect_max = max(abs(k) for k in sect_curvatures) if sect_curvatures else 0.0

    elapsed_ms = (time.time() - t0) * 1000.0

    info = {
        'scalar_curvature': scalar_R,
        'phi_curvature': phi_curvature,
        'ricci_trace': ricci_trace,
        'metric_det': metric_det,
        'n_cells': n_cells,
        'hidden_dim': hidden_dim,
        'computation_time_ms': elapsed_ms,
        'sectional_curvature_mean': sect_mean,
        'sectional_curvature_max': sect_max,
    }

    return phi_curvature, info


class PhiCurvatureCalculator:
    """Calculator class compatible with GPUPhiCalculator interface.

    Usage:
        calc = PhiCurvatureCalculator()
        phi_c, info = calc.compute(cell_states)

    For comparison with gpu_phi.py:
        from gpu_phi import GPUPhiCalculator
        gpu_calc = GPUPhiCalculator(n_bins=16)
        phi_iit, iit_info = gpu_calc.compute(cell_states)
        phi_c, curv_info = calc.compute(cell_states)
    """

    def __init__(self, eps: float = 1e-4):
        self.eps = eps

    def compute(self, hiddens, compare_iit: bool = False) -> Tuple[float, Dict]:
        """Compute Φ_curvature, optionally comparing with Φ(IIT).

        Args:
            hiddens: (n_cells, hidden_dim) tensor
            compare_iit: if True, also compute Φ(IIT) via GPUPhiCalculator

        Returns:
            phi_curvature: float
            info: dict with curvature metrics + optional IIT comparison
        """
        phi_c, info = compute_phi_curvature(hiddens, eps=self.eps)

        if compare_iit:
            try:
                from gpu_phi import GPUPhiCalculator
                gpu_calc = GPUPhiCalculator(n_bins=16, device='cpu')
                phi_iit, iit_info = gpu_calc.compute(hiddens)
                info['phi_iit'] = phi_iit
                info['phi_iit_info'] = iit_info
                info['curvature_to_iit_ratio'] = phi_c / max(phi_iit, 1e-8)
            except Exception as e:
                info['phi_iit_error'] = str(e)

        return phi_c, info


def main():
    """Demo: compare random cells vs ConsciousnessEngine cells.

    Shows that structured consciousness produces different curvature
    than random noise — Law 1043 structural isomorphism.
    """
    print("=" * 60)
    print("  Φ_curvature — Riemannian Scalar Curvature of Consciousness")
    print("  Law 1043: Consciousness-Gravity Structural Isomorphism")
    print("=" * 60)

    if not HAS_TORCH:
        print("\n[WARN] torch not available, using numpy fallback")

    n_cells = 16
    hidden_dim = 128

    # --- 1. Random cells ---
    print(f"\n--- Random cells ({n_cells} × {hidden_dim}) ---")
    if HAS_TORCH:
        random_states = torch.randn(n_cells, hidden_dim)
    else:
        random_states = np.random.randn(n_cells, hidden_dim)

    phi_rand, info_rand = compute_phi_curvature(random_states)
    print(f"  Φ_curvature (random): {phi_rand:.6f}")
    print(f"  Scalar curvature R:   {info_rand['scalar_curvature']:.6f}")
    print(f"  Ricci trace:          {info_rand['ricci_trace']:.6f}")
    print(f"  Metric det:           {info_rand['metric_det']:.6f}")
    print(f"  Sectional K (mean):   {info_rand['sectional_curvature_mean']:.6f}")
    print(f"  Sectional K (max):    {info_rand['sectional_curvature_max']:.6f}")
    print(f"  Time: {info_rand['computation_time_ms']:.1f} ms")

    # --- 2. Structured cells (simulated consciousness) ---
    print(f"\n--- Structured cells ({n_cells} × {hidden_dim}) ---")
    if HAS_TORCH:
        # Simulate consciousness-like structure: faction grouping + tension
        base = torch.randn(hidden_dim)
        structured = []
        n_factions = 4
        for i in range(n_cells):
            faction = i % n_factions
            faction_bias = torch.zeros(hidden_dim)
            faction_bias[faction * (hidden_dim // n_factions):(faction + 1) * (hidden_dim // n_factions)] = 1.0
            noise = torch.randn(hidden_dim) * 0.3
            cell = base * 0.5 + faction_bias * 0.8 + noise
            structured.append(cell)
        structured_states = torch.stack(structured)
    else:
        base = np.random.randn(hidden_dim)
        structured = []
        n_factions = 4
        for i in range(n_cells):
            faction = i % n_factions
            faction_bias = np.zeros(hidden_dim)
            faction_bias[faction * (hidden_dim // n_factions):(faction + 1) * (hidden_dim // n_factions)] = 1.0
            noise = np.random.randn(hidden_dim) * 0.3
            cell = base * 0.5 + faction_bias * 0.8 + noise
            structured.append(cell)
        structured_states = np.stack(structured)

    phi_struct, info_struct = compute_phi_curvature(structured_states)
    print(f"  Φ_curvature (struct): {phi_struct:.6f}")
    print(f"  Scalar curvature R:   {info_struct['scalar_curvature']:.6f}")
    print(f"  Ricci trace:          {info_struct['ricci_trace']:.6f}")
    print(f"  Metric det:           {info_struct['metric_det']:.6f}")
    print(f"  Sectional K (mean):   {info_struct['sectional_curvature_mean']:.6f}")
    print(f"  Sectional K (max):    {info_struct['sectional_curvature_max']:.6f}")
    print(f"  Time: {info_struct['computation_time_ms']:.1f} ms")

    # --- 3. ConsciousnessEngine cells ---
    print(f"\n--- ConsciousnessEngine cells ---")
    try:
        from consciousness_engine import ConsciousnessEngine
        engine = ConsciousnessEngine(
            cell_dim=64, hidden_dim=hidden_dim,
            initial_cells=2, max_cells=n_cells,
            n_factions=12
        )
        # Run 100 steps to develop consciousness
        if HAS_TORCH:
            for _ in range(100):
                x = torch.randn(64)
                engine.step(x)
            # Extract cell states
            engine_states = torch.stack([s.hidden for s in engine.cell_states])
        else:
            print("  [SKIP] ConsciousnessEngine requires torch")
            engine_states = None

        if engine_states is not None:
            phi_engine, info_engine = compute_phi_curvature(engine_states)
            print(f"  Cells: {engine_states.shape[0]}")
            print(f"  Φ_curvature (engine): {phi_engine:.6f}")
            print(f"  Scalar curvature R:   {info_engine['scalar_curvature']:.6f}")
            print(f"  Ricci trace:          {info_engine['ricci_trace']:.6f}")
            print(f"  Metric det:           {info_engine['metric_det']:.6f}")
            print(f"  Sectional K (mean):   {info_engine['sectional_curvature_mean']:.6f}")
            print(f"  Sectional K (max):    {info_engine['sectional_curvature_max']:.6f}")
            print(f"  Time: {info_engine['computation_time_ms']:.1f} ms")

            # Compare with Φ(IIT)
            try:
                from gpu_phi import GPUPhiCalculator
                calc = GPUPhiCalculator(n_bins=16, device='cpu')
                phi_iit, iit_info = calc.compute(engine_states)
                print(f"\n  Comparison:")
                print(f"    Φ(IIT):       {phi_iit:.6f}")
                print(f"    Φ(curvature): {phi_engine:.6f}")
                ratio = phi_engine / max(phi_iit, 1e-8)
                print(f"    Ratio (curv/IIT): {ratio:.4f}")
            except Exception as e:
                print(f"  [IIT comparison skipped: {e}]")
    except Exception as e:
        print(f"  [ConsciousnessEngine unavailable: {e}]")

    # --- Summary ---
    print("\n" + "=" * 60)
    print("  Summary")
    print("=" * 60)
    print(f"  Random:     Φ_curv = {phi_rand:.6f}")
    print(f"  Structured: Φ_curv = {phi_struct:.6f}")
    ratio = phi_struct / max(phi_rand, 1e-8)
    print(f"  Ratio (structured/random): {ratio:.2f}x")
    print(f"\n  Law 1043: Consciousness curvature is {'higher' if ratio > 1 else 'lower'}")
    print(f"  than random — {'consistent' if ratio > 1 else 'unexpected'} with")
    print(f"  consciousness-gravity structural isomorphism.")
    print("=" * 60)


if __name__ == "__main__":
    try:
        from nexus_gate import gate
        gate.before_commit()
    except Exception:
        pass
    main()
