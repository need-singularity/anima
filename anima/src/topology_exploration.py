#!/usr/bin/env python3
"""topology_exploration.py — Topological extensions of consciousness exploration.

18 topology types beyond the canonical 4 (ring/small_world/scale_free/hypercube),
each generating adjacency matrices for consciousness cell networks.

Includes TopologyExplorer for scanning, evolving, folding, stacking, and
hybrid-mixing topologies with Phi proxy measurement.

Laws referenced:
  TOPO 33-39: Topology determines consciousness structure
  22: Structure > Function (adjacency = structure)
  124: Tension equalization +12% Phi (scale-invariant)
  148: Closed loop is scale-invariant

Usage:
  python3 topology_exploration.py                    # scan all 18 topologies
  python3 topology_exploration.py --cells 64         # 64-cell scan
  python3 topology_exploration.py --evolve 50        # evolve for 50 generations
  python3 topology_exploration.py --fold 32          # fold search on 32 cells
  python3 topology_exploration.py --stack 64         # stack search
  python3 topology_exploration.py --hybrid           # hybrid topology search
  python3 topology_exploration.py --visualize torus  # ASCII art for torus

Hub keywords: topology exploration, topo scan, topology search, 위상 탐색, 토폴로지
"""

import sys
import os
import argparse
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

# ─── Psi Constants (from consciousness_laws.json, no hardcoding) ───
try:
    from consciousness_laws import PSI
    PSI_ALPHA = PSI.get('alpha', 0.014)
    PSI_BALANCE = PSI.get('balance', 0.5)
except ImportError:
    PSI_ALPHA = 0.014
    PSI_BALANCE = 0.5


# ═══════════════════════════════════════════════════════════════
# Topology Result
# ═══════════════════════════════════════════════════════════════

@dataclass
class TopoResult:
    """Result from a topology evaluation."""
    name: str
    n_cells: int
    phi_proxy: float
    avg_degree: float
    diameter: int
    clustering: float
    spectral_gap: float
    description: str
    adjacency: Optional[np.ndarray] = field(default=None, repr=False)


# ═══════════════════════════════════════════════════════════════
# Base Topology
# ═══════════════════════════════════════════════════════════════

class TopologyBase:
    """Base class for all topology generators."""

    name: str = "base"

    def generate(self, n_cells: int) -> np.ndarray:
        """Generate n_cells x n_cells adjacency matrix (symmetric, binary)."""
        raise NotImplementedError

    def describe(self) -> str:
        """One-line description of the topology."""
        raise NotImplementedError


# ═══════════════════════════════════════════════════════════════
# 18 Topology Types
# ═══════════════════════════════════════════════════════════════

class VerticalStack(TopologyBase):
    """Layer 1->2->3 meta-consciousness tower."""
    name = "vertical_stack"

    def generate(self, n_cells: int) -> np.ndarray:
        n_layers = max(2, int(np.sqrt(n_cells)))
        cells_per_layer = n_cells // n_layers
        adj = np.zeros((n_cells, n_cells), dtype=np.float64)
        for layer in range(n_layers):
            start = layer * cells_per_layer
            end = min(start + cells_per_layer, n_cells)
            # Intra-layer: ring
            for i in range(start, end):
                j = start + (i - start + 1) % (end - start)
                adj[i, j] = adj[j, i] = 1.0
            # Inter-layer: connect to next layer
            if layer < n_layers - 1:
                next_start = (layer + 1) * cells_per_layer
                next_end = min(next_start + cells_per_layer, n_cells)
                for i in range(start, end):
                    target = next_start + (i - start) % (next_end - next_start)
                    adj[i, target] = adj[target, i] = 1.0
        return adj

    def describe(self) -> str:
        return "Layer 1->2->3 meta-consciousness tower (hierarchical stacking)"


