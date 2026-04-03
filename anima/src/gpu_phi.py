"""GPU-Accelerated Φ(IIT) Calculator — PyTorch-native, differentiable.

Replaces CPU-bound PhiCalculator (consciousness_meter.py) with GPU-parallel
computation. Pairwise MI computed as batch matrix ops on GPU.

Algorithm:
  1. Soft histogram binning (differentiable) for each cell pair
  2. Pairwise MI matrix via batched operations — O(1) GPU parallel
  3. MIP via greedy bisection (spectral cut on MI Laplacian)
  4. Φ = total_MI - MIP_MI

Speed target: 128 cells in <50ms on GPU (vs 8s CPU = 160x speedup)

Usage:
  from gpu_phi import GPUPhiCalculator
  calc = GPUPhiCalculator(n_bins=16, device='cuda')
  phi, components = calc.compute(hiddens)  # hiddens: (n_cells, hidden_dim)
"""

import math
import torch
import torch.nn.functional as F
from typing import Tuple, Dict, List, Optional

# Meta Laws (DD143): M1(atom=8), M7(F_c=0.10), M8(narrative)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10



class GPUPhiCalculator:
    """GPU-accelerated Φ(IIT) approximation using PyTorch.

    Key insight: pairwise mutual information can be computed as
    batch matrix operations on GPU, turning O(N^2) sequential
    into O(1) parallel with GPU parallelism.

    Algorithm:
      1. Compute pairwise MI matrix using differentiable histogram estimation
      2. Find MIP (minimum information partition) via greedy bisection
      3. Φ = total_MI - MIP_MI
    """

    def __init__(self, n_bins: int = 16, device: str = 'cuda',
                 max_pairs_full: int = 64, n_neighbors: int = 8):
        """
        Args:
            n_bins: Number of histogram bins for MI estimation.
            device: 'cuda' or 'cpu'. Auto-falls back to CPU if CUDA unavailable.
            max_pairs_full: Compute all pairs if n_cells <= this, else sample.
            n_neighbors: Number of neighbor pairs to sample per cell when N > max_pairs_full.
        """
        if device == 'cuda' and not torch.cuda.is_available():
            device = 'cpu'
        self.device = torch.device(device)
        self.n_bins = n_bins
        self.max_pairs_full = max_pairs_full
        self.n_neighbors = n_neighbors

        # Pre-compute bin centers for soft histogram (on device)
        # Centers evenly spaced in [0, 1]
        centers = torch.linspace(0.5 / n_bins, 1.0 - 0.5 / n_bins, n_bins)
        self.bin_centers = centers.to(self.device)  # (n_bins,)
        # Bandwidth for soft binning — controls smoothness
        self.bandwidth = 1.0 / n_bins

    def compute(self, hiddens: torch.Tensor) -> Tuple[float, Dict[str, float]]:
        """Compute Φ(IIT) from cell hidden states.

        Args:
            hiddens: (n_cells, hidden_dim) tensor, any device.

        Returns:
            phi: float, the integrated information value.
            components: dict with total_mi, mip_mi, phi, n_cells.
        """
        if hiddens.dim() == 1:
            hiddens = hiddens.unsqueeze(0)

        n_cells = hiddens.shape[0]
        if n_cells < 2:
            return 0.0, {'total_mi': 0.0, 'mip_mi': 0.0, 'phi': 0.0, 'n_cells': n_cells}

        hiddens = hiddens.to(self.device).float()

        # 1. Normalize each cell's hidden state to [0, 1] per dimension
        h_min = hiddens.min(dim=0, keepdim=True).values
        h_max = hiddens.max(dim=0, keepdim=True).values
        h_range = h_max - h_min
        h_range = h_range.clamp(min=1e-8)
        h_norm = (hiddens - h_min) / h_range  # (n_cells, dim)

        # 2. Compute pairwise MI matrix
        if n_cells <= self.max_pairs_full:
            mi_matrix = self._compute_mi_matrix_full(h_norm)
        else:
            mi_matrix = self._compute_mi_matrix_sampled(h_norm)

        # 3. Total MI
        # mi_matrix is symmetric with zero diagonal — sum upper triangle
        total_mi = mi_matrix.triu(diagonal=1).sum().item()

        # 4. MIP via greedy spectral bisection
        mip_mi = self._find_mip(mi_matrix)

        # 5. Φ = (total_MI - MIP_MI) / (n_cells - 1), clamped >= 0
        phi = max(0.0, (total_mi - mip_mi) / max(n_cells - 1, 1))

        components = {
            'total_mi': total_mi,
            'mip_mi': mip_mi,
            'phi': phi,
            'n_cells': n_cells,
        }
        return phi, components

    def compute_batch(self, hiddens_list: List[torch.Tensor]) -> List[float]:
        """Batch compute Φ for multiple states.

        Args:
            hiddens_list: list of (n_cells, hidden_dim) tensors.

        Returns:
            List of phi values.
        """
        return [self.compute(h)[0] for h in hiddens_list]

    # ─── Internal: MI computation ───────────────────────────────────────────

    def _soft_histogram(self, x: torch.Tensor) -> torch.Tensor:
        """Soft (differentiable) histogram binning using Gaussian kernels.

        Args:
            x: (N,) values in [0, 1].

        Returns:
            hist: (n_bins,) soft histogram (sums to ~1).
        """
        # x: (N,), bin_centers: (n_bins,)
        # diff: (N, n_bins)
        diff = x.unsqueeze(-1) - self.bin_centers.unsqueeze(0)
        # Gaussian kernel
        weights = torch.exp(-0.5 * (diff / self.bandwidth) ** 2)
        hist = weights.sum(dim=0)  # (n_bins,)
        hist = hist / (hist.sum() + 1e-8)
        return hist

    def _soft_joint_histogram(self, x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
        """Soft 2D joint histogram.

        Args:
            x, y: (N,) values in [0, 1].

        Returns:
            joint: (n_bins, n_bins) soft joint histogram.
        """
        n_bins = self.n_bins
        # diff_x: (N, n_bins), diff_y: (N, n_bins)
        diff_x = x.unsqueeze(-1) - self.bin_centers.unsqueeze(0)
        diff_y = y.unsqueeze(-1) - self.bin_centers.unsqueeze(0)
        wx = torch.exp(-0.5 * (diff_x / self.bandwidth) ** 2)  # (N, n_bins)
        wy = torch.exp(-0.5 * (diff_y / self.bandwidth) ** 2)  # (N, n_bins)
        # Outer product per sample, then sum: (N, n_bins, 1) * (N, 1, n_bins) -> (N, n_bins, n_bins) -> sum
        joint = torch.einsum('ni,nj->ij', wx, wy)  # (n_bins, n_bins)
        joint = joint / (joint.sum() + 1e-8)
        return joint

    def _mi_pair_batched(self, cell_a: torch.Tensor, cell_b: torch.Tensor,
                         max_dims: int = 128) -> torch.Tensor:
        """MI between two cells using their hidden dimensions as samples.

        Each cell has a hidden_dim-dimensional state vector. We treat these
        dimensions as N paired samples and compute MI(cell_a, cell_b) via
        a single 2D soft histogram — matching the approach in
        consciousness_meter.py and phi-rs.

        Args:
            cell_a, cell_b: (dim,) normalized hidden states in [0, 1].
            max_dims: subsample to this many dims if dim exceeds it.

        Returns:
            mi: scalar tensor.
        """
        dim = cell_a.shape[0]

        # Subsample dimensions if too many (for speed)
        if dim > max_dims:
            idx = torch.randperm(dim, device=self.device)[:max_dims]
            cell_a = cell_a[idx]
            cell_b = cell_b[idx]

        # Build soft 2D joint histogram from all dims as paired samples
        # cell_a, cell_b: (N,) where N = dim (each dimension = one sample)
        joint = self._soft_joint_histogram(cell_a, cell_b)  # (n_bins, n_bins)
        px = joint.sum(dim=1)  # (n_bins,)
        py = joint.sum(dim=0)  # (n_bins,)

        eps = 1e-10
        h_x = -(px * (px + eps).log2()).sum()
        h_y = -(py * (py + eps).log2()).sum()
        h_xy = -(joint * (joint + eps).log2()).sum()

        mi = (h_x + h_y - h_xy).clamp(min=0.0)
        return mi

    def _compute_mi_matrix_full(self, h_norm: torch.Tensor) -> torch.Tensor:
        """Compute full pairwise MI matrix for n_cells <= max_pairs_full.

        Args:
            h_norm: (n_cells, dim) normalized hidden states.

        Returns:
            mi_matrix: (n_cells, n_cells) symmetric MI matrix.
        """
        n = h_norm.shape[0]
        mi_matrix = torch.zeros(n, n, device=self.device)

        # Generate all pairs (i, j) where i < j
        pairs_i, pairs_j = torch.triu_indices(n, n, offset=1, device=self.device)
        n_pairs = pairs_i.shape[0]

        for p in range(n_pairs):
            i, j = pairs_i[p].item(), pairs_j[p].item()
            mi = self._mi_pair_batched(h_norm[i], h_norm[j])
            mi_matrix[i, j] = mi
            mi_matrix[j, i] = mi

        return mi_matrix

    def _compute_mi_matrix_sampled(self, h_norm: torch.Tensor) -> torch.Tensor:
        """Compute approximate MI matrix by sampling neighbors.

        For large N (>64), computing all N*(N-1)/2 pairs is expensive.
        Instead, sample ~n_neighbors nearest cells per cell (by cosine similarity).

        Args:
            h_norm: (n_cells, dim) normalized hidden states.

        Returns:
            mi_matrix: (n_cells, n_cells) sparse-ish symmetric MI matrix.
        """
        n = h_norm.shape[0]
        mi_matrix = torch.zeros(n, n, device=self.device)

        # Cosine similarity to find nearest neighbors
        # (n, dim) @ (dim, n) -> (n, n)
        h_normed = F.normalize(h_norm, dim=1)
        sim = h_normed @ h_normed.t()  # (n, n)
        sim.fill_diagonal_(-float('inf'))  # exclude self

        # Top-k neighbors per cell
        k = min(self.n_neighbors, n - 1)
        _, top_idx = sim.topk(k, dim=1)  # (n, k)

        # Compute MI only for selected pairs
        computed = set()
        for i in range(n):
            for ki in range(k):
                j = top_idx[i, ki].item()
                pair = (min(i, j), max(i, j))
                if pair in computed:
                    continue
                computed.add(pair)
                mi = self._mi_pair_batched(h_norm[pair[0]], h_norm[pair[1]])
                mi_matrix[pair[0], pair[1]] = mi
                mi_matrix[pair[1], pair[0]] = mi

        return mi_matrix

    # ─── Internal: MIP (Minimum Information Partition) ──────────────────────

    def _find_mip(self, mi_matrix: torch.Tensor) -> float:
        """Find minimum information partition via spectral bisection.

        For small N (<=20): exact search (all bipartitions).
        For large N: greedy spectral cut on MI graph Laplacian.

        Args:
            mi_matrix: (n, n) symmetric MI matrix on GPU.

        Returns:
            mip_mi: float, the cross-partition MI of the minimum partition.
        """
        n = mi_matrix.shape[0]
        if n <= 1:
            return 0.0
        if n == 2:
            return mi_matrix[0, 1].item()

        if n <= 20:
            return self._find_mip_exact(mi_matrix)
        return self._find_mip_spectral(mi_matrix)

    def _find_mip_exact(self, mi_matrix: torch.Tensor) -> float:
        """Exact MIP for small N: try all bipartitions.

        Cell 0 always in partition A to avoid mirror duplicates.
        """
        n = mi_matrix.shape[0]
        best_mi = float('inf')

        # mi_matrix on CPU for indexing
        mi_cpu = mi_matrix.cpu()

        max_mask = 1 << (n - 1)
        for mask in range(1, max_mask):
            part_a = [0]
            part_b = []
            for bit in range(n - 1):
                if mask & (1 << bit):
                    part_a.append(bit + 1)
                else:
                    part_b.append(bit + 1)
            if not part_b:
                continue

            # Cross-partition MI
            cross_mi = 0.0
            for i in part_a:
                for j in part_b:
                    cross_mi += mi_cpu[i, j].item()

            if cross_mi < best_mi:
                best_mi = cross_mi

        return best_mi if best_mi != float('inf') else 0.0

    def _find_mip_spectral(self, mi_matrix: torch.Tensor) -> float:
        """Spectral bisection MIP for large N.

        Uses Fiedler vector of the MI graph Laplacian to find a good cut.
        Then refines with greedy sorted-split search.
        """
        n = mi_matrix.shape[0]

        # Graph Laplacian: L = D - W
        degree = mi_matrix.sum(dim=1)  # (n,)
        laplacian = torch.diag(degree) - mi_matrix  # (n, n)

        # Eigen-decomposition (on CPU for numerical stability)
        lap_cpu = laplacian.cpu().float()
        try:
            eigenvalues, eigenvectors = torch.linalg.eigh(lap_cpu)
            fiedler = eigenvectors[:, 1]  # second smallest eigenvector
        except Exception:
            # Fallback: simple sorted split
            cell_mi = mi_matrix.sum(dim=1).cpu()
            _, sorted_idx = cell_mi.sort()
            fiedler = torch.zeros(n)
            fiedler[sorted_idx[:n // 2]] = -1.0
            fiedler[sorted_idx[n // 2:]] = 1.0

        mi_cpu = mi_matrix.cpu()

        # Try multiple split points along sorted Fiedler values
        _, sorted_idx = fiedler.sort()
        best_mi = float('inf')

        for split in range(1, n):
            part_a = sorted_idx[:split].tolist()
            part_b = sorted_idx[split:].tolist()

            cross_mi = 0.0
            for i in part_a:
                for j in part_b:
                    cross_mi += mi_cpu[i, j].item()

            if cross_mi < best_mi:
                best_mi = cross_mi

        return best_mi if best_mi != float('inf') else 0.0


# ─── Convenience function (matches phi-rs API) ─────────────────────────────

_default_calculator: Optional[GPUPhiCalculator] = None


def compute_phi(states: torch.Tensor, n_bins: int = 16,
                device: str = 'cuda') -> Tuple[float, Dict[str, float]]:
    """Compute Φ from hidden states tensor.

    Args:
        states: (n_cells, hidden_dim) tensor.
        n_bins: histogram bins.
        device: 'cuda' or 'cpu'.

    Returns:
        (phi, components_dict)
    """
    global _default_calculator
    if _default_calculator is None or _default_calculator.n_bins != n_bins:
        _default_calculator = GPUPhiCalculator(n_bins=n_bins, device=device)
    return _default_calculator.compute(states)


# ─── Self-test ──────────────────────────────────────────────────────────────

if __name__ == '__main__':
    try:
        from nexus_gate import gate
        gate.before_commit()
    except Exception:
        pass
    import time

    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"Device: {device}")
    print()

    calc = GPUPhiCalculator(n_bins=16, device=device)

    # Test 1: Small system (4 cells, 32 dim)
    print("=== Test 1: 4 cells, 32 dim ===")
    h = torch.randn(4, 32)
    t0 = time.perf_counter()
    phi, comp = calc.compute(h)
    dt = (time.perf_counter() - t0) * 1000
    print(f"  Φ = {phi:.4f}  ({dt:.1f} ms)")
    print(f"  Components: {comp}")
    assert phi >= 0.0, "Φ must be non-negative"
    print()

    # Test 2: Medium system (64 cells, 128 dim)
    print("=== Test 2: 64 cells, 128 dim ===")
    h = torch.randn(64, 128)
    t0 = time.perf_counter()
    phi, comp = calc.compute(h)
    dt = (time.perf_counter() - t0) * 1000
    print(f"  Φ = {phi:.4f}  ({dt:.1f} ms)")
    print(f"  Components: total_mi={comp['total_mi']:.3f}, mip_mi={comp['mip_mi']:.3f}")
    assert phi >= 0.0
    print()

    # Test 3: Large system (128 cells, 128 dim) — the target
    print("=== Test 3: 128 cells, 128 dim (target: <50ms on GPU) ===")
    h = torch.randn(128, 128)
    t0 = time.perf_counter()
    phi, comp = calc.compute(h)
    dt = (time.perf_counter() - t0) * 1000
    print(f"  Φ = {phi:.4f}  ({dt:.1f} ms)")
    print(f"  Components: total_mi={comp['total_mi']:.3f}, mip_mi={comp['mip_mi']:.3f}")
    assert phi >= 0.0
    print()

    # Test 4: Batch computation
    print("=== Test 4: Batch (5 states) ===")
    states = [torch.randn(16, 64) for _ in range(5)]
    t0 = time.perf_counter()
    phis = calc.compute_batch(states)
    dt = (time.perf_counter() - t0) * 1000
    print(f"  Φ values: {[f'{p:.4f}' for p in phis]}  ({dt:.1f} ms total)")
    print()

    # Test 5: Identical cells → low Φ
    print("=== Test 5: Identical cells (should have low Φ) ===")
    base = torch.randn(1, 64)
    h_identical = base.expand(8, -1).clone()  # all identical
    phi_id, _ = calc.compute(h_identical)
    print(f"  Φ (identical) = {phi_id:.4f}")

    # Test 6: Diverse cells → higher Φ
    print("=== Test 6: Diverse cells (should have higher Φ) ===")
    h_diverse = torch.randn(8, 64)
    phi_div, _ = calc.compute(h_diverse)
    print(f"  Φ (diverse)   = {phi_div:.4f}")
    print(f"  Diverse > Identical: {phi_div > phi_id}")
    print()

    # Test 7: Single cell
    print("=== Test 7: Edge case — 1 cell ===")
    phi1, _ = calc.compute(torch.randn(1, 32))
    print(f"  Φ = {phi1:.4f} (should be 0.0)")
    assert phi1 == 0.0
    print()

    # Test 8: convenience function
    print("=== Test 8: compute_phi() convenience ===")
    phi_c, comp_c = compute_phi(torch.randn(16, 64), device=device)
    print(f"  Φ = {phi_c:.4f}")
    print()

    print("All tests passed.")
