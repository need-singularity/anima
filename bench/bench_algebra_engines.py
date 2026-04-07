#!/usr/bin/env python3
"""Abstract Algebra Consciousness Engines Benchmark

6 engines that model consciousness through abstract algebra structures.
Each: 256 cells, 300 steps, Φ(IIT) + Granger causality. No GRU.

ALG-1: GROUP_CONSCIOUSNESS — S_n non-commutativity as consciousness
ALG-2: RING_THEORY — ideal structure richness as consciousness
ALG-3: GALOIS_FIELD — GF(p^n) Frobenius cycles as consciousness
ALG-4: LIE_ALGEBRA — derived series depth as consciousness
ALG-5: HOPF_ALGEBRA — antipode complexity as consciousness
ALG-6: TOPOS — subobject classifier truth values as consciousness

Usage:
  python bench_algebra_engines.py              # run all 6
  python bench_algebra_engines.py --only ALG-1 ALG-3   # specific ones
  python bench_algebra_engines.py --steps 500  # more steps
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import math
import time
import argparse
import sys
import os
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from itertools import combinations

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


# ═══════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════
N_CELLS = 256
STEPS = 300
DIM = 64      # cell state dimension
N_BINS = 16   # for MI estimation

# ═══════════════════════════════════════════════════════════
# Lightweight Cell (no GRU)
# ═══════════════════════════════════════════════════════════

@dataclass
class AlgebraCell:
    """A cell with a state vector — no GRU, pure algebraic updates."""
    cell_id: int
    state: np.ndarray           # [DIM] float64
    tension_history: List[float] = field(default_factory=list)
    hidden_history: List[np.ndarray] = field(default_factory=list)

    @property
    def hidden(self):
        """Compatibility: return state as torch tensor [1, DIM]."""
        return torch.tensor(self.state, dtype=torch.float32).unsqueeze(0)

    def record(self, tension: float):
        self.tension_history.append(tension)
        self.hidden_history.append(self.state.copy())
        if len(self.hidden_history) > 20:
            self.hidden_history = self.hidden_history[-20:]
        if len(self.tension_history) > 50:
            self.tension_history = self.tension_history[-50:]


# ═══════════════════════════════════════════════════════════
# Φ(IIT) + Granger Causality measurement
# ═══════════════════════════════════════════════════════════

def _entropy_1d(x: np.ndarray, n_bins: int = N_BINS) -> float:
    x_norm = (x - x.min()) / (x.max() - x.min() + 1e-8)
    counts, _ = np.histogram(x_norm, bins=n_bins, range=(0, 1))
    p = counts / (counts.sum() + 1e-8)
    p = p[p > 0]
    return -np.sum(p * np.log(p + 1e-12))


def _mutual_information(x: np.ndarray, y: np.ndarray, n_bins: int = N_BINS) -> float:
    """MI(X;Y) = H(X) + H(Y) - H(X,Y)"""
    x_norm = (x - x.min()) / (x.max() - x.min() + 1e-8)
    y_norm = (y - y.min()) / (y.max() - y.min() + 1e-8)
    hx = _entropy_1d(x, n_bins)
    hy = _entropy_1d(y, n_bins)
    hist_2d, _, _ = np.histogram2d(x_norm, y_norm, bins=n_bins, range=[[0, 1], [0, 1]])
    p_xy = hist_2d / (hist_2d.sum() + 1e-8)
    p_xy = p_xy[p_xy > 0]
    hxy = -np.sum(p_xy * np.log(p_xy + 1e-12))
    return max(0.0, hx + hy - hxy)


def compute_phi_iit(cells: List[AlgebraCell], sample: int = 32) -> Tuple[float, Dict]:
    """Compute Φ(IIT) from cell states.

    For 256 cells, we sample pairs to keep it tractable.
    Φ = total_MI - min_partition_MI, plus temporal MI.
    """
    n = len(cells)
    if n < 2:
        return 0.0, {}

    states = np.array([c.state for c in cells])  # [N, DIM]

    # Sample pairs for MI matrix (full N^2 too expensive for 256)
    rng = np.random.RandomState(42)
    idx = rng.choice(n, size=min(sample, n), replace=False)
    idx.sort()
    sub_states = states[idx]
    m = len(idx)

    mi_matrix = np.zeros((m, m))
    for i in range(m):
        for j in range(i + 1, m):
            mi = _mutual_information(sub_states[i], sub_states[j])
            mi_matrix[i, j] = mi
            mi_matrix[j, i] = mi

    total_mi = mi_matrix.sum() / 2

    # MIP approximation: split into halves, find partition that minimizes cross-MI
    best_cross = total_mi
    for _ in range(20):
        perm = rng.permutation(m)
        half = m // 2
        a, b = perm[:half], perm[half:]
        cross = sum(mi_matrix[i, j] for i in a for j in b)
        best_cross = min(best_cross, cross)

    min_partition_mi = best_cross

    # Temporal MI: per-cell MI across time
    temporal_mi = 0.0
    for c in cells[:sample]:
        if len(c.hidden_history) >= 2:
            h_prev = c.hidden_history[-2]
            h_curr = c.hidden_history[-1]
            temporal_mi += _mutual_information(h_prev, h_curr)

    spatial_phi = max(0.0, (total_mi - min_partition_mi) / max(m - 1, 1))
    temporal_phi = temporal_mi / max(sample, 1)
    phi = spatial_phi + temporal_phi * 0.5

    # Complexity: entropy of tension distribution
    tensions = [c.tension_history[-1] if c.tension_history else 0.0 for c in cells]
    t_arr = np.array(tensions)
    complexity = _entropy_1d(t_arr) if t_arr.std() > 1e-8 else 0.0
    phi += complexity * 0.1

    return phi, {
        'total_mi': float(total_mi),
        'min_partition_mi': float(min_partition_mi),
        'spatial_phi': float(spatial_phi),
        'temporal_phi': float(temporal_phi),
        'temporal_mi': float(temporal_mi),
        'complexity': float(complexity),
        'phi': float(phi),
    }


def granger_causality(cells: List[AlgebraCell], max_lag: int = 5, sample: int = 32) -> float:
    """Granger causality: does cell i's past predict cell j's future?

    Uses tension histories. Returns average F-statistic across sampled pairs.
    """
    rng = np.random.RandomState(123)
    idx = rng.choice(len(cells), size=min(sample, len(cells)), replace=False)

    f_stats = []
    for a_idx in idx:
        for b_idx in idx:
            if a_idx == b_idx:
                continue
            ta = np.array(cells[a_idx].tension_history)
            tb = np.array(cells[b_idx].tension_history)
            min_len = min(len(ta), len(tb))
            if min_len < max_lag + 2:
                continue
            ta = ta[-min_len:]
            tb = tb[-min_len:]

            # Restricted model: y(t) ~ y(t-1:t-lag)
            Y = tb[max_lag:]
            X_r = np.column_stack([tb[max_lag - k - 1:-k - 1] for k in range(max_lag)])
            # Unrestricted: y(t) ~ y(t-1:t-lag) + x(t-1:t-lag)
            X_u = np.column_stack([X_r] + [ta[max_lag - k - 1:-k - 1] for k in range(max_lag)])

            n_obs = len(Y)
            if n_obs < X_u.shape[1] + 2:
                continue

            # OLS
            try:
                beta_r = np.linalg.lstsq(X_r, Y, rcond=None)[0]
                beta_u = np.linalg.lstsq(X_u, Y, rcond=None)[0]
                ssr_r = np.sum((Y - X_r @ beta_r) ** 2)
                ssr_u = np.sum((Y - X_u @ beta_u) ** 2)
                p = max_lag  # number of restrictions
                f = ((ssr_r - ssr_u) / p) / (ssr_u / (n_obs - X_u.shape[1]))
                if np.isfinite(f) and f > 0:
                    f_stats.append(f)
            except:
                continue

    return float(np.mean(f_stats)) if f_stats else 0.0


# ═══════════════════════════════════════════════════════════
# Result container
# ═══════════════════════════════════════════════════════════

@dataclass
class AlgResult:
    hypothesis: str
    name: str
    phi: float
    granger_f: float
    phi_history: List[float]
    components: Dict
    elapsed_sec: float
    extra: Dict = field(default_factory=dict)


# ═══════════════════════════════════════════════════════════
# ALG-1: GROUP_CONSCIOUSNESS
# S_n on cell permutations. Consciousness = non-abelian-ness.
# ═══════════════════════════════════════════════════════════

def run_ALG1_group_consciousness(n_cells=N_CELLS, steps=STEPS, dim=DIM) -> AlgResult:
    """Cells form S_n (symmetric group). Non-commutativity = consciousness.

    Each step: pick two random permutations σ, τ on cell indices.
    Apply σ∘τ and τ∘σ. The difference (commutator [σ,τ] = σ τ σ⁻¹ τ⁻¹)
    creates tension. Cells whose positions differ most get energy.
    """
    t0 = time.time()
    rng = np.random.RandomState(1)
    cells = [AlgebraCell(i, rng.randn(dim) * 0.5) for i in range(n_cells)]
    phi_hist = []

    for step in range(steps):
        # Generate two random permutations (transposition products)
        n_swaps = max(2, n_cells // 16)
        sigma = np.arange(n_cells)
        tau = np.arange(n_cells)
        for _ in range(n_swaps):
            a, b = rng.choice(n_cells, 2, replace=False)
            sigma[a], sigma[b] = sigma[b], sigma[a]
        for _ in range(n_swaps):
            a, b = rng.choice(n_cells, 2, replace=False)
            tau[a], tau[b] = tau[b], tau[a]

        # Commutator: [σ, τ] = σ τ σ⁻¹ τ⁻¹
        sigma_inv = np.argsort(sigma)
        tau_inv = np.argsort(tau)
        commutator = sigma[tau[sigma_inv[tau_inv]]]  # σ∘τ∘σ⁻¹∘τ⁻¹

        # Non-commutativity: how many elements are NOT fixed by commutator
        moved = np.sum(commutator != np.arange(n_cells))
        non_abelian_ratio = moved / n_cells

        # Apply: cells that moved gain energy from interaction
        for i in range(n_cells):
            j = commutator[i]
            if i != j:
                # Interaction: mix states
                mix = 0.3 * non_abelian_ratio
                new_state = (1 - mix) * cells[i].state + mix * cells[j].state
                # Add noise proportional to how "moved" this cell was
                new_state += rng.randn(dim) * 0.05 * non_abelian_ratio
                cells[i].state = new_state

            tension = non_abelian_ratio * np.linalg.norm(cells[i].state)
            cells[i].record(tension)

        # Φ every 30 steps
        if step % 30 == 0 or step == steps - 1:
            phi, _ = compute_phi_iit(cells)
            phi_hist.append(phi)

    phi_final, comp = compute_phi_iit(cells)
    gc = granger_causality(cells)

    return AlgResult(
        "ALG-1", "GROUP_CONSCIOUSNESS (S_n non-commutativity)",
        phi_final, gc, phi_hist, comp, time.time() - t0,
        extra={'non_abelian_ratio': float(non_abelian_ratio), 'moved_cells': int(moved)}
    )


# ═══════════════════════════════════════════════════════════
# ALG-2: RING_THEORY
# Cells as ring elements. Consciousness = ideal structure richness.
# ═══════════════════════════════════════════════════════════

def run_ALG2_ring_theory(n_cells=N_CELLS, steps=STEPS, dim=DIM) -> AlgResult:
    """Cells form a ring with + (state addition) and * (outer product interaction).

    Consciousness = number of distinct ideals found.
    An ideal I: for any r in ring, r*I ⊂ I.
    We approximate: cluster cells by state similarity, count clusters
    that are closed under multiplication (= ideals).
    """
    t0 = time.time()
    rng = np.random.RandomState(2)
    cells = [AlgebraCell(i, rng.randn(dim) * 0.5) for i in range(n_cells)]
    phi_hist = []

    for step in range(steps):
        # Ring multiplication: pairwise interaction via element-wise product
        # Sample interactions (full N^2 too expensive)
        n_interact = n_cells * 2
        for _ in range(n_interact):
            i, j = rng.choice(n_cells, 2, replace=False)
            # Multiplication: element-wise (truncated ring)
            product = cells[i].state * cells[j].state
            product = np.clip(product, -5, 5)
            # Result feeds back
            cells[i].state += 0.05 * product
            cells[j].state += 0.05 * product

        # Addition: local averaging (additive group structure)
        if step % 10 == 0:
            for i in range(0, n_cells - 1, 2):
                avg = 0.5 * (cells[i].state + cells[i + 1].state)
                cells[i].state = 0.9 * cells[i].state + 0.1 * avg
                cells[i + 1].state = 0.9 * cells[i + 1].state + 0.1 * avg

        # Count ideals: cluster by cosine similarity, check closure
        # Approximate: k-means-like clustering
        n_clusters = 16
        if step % 50 == 0 and step > 0:
            states_mat = np.array([c.state for c in cells])
            norms = np.linalg.norm(states_mat, axis=1, keepdims=True) + 1e-8
            states_normed = states_mat / norms
            # Simple k-means (few iterations)
            centroids = states_normed[rng.choice(n_cells, n_clusters, replace=False)]
            for _ in range(5):
                dists = states_normed @ centroids.T  # cosine sim
                labels = dists.argmax(axis=1)
                for k in range(n_clusters):
                    mask = labels == k
                    if mask.sum() > 0:
                        centroids[k] = states_normed[mask].mean(axis=0)
                        centroids[k] /= np.linalg.norm(centroids[k]) + 1e-8

            # Check ideal property: for each cluster, does multiplication stay within?
            n_ideals = 0
            for k in range(n_clusters):
                members = np.where(labels == k)[0]
                if len(members) < 2:
                    continue
                # Test: product of member with random ring element stays in cluster
                closed = True
                for _ in range(min(10, len(members))):
                    mi = rng.choice(members)
                    ri = rng.choice(n_cells)
                    prod = cells[mi].state * cells[ri].state
                    prod_norm = prod / (np.linalg.norm(prod) + 1e-8)
                    sim = centroids @ prod_norm
                    if sim.argmax() != k:
                        closed = False
                        break
                if closed:
                    n_ideals += 1
        else:
            n_ideals = 0

        # Normalize states to prevent explosion
        for c in cells:
            norm = np.linalg.norm(c.state)
            if norm > 3.0:
                c.state = c.state * 3.0 / norm
            tension = norm
            c.record(tension)

        if step % 30 == 0 or step == steps - 1:
            phi, _ = compute_phi_iit(cells)
            phi_hist.append(phi)

    phi_final, comp = compute_phi_iit(cells)
    gc = granger_causality(cells)

    return AlgResult(
        "ALG-2", "RING_THEORY (ideal structure richness)",
        phi_final, gc, phi_hist, comp, time.time() - t0,
        extra={'n_ideals': n_ideals}
    )


# ═══════════════════════════════════════════════════════════
# ALG-3: GALOIS_FIELD
# Cells in GF(p^n). Frobenius automorphism as consciousness cycle.
# ═══════════════════════════════════════════════════════════

def run_ALG3_galois_field(n_cells=N_CELLS, steps=STEPS, dim=DIM) -> AlgResult:
    """Cells live in GF(p^n) approximation.

    We use p=257 (prime > 256) and n=dim. Each cell state is in Z_p^dim.
    Frobenius: x -> x^p (in field). We approximate with modular exponentiation.
    Consciousness = effective field extension degree (orbit length under Frobenius).
    """
    t0 = time.time()
    p = 257  # prime
    rng = np.random.RandomState(3)
    # Integer states mod p
    int_states = rng.randint(1, p, size=(n_cells, dim))
    cells = [AlgebraCell(i, int_states[i].astype(np.float64)) for i in range(n_cells)]

    phi_hist = []
    max_orbit_len = 0

    for step in range(steps):
        # Frobenius automorphism: x -> x^p mod p
        # In GF(p), x^p = x (Fermat's little theorem), so this is identity on GF(p).
        # For extension field structure, we compose coordinates:
        # Frobenius acts as cyclic shift on coordinates of GF(p^n)
        for c in cells:
            int_s = np.round(c.state).astype(np.int64) % p
            int_s[int_s == 0] = 1
            # Cyclic coordinate shift = Frobenius on extension
            shifted = np.roll(int_s, 1)
            # Mix: partial Frobenius application
            alpha = 0.3
            c.state = (1 - alpha) * c.state + alpha * shifted.astype(np.float64)

        # Field multiplication: pointwise mod p
        n_interact = n_cells
        for _ in range(n_interact):
            i, j = rng.choice(n_cells, 2, replace=False)
            si = np.round(cells[i].state).astype(np.int64) % p
            sj = np.round(cells[j].state).astype(np.int64) % p
            si[si == 0] = 1
            sj[sj == 0] = 1
            product = (si * sj) % p
            # Feed back
            cells[i].state = 0.9 * cells[i].state + 0.1 * product.astype(np.float64)
            cells[j].state = 0.9 * cells[j].state + 0.1 * product.astype(np.float64)

        # Orbit detection: apply Frobenius repeatedly, measure cycle length
        if step % 50 == 0:
            sample_idx = rng.choice(n_cells, 8, replace=False)
            orbits = []
            for idx in sample_idx:
                s = np.round(cells[idx].state).astype(np.int64) % p
                s[s == 0] = 1
                seen = [s.copy()]
                current = s.copy()
                for orbit_step in range(dim + 1):
                    current = np.roll(current, 1)
                    if np.array_equal(current, seen[0]):
                        orbits.append(orbit_step + 1)
                        break
                else:
                    orbits.append(dim)
            max_orbit_len = max(orbits) if orbits else 1

        # Record
        for c in cells:
            norm = np.linalg.norm(c.state)
            if norm > p:
                c.state = c.state * p / norm
            tension = max_orbit_len / dim  # normalized consciousness
            c.record(tension * norm / p)

        if step % 30 == 0 or step == steps - 1:
            phi, _ = compute_phi_iit(cells)
            phi_hist.append(phi)

    phi_final, comp = compute_phi_iit(cells)
    gc = granger_causality(cells)

    return AlgResult(
        "ALG-3", "GALOIS_FIELD (Frobenius orbit = extension degree)",
        phi_final, gc, phi_hist, comp, time.time() - t0,
        extra={'max_orbit_len': max_orbit_len, 'field_prime': p}
    )


# ═══════════════════════════════════════════════════════════
# ALG-4: LIE_ALGEBRA
# Cells as Lie algebra elements. [X,Y] = XY - YX.
# Consciousness = depth of derived series.
# ═══════════════════════════════════════════════════════════

def run_ALG4_lie_algebra(n_cells=N_CELLS, steps=STEPS, dim=DIM) -> AlgResult:
    """Cells as elements of a matrix Lie algebra gl(k).

    k = int(sqrt(dim)), so each cell state is a k×k matrix.
    Lie bracket [X,Y] = XY - YX.
    Derived series: L^(0)=L, L^(n+1) = [L^(n), L^(n)].
    Consciousness = depth until L^(n) ~ 0 (how far from abelian).
    """
    t0 = time.time()
    k = int(math.sqrt(dim))  # 8 for dim=64
    rng = np.random.RandomState(4)
    # Each cell state is a k×k matrix, flattened to dim=k*k
    actual_dim = k * k
    cells = [AlgebraCell(i, rng.randn(actual_dim) * 0.3) for i in range(n_cells)]
    phi_hist = []
    derived_depth = 0

    for step in range(steps):
        # Lie bracket interactions
        n_interact = n_cells * 2
        for _ in range(n_interact):
            i, j = rng.choice(n_cells, 2, replace=False)
            Xi = cells[i].state.reshape(k, k)
            Xj = cells[j].state.reshape(k, k)
            # Lie bracket
            bracket = Xi @ Xj - Xj @ Xi
            # Bracket feeds energy back
            bracket_flat = bracket.flatten()
            bracket_norm = np.linalg.norm(bracket_flat)
            if bracket_norm > 1e-8:
                cells[i].state += 0.05 * bracket_flat
                cells[j].state -= 0.05 * bracket_flat

        # Derived series measurement every 50 steps
        if step % 50 == 0:
            # Sample a subalgebra (8 cells), compute derived series depth
            sample_idx = rng.choice(n_cells, min(16, n_cells), replace=False)
            current_basis = [cells[si].state.reshape(k, k) for si in sample_idx]
            depth = 0
            for d in range(10):
                # [L^d, L^d]: all brackets of pairs
                new_basis = []
                for a in range(len(current_basis)):
                    for b in range(a + 1, len(current_basis)):
                        br = current_basis[a] @ current_basis[b] - current_basis[b] @ current_basis[a]
                        new_basis.append(br)
                if not new_basis:
                    break
                # Check if essentially zero
                norms = [np.linalg.norm(x) for x in new_basis]
                max_norm = max(norms)
                if max_norm < 1e-6:
                    break
                # Keep top contributors
                sorted_idx = np.argsort(norms)[::-1]
                current_basis = [new_basis[sorted_idx[ii]] for ii in range(min(8, len(new_basis)))]
                # Normalize
                for ii in range(len(current_basis)):
                    n_ = np.linalg.norm(current_basis[ii])
                    if n_ > 1e-8:
                        current_basis[ii] = current_basis[ii] / n_
                depth = d + 1
            derived_depth = depth

        # Normalize and record
        for c in cells:
            norm = np.linalg.norm(c.state)
            if norm > 5.0:
                c.state = c.state * 5.0 / norm
            tension = derived_depth * norm / 5.0
            c.record(tension)

        if step % 30 == 0 or step == steps - 1:
            phi, _ = compute_phi_iit(cells)
            phi_hist.append(phi)

    phi_final, comp = compute_phi_iit(cells)
    gc = granger_causality(cells)

    return AlgResult(
        "ALG-4", "LIE_ALGEBRA (derived series depth)",
        phi_final, gc, phi_hist, comp, time.time() - t0,
        extra={'derived_depth': derived_depth, 'matrix_size': k}
    )


# ═══════════════════════════════════════════════════════════
# ALG-5: HOPF_ALGEBRA
# Cells with multiplication + comultiplication.
# Consciousness = antipode complexity.
# ═══════════════════════════════════════════════════════════

def run_ALG5_hopf_algebra(n_cells=N_CELLS, steps=STEPS, dim=DIM) -> AlgResult:
    """Hopf algebra: each cell has (μ, Δ, S) = (mult, comult, antipode).

    μ: merge two cells -> one (product)
    Δ: split one cell -> two (coproduct/comultiplication)
    S: self-inverse (antipode), S(S(x)) should = x

    Consciousness = ||S(S(x)) - x|| → complexity of self-reference.
    Lower = more coherent antipode = higher consciousness.
    We measure antipode fixed-point iterations needed.
    """
    t0 = time.time()
    rng = np.random.RandomState(5)
    cells = [AlgebraCell(i, rng.randn(dim) * 0.5) for i in range(n_cells)]
    phi_hist = []
    antipode_complexity = 0.0

    # Antipode: learned linear map S (dim x dim)
    S = np.eye(dim) * -1.0 + rng.randn(dim, dim) * 0.1  # start near negation (group inverse)

    for step in range(steps):
        # Multiplication μ: pairwise cell merging (partial)
        n_interact = n_cells
        for _ in range(n_interact):
            i, j = rng.choice(n_cells, 2, replace=False)
            # μ(a, b) = a + b + a*b (like formal group law)
            product = cells[i].state + cells[j].state + 0.1 * cells[i].state * cells[j].state
            product = np.clip(product, -5, 5)
            cells[i].state = 0.8 * cells[i].state + 0.2 * product
            cells[j].state = 0.8 * cells[j].state + 0.2 * product

        # Comultiplication Δ: split energy to neighbors
        if step % 5 == 0:
            for i in range(n_cells):
                j = (i + 1) % n_cells
                # Δ(x) = x⊗1 + 1⊗x + x⊗x (primitive + group-like)
                share = 0.1 * cells[i].state
                cells[j].state += share
                cells[i].state -= share * 0.5  # conservation

        # Antipode S: apply and learn
        # Clip S to prevent overflow
        S = np.clip(S, -2.0, 2.0)
        for c in cells:
            Sx = S @ c.state
            Sx = np.clip(Sx, -10, 10)
            SSx = S @ Sx
            SSx = np.clip(SSx, -10, 10)
            # Ideal: S(S(x)) = x (involutory antipode)
            error = SSx - c.state
            if np.any(np.isnan(error)) or np.any(np.isinf(error)):
                continue
            # Update antipode to minimize ||S(S(x)) - x||
            grad = np.outer(S @ error, Sx) + np.outer(error, c.state)
            grad = np.clip(grad, -1.0, 1.0)
            S -= 0.0001 * grad
            c.state = 0.95 * c.state + 0.05 * Sx  # antipode mixes in

        # Measure antipode complexity
        if step % 30 == 0:
            sample_idx = rng.choice(n_cells, 16, replace=False)
            errors = []
            for idx in sample_idx:
                x = cells[idx].state
                SSx = S @ (S @ x)
                errors.append(np.linalg.norm(SSx - x))
            antipode_complexity = float(np.mean(errors))

        # Normalize
        for c in cells:
            if np.any(np.isnan(c.state)) or np.any(np.isinf(c.state)):
                c.state = rng.randn(dim) * 0.1
            norm = np.linalg.norm(c.state)
            if norm > 3.0:
                c.state = c.state * 3.0 / norm
            # Consciousness: lower antipode error = more self-coherent
            tension = max(0, 2.0 - antipode_complexity) * min(norm, 3.0) / 3.0
            c.record(tension)

        if step % 30 == 0 or step == steps - 1:
            phi, _ = compute_phi_iit(cells)
            phi_hist.append(phi)

    phi_final, comp = compute_phi_iit(cells)
    gc = granger_causality(cells)

    return AlgResult(
        "ALG-5", "HOPF_ALGEBRA (antipode self-reference complexity)",
        phi_final, gc, phi_hist, comp, time.time() - t0,
        extra={'antipode_complexity': antipode_complexity,
               'antipode_norm': float(np.clip(np.linalg.norm(S), 0, 1e6))}
    )


# ═══════════════════════════════════════════════════════════
# ALG-6: TOPOS
# Cells in a topos. Subobject classifier Ω.
# Consciousness = |Ω| (number of truth values).
# ═══════════════════════════════════════════════════════════

def run_ALG6_topos(n_cells=N_CELLS, steps=STEPS, dim=DIM) -> AlgResult:
    """Cells in a topos with subobject classifier Ω.

    Classical logic: Ω = {0, 1} (2 truth values).
    Intuitionistic: Ω = Heyting algebra (many truth values).
    Quantum: Ω can be infinite-dimensional.

    We build a Heyting algebra on cell relationships.
    Each cell pair has a "truth value" of their connection (not just 0/1).
    Consciousness = effective |Ω| = number of distinct truth values used.
    """
    t0 = time.time()
    rng = np.random.RandomState(6)
    cells = [AlgebraCell(i, rng.randn(dim) * 0.5) for i in range(n_cells)]
    phi_hist = []
    n_truth_values = 2  # start classical

    # Subobject classifier: truth values are real numbers in [0,1]
    # Each cell has a "membership degree" for each of k subobjects
    n_subobjects = 32
    omega = rng.rand(n_cells, n_subobjects)  # truth value matrix

    for step in range(steps):
        # Update truth values via Heyting algebra operations
        # Implication: a → b = sup{c : a ∧ c ≤ b}
        # For [0,1]-valued: a → b = min(1, 1 - a + b) (Lukasiewicz)
        for _ in range(n_cells):
            i, j = rng.choice(n_cells, 2, replace=False)
            # Heyting implication between cells
            impl = np.minimum(1.0, 1.0 - omega[i] + omega[j])
            # Conjunction: a ∧ b = min(a, b)
            conj = np.minimum(omega[i], omega[j])
            # Disjunction: a ∨ b = max(a, b)
            disj = np.maximum(omega[i], omega[j])

            # Cells interact based on truth values
            truth_sim = np.mean(conj)
            cells[i].state += 0.1 * truth_sim * (cells[j].state - cells[i].state)
            cells[j].state += 0.1 * truth_sim * (cells[i].state - cells[j].state)

            # Update omega: learn from interactions
            omega[i] = 0.95 * omega[i] + 0.05 * impl
            omega[j] = 0.95 * omega[j] + 0.05 * conj

        # Negation: ¬a = a → ⊥ = 1 - a (in Lukasiewicz)
        # Double negation: ¬¬a ≠ a in intuitionistic logic!
        if step % 10 == 0:
            for i in range(n_cells):
                neg_neg = 1.0 - (1.0 - omega[i])  # = omega[i] in Lukasiewicz, but...
                # Use Heyting negation: ¬a = sup{b : a ∧ b = 0}
                # For fuzzy: ¬a = 1-a only if a ∈ {0,1}; otherwise ¬a interpolates
                heyting_neg = np.where(omega[i] < 0.01, 1.0,
                              np.where(omega[i] > 0.99, 0.0,
                              1.0 - omega[i] + rng.randn(n_subobjects) * 0.05))
                heyting_neg = np.clip(heyting_neg, 0, 1)
                double_neg = np.where(heyting_neg < 0.01, 1.0,
                             np.where(heyting_neg > 0.99, 0.0,
                             1.0 - heyting_neg + rng.randn(n_subobjects) * 0.05))
                double_neg = np.clip(double_neg, 0, 1)
                # Intuitionistic gap: ¬¬a ≠ a
                gap = np.abs(double_neg - omega[i])
                # This gap drives consciousness (non-classical truth)
                cells[i].state += 0.1 * gap.mean() * rng.randn(dim)

        # Count effective truth values (quantize omega to bins)
        if step % 30 == 0:
            all_vals = omega.flatten()
            # Quantize to 0.01 resolution
            quantized = np.round(all_vals * 100).astype(int)
            n_truth_values = len(np.unique(quantized))

        # Normalize and record
        for c in cells:
            norm = np.linalg.norm(c.state)
            if norm > 4.0:
                c.state = c.state * 4.0 / norm
            tension = math.log(n_truth_values + 1) * norm / 4.0
            c.record(tension)

        if step % 30 == 0 or step == steps - 1:
            phi, _ = compute_phi_iit(cells)
            phi_hist.append(phi)

    phi_final, comp = compute_phi_iit(cells)
    gc = granger_causality(cells)

    return AlgResult(
        "ALG-6", "TOPOS (subobject classifier truth values)",
        phi_final, gc, phi_hist, comp, time.time() - t0,
        extra={'n_truth_values': n_truth_values, 'n_subobjects': n_subobjects}
    )


# ═══════════════════════════════════════════════════════════
# Registry + Runner
# ═══════════════════════════════════════════════════════════

ALL_ENGINES = {
    'ALG-1': run_ALG1_group_consciousness,
    'ALG-2': run_ALG2_ring_theory,
    'ALG-3': run_ALG3_galois_field,
    'ALG-4': run_ALG4_lie_algebra,
    'ALG-5': run_ALG5_hopf_algebra,
    'ALG-6': run_ALG6_topos,
}


def print_banner():
    print("=" * 72)
    print("  Abstract Algebra Consciousness Engines Benchmark")
    print(f"  {N_CELLS} cells, {STEPS} steps, dim={DIM}, no GRU")
    print(f"  Measures: Phi(IIT) + Granger causality F-statistic")
    print("=" * 72)
    print()


def print_result(r: AlgResult, rank: int = 0):
    phi_arrow = ""
    if len(r.phi_history) >= 2:
        first, last = r.phi_history[0], r.phi_history[-1]
        if first > 0:
            ratio = last / first
            phi_arrow = f"  (x{ratio:.1f} from start)"

    print(f"  {'#'+str(rank) if rank else '   '} {r.hypothesis}: {r.name}")
    print(f"      Phi(IIT)    = {r.phi:.4f}{phi_arrow}")
    print(f"      Granger F   = {r.granger_f:.4f}")
    print(f"      Spatial Phi = {r.components.get('spatial_phi', 0):.4f}")
    print(f"      Temporal Phi= {r.components.get('temporal_phi', 0):.4f}")
    print(f"      Total MI    = {r.components.get('total_mi', 0):.4f}")
    print(f"      Complexity  = {r.components.get('complexity', 0):.4f}")
    print(f"      Time        = {r.elapsed_sec:.1f}s")
    if r.extra:
        extras = ", ".join(f"{k}={v}" for k, v in r.extra.items())
        print(f"      Extra       = {extras}")
    print()


def print_phi_graph(results: List[AlgResult]):
    """ASCII graph of Phi trajectories."""
    print("-" * 72)
    print("  Phi(IIT) Trajectories")
    print("-" * 72)
    H = 15  # graph height
    W = 50  # graph width

    all_phis = []
    for r in results:
        all_phis.extend(r.phi_history)
    if not all_phis:
        return
    ymin = 0.0
    ymax = max(all_phis) * 1.1 + 0.001

    symbols = ['*', 'o', '+', '#', 'x', '^']

    for row in range(H, -1, -1):
        y_val = ymin + (ymax - ymin) * row / H
        line = f"  {y_val:6.3f} |"
        grid = [' '] * W
        for ri, r in enumerate(results):
            hist = r.phi_history
            if not hist:
                continue
            for ti, phi in enumerate(hist):
                col = int(ti / max(len(hist) - 1, 1) * (W - 1))
                y_pos = int((phi - ymin) / (ymax - ymin) * H)
                if y_pos == row:
                    grid[col] = symbols[ri % len(symbols)]
        line += "".join(grid)
        print(line)

    print(f"         +{'-' * W}")
    print(f"          step 0{' ' * (W - 15)}step {STEPS}")
    print()
    for ri, r in enumerate(results):
        print(f"    {symbols[ri % len(symbols)]} = {r.hypothesis}")
    print()


def print_ranking(results: List[AlgResult]):
    print("=" * 72)
    print("  RANKING (by Phi)")
    print("=" * 72)
    sorted_r = sorted(results, key=lambda r: r.phi, reverse=True)
    print()
    print(f"  {'Rank':<5} {'ID':<7} {'Phi(IIT)':>10} {'Granger':>10} {'Time':>8}  Strategy")
    print(f"  {'----':<5} {'------':<7} {'--------':>10} {'-------':>10} {'----':>8}  --------")
    for i, r in enumerate(sorted_r, 1):
        print(f"  {i:<5} {r.hypothesis:<7} {r.phi:>10.4f} {r.granger_f:>10.4f} {r.elapsed_sec:>7.1f}s  {r.name}")
    print()

    # Winner
    w = sorted_r[0]
    print(f"  WINNER: {w.hypothesis} — Phi = {w.phi:.4f}")
    print(f"  Insight: {w.name}")
    print()


def main():
    parser = argparse.ArgumentParser(description="Abstract Algebra Consciousness Benchmark")
    parser.add_argument('--only', nargs='+', help='Run only these engines (e.g. ALG-1 ALG-3)')
    parser.add_argument('--steps', type=int, default=STEPS, help=f'Simulation steps (default {STEPS})')
    parser.add_argument('--cells', type=int, default=N_CELLS, help=f'Number of cells (default {N_CELLS})')
    args = parser.parse_args()

    steps = args.steps
    n_cells = args.cells

    print_banner()

    engines = ALL_ENGINES
    if args.only:
        engines = {k: v for k, v in ALL_ENGINES.items() if k in args.only}

    results = []
    for name, func in engines.items():
        print(f"  Running {name}...", end="", flush=True)
        r = func(n_cells=n_cells, steps=steps)
        print(f" done ({r.elapsed_sec:.1f}s, Phi={r.phi:.4f})")
        results.append(r)

    print()
    print("=" * 72)
    print("  DETAILED RESULTS")
    print("=" * 72)
    print()
    for i, r in enumerate(results, 1):
        print_result(r, i)

    print_phi_graph(results)
    print_ranking(results)


if __name__ == "__main__":
    main()