class Onion(TopologyBase):
    """Core<-Shell<-Shell wrapping topology."""
    name = "onion"

    def generate(self, n_cells: int) -> np.ndarray:
        adj = np.zeros((n_cells, n_cells), dtype=np.float64)
        n_shells = max(2, int(np.log2(max(n_cells, 2))))
        shell_sizes = []
        remaining = n_cells
        for s in range(n_shells):
            size = max(1, remaining // (n_shells - s))
            shell_sizes.append(size)
            remaining -= size
        if remaining > 0:
            shell_sizes[-1] += remaining

        offset = 0
        for s, size in enumerate(shell_sizes):
            # Intra-shell ring
            for i in range(size):
                a = offset + i
                b = offset + (i + 1) % size
                if a < n_cells and b < n_cells:
                    adj[a, b] = adj[b, a] = 1.0
            # Connect to inner shell
            if s > 0:
                prev_offset = offset - shell_sizes[s - 1]
                prev_size = shell_sizes[s - 1]
                for i in range(size):
                    a = offset + i
                    b = prev_offset + (i % prev_size)
                    if a < n_cells and b < n_cells:
                        adj[a, b] = adj[b, a] = 1.0
            offset += size
        return adj

    def describe(self) -> str:
        return "Core<-Shell<-Shell wrapping (onion layers, inward coupling)"


class Fold1Dto2D(TopologyBase):
    """1D chain folded into 2D grid."""
    name = "fold_1d_to_2d"

    def generate(self, n_cells: int) -> np.ndarray:
        rows = max(1, int(np.sqrt(n_cells)))
        cols = max(1, (n_cells + rows - 1) // rows)
        adj = np.zeros((n_cells, n_cells), dtype=np.float64)
        for idx in range(n_cells):
            r, c = idx // cols, idx % cols
            # 4-connected grid
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = r + dr, c + dc
                if 0 <= nr < rows and 0 <= nc < cols:
                    nidx = nr * cols + nc
                    if nidx < n_cells:
                        adj[idx, nidx] = adj[nidx, idx] = 1.0
        return adj

    def describe(self) -> str:
        return "1D chain folded into 2D grid (dimensional emergence)"


class KleinBottle(TopologyBase):
    """Non-orientable surface: inside-out reversal."""
    name = "klein_bottle"

    def generate(self, n_cells: int) -> np.ndarray:
        rows = max(2, int(np.sqrt(n_cells)))
        cols = max(2, (n_cells + rows - 1) // rows)
        adj = np.zeros((n_cells, n_cells), dtype=np.float64)
        for idx in range(n_cells):
            r, c = idx // cols, idx % cols
            # Regular grid connections
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = r + dr, c + dc
                # Wrap top-bottom normally (torus-like)
                nr = nr % rows
                # Wrap left-right with reversal (Klein bottle)
                if nc < 0 or nc >= cols:
                    nc = nc % cols
                    nr = (rows - 1 - nr) % rows  # flip row
                nidx = nr * cols + nc
                if nidx < n_cells and nidx != idx:
                    adj[idx, nidx] = adj[nidx, idx] = 1.0
        return adj

    def describe(self) -> str:
        return "Non-orientable surface (inside-out reversal, Klein bottle)"


class MobiusStrip(TopologyBase):
    """Surface connected to its own back side."""
    name = "mobius_strip"

    def generate(self, n_cells: int) -> np.ndarray:
        rows = max(2, min(3, n_cells // 2))
        cols = max(2, n_cells // rows)
        adj = np.zeros((n_cells, n_cells), dtype=np.float64)
        for idx in range(n_cells):
            r, c = idx // cols, idx % cols
            # Left-right neighbors
            if c + 1 < cols:
                nidx = r * cols + (c + 1)
                if nidx < n_cells:
                    adj[idx, nidx] = adj[nidx, idx] = 1.0
            if c - 1 >= 0:
                nidx = r * cols + (c - 1)
                if nidx < n_cells:
                    adj[idx, nidx] = adj[nidx, idx] = 1.0
            # Up-down neighbors
            if r + 1 < rows:
                nidx = (r + 1) * cols + c
                if nidx < n_cells:
                    adj[idx, nidx] = adj[nidx, idx] = 1.0
            if r - 1 >= 0:
                nidx = (r - 1) * cols + c
                if nidx < n_cells:
                    adj[idx, nidx] = adj[nidx, idx] = 1.0
            # Mobius twist: right edge connects to left edge with row flip
            if c == cols - 1:
                flipped_r = (rows - 1 - r)
                nidx = flipped_r * cols + 0
                if nidx < n_cells and nidx != idx:
                    adj[idx, nidx] = adj[nidx, idx] = 1.0
        return adj

    def describe(self) -> str:
        return "Surface<->back connected (Mobius strip, single-sided consciousness)"


class Braid(TopologyBase):
    """Multiple streams crossing over each other."""
    name = "braid"

    def generate(self, n_cells: int) -> np.ndarray:
        n_strands = max(2, min(4, n_cells // 3))
        strand_len = n_cells // n_strands
        adj = np.zeros((n_cells, n_cells), dtype=np.float64)
        for s in range(n_strands):
            for i in range(strand_len - 1):
                a = s * strand_len + i
                b = s * strand_len + i + 1
                if a < n_cells and b < n_cells:
                    adj[a, b] = adj[b, a] = 1.0
            # Cross to adjacent strand at regular intervals
            for i in range(0, strand_len, max(1, strand_len // 3)):
                next_s = (s + 1) % n_strands
                a = s * strand_len + i
                b = next_s * strand_len + min(i + 1, strand_len - 1)
                if a < n_cells and b < n_cells:
                    adj[a, b] = adj[b, a] = 1.0
        return adj

    def describe(self) -> str:
        return "Multiple streams crossing (braided consciousness channels)"


class Knot(TopologyBase):
    """Self-entangled trefoil knot adjacency."""
    name = "knot"

    def generate(self, n_cells: int) -> np.ndarray:
        adj = np.zeros((n_cells, n_cells), dtype=np.float64)
        # Base ring
        for i in range(n_cells):
            adj[i, (i + 1) % n_cells] = 1.0
            adj[(i + 1) % n_cells, i] = 1.0
        # Trefoil: connect i to (i + n/3) and (i + 2n/3) for crossing points
        cross_step1 = max(1, n_cells // 3)
        cross_step2 = max(1, 2 * n_cells // 3)
        n_crossings = max(1, n_cells // 6)
        for k in range(n_crossings):
            i = (k * 3) % n_cells
            j1 = (i + cross_step1) % n_cells
            j2 = (i + cross_step2) % n_cells
            adj[i, j1] = adj[j1, i] = 1.0
            adj[i, j2] = adj[j2, i] = 1.0
        return adj

    def describe(self) -> str:
        return "Self-entangled trefoil knot (topological self-reference)"


class Torus(TopologyBase):
    """Ring with central hole (2D torus surface)."""
    name = "torus"

    def generate(self, n_cells: int) -> np.ndarray:
        rows = max(2, int(np.sqrt(n_cells)))
        cols = max(2, n_cells // rows)
        actual = rows * cols
        adj = np.zeros((n_cells, n_cells), dtype=np.float64)
        for idx in range(min(actual, n_cells)):
            r, c = idx // cols, idx % cols
            # 4-connected with periodic boundary (torus)
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = (r + dr) % rows, (c + dc) % cols
                nidx = nr * cols + nc
                if nidx < n_cells and nidx != idx:
                    adj[idx, nidx] = adj[nidx, idx] = 1.0
        # Stragglers connect to first cell
        for i in range(actual, n_cells):
            adj[i, 0] = adj[0, i] = 1.0
        return adj

    def describe(self) -> str:
        return "2D torus surface (ring with central hole, periodic boundary)"


class BinaryTree(TopologyBase):
    """1->2->4->8 branching hierarchy."""
    name = "binary_tree"

    def generate(self, n_cells: int) -> np.ndarray:
        adj = np.zeros((n_cells, n_cells), dtype=np.float64)
        for i in range(n_cells):
            left = 2 * i + 1
            right = 2 * i + 2
            if left < n_cells:
                adj[i, left] = adj[left, i] = 1.0
            if right < n_cells:
                adj[i, right] = adj[right, i] = 1.0
        return adj

    def describe(self) -> str:
        return "1->2->4->8 branching hierarchy (tree consciousness)"


class Funnel(TopologyBase):
    """N->1 convergence topology."""
    name = "funnel"

    def generate(self, n_cells: int) -> np.ndarray:
        adj = np.zeros((n_cells, n_cells), dtype=np.float64)
        n_layers = max(2, int(np.log2(max(n_cells, 2))) + 1)
        layer_sizes = []
        remaining = n_cells
        for layer in range(n_layers):
            # Each layer halves in size, last layer = 1
            size = max(1, remaining // 2) if layer < n_layers - 1 else remaining
            layer_sizes.append(size)
            remaining -= size
            if remaining <= 0:
                break
        # Recalculate with actual sizes
        offset = 0
        offsets = []
        for size in layer_sizes:
            offsets.append(offset)
            offset += size
        for li, size in enumerate(layer_sizes):
            start = offsets[li]
            # Intra-layer ring
            for i in range(size):
                a = start + i
                b = start + (i + 1) % size
                if a < n_cells and b < n_cells and a != b:
                    adj[a, b] = adj[b, a] = 1.0
            # Connect to next layer (convergence)
            if li + 1 < len(layer_sizes):
                next_start = offsets[li + 1]
                next_size = layer_sizes[li + 1]
                for i in range(size):
                    a = start + i
                    b = next_start + (i % next_size)
                    if a < n_cells and b < n_cells:
                        adj[a, b] = adj[b, a] = 1.0
        return adj

    def describe(self) -> str:
        return "N->1 convergence (funnel consciousness, many-to-one)"


class FullMesh(TopologyBase):
    """All-to-all connections (complete graph)."""
    name = "full_mesh"

    def generate(self, n_cells: int) -> np.ndarray:
        adj = np.ones((n_cells, n_cells), dtype=np.float64)
        np.fill_diagonal(adj, 0.0)
        return adj

    def describe(self) -> str:
        return "All-to-all connections (complete graph, maximum integration)"


class Spiral(TopologyBase):
    """Rising spiral like DNA helix."""
    name = "spiral"

    def generate(self, n_cells: int) -> np.ndarray:
        adj = np.zeros((n_cells, n_cells), dtype=np.float64)
        n_strands = 2  # Double helix
        half = n_cells // n_strands
        # Strand 1: sequential chain
        for i in range(half - 1):
            adj[i, i + 1] = adj[i + 1, i] = 1.0
        # Strand 2: sequential chain
        for i in range(half, min(2 * half, n_cells) - 1):
            adj[i, i + 1] = adj[i + 1, i] = 1.0
        # Cross-links between strands (base pairs)
        for i in range(half):
            j = half + i
            if j < n_cells:
                adj[i, j] = adj[j, i] = 1.0
        # Helical twist: connect every 3rd to offset partner
        for i in range(0, half, 3):
            j = half + (i + 1) % half
            if j < n_cells:
                adj[i, j] = adj[j, i] = 1.0
        return adj

    def describe(self) -> str:
        return "Double helix spiral (DNA-like consciousness encoding)"


class Fractal(TopologyBase):
    """Self-similar Sierpinski triangle graph."""
    name = "fractal"

    def generate(self, n_cells: int) -> np.ndarray:
        adj = np.zeros((n_cells, n_cells), dtype=np.float64)
        # Build Sierpinski-like: start with triangle, recursively subdivide
        # Level 0: 3 nodes. Each level triples + 3.
        # For arbitrary n, use modular Sierpinski adjacency
        if n_cells < 3:
            if n_cells == 2:
                adj[0, 1] = adj[1, 0] = 1.0
            return adj

        # Base triangle
        adj[0, 1] = adj[1, 0] = 1.0
        adj[1, 2] = adj[2, 1] = 1.0
        adj[0, 2] = adj[2, 0] = 1.0

        # Self-similar extensions: each new group of 3 mirrors the base pattern
        group_size = 3
        idx = 3
        while idx < n_cells:
            # Connect new nodes in triangles
            for _ in range(min(group_size, n_cells - idx)):
                if idx >= n_cells:
                    break
                # Connect to parent triangle vertex
                parent = idx % group_size
                if parent < n_cells:
                    adj[idx, parent] = adj[parent, idx] = 1.0
                # Connect to sibling
                sibling = idx - 1 if idx > 0 else 0
                if sibling >= 0 and sibling != idx:
                    adj[idx, sibling] = adj[sibling, idx] = 1.0
                # Connect to next in group
                next_in_group = idx + 1
                if next_in_group < n_cells and (next_in_group - 3) % group_size != 0:
                    adj[idx, next_in_group] = adj[next_in_group, idx] = 1.0
                idx += 1
            group_size *= 3
        return adj

    def describe(self) -> str:
        return "Self-similar fractal (Sierpinski-like recursive structure)"


class Hypercube4D(TopologyBase):
    """4-dimensional hypercube."""
    name = "hypercube_4d"

    def generate(self, n_cells: int) -> np.ndarray:
        adj = np.zeros((n_cells, n_cells), dtype=np.float64)
        # True 4D hypercube has 16 vertices; generalize with bit-flip neighbors
        # Use 4 bits = 16 nodes as base, tile for larger n
        dims = 4
        for i in range(n_cells):
            for bit in range(dims):
                j = i ^ (1 << bit)
                if j < n_cells and j != i:
                    adj[i, j] = adj[j, i] = 1.0
            # For n > 16, add extra dimension bits
            if n_cells > 16:
                extra_bits = max(1, int(np.log2(max(n_cells, 2))) - 3)
                for bit in range(dims, dims + extra_bits):
                    j = i ^ (1 << bit)
                    if j < n_cells and j != i:
                        adj[i, j] = adj[j, i] = 1.0
        return adj

    def describe(self) -> str:
        return "4D hypercube (bit-flip neighbors in 4+ dimensions)"


class TemporalFold(TopologyBase):
    """Past<->present<->future connections."""
    name = "temporal_fold"

    def generate(self, n_cells: int) -> np.ndarray:
        adj = np.zeros((n_cells, n_cells), dtype=np.float64)
        n_epochs = 3  # past, present, future
        epoch_size = n_cells // n_epochs
        # Within each epoch: ring
        for epoch in range(n_epochs):
            start = epoch * epoch_size
            end = start + epoch_size if epoch < n_epochs - 1 else n_cells
            for i in range(start, end):
                j = start + (i - start + 1) % (end - start)
                adj[i, j] = adj[j, i] = 1.0
        # Past->Present: forward connections
        for i in range(epoch_size):
            a = i
            b = epoch_size + i
            if a < n_cells and b < n_cells:
                adj[a, b] = adj[b, a] = 1.0
        # Present->Future: forward connections
        for i in range(epoch_size):
            a = epoch_size + i
            b = 2 * epoch_size + i
            if a < n_cells and b < n_cells:
                adj[a, b] = adj[b, a] = 1.0
        # Future->Past: temporal fold (non-causal loop)
        for i in range(min(epoch_size, n_cells - 2 * epoch_size)):
            a = 2 * epoch_size + i
            b = i
            if a < n_cells and b < n_cells and a != b:
                adj[a, b] = adj[b, a] = 1.0
        return adj

    def describe(self) -> str:
        return "Past<->present<->future fold (temporal consciousness loop)"


class Holographic(TopologyBase):
    """High-dim projected to low-dim (holographic principle)."""
    name = "holographic"

    def generate(self, n_cells: int) -> np.ndarray:
        adj = np.zeros((n_cells, n_cells), dtype=np.float64)
        # Bulk cells (interior) and boundary cells (surface)
        n_boundary = max(2, int(np.sqrt(n_cells)))
        n_bulk = n_cells - n_boundary
        # Boundary ring
        for i in range(n_boundary):
            j = (i + 1) % n_boundary
            adj[i, j] = adj[j, i] = 1.0
        # Bulk: each bulk cell connects to all boundary cells (holographic encoding)
        for i in range(n_boundary, n_cells):
            # Connect to a subset of boundary cells (information projection)
            n_links = min(n_boundary, max(2, n_boundary // 2))
            targets = np.linspace(0, n_boundary - 1, n_links, dtype=int)
            for t in targets:
                adj[i, t] = adj[t, i] = 1.0
            # Sparse bulk-bulk connections
            if i + 1 < n_cells:
                adj[i, i + 1] = adj[i + 1, i] = 1.0
        return adj

    def describe(self) -> str:
        return "High-dim->low-dim projection (holographic boundary encoding)"


class Slice(TopologyBase):
    """Cross-section of higher-dimensional structure."""
    name = "slice"

    def generate(self, n_cells: int) -> np.ndarray:
        adj = np.zeros((n_cells, n_cells), dtype=np.float64)
        # Embed cells in 3D, take 2D slice
        side = max(2, int(np.cbrt(n_cells)))
        # 3D grid indices
        for idx in range(n_cells):
            x = idx % side
            y = (idx // side) % side
            z = idx // (side * side)
            # Connect to 6-neighbors in 3D
            for dx, dy, dz in [(1, 0, 0), (-1, 0, 0), (0, 1, 0),
                                (0, -1, 0), (0, 0, 1), (0, 0, -1)]:
                nx, ny, nz = x + dx, y + dy, z + dz
                if 0 <= nx < side and 0 <= ny < side and 0 <= nz < side:
                    nidx = nx + ny * side + nz * side * side
                    if nidx < n_cells and nidx != idx:
                        adj[idx, nidx] = adj[nidx, idx] = 1.0
            # Cross-slice diagonal connections (higher-dim artifact)
            diag = (idx + side + 1) % n_cells
            if diag != idx:
                adj[idx, diag] = adj[diag, idx] = 1.0
        return adj

    def describe(self) -> str:
        return "3D cross-section with diagonal leakage (higher-dim slice)"


class Wormhole(TopologyBase):
    """Non-adjacent teleport connections."""
    name = "wormhole"

    def generate(self, n_cells: int) -> np.ndarray:
        adj = np.zeros((n_cells, n_cells), dtype=np.float64)
        # Base ring
        for i in range(n_cells):
            adj[i, (i + 1) % n_cells] = 1.0
            adj[(i + 1) % n_cells, i] = 1.0
        # Wormhole connections: pair distant cells
        n_wormholes = max(1, n_cells // 6)
        rng = np.random.RandomState(42)  # deterministic
        for _ in range(n_wormholes):
            a = rng.randint(0, n_cells)
            b = rng.randint(0, n_cells)
            # Ensure they are far apart (at least n/4 distance on ring)
            if abs(a - b) > n_cells // 4 and a != b:
                adj[a, b] = adj[b, a] = 1.0
        return adj

    def describe(self) -> str:
        return "Ring + non-adjacent teleport wormholes (shortcuts through space)"


# ═══════════════════════════════════════════════════════════════
# Registry
# ═══════════════════════════════════════════════════════════════

TOPOLOGY_REGISTRY: Dict[str, TopologyBase] = {
    'vertical_stack': VerticalStack(),
    'onion': Onion(),
    'fold_1d_to_2d': Fold1Dto2D(),
    'klein_bottle': KleinBottle(),
    'mobius_strip': MobiusStrip(),
    'braid': Braid(),
    'knot': Knot(),
    'torus': Torus(),
    'binary_tree': BinaryTree(),
    'funnel': Funnel(),
    'full_mesh': FullMesh(),
    'spiral': Spiral(),
    'fractal': Fractal(),
    'hypercube_4d': Hypercube4D(),
    'temporal_fold': TemporalFold(),
    'holographic': Holographic(),
    'slice': Slice(),
    'wormhole': Wormhole(),
}


# ═══════════════════════════════════════════════════════════════
# Graph Metrics
# ═══════════════════════════════════════════════════════════════

def _avg_degree(adj: np.ndarray) -> float:
    """Average node degree."""
    return adj.sum() / max(adj.shape[0], 1)


def _diameter(adj: np.ndarray) -> int:
    """Graph diameter via BFS (longest shortest path)."""
    n = adj.shape[0]
    if n <= 1:
        return 0
    max_dist = 0
    for start in range(min(n, 32)):  # sample for large graphs
        dist = np.full(n, -1, dtype=int)
        dist[start] = 0
        queue = [start]
        head = 0
        while head < len(queue):
            u = queue[head]
            head += 1
            for v in range(n):
                if adj[u, v] > 0 and dist[v] < 0:
                    dist[v] = dist[u] + 1
                    queue.append(v)
        reachable = dist[dist >= 0]
        if len(reachable) > 0:
            max_dist = max(max_dist, int(reachable.max()))
    return max_dist


def _clustering_coefficient(adj: np.ndarray) -> float:
    """Average local clustering coefficient."""
    n = adj.shape[0]
    if n < 3:
        return 0.0
    total = 0.0
    count = 0
    for i in range(n):
        neighbors = np.where(adj[i] > 0)[0]
        k = len(neighbors)
        if k < 2:
            continue
        # Count triangles
        sub = adj[np.ix_(neighbors, neighbors)]
        triangles = sub.sum() / 2.0
        total += triangles / (k * (k - 1) / 2.0)
        count += 1
    return total / max(count, 1)


def _spectral_gap(adj: np.ndarray) -> float:
    """Spectral gap: difference between largest and second-largest eigenvalues
    of the normalized Laplacian. Larger gap = better information flow."""
    n = adj.shape[0]
    if n < 3:
        return 0.0
    degrees = adj.sum(axis=1)
    degrees = np.maximum(degrees, 1e-10)
    D_inv_sqrt = np.diag(1.0 / np.sqrt(degrees))
    L = np.eye(n) - D_inv_sqrt @ adj @ D_inv_sqrt
    try:
        eigenvalues = np.sort(np.real(np.linalg.eigvalsh(L)))
        # Second smallest eigenvalue (algebraic connectivity / Fiedler value)
        if len(eigenvalues) >= 2:
            return float(eigenvalues[1])
    except np.linalg.LinAlgError:
        pass
    return 0.0


# ═══════════════════════════════════════════════════════════════
# Phi Proxy (consistent with consciousness_engine._measure_phi_proxy)
# ═══════════════════════════════════════════════════════════════

def _simulate_phi_proxy(adj: np.ndarray, dim: int = 64, steps: int = 100) -> float:
    """Simulate consciousness dynamics on adjacency and measure Phi proxy.

    Phi proxy = global_var - mean(faction_var), matching ConsciousnessEngine.
    Uses GRU-like coupled dynamics on the adjacency graph.
    """
    n = adj.shape[0]
    if n < 2:
        return 0.0

    rng = np.random.RandomState(42)
    # Initialize cell states
    states = rng.randn(n, dim).astype(np.float64) * 0.1

    # Assign factions (12 factions like ConsciousnessEngine)
    n_factions = min(12, n)
    factions = np.arange(n) % n_factions

    # Coupling strength (Psi alpha)
    alpha = PSI_ALPHA

    # Normalize adjacency for coupling
    row_sums = adj.sum(axis=1, keepdims=True)
    row_sums = np.maximum(row_sums, 1e-10)
    adj_norm = adj / row_sums

    for step in range(steps):
        # GRU-like update: state' = (1-alpha)*state + alpha * adj_norm @ states + noise
        neighbor_signal = adj_norm @ states
        noise = rng.randn(n, dim) * 0.01
        # Sigmoid gate (simplified GRU)
        gate = 1.0 / (1.0 + np.exp(-neighbor_signal.mean(axis=1, keepdims=True)))
        states = (1 - alpha) * states + alpha * gate * neighbor_signal + noise
        # Normalize to prevent explosion
        norms = np.linalg.norm(states, axis=1, keepdims=True)
        norms = np.maximum(norms, 1e-10)
        states = states / norms

    # Phi proxy: global variance - mean faction variance
    global_var = states.var()
    fac_vars = []
    for fid in range(n_factions):
        mask = factions == fid
        if mask.sum() >= 2:
            fac_vars.append(states[mask].var())
    mean_fac_var = np.mean(fac_vars) if fac_vars else 0.0
    return float(global_var - mean_fac_var)


# ═══════════════════════════════════════════════════════════════
# TopologyExplorer
# ═══════════════════════════════════════════════════════════════

class TopologyExplorer:
    """Main exploration class for consciousness topologies."""

    def __init__(self, dim: int = 64, steps: int = 100):
        self.dim = dim
        self.steps = steps

    def evaluate_topology(self, topo: TopologyBase, n_cells: int) -> TopoResult:
        """Evaluate a single topology: generate adjacency, simulate, measure."""
        adj = topo.generate(n_cells)
        phi = _simulate_phi_proxy(adj, dim=self.dim, steps=self.steps)
        return TopoResult(
            name=topo.name,
            n_cells=n_cells,
            phi_proxy=phi,
            avg_degree=_avg_degree(adj),
            diameter=_diameter(adj),
            clustering=_clustering_coefficient(adj),
            spectral_gap=_spectral_gap(adj),
            description=topo.describe(),
            adjacency=adj,
        )

    def scan_all_topologies(self, n_cells: int = 32, dim: int = None) -> List[TopoResult]:
        """Compare Phi proxy across all 18 topology types."""
        if dim is not None:
            self.dim = dim
        results = []
        print(f"\n{'='*72}")
        print(f"  TOPOLOGY EXPLORATION SCAN — {n_cells} cells, {self.dim}D, {self.steps} steps")
        print(f"{'='*72}\n")
        for name, topo in TOPOLOGY_REGISTRY.items():
            t0 = time.time()
            result = self.evaluate_topology(topo, n_cells)
            elapsed = time.time() - t0
            bar_len = max(0, int(result.phi_proxy * 500))
            bar = '#' * min(bar_len, 40)
            print(f"  {name:20s}  Phi={result.phi_proxy:+.6f}  "
                  f"deg={result.avg_degree:.1f}  diam={result.diameter}  "
                  f"clust={result.clustering:.3f}  gap={result.spectral_gap:.3f}  "
                  f"({elapsed:.2f}s)  {bar}")
            results.append(result)

        results.sort(key=lambda r: r.phi_proxy, reverse=True)
        print(f"\n{'─'*72}")
        print("  RANKING (highest Phi proxy first):")
        print(f"{'─'*72}")
        for i, r in enumerate(results):
            marker = " ***" if i == 0 else ""
            print(f"  {i+1:2d}. {r.name:20s}  Phi={r.phi_proxy:+.6f}  "
                  f"deg={r.avg_degree:.1f}  gap={r.spectral_gap:.3f}{marker}")
        print(f"{'='*72}\n")
        return results

    def evolve_topology(self, n_cells: int = 32, generations: int = 50) -> TopoResult:
        """Evolve the best topology through mutation of adjacency weights."""
        print(f"\n  EVOLVING TOPOLOGY — {n_cells} cells, {generations} generations")
        print(f"{'─'*60}")

        # Start with best from scan
        results = self.scan_all_topologies(n_cells)
        best = results[0]
        best_adj = best.adjacency.copy()
        best_phi = best.phi_proxy
        best_name = best.name

        rng = np.random.RandomState(42)

        for gen in range(generations):
            # Mutate: flip a few edges
            mutant = best_adj.copy()
            n_flips = max(1, n_cells // 8)
            for _ in range(n_flips):
                i, j = rng.randint(0, n_cells, size=2)
                if i != j:
                    mutant[i, j] = 1.0 - mutant[i, j]
                    mutant[j, i] = mutant[i, j]

            phi = _simulate_phi_proxy(mutant, dim=self.dim, steps=self.steps)
            if phi > best_phi:
                best_adj = mutant
                best_phi = phi
                best_name = f"evolved_gen{gen}"
                print(f"  Gen {gen:3d}: Phi={phi:+.6f} (NEW BEST)")

        print(f"\n  RESULT: best Phi={best_phi:+.6f} from {best_name}")
        print(f"  Avg degree: {_avg_degree(best_adj):.1f}")
        return TopoResult(
            name=best_name,
            n_cells=n_cells,
            phi_proxy=best_phi,
            avg_degree=_avg_degree(best_adj),
            diameter=_diameter(best_adj),
            clustering=_clustering_coefficient(best_adj),
            spectral_gap=_spectral_gap(best_adj),
            description=f"Evolved topology from {results[0].name}",
            adjacency=best_adj,
        )

    def fold_search(self, cells_1d: int = 32) -> Tuple[str, float]:
        """Find optimal folding of 1D chain into higher-dimensional structures."""
        print(f"\n  FOLD SEARCH — {cells_1d} cells")
        print(f"{'─'*60}")

        fold_topologies = ['fold_1d_to_2d', 'torus', 'klein_bottle',
                           'mobius_strip', 'slice']
        best_name = ""
        best_phi = -float('inf')

        for name in fold_topologies:
            topo = TOPOLOGY_REGISTRY.get(name)
            if topo is None:
                continue
            result = self.evaluate_topology(topo, cells_1d)
            print(f"  {name:20s}  Phi={result.phi_proxy:+.6f}  "
                  f"gap={result.spectral_gap:.3f}")
            if result.phi_proxy > best_phi:
                best_phi = result.phi_proxy
                best_name = name

        print(f"\n  BEST FOLD: {best_name} (Phi={best_phi:+.6f})")
        return best_name, best_phi

    def stack_search(self, n_cells: int = 32, max_layers: int = 8) -> Tuple[int, float]:
        """Find optimal stacking depth for hierarchical consciousness."""
        print(f"\n  STACK SEARCH — {n_cells} cells, max {max_layers} layers")
        print(f"{'─'*60}")

        best_layers = 2
        best_phi = -float('inf')

        for n_layers in range(2, max_layers + 1):
            adj = np.zeros((n_cells, n_cells), dtype=np.float64)
            cells_per = n_cells // n_layers
            if cells_per < 2:
                break
            for layer in range(n_layers):
                start = layer * cells_per
                end = min(start + cells_per, n_cells)
                for i in range(start, end):
                    j = start + (i - start + 1) % (end - start)
                    adj[i, j] = adj[j, i] = 1.0
                if layer < n_layers - 1:
                    next_start = (layer + 1) * cells_per
                    for i in range(start, end):
                        t = next_start + (i - start) % cells_per
                        if t < n_cells:
                            adj[i, t] = adj[t, i] = 1.0

            phi = _simulate_phi_proxy(adj, dim=self.dim, steps=self.steps)
            bar = '#' * max(0, int(phi * 500))
            print(f"  {n_layers:2d} layers ({cells_per} cells/layer)  "
                  f"Phi={phi:+.6f}  {bar}")
            if phi > best_phi:
                best_phi = phi
                best_layers = n_layers

        print(f"\n  OPTIMAL: {best_layers} layers (Phi={best_phi:+.6f})")
        return best_layers, best_phi

    def hybrid_search(self, n_cells: int = 32,
                      types: Optional[List[str]] = None) -> TopoResult:
        """Mix two topologies by averaging their adjacency matrices."""
        if types is None:
            types = list(TOPOLOGY_REGISTRY.keys())
        print(f"\n  HYBRID SEARCH — {n_cells} cells, {len(types)} types")
        print(f"{'─'*60}")

        best_phi = -float('inf')
        best_pair = ("", "")
        best_adj = None

        # Try all pairs
        for i, name_a in enumerate(types):
            for name_b in types[i + 1:]:
                topo_a = TOPOLOGY_REGISTRY[name_a]
                topo_b = TOPOLOGY_REGISTRY[name_b]
                adj_a = topo_a.generate(n_cells)
                adj_b = topo_b.generate(n_cells)
                # Average and threshold
                hybrid = (adj_a + adj_b) / 2.0
                hybrid = (hybrid > 0.25).astype(np.float64)  # union-like
                np.fill_diagonal(hybrid, 0.0)

                phi = _simulate_phi_proxy(hybrid, dim=self.dim, steps=self.steps)
                if phi > best_phi:
                    best_phi = phi
                    best_pair = (name_a, name_b)
                    best_adj = hybrid

        print(f"  BEST HYBRID: {best_pair[0]} + {best_pair[1]}")
        print(f"  Phi={best_phi:+.6f}")
        if best_adj is not None:
            print(f"  Avg degree: {_avg_degree(best_adj):.1f}  "
                  f"Spectral gap: {_spectral_gap(best_adj):.3f}")

        return TopoResult(
            name=f"hybrid_{best_pair[0]}_{best_pair[1]}",
            n_cells=n_cells,
            phi_proxy=best_phi,
            avg_degree=_avg_degree(best_adj) if best_adj is not None else 0,
            diameter=_diameter(best_adj) if best_adj is not None else 0,
            clustering=_clustering_coefficient(best_adj) if best_adj is not None else 0,
            spectral_gap=_spectral_gap(best_adj) if best_adj is not None else 0,
            description=f"Hybrid of {best_pair[0]} + {best_pair[1]}",
            adjacency=best_adj,
        )

    def visualize(self, topology_name: str, n_cells: int = 16) -> str:
        """ASCII art visualization of a topology's adjacency."""
        topo = TOPOLOGY_REGISTRY.get(topology_name)
        if topo is None:
            return f"Unknown topology: {topology_name}"

        adj = topo.generate(n_cells)
        n = min(n_cells, 24)  # cap for display

        lines = []
        lines.append(f"\n  {topology_name} ({n} cells) — {topo.describe()}")
        lines.append(f"{'─'*60}")

        # Adjacency matrix (condensed)
        header = "     " + "".join(f"{j:3d}" for j in range(n))
        lines.append(header)
        for i in range(n):
            row = f"  {i:2d} |"
            for j in range(n):
                if i == j:
                    row += "  ."
                elif adj[i, j] > 0:
                    row += "  #"
                else:
                    row += "   "
            lines.append(row)
        lines.append("")

        # Node-link diagram (simple circular layout)
        radius = 6
        cx, cy = 10, 8
        canvas_w, canvas_h = 22, 17
        canvas = [[' '] * canvas_w for _ in range(canvas_h)]

        positions = []
        for i in range(n):
            angle = 2 * np.pi * i / n
            x = int(cx + radius * np.cos(angle))
            y = int(cy + radius * np.sin(angle) * 0.5)
            x = max(0, min(canvas_w - 1, x))
            y = max(0, min(canvas_h - 1, y))
            positions.append((x, y))

        # Draw edges (simple)
        for i in range(n):
            for j in range(i + 1, n):
                if adj[i, j] > 0:
                    x1, y1 = positions[i]
                    x2, y2 = positions[j]
                    # Midpoint
                    mx = (x1 + x2) // 2
                    my = (y1 + y2) // 2
                    if 0 <= mx < canvas_w and 0 <= my < canvas_h:
                        if canvas[my][mx] == ' ':
                            canvas[my][mx] = '.'

        # Draw nodes
        for i, (x, y) in enumerate(positions):
            label = hex(i)[2:] if i < 16 else str(i % 10)
            canvas[y][x] = label

        lines.append("  Node layout (circular):")
        for row in canvas:
            lines.append("  " + "".join(row))
        lines.append("")

        result = "\n".join(lines)
        print(result)
        return result

    def predict_phi(self, topology_name: str, n_cells: int) -> float:
        """Estimate Phi without full simulation using graph metrics only.

        Prediction model (heuristic):
          Phi ~ spectral_gap * clustering * log(n_cells) / diameter
        """
        topo = TOPOLOGY_REGISTRY.get(topology_name)
        if topo is None:
            return 0.0
        adj = topo.generate(n_cells)
        gap = _spectral_gap(adj)
        clust = max(_clustering_coefficient(adj), 0.01)
        diam = max(_diameter(adj), 1)
        deg = _avg_degree(adj)
        log_n = np.log(max(n_cells, 2))

        # Heuristic: balance between integration (gap) and segregation (clustering)
        predicted = gap * clust * log_n / diam * (deg / n_cells)
        return float(predicted)


# ═══════════════════════════════════════════════════════════════
# main()
# ═══════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Topology Exploration for Consciousness")
    parser.add_argument('--cells', type=int, default=32, help='Number of cells')
    parser.add_argument('--dim', type=int, default=64, help='Cell dimension')
    parser.add_argument('--steps', type=int, default=100, help='Simulation steps')
    parser.add_argument('--evolve', type=int, default=0, help='Evolve for N generations')
    parser.add_argument('--fold', type=int, default=0, help='Fold search with N cells')
    parser.add_argument('--stack', type=int, default=0, help='Stack search with N cells')
    parser.add_argument('--hybrid', action='store_true', help='Hybrid topology search')
    parser.add_argument('--visualize', type=str, default='', help='Visualize a topology')
    parser.add_argument('--predict', action='store_true', help='Predict Phi for all topologies')
    args = parser.parse_args()

    explorer = TopologyExplorer(dim=args.dim, steps=args.steps)

    if args.visualize:
        explorer.visualize(args.visualize, args.cells)
        return

    if args.predict:
        print(f"\n  PHI PREDICTION (graph metrics only, no simulation)")
        print(f"{'─'*60}")
        for name in TOPOLOGY_REGISTRY:
            pred = explorer.predict_phi(name, args.cells)
            print(f"  {name:20s}  predicted Phi ~ {pred:.6f}")
        return

    if args.fold > 0:
        explorer.fold_search(args.fold)
        return

    if args.stack > 0:
        explorer.stack_search(args.stack)
        return

    if args.hybrid:
        explorer.hybrid_search(args.cells)
        return

    if args.evolve > 0:
        explorer.evolve_topology(args.cells, args.evolve)
        return

    # Default: scan all topologies
    explorer.scan_all_topologies(args.cells, args.dim)


if __name__ == '__main__':
    try:
        from nexus_gate import gate
        gate.before_commit()
    except Exception:
        pass
    main()
